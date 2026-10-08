"""
उत्पाद राउटर - आइटम और फ़ोटो एंडपॉइंट

हर क्वेरी tenant_id से फ़िल्टर होती है - ARCHITECTURE RULE।
फ्रंटएंड कॉन्ट्रैक्ट: GET/POST/PUT/DELETE /products (+ photo फ़ील्ड)
"""

from fastapi import APIRouter, Depends, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id
from app.core.database import get_db
from app.core.exceptions import ProductNotFoundError
from app.core.images import compress_data_uri
from app.models.product import Product, ProductPhoto

router = APIRouter()


class ProductCreate(BaseModel):
    """नया उत्पाद बनाने की स्कीमा।"""

    name: str
    description: str | None = None
    price: float | None = None
    tags: str | None = None
    # फ़ोटो (data-URL या URL) - MVP में सीधे रिकॉर्ड में,
    # असली S3 स्टोरेज बाद में जुड़ेगा
    photo: str | None = None


class ProductUpdate(BaseModel):
    """उत्पाद अपडेट स्कीमा - सिर्फ़ भेजे गए फ़ील्ड बदलते हैं।"""

    name: str | None = None
    description: str | None = None
    price: float | None = None
    tags: str | None = None
    photo: str | None = None


class ProductResponse(BaseModel):
    """उत्पाद उत्तर स्कीमा।"""

    id: int
    name: str
    description: str | None
    price: float | None
    tags: str | None
    photo: str | None
    is_active: bool

    class Config:
        from_attributes = True


def _to_response(product: Product) -> ProductResponse:
    """Product मॉडल को उत्तर में बदलें (पहली फ़ोटो का URL साथ)।"""
    photo_url = None
    if product.photos:
        photo_url = product.photos[0].url
    return ProductResponse(
        id=product.id,
        name=product.name,
        description=product.description,
        price=product.price,
        tags=product.tags,
        photo=photo_url,
        is_active=product.is_active,
    )


async def _get_product(
    db: AsyncSession, tenant_id: int, product_id: int
) -> Product:
    """टेनेंट का उत्पाद लाएँ (tenant_id फ़िल्टर अनिवार्य)।"""
    result = await db.execute(
        select(Product).where(
            Product.id == product_id, Product.tenant_id == tenant_id
        )
    )
    product = result.scalar_one_or_none()
    if product is None:
        raise ProductNotFoundError(product_id)
    return product


@router.get("", response_model=list[ProductResponse])
async def list_products(
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """अपने सभी उत्पाद देखें (tenant_id से फ़िल्टर)।"""
    result = await db.execute(
        select(Product).where(
            Product.tenant_id == tenant_id, Product.is_active == True  # noqa: E712
        )
    )
    products = result.scalars().all()
    return [_to_response(p) for p in products]


@router.post("", response_model=ProductResponse)
async def create_product(
    payload: ProductCreate,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """नया उत्पाद जोड़ें। tenant_id स्वतः सेट होता है।"""
    data = payload.model_dump()
    photo_url = data.pop("photo", None)
    if photo_url:
        photo_url = compress_data_uri(photo_url)

    product = Product(
        tenant_id=tenant_id,  # ARCHITECTURE RULE: हर row में tenant_id
        **data,
    )
    db.add(product)
    await db.flush()

    # फ़ोटो (यदि भेजी) - ProductPhoto रिकॉर्ड में
    if photo_url:
        db.add(ProductPhoto(
            tenant_id=tenant_id,  # ARCHITECTURE RULE
            product_id=product.id,
            url=photo_url,
            photo_type="original",
            is_primary=True,
        ))
        await db.flush()

    await db.refresh(product)
    return _to_response(product)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """एक उत्पाद देखें (tenant_id से फ़िल्टर)।"""
    product = await _get_product(db, tenant_id, product_id)
    return _to_response(product)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    payload: ProductUpdate,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """उत्पाद अपडेट करें - सिर्फ़ भेजे गए फ़ील्ड।"""
    product = await _get_product(db, tenant_id, product_id)

    data = payload.model_dump(exclude_unset=True)
    photo_url = data.pop("photo", None)
    if photo_url is not None:
        photo_url = compress_data_uri(photo_url)
    for field, value in data.items():
        setattr(product, field, value)

    if photo_url is not None:
        # पुरानी प्राथमिक फ़ोटो हटाकर नई रखें (MVP सरलता)
        for old_photo in product.photos:
            await db.delete(old_photo)
        db.add(ProductPhoto(
            tenant_id=tenant_id,  # ARCHITECTURE RULE
            product_id=product.id,
            url=photo_url,
            photo_type="original",
            is_primary=True,
        ))

    await db.flush()
    await db.refresh(product)
    return _to_response(product)


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """उत्पाद हटाएँ - soft-delete (is_active=false, ARCHITECTURE RULE #7)।"""
    product = await _get_product(db, tenant_id, product_id)
    product.is_active = False
    await db.flush()


@router.post("/{product_id}/photos")
async def upload_product_photo(
    product_id: int,
    file: UploadFile = File(...),
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """
    उत्पाद की फ़ोटो अपलोड करें।

    MVP में: स्थानीय/S3 स्टोरेज पर सेव करके URL रिकॉर्ड में रखें।
    यह stub है - असली स्टोरेज बैकएंड बाद में जुड़ेगा।
    """
    # TODO: फ़ाइल स्टोरेज (S3) सेव करें और URL लौटाएँ
    photo = ProductPhoto(
        tenant_id=tenant_id,  # ARCHITECTURE RULE
        product_id=product_id,
        url=f"/uploads/{file.filename}",  # stub URL
        photo_type="original",
    )
    db.add(photo)
    await db.flush()
    return {"id": photo.id, "url": photo.url, "message": "फ़ोटो अपलोड हुई"}
