"""
उत्पाद सर्विस - आइटम/फ़ोटो लॉजिक
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ProductNotFoundError
from app.models.product import Product


async def get_product(db: AsyncSession, tenant_id: int, product_id: int) -> Product:
    """
    टेनेंट का उत्पाद लाएँ।

    नोट: क्वेरी में tenant_id अनिवार्य - दूसरे टेनेंट का
    उत्पाद कभी नहीं दिखेगा (multi-tenancy सुरक्षा)।
    """
    result = await db.execute(
        select(Product).where(
            Product.id == product_id, Product.tenant_id == tenant_id
        )
    )
    product = result.scalar_one_or_none()
    if product is None:
        raise ProductNotFoundError(product_id)
    return product
