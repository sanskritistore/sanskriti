"""
भुगतान सर्विस - UPI रिचार्ज लॉजिक

संरचना: Razorpay (या सीधे UPI collect) से order बनाना,
webhook पुष्टि से वॉलेट रिचार्ज करना।
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.payment import WalletTransaction


async def create_recharge_order(db: AsyncSession, tenant_id: int, amount: float) -> dict:
    """
    रिचार्ज order बनाएँ।

    MVP संरचना:
    - Razorpay order API कॉल (असली कार्यान्वयन में)
    - order_id सेव करके UPI लिंक/QR लौटाना
    """
    # TODO: असली Razorpay order बनाएँ (settings.RAZORPAY_KEY_ID से)
    gateway_order_id = f"order_{uuid.uuid4().hex[:12]}"

    # लेनदेन रिकॉर्ड - pending स्थिति में (tenant_id अनिवार्य)
    txn = WalletTransaction(
        tenant_id=tenant_id,
        transaction_type="recharge",
        amount=amount,
        gateway_order_id=gateway_order_id,
        status="pending",
        notes="UPI रिचार्ज - पुष्टि प्रतीक्षित",
    )
    db.add(txn)
    await db.flush()

    # UPI लिंक - सीधे UPI collect के लिए (MVP)
    upi_link = (
        f"upi://pay?pa={settings.UPI_VPA}&pn=Sanskriti&am={amount}"
        f"&tn=Recharge%20{gateway_order_id}"
    )

    return {
        "order_id": gateway_order_id,
        "amount": amount,
        "upi_link": upi_link,
        "status": "pending",
        "संदेश": "UPI ऐप में भुगतान करें, वॉलेट स्वतः रिचार्ज होगा",
    }


async def handle_payment_webhook(db: AsyncSession, payload: dict) -> dict:
    """
    भुगतान webhook संभालें।

    प्रवाह:
    1. सिग्नेचर सत्यापित करें (TODO - सुरक्षा अनिवार्य)
    2. order_id से pending लेनदेन खोजें
    3. सफलता पर: लेनदेन success + वॉलेट बैलेंस बढ़ाएँ
    """
    from sqlalchemy import select

    gateway_order_id = payload.get("order_id")
    payment_status = payload.get("status")  # "success" | "failed"

    if not gateway_order_id:
        return {"ok": False, "संदेश": "order_id नहीं मिला"}

    # pending लेनदेन खोजें
    result = await db.execute(
        select(WalletTransaction).where(
            WalletTransaction.gateway_order_id == gateway_order_id,
            WalletTransaction.status == "pending",
        )
    )
    txn = result.scalar_one_or_none()
    if txn is None:
        return {"ok": False, "संदेश": "लेनदेन नहीं मिला या पहले ही पूर्ण"}

    if payment_status != "success":
        txn.status = "failed"
        await db.flush()
        return {"ok": False, "संदेश": "भुगतान विफल"}

    # सफलता: वॉलेट बढ़ाएँ
    from app.modules.tenant.service import update_wallet_balance
    new_balance = await update_wallet_balance(db, txn.tenant_id, txn.amount)

    txn.status = "success"
    txn.balance_after = new_balance
    await db.flush()

    return {"ok": True, "नया_बैलेंस": new_balance}
