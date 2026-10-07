"""
रिपोर्ट राउटर - सरल रिपोर्ट एंडपॉइंट

MVP में सरल रिपोर्ट: कैंपेन का खर्च, रीच, क्लिक, लीड।
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id
from app.core.database import get_db
from app.models.campaign import Campaign
from app.modules.reports import service

router = APIRouter()


@router.get("/summary")
async def campaign_summary(
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """सभी कैंपेनों का सारांश - कुल खर्च, कुल लीड, सक्रिय कैंपेन।"""
    result = await db.execute(
        select(Campaign).where(Campaign.tenant_id == tenant_id)
    )
    campaigns = result.scalars().all()
    return service.build_summary(campaigns)


@router.get("/campaigns/{campaign_id}")
async def campaign_report(
    campaign_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """एक कैंपेन की विस्तृत रिपोर्ट (प्लेटफॉर्म से ताज़ा मेट्रिक्स)।"""
    return await service.build_campaign_report(db, tenant_id, campaign_id)
