"""
उत्पाद राउटर - आइटम और फ़ोटो एंडपॉइंट

हर क्वेरी tenant_id से फ़िल्टर होती है - ARCHITECTURE RULE।
फ्रंटएंड कॉन्ट्रैक्ट: GET/POST/PUT/DELETE /products (+ photo फ़ील्ड)
"""

from fastapi import APIRouter, Depends
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
    # 📸 Album (10-10 user माँग): main photo के अलावा छोटी photos भी
    # एक साथ — add flow से (अधिकतम 6 extra = कुल 7)
    extra_photos: list[str] | None = None


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


class ProductPhotoResponse(BaseModel):
    """एक फ़ोटो का उत्तर (photo album के लिए, 10-10 user माँग)।"""

    id: int
    url: str
    is_primary: bool

    class Config:
        from_attributes = True


class ProductDetailResponse(ProductResponse):
    """उत्पाद की पूरी जानकारी + सारी photos (main पहले)।"""

    photos: list[ProductPhotoResponse] = []


def _to_response(product: Product) -> ProductResponse:
    """Product मॉडल को उत्तर में बदलें (पहली फ़ोटो का URL साथ)।"""
    photo_url = None
    if product.photos:
        # main (is_primary) photo दिखाएँ, नहीं तो पहली
        primary = next((p for p in product.photos if p.is_primary), None)
        photo_url = (primary or product.photos[0]).url
    return ProductResponse(
        id=product.id,
        name=product.name,
        description=product.description,
        price=product.price,
        tags=product.tags,
        photo=photo_url,
        is_active=product.is_active,
    )


def _to_detail_response(product: Product) -> ProductDetailResponse:
    """उत्पाद + photos (main photo सबसे पहले)।"""
    base = _to_response(product).model_dump()
    photos = sorted(product.photos or [], key=lambda p: (not p.is_primary, p.id))
    base["photos"] = [
        ProductPhotoResponse(id=p.id, url=p.url, is_primary=p.is_primary)
        for p in photos
    ]
    return ProductDetailResponse(**base)


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
    extra_photos = data.pop("extra_photos", None) or []  # 💥 Product() में न जाए!
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

    # 📸 extra photos (album की छोटी photos) — main के बाद, क्रम में
    for extra in extra_photos[:6]:
        if not extra:
            continue
        db.add(ProductPhoto(
            tenant_id=tenant_id,  # ARCHITECTURE RULE
            product_id=product.id,
            url=compress_data_uri(extra),
            photo_type="original",
            is_primary=False,
        ))
    if extra_photos:
        await db.flush()

    await db.refresh(product)
    return _to_response(product)


@router.get("/{product_id}", response_model=ProductDetailResponse)
async def get_product(
    product_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """एक उत्पाद देखें — सारी photos समेत (photo album)।"""
    product = await _get_product(db, tenant_id, product_id)
    return _to_detail_response(product)


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
        # 📸 Album (10-10 user माँग): नई photo MAIN बनाएँ, पुरानी सब
        # album में बनी रहें (उनका is_primary हटाएँ) — पहले सब हटती थीं!
        for old_photo in product.photos:
            old_photo.is_primary = False
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


# 📸 Photo Album (10-10 user माँग): एक product की अधिकतम photos
MAX_PRODUCT_PHOTOS = 7


class PhotoAddRequest(BaseModel):
    """नई photo जोड़ने की स्कीमा (base64 data-URL)।"""

    photo: str  # data:image/...;base64,...


@router.post("/{product_id}/photos", response_model=ProductDetailResponse)
async def add_product_photo(
    product_id: int,
    payload: PhotoAddRequest,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """
    📸 Album में नई photo जोड़ें (अधिकतम 7)।

    base64 data-URL → compress → ProductPhoto (is_primary=False;
    main photo वही रहती है जो पहले थी — बदलनी हो तो /primary)।
    """
    product = await _get_product(db, tenant_id, product_id)
    if len(product.photos or []) >= MAX_PRODUCT_PHOTOS:
        from app.core.exceptions import SanskritiException
        raise SanskritiException(
            400,
            f"एक product में अधिकतम {MAX_PRODUCT_PHOTOS} photos हो सकती हैं"
        )

    url = compress_data_uri(payload.photo)
    db.add(ProductPhoto(
        tenant_id=tenant_id,  # ARCHITECTURE RULE
        product_id=product.id,
        url=url,
        photo_type="original",
        is_primary=not product.photos,  # पहली photo तो main
    ))
    await db.flush()
    await db.refresh(product)
    return _to_detail_response(product)


@router.put("/{product_id}/photos/{photo_id}/primary", response_model=ProductDetailResponse)
async def set_primary_photo(
    product_id: int,
    photo_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """⭐ किसी photo को MAIN बनाएँ — वही ads में दिखेगी।"""
    product = await _get_product(db, tenant_id, product_id)
    target = next((p for p in product.photos if p.id == photo_id), None)
    if target is None:
        raise ProductNotFoundError(product_id)
    for p in product.photos:
        p.is_primary = p.id == photo_id
    await db.flush()
    await db.refresh(product)
    return _to_detail_response(product)


@router.delete("/{product_id}/photos/{photo_id}", response_model=ProductDetailResponse)
async def delete_product_photo(
    product_id: int,
    photo_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Album से photo हटाएँ। Main हटे तो अगली photo खुद main बने।"""
    product = await _get_product(db, tenant_id, product_id)
    target = next((p for p in product.photos if p.id == photo_id), None)
    if target is None:
        raise ProductNotFoundError(product_id)
    was_primary = target.is_primary
    await db.delete(target)
    await db.flush()
    await db.refresh(product)
    if was_primary and product.photos:
        product.photos[0].is_primary = True
        await db.flush()
        await db.refresh(product)
    return _to_detail_response(product)
