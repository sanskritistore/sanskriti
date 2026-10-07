"""
टेनेंट सर्विस - व्यवसाय प्रोफ़ाइल लॉजिक

राउटर से अलग रखा गया है ताकि लॉजिक परीक्षणीय रहे।
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import TenantNotFoundError
from app.models.tenant import Tenant


async def get_tenant(db: AsyncSession, tenant_id: int) -> Tenant:
    """ID से टेनेंट लाएँ, न मिले तो त्रुटि।"""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise TenantNotFoundError(tenant_id)
    return tenant


async def update_wallet_balance(
    db: AsyncSession, tenant_id: int, delta: float
) -> float:
    """
    वॉलेट बैलेंस बदलें (delta positive = जमा, negative = कटौती)।

    नोट: असली कार्यान्वयन में row-level lock (SELECT ... FOR UPDATE)
    का उपयोग होना चाहिए ताकि समवर्ती कटौती से बचा जाए।
    """
    tenant = await get_tenant(db, tenant_id)
    tenant.wallet_balance += delta
    await db.flush()
    return tenant.wallet_balance
