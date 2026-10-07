"""
टेनेंट राउटर - व्यवसाय प्रोफ़ाइल एंडपॉइंट

सभी एंडपॉइंट टेनेंट-बाउंड हैं - get_current_tenant_id dependency अनिवार्य।
फ्रंटएंड Settings पेज इन क्षेत्रों का उपयोग करता है:
shop_name, owner_name, category, address
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id
from app.core.database import get_db
from app.models.tenant import Tenant, User

router = APIRouter()


class BusinessResponse(BaseModel):
    """व्यवसाय प्रोफ़ाइल उत्तर स्कीमा (फ्रंटएंड के फ़ील्ड नामों में)।"""

    id: int
    shop_name: str
    owner_name: str | None
    category: str | None
    address: str | None
    phone: str
    city: str | None
    language: str
    wallet_balance: float
    is_active: bool

    class Config:
        from_attributes = True


class BusinessUpdate(BaseModel):
    """व्यवसाय प्रोफ़ाइल अपडेट स्कीमा - सिर्फ़ भेजे गए फ़ील्ड बदलते हैं।"""

    shop_name: str | None = None
    owner_name: str | None = None
    category: str | None = None
    address: str | None = None
    city: str | None = None
    language: str | None = None


def _to_response(tenant: Tenant, owner_name: str | None) -> BusinessResponse:
    """Tenant मॉडल को फ्रंटएंड के फ़ील्ड नामों में बदलें।"""
    return BusinessResponse(
        id=tenant.id,
        shop_name=tenant.name,
        owner_name=owner_name,
        category=tenant.business_category,
        address=tenant.address,
        phone=tenant.phone,
        city=tenant.city,
        language=tenant.language,
        wallet_balance=tenant.wallet_balance,
        is_active=tenant.is_active,
    )


async def _get_tenant_and_owner(
    db: AsyncSession, tenant_id: int
) -> tuple[Tenant, str | None]:
    """टेनेंट + मालिक का नाम लाएँ।"""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        from app.core.exceptions import TenantNotFoundError
        raise TenantNotFoundError(tenant_id)

    # मालिक (owner role) का नाम - User टेबल में
    result = await db.execute(
        select(User).where(User.tenant_id == tenant_id, User.role == "owner")
    )
    owner = result.scalars().first()
    return tenant, (owner.full_name if owner else None)


@router.get("", response_model=BusinessResponse)
async def get_my_profile(
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """अपनी व्यवसाय प्रोफ़ाइल देखें।"""
    tenant, owner_name = await _get_tenant_and_owner(db, tenant_id)
    return _to_response(tenant, owner_name)


@router.put("", response_model=BusinessResponse)
async def update_my_profile(
    payload: BusinessUpdate,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """व्यवसाय प्रोफ़ाइल अपडेट करें - सिर्फ़ भेजे गए फ़ील्ड।"""
    tenant, _ = await _get_tenant_and_owner(db, tenant_id)

    # फ़ील्ड मैपिंग: फ्रंटएंड → मॉडल
    if payload.shop_name is not None:
        tenant.name = payload.shop_name
    if payload.category is not None:
        tenant.business_category = payload.category
    if payload.address is not None:
        tenant.address = payload.address
    if payload.city is not None:
        tenant.city = payload.city
    if payload.language is not None:
        tenant.language = payload.language

    # मालिक का नाम User टेबल में अपडेट करें
    if payload.owner_name is not None:
        result = await db.execute(
            select(User).where(User.tenant_id == tenant_id, User.role == "owner")
        )
        owner = result.scalars().first()
        if owner is not None:
            owner.full_name = payload.owner_name

    await db.flush()
    tenant, owner_name = await _get_tenant_and_owner(db, tenant_id)
    return _to_response(tenant, owner_name)
