"""
Public shop routes — customer की मिनी-दुकान।

10-10 user माँग (option B): "customer सारी photos tap करके बड़ी-बड़ी देखे
और WhatsApp से order करे" — ads में full-page photo नहीं खुलती, इसलिए
दुकान का public page बना रहे हैं।

⚠️ बिना login (public) — इसलिए सिर्फ वही fields लौटाओ जो customer के काम
की हैं। कभी भी wallet_balance, email, hashed_password जैसी चीज़ें मत भेजो!
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import SanskritiException
from app.models.product import Product
from app.models.tenant import Tenant

router = APIRouter()


@router.get("/{tenant_id}")
async def get_public_shop(tenant_id: int, db: AsyncSession = Depends(get_db)):
    """मिनी-दुकान का सारा सामान — बिना लॉगिन, public link के लिए।"""
    tenant = (
        await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    ).scalar_one_or_none()
    if not tenant or not tenant.is_active:
        raise SanskritiException(404, "दुकान नहीं मिली")

    products = (
        await db.execute(
            select(Product)
            .where(Product.tenant_id == tenant_id)
            .order_by(Product.id.desc())
        )
    ).scalars().all()

    items = []
    for p in products:
        # main photo सबसे पहले (album वाला क्रम)
        photos = sorted(p.photos, key=lambda ph: (not ph.is_primary, ph.id))
        items.append({
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "photos": [
                {"id": ph.id, "url": ph.url, "is_primary": ph.is_primary}
                for ph in photos
            ],
        })

    return {
        "name": tenant.name,
        "phone": tenant.phone,  # WhatsApp order इसी पर
        "city": tenant.city,
        "address": tenant.address,
        "google_rating": tenant.google_rating,
        "google_reviews_count": tenant.google_reviews_count,
        "products": items,
    }
