"""
रिपोर्ट सर्विस - सरल रिपोर्टिंग लॉजिक

MVP रिपोर्ट: जो डेटा हमारे पास है उसे जोड़कर सरल सारांश बनाएँ।
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CampaignNotFoundError
from app.models.campaign import Campaign


def build_summary(campaigns: list[Campaign]) -> dict:
    """सभी कैंपेनों का सारांश बनाएँ।"""
    total_budget = sum(c.budget_total for c in campaigns)
    total_spent = sum(c.budget_spent for c in campaigns)
    active = [c for c in campaigns if c.status == "active"]

    return {
        # फ्रंटएंड की भाषा: "₹X ख़र्च → Y ग्राहक"
        "total_spent": total_spent,
        "total_customers": 0,  # लीड गिनती WhatsApp कनेक्टर जुड़ने पर आएगी
        "total_budget": total_budget,
        "active_campaigns": len(active),
        "total_campaigns": len(campaigns),
        # हिंदी कुंजियाँ (पुराने उत्तर के साथ संगत)
        "कुल_कैंपेन": len(campaigns),
        "सक्रिय_कैंपेन": len(active),
        "कुल_बजट": total_budget,
        "कुल_खर्च": total_spent,
        "शेष_बजट": total_budget - total_spent,
        "campaigns": [
            {
                "id": c.id,
                "name": c.name,
                "status": c.status,
                "budget_total": c.budget_total,
                "budget_spent": c.budget_spent,
            }
            for c in campaigns
        ],
    }


async def build_campaign_report(
    db: AsyncSession, tenant_id: int, campaign_id: int
) -> dict:
    """
    एक कैंपेन की विस्तृत रिपोर्ट।

    प्रत्येक प्लेटफॉर्म कैंपेन (लेयर 2) से एडाप्टर के जरिए
    ताज़ा मेट्रिक्स लाता है।
    """
    from sqlalchemy import select

    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id, Campaign.tenant_id == tenant_id
        )
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise CampaignNotFoundError(campaign_id)

    report = {
        "campaign_id": campaign.id,
        "name": campaign.name,
        "objective": campaign.objective,
        "status": campaign.status,
        "budget_total": campaign.budget_total,
        "budget_spent": campaign.budget_spent,
        "platforms": [],
    }

    # प्रत्येक प्लेटफॉर्म से मेट्रिक्स लाएँ
    from app.modules.adapters import get_adapter
    for pc in campaign.platform_campaigns:
        adapter = get_adapter(pc.platform)
        metrics = await adapter.get_campaign_metrics(pc.platform_campaign_id)
        report["platforms"].append({
            "platform": pc.platform,
            "platform_campaign_id": pc.platform_campaign_id,
            "status": pc.platform_status,
            **metrics,
        })

    return report
