"""
विज्ञापन स्टूडियो राउटर - AI विज्ञापन निर्माण एंडपॉइंट

प्रवाह:
1. टेनेंट उत्पाद चुनता है
2. AI (OpenAI) से हिंदी/क्षेत्रीय भाषा में विज्ञापन टेक्स्ट बनता है
3. टेनेंट संशोधन/स्वीकृति करता है
4. स्वीकृत क्रिएटिव कैंपेन (runner) में उपयोग होता है
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id
from app.core.database import get_db
from app.modules.ad_studio import service

router = APIRouter()


class AdGenerateRequest(BaseModel):
    """AI विज्ञापन जनरेशन अनुरोध।"""

    product_id: int
    language: str = "hi"  # डिफ़ॉल्ट हिंदी
    tone: str = "friendly"  # विज्ञापन की शैली
    # अतिरिक्त निर्देश - जैसे "दिवाली सेल पर ज़ोर दें"
    extra_instructions: str | None = None


class AdCreativeResponse(BaseModel):
    """AI विज्ञापन उत्तर स्कीमा।"""

    id: int
    product_id: int | None
    headline: str | None
    primary_text: str | None
    description: str | None
    image_url: str | None
    language: str
    is_approved: bool

    class Config:
        from_attributes = True


@router.post("/generate", response_model=AdCreativeResponse)
async def generate_ad(
    payload: AdGenerateRequest,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """AI से विज्ञापन बनाएँ (हिंदी/क्षेत्रीय भाषा में)।"""
    creative = await service.generate_ad_creative(
        db=db,
        tenant_id=tenant_id,
        product_id=payload.product_id,
        language=payload.language,
        tone=payload.tone,
        extra_instructions=payload.extra_instructions,
    )
    return creative


@router.post("/{creative_id}/approve", response_model=AdCreativeResponse)
async def approve_ad(
    creative_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """विज्ञापन स्वीकार करें (कैंपेन लॉन्च से पहले अनिवार्य)।"""
    creative = await service.approve_creative(db, tenant_id, creative_id)
    return creative
