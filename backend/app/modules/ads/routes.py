"""
विज्ञापन राउटर - फ्रंटएंड के "ads" कॉन्ट्रैक्ट का सरल मुखौटा

फ्रंटएंड 3-चरण में ad बनाता है: product चुनें → बजट चुनें → प्रकाशित करें
इसलिए यह राउटर एक ही POST /ads में सब सँभालता है।

बाक़ी जटिल एंडपॉइंट (AI जनरेशन, लॉन्च, पॉज़) अपनी-अपनी ईंटों में रहते हैं:
- /ad-studio/*  → AI क्रिएटिव
- /campaigns/*  → कैंपेन लॉन्च/पॉज़ (2-लेयर पैटर्न)

2-लेयर कैंपेन पैटर्न यहाँ भी अछूता है: यह राउटर सिर्फ
Campaign (लेयर 1) बनाता/पढ़ता है - प्लेटफ़ॉर्म की कॉपी
(PlatformCampaign, लेयर 2) runner के ज़रिए बनती है।
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id
from app.core.database import get_db
from app.models.campaign import Campaign
from app.models.product import Product

router = APIRouter()


class AdCreate(BaseModel):
    """नया ad बनाने का अनुरोध (फ्रंटएंड 3-चरण का अंतिम रूप)।"""

    product_id: int
    budget: float  # प्रीसेट ₹100/250/500/1000
    status: str = "active"  # फ्रंटएंड "active" भेजता है


class AdResponse(BaseModel):
    """ad उत्तर स्कीमा (फ्रंटएंड के फ़ील्ड नामों में)।"""

    id: int
    product_id: int
    product_name: str | None
    budget: float
    status: str
    spent: float


def _to_response(campaign: Campaign, product_name: str | None) -> AdResponse:
    """Campaign (लेयर 1) को फ्रंटएंड के ad रूप में बदलें।"""
    return AdResponse(
        id=campaign.id,
        product_id=0,  # नीचे असली मान सेट होता है
        product_name=product_name,
        budget=campaign.budget_total,
        status=campaign.status,
        spent=campaign.budget_spent,
    )


@router.get("", response_model=list[AdResponse])
async def list_ads(
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """अपने सभी ads (कैंपेन) देखें - tenant_id से फ़िल्टर।
    हटाई गई (deleted) ads मुख्य list में नहीं दिखतीं - वे /records में रहती हैं।"""
    result = await db.execute(
        select(Campaign).where(
            Campaign.tenant_id == tenant_id,
            Campaign.status != "deleted",
        )
    )
    campaigns = result.scalars().all()

    # उत्पाद नाम एक ही क्वेरी में लाएँ (N+1 से बचने के लिए)
    product_ids = {c.id: None for c in campaigns}
    names: dict[int, str] = {}
    if campaigns:
        result = await db.execute(
            select(Product.id, Product.name).where(
                Product.tenant_id == tenant_id  # ARCHITECTURE RULE
            )
        )
        names = {pid: pname for pid, pname in result.all()}

    ads = []
    for c in campaigns:
        # MVP: कैंपेन का नाम ही उत्पाद संदर्भ रखता है "ad:<product_id>:<name>"
        # (Campaign मॉडल में product_id कॉलम नहीं - लेयर अलग रखने के लिए)
        product_id = None
        if c.name.startswith("ad:"):
            try:
                product_id = int(c.name.split(":")[1])
            except (IndexError, ValueError):
                product_id = None
        product_name = names.get(product_id) if product_id else None
        ad = _to_response(c, product_name)
        ad.product_id = product_id or 0
        ads.append(ad)
    return ads


@router.get("/records")
async def ad_records(
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """हटाई गई ads का पूरा रिकॉर्ड — delete के बाद भी इतिहास सुरक्षित।

    User demand (08-10): "hamne kitni ads chalai he, kis kis ki"
    हमेशा दिखनी चाहिए, भले list से हटा दी जाएँ।
    """
    result = await db.execute(
        select(Campaign).where(Campaign.tenant_id == tenant_id)  # ARCHITECTURE RULE
    )
    campaigns = result.scalars().all()

    # उत्पाद नाम (N+1 से बचने के लिए एक क्वेरी)
    result = await db.execute(
        select(Product.id, Product.name).where(Product.tenant_id == tenant_id)
    )
    names = {pid: pname for pid, pname in result.all()}

    records = []
    for c in campaigns:
        if c.status != "deleted":
            continue
        product_id = None
        if c.name.startswith("ad:"):
            try:
                product_id = int(c.name.split(":")[1])
            except (IndexError, ValueError):
                product_id = None
        records.append({
            "id": c.id,
            "name": c.name,
            "product_name": names.get(product_id) if product_id else None,
            "budget": c.budget_total,
            "budget_daily": c.budget_daily,
            "spent": c.budget_spent,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    return {
        "total_ads": len(campaigns),  # अब तक कुल बनाई गई ads (सब स्थितियाँ)
        "deleted_count": len(records),
        "records": records,
    }


@router.post("", response_model=AdResponse)
async def create_ad(
    payload: AdCreate,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """
    नया ad प्रकाशित करें।

    फ्रंटएंड के सरल 3-चरण कॉन्ट्रैक्ट को Campaign (लेयर 1) में बदलें।
    नाम में उत्पाद संदर्भ रखा जाता है: "ad:<product_id>:<product_name>"
    (MVP सरलता - बाद में उचित कॉलम/रिलेशन बनेगा)

    नोट: असली प्लेटफ़ॉर्म लॉन्च runner के /campaigns/{id}/launch से होता है।
    यहाँ कैंपेन "draft" बनती है (2-लेयर पैटर्न अछूता)।
    """
    # उत्पाद जाँचें (tenant_id फ़िल्टर - ARCHITECTURE RULE)
    result = await db.execute(
        select(Product).where(
            Product.id == payload.product_id, Product.tenant_id == tenant_id
        )
    )
    product = result.scalar_one_or_none()
    if product is None:
        from app.core.exceptions import ProductNotFoundError
        raise ProductNotFoundError(payload.product_id)

    # कैंपेन नाम में उत्पाद संदर्भ (MVP एन्कोडिंग)
    campaign_name = f"ad:{product.id}:{product.name}"

    campaign = Campaign(
        tenant_id=tenant_id,  # ARCHITECTURE RULE: हर row में tenant_id
        name=campaign_name,
        objective="leads",  # MVP: WhatsApp लीड डिफ़ॉल्ट
        budget_total=payload.budget,
        budget_daily=payload.budget,  # MVP: एक दिन का प्रीसेट बजट
        status="draft",  # लॉन्च runner के ज़रिए होगा
    )
    db.add(campaign)
    await db.flush()

    ad = _to_response(campaign, product.name)
    ad.product_id = product.id
    return ad


@router.get("/{ad_id}", response_model=AdResponse)
async def get_ad(
    ad_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """एक ad (कैंपेन) देखें - tenant_id से फ़िल्टर।"""
    result = await db.execute(
        select(Campaign).where(Campaign.id == ad_id, Campaign.tenant_id == tenant_id)
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        from app.core.exceptions import CampaignNotFoundError
        raise CampaignNotFoundError(ad_id)
    ad = _to_response(campaign, None)
    ad.product_id = 0
    return ad


@router.put("/{ad_id}", response_model=AdResponse)
async def update_ad(
    ad_id: int,
    payload: AdCreate,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """ad अपडेट करें - MVP में सिर्फ़ बजट बदलना समर्थित।"""
    result = await db.execute(
        select(Campaign).where(Campaign.id == ad_id, Campaign.tenant_id == tenant_id)
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        from app.core.exceptions import CampaignNotFoundError
        raise CampaignNotFoundError(ad_id)
    campaign.budget_total = payload.budget
    await db.flush()
    ad = _to_response(campaign, None)
    ad.product_id = payload.product_id
    return ad


@router.delete("/{ad_id}", status_code=204)
async def delete_ad(
    ad_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """ad हटाएँ - soft-delete (स्थिति "deleted")।

    - record DB में सुरक्षित रहता है (GET /ads/records में दिखता है)
    - चालू (active) ad हटाई नहीं जा सकती — पहले रोकनी होगी
    """
    from fastapi import HTTPException

    result = await db.execute(
        select(Campaign).where(Campaign.id == ad_id, Campaign.tenant_id == tenant_id)
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        from app.core.exceptions import CampaignNotFoundError
        raise CampaignNotFoundError(ad_id)
    if campaign.status == "active":
        raise HTTPException(
            status_code=400,
            detail="चालू ad नहीं हट सकती — पहले उसे रोकें (pause) करें।",
        )
    campaign.status = "deleted"
    await db.flush()
