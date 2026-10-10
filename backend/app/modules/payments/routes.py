"""
भुगतान राउटर - UPI रिचार्ज एंडपॉइंट

प्रवाह (UPI रिचार्ज):
1. टेनेंट रिचार्ज राशि चुनता है → order बनता है
2. UPI से भुगतान होता है (Razorpay/सीधे UPI)
3. webhook से पुष्टि → वॉलेट में पैसे जुड़ते हैं
"""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id
from app.core.database import get_db
from app.modules.payments import service

router = APIRouter()


class RechargeRequest(BaseModel):
    """वॉलेट रिचार्ज अनुरोध।"""

    amount: float  # ₹ में


@router.post("/recharge")
async def create_recharge(
    payload: RechargeRequest,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """
    रिचार्ज order बनाएँ - UPI लिंक/QR लौटाता है।

    टेनेंट इस लिंक से UPI ऐप में भुगतान करता है,
    फिर webhook से पुष्टि आती है।
    """
    order = await service.create_recharge_order(db, tenant_id, payload.amount)
    return order


@router.post("/webhook")
async def payment_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    भुगतान webhook - गेटवे से पुष्टि आती है।

    पुष्टि होने पर वॉलेट में राशि जुड़ती है।
    नोट: webhook सिग्नेचर सत्यापन अनिवार्य (सुरक्षा)।
    """
    payload = await request.json()
    result = await service.handle_payment_webhook(db, payload)
    return result

@router.post("/dev-credit")
async def dev_credit(
    payload: RechargeRequest,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """
    \u0938\u093f\u0930\u094d\u092b\u093c DEVELOPMENT \u092e\u0947\u0902: \u0935\u0949\u0932\u0947\u091f \u092e\u0947\u0902 \u0924\u0941\u0930\u0902\u0924 \u092a\u0948\u0938\u093e \u0921\u093e\u0932\u0947\u0902 (testing \u0915\u0947 \u0932\u093f\u090f)\u0964
    production \u092e\u0947\u0902 \u092f\u0939 \u0930\u093e\u0938\u094d\u0924\u093e \u092c\u0902\u0926 \u0930\u0939\u0924\u093e \u0939\u0948\u0964
    """
    from fastapi import HTTPException

    from app.core.config import settings
    from app.modules.tenant.service import get_tenant
    from app.models.payment import WalletTransaction

    if settings.APP_ENV != "development":
        raise HTTPException(status_code=404, detail="Not found")

    tenant = await get_tenant(db, tenant_id)
    tenant.wallet_balance += payload.amount
    db.add(WalletTransaction(
        tenant_id=tenant_id,
        transaction_type="recharge",
        amount=payload.amount,
        balance_after=tenant.wallet_balance,
        status="success",
        notes="DEV \u091f\u0947\u0938\u094d\u091f \u0930\u093f\u091a\u093e\u0930\u094d\u091c",
    ))
    await db.flush()
    return {"ok": True, "wallet_balance": tenant.wallet_balance,
            "\u0938\u0902\u0926\u0947\u0936": f"DEV: \u20b9{payload.amount} \u091c\u092e\u093e \u0939\u0941\u090f"}


class AdminCreditRequest(BaseModel):
    """एडमिन वॉलेट क्रेडिट अनुरोध — tenant_id + राशि + नोट।"""

    tenant_id: int
    amount: float  # ₹ में
    notes: str = "एडमिन क्रेडिट (ऑफ़लाइन भुगतान)"


@router.post("/admin-credit")
async def admin_credit(
    payload: AdminCreditRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    एडमिन wallet credit — X-Admin-Key (JWT_SECRET_KEY) से सुरक्षित।

    असली काम: ग्राहक ने नकद/UPI से पैसे दिए → उसका wallet भरो ताकि
    ad launch हो सके। (10-10: launch 402 पर अटका था — wallet खाली।)
    """
    from fastapi import HTTPException

    from app.core.config import settings
    from app.models.payment import WalletTransaction
    from app.models.tenant import Tenant

    if request.headers.get("X-Admin-Key") != settings.JWT_SECRET_KEY:
        raise HTTPException(status_code=403, detail="गलत एडमिन कुंजी")

    tenant = await db.get(Tenant, payload.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant नहीं मिला")

    tenant.wallet_balance += payload.amount
    db.add(WalletTransaction(
        tenant_id=payload.tenant_id,
        transaction_type="recharge",
        amount=payload.amount,
        balance_after=tenant.wallet_balance,
        status="success",
        notes=payload.notes,
    ))
    await db.flush()
    return {"ok": True, "wallet_balance": tenant.wallet_balance,
            "संदेश": f"₹{payload.amount} जमा हुए (admin)"}

