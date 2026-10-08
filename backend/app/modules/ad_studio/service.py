"""
विज्ञापन स्टूडियो सर्विस - AI विज्ञापन निर्माण लॉजिक

OpenAI API से भारतीय भाषाओं में विज्ञापन टेक्स्ट बनाता है।
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ProductNotFoundError
from app.models.campaign import AdCreative
from app.models.product import Product


async def get_creative(
    db: AsyncSession, tenant_id: int, creative_id: int
) -> AdCreative:
    """टेनेंट का क्रिएटिव लाएँ (tenant_id से फ़िल्टर)।"""
    result = await db.execute(
        select(AdCreative).where(
            AdCreative.id == creative_id, AdCreative.tenant_id == tenant_id
        )
    )
    creative = result.scalar_one_or_none()
    if creative is None:
        from app.core.exceptions import SanskritiException
        from fastapi import status
        raise SanskritiException(status.HTTP_404_NOT_FOUND, "विज्ञापन नहीं मिला")
    return creative


async def generate_ad_creative(
    db: AsyncSession,
    tenant_id: int,
    product_id: int,
    language: str = "hi",
    tone: str = "friendly",
    extra_instructions: str | None = None,
) -> AdCreative:
    """
    AI से विज्ञापन क्रिएटिव बनाएँ।

    प्रवाह:
    1. उत्पाद का विवरण लें (tenant_id से फ़िल्टर)
    2. AI को प्रॉम्प्ट भेजें - भारतीय संदर्भ में, अनुरोधित भाषा में
    3. उत्तर सेव करके लौटाएँ (is_approved = False)
    """
    # उत्पाद लें (multi-tenant सुरक्षा)
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id)
    )
    product = result.scalar_one_or_none()
    if product is None:
        raise ProductNotFoundError(product_id)

    # AI कॉल (MVP stub - असली OpenAI कॉल यहाँ जाएगा)
    headline, primary_text, description = await _call_ai_for_ad(
        product=product, language=language, tone=tone,
        extra_instructions=extra_instructions,
    )

    # क्रिएटिव सेव करें - tenant_id अनिवार्य (ARCHITECTURE RULE)
    creative = AdCreative(
        tenant_id=tenant_id,
        product_id=product.id,
        headline=headline,
        primary_text=primary_text,
        description=description,
        language=language,
        is_approved=False,  # टेनेंट की स्वीकृति बाद में
        ai_model=settings.AI_MODEL,
    )
    db.add(creative)
    await db.flush()
    return creative


async def _call_ai_for_ad(
    product, language: str, tone: str, extra_instructions: str | None
) -> tuple[str, str, str]:
    """
    AI से विज्ञापन टेक्स्ट बनाएँ।

    TODO (MVP के अगले चरण में):
    - OpenAI chat completion कॉल (settings.OPENAI_API_KEY से)
    - प्रॉम्प्ट में शामिल करें: उत्पाद विवरण, व्यवसाय श्रेणी, भाषा, शैली
    - उत्तर पार्स करके headline / primary_text / description निकालें
    """
    # स्थानीय stub - असली AI कॉल बाद में
    headline = f"{product.name} - विशेष ऑफ़र!"
    primary_text = (
        f"{product.name} अब उपलब्ध! "
        f"{product.description or 'सर्वोत्तम गुणवत्ता, सर्वोत्तम मूल्य।'}"
    )
    description = product.description or "आज ही ऑर्डर करें।"
    return headline, primary_text, description


async def approve_creative(
    db: AsyncSession, tenant_id: int, creative_id: int
) -> AdCreative:
    """क्रिएटिव स्वीकृत करें - इसके बाद कैंपेन लॉन्च संभव है।"""
    creative = await get_creative(db, tenant_id, creative_id)
    creative.is_approved = True
    await db.flush()
    return creative


async def update_creative(
    db: AsyncSession,
    tenant_id: int,
    creative_id: int,
    headline: str | None,
    primary_text: str | None,
    description: str | None,
) -> AdCreative:
    """
    क्रिएटिव का text बदलें — AI लिखे, दुकानदार सुधारे (08-10)।
    जो field None है वह ज्यों का त्यों रहता है।
    """
    creative = await get_creative(db, tenant_id, creative_id)
    if headline is not None:
        creative.headline = headline
    if primary_text is not None:
        creative.primary_text = primary_text
    if description is not None:
        creative.description = description
    await db.flush()
    return creative
