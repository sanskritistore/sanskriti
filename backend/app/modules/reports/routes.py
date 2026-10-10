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


@router.get("/score-card")
async def score_card(
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """
    📊 असली Score Card — आज + 7 दिन: कितनों ने देखी, clicks, WhatsApp, खर्च।
    (10-10 user माँग: "सारा score card अपने software पर आए" — Meta के असली
    numbers, DB के ₹0 वाले अंदाज़े नहीं।)
    """
    return await service.build_score_card(db, tenant_id)


@router.get("/who-saw")
async def who_saw(
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """
    किसने ad देखी — user की माँग (08-10): "सटीक information कि कौन ad देख रहा है"।
    ईमानदार सच: Meta नाम/नंबर किसी को नहीं देता (privacy क़ानून) — पर उम्र,
    लड़का/लड़की, इलाका (region) और FB/Instagram बंटवारा ज़रूर देता है।
    """
    return await service.build_who_saw(db, tenant_id)
