"""
रनर राउटर - कैंपेन लॉन्च और प्रबंधन एंडपॉइंट

कैंपेन लॉन्च का प्रवाह (2-लेयर पैटर्न):
1. टेनेंट कैंपेन बनाता है (हमारी कैंपेन - लेयर 1)
2. वॉलेट से बजट कटता है (budget management)
3. एडाप्टर के जरिए प्लेटफॉर्म पर कैंपेन बनती है (लेयर 2 - PlatformCampaign)
4. स्टेटस/खर्च समय-समय पर sync होता है
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id
from app.core.database import get_db
from app.models.campaign import Campaign
from app.modules.runner import service

router = APIRouter()


class CampaignCreate(BaseModel):
    """नई कैंपेन बनाने की स्कीमा।"""

    name: str
    objective: str = "leads"  # leads | traffic | awareness | sales
    ad_creative_id: int
    budget_total: float
    budget_daily: float
    start_date: datetime | None = None
    end_date: datetime | None = None
    targeting: str | None = None
    # किस प्लेटफॉर्म पर लॉन्च करना है - MVP में "meta"
    platforms: list[str] = ["meta"]


class CampaignResponse(BaseModel):
    """कैंपेन उत्तर स्कीमा।"""

    id: int
    name: str
    objective: str
    status: str
    budget_total: float
    budget_daily: float
    budget_spent: float
    start_date: datetime | None
    end_date: datetime | None

    class Config:
        from_attributes = True


@router.get("", response_model=list[CampaignResponse])
async def list_campaigns(
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """अपनी सभी कैंपेन देखें — हटाई गई (deleted) छिपी रहती हैं, /records में मिलती हैं।"""
    result = await db.execute(
        select(Campaign).where(
            Campaign.tenant_id == tenant_id,
            Campaign.status != "deleted",
        )
    )
    return result.scalars().all()


@router.get("/records")
async def campaign_records(
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """हटाई गई ads का पूरा रिकॉर्ड — "kitni ads chalai, kis kis ki" हमेशा सुरक्षित।"""
    result = await db.execute(
        select(Campaign).where(Campaign.tenant_id == tenant_id)  # ARCHITECTURE RULE
    )
    campaigns = result.scalars().all()

    records = [
        {
            "id": c.id,
            "name": c.name,
            "objective": c.objective,
            "budget": c.budget_total,
            "budget_daily": c.budget_daily,
            "spent": c.budget_spent,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in campaigns
        if c.status == "deleted"
    ]
    return {
        "total_ads": len(campaigns),  # अब तक कुल बनाई गई ads (सब स्थितियाँ)
        "deleted_count": len(records),
        "records": records,
    }


@router.post("", response_model=CampaignResponse)
async def create_campaign(
    payload: CampaignCreate,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """नई कैंपेन बनाएँ (अभी लॉन्च नहीं - पहले draft)।"""
    campaign = await service.create_campaign(db, tenant_id, payload)
    return campaign


@router.post("/{campaign_id}/launch", response_model=CampaignResponse)
async def launch_campaign(
    campaign_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """
    कैंपेन लॉन्च करें।

    यहाँ 2-लेयर पैटर्न चलता है:
    1. वॉलेट से बजट कटता है
    2. एडाप्टर के जरिए प्लेटफॉर्म कैंपेन बनती है (PlatformCampaign row)
    """
    campaign = await service.launch_campaign(db, tenant_id, campaign_id)
    return campaign


@router.post("/{campaign_id}/pause", response_model=CampaignResponse)
async def pause_campaign(
    campaign_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """कैंपेन रोकें (प्लेटफॉर्म पर भी PAUSE)।"""
    campaign = await service.pause_campaign(db, tenant_id, campaign_id)
    return campaign


@router.post("/{campaign_id}/resume", response_model=CampaignResponse)
async def resume_campaign(
    campaign_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """रुकी कैंपेन फिर चालू करें (प्लेटफॉर्म पर भी ACTIVE)।"""
    campaign = await service.resume_campaign(db, tenant_id, campaign_id)
    return campaign


@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """कचरा draft कैंपेन मिटाएँ — सिर्फ़ draft मिटेगी (08-10 user माँग)।"""
    await service.delete_campaign(db, tenant_id, campaign_id)
    return {"ok": True, "deleted": campaign_id}
