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


async def build_who_saw(db: AsyncSession, tenant_id: int) -> dict:
    """
    किसने ad देखी — पिछले 7 दिन का बंटवारा (08-10 user माँग)।

    तीन नज़रिए: उम्र×लड़का/लड़की, इलाका (region), FB/Instagram।
    नाम/नंबर Meta किसी को नहीं देता — यही क़ानूनन सबसे सटीक जानकारी है।
    """
    import httpx
    from sqlalchemy import select
    from app.core.config import settings

    result = await db.execute(
        select(Campaign).where(Campaign.tenant_id == tenant_id)
    )
    campaigns = result.scalars().all()
    meta_ids = [
        pc.platform_campaign_id
        for c in campaigns
        for pc in c.platform_campaigns
        if pc.platform == "meta"
    ]
    if not meta_ids or not settings.META_ACCESS_TOKEN:
        return {"age_gender": [], "regions": [], "platforms": [], "days": 7}

    base = f"{settings.META_GRAPH_URL}/{settings.META_API_VERSION}"

    async def fetch(campaign_id: str, breakdown: str) -> list:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                f"{base}/{campaign_id}/insights",
                params={
                    "fields": "impressions,clicks,spend",
                    "breakdowns": breakdown,
                    "date_preset": "last_7d",
                    "access_token": settings.META_ACCESS_TOKEN,
                },
            )
            if resp.status_code >= 400:
                return []
            return resp.json().get("data", [])

    def merge(acc: dict, key: tuple, row: dict) -> None:
        cur = acc.setdefault(key, {"impressions": 0, "clicks": 0, "spend": 0.0})
        cur["impressions"] += int(row.get("impressions", 0))
        cur["clicks"] += int(row.get("clicks", 0))
        cur["spend"] += float(row.get("spend", 0))

    age_gender: dict = {}
    regions: dict = {}
    platforms: dict = {}
    for cid in meta_ids:
        for row in await fetch(cid, "age,gender"):
            merge(age_gender, (row.get("age"), row.get("gender")), row)
        for row in await fetch(cid, "region"):
            merge(regions, (row.get("region"), row.get("country")), row)
        for row in await fetch(cid, "publisher_platform"):
            merge(platforms, (row.get("publisher_platform"),), row)

    def ranked(items, keys):
        out = [dict(zip(keys, k), **v) for k, v in items.items()]
        total = sum(x["impressions"] for x in out) or 1
        out.sort(key=lambda x: -x["impressions"])
        for x in out:
            x["pct"] = round(x["impressions"] * 100 / total)
            x["spend"] = round(x["spend"], 2)
        return out

    return {
        "age_gender": ranked(age_gender, ("age", "gender")),
        "regions": ranked(regions, ("region", "country")),
        "platforms": ranked(platforms, ("platform",)),
        "days": 7,
    }


async def build_score_card(db: AsyncSession, tenant_id: int) -> dict:
    """
    📊 असली Score Card — Meta से सीधे आज + पिछले 7 दिन की गिनती।

    (10-10 user माँग: "software पर score card आए — किसने देखी, कहाँ तक गई,
    कितना खर्च, कितने ग्राहक आए। DB के ₹0 नहीं — Meta के असली numbers!")

    ईमानदारी: नाम/फ़ोन क़ानूनन नहीं मिलते (privacy) — पर reach, बार,
    clicks, WhatsApp messages और खर्च सब असली, सीधे Meta से।
    """
    import httpx
    from sqlalchemy import select
    from app.core.config import settings

    result = await db.execute(
        select(Campaign).where(Campaign.tenant_id == tenant_id)
    )
    campaigns = result.scalars().all()

    # Meta id → हमारी campaign (नाम + status के लिए)
    meta_map: dict = {}
    for c in campaigns:
        for pc in c.platform_campaigns:
            if pc.platform == "meta":
                meta_map[pc.platform_campaign_id] = c

    empty = {"reach": 0, "impressions": 0, "clicks": 0, "spend": 0.0, "messages": 0}
    if not meta_map or not settings.META_ACCESS_TOKEN:
        return {"today": dict(empty), "week": dict(empty), "campaigns": []}

    base = f"{settings.META_GRAPH_URL}/{settings.META_API_VERSION}"

    # WhatsApp/message जुड़े action types — इन्हें "ग्राहक enquiry" गिनें
    MSG_TYPES = ("contact", "messaging", "whatsapp")

    def read_row(row: dict) -> dict:
        actions = row.get("actions") or []
        messages = sum(
            int(a.get("value", 0))
            for a in actions
            if any(k in str(a.get("action_type", "")).lower() for k in MSG_TYPES)
        )
        return {
            "reach": int(row.get("reach", 0) or 0),
            "impressions": int(row.get("impressions", 0) or 0),
            "clicks": int(row.get("clicks", 0) or 0),
            "spend": float(row.get("spend", 0) or 0),
            "messages": messages,
        }

    async def fetch(campaign_id: str, preset: str) -> dict:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                f"{base}/{campaign_id}/insights",
                params={
                    "fields": "impressions,reach,clicks,spend,actions",
                    "date_preset": preset,
                    "access_token": settings.META_ACCESS_TOKEN,
                },
            )
            if resp.status_code >= 400:
                return dict(empty)
            data = resp.json().get("data", [])
            return read_row(data[0]) if data else dict(empty)

    def add(a: dict, b: dict) -> dict:
        return {k: round(a[k] + b[k], 2) for k in a}

    today_total, week_total = dict(empty), dict(empty)
    per_campaign = []
    for cid, c in meta_map.items():
        t = await fetch(cid, "today")
        w = await fetch(cid, "last_7d")
        today_total = add(today_total, t)
        week_total = add(week_total, w)
        # सिर्फ़ वही campaigns दिखाएँ जो आज/इस हफ्ते चलीं (0-0 की पुरानी नहीं)
        if t["impressions"] or w["impressions"] or c.status == "active":
            per_campaign.append(
                {
                    "id": c.id,
                    "name": c.name,
                    "status": c.status,
                    "today": t,
                    "week": w,
                }
            )

    # active पहले, फिर नाम से
    per_campaign.sort(key=lambda x: (x["status"] != "active", x["name"]))
    return {"today": today_total, "week": week_total, "campaigns": per_campaign}
