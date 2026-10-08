"""
रनर सर्विस - कैंपेन लॉन्च + बजट प्रबंधन

यहाँ 2-लेयर कैंपेन पैटर्न का मुख्य लॉजिक है:
- हमारी कैंपेन (Campaign) बनती है
- वॉलेट से बजट कटता है (atomic तरीके से)
- एडाप्टर के जरिए प्लेटफॉर्म पर कैंपेन बनती है (PlatformCampaign)
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    CampaignNotFoundError,
    CampaignNotDraftError,
    InsufficientBudgetError,
)
from app.models.campaign import Campaign, PlatformCampaign
from app.models.payment import WalletTransaction
from app.modules.adapters import get_adapter
from app.modules.adapters.base import CampaignConfig


async def get_campaign(db: AsyncSession, tenant_id: int, campaign_id: int) -> Campaign:
    """टेनेंट की कैंपेन लाएँ (tenant_id से फ़िल्टर)।"""
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id, Campaign.tenant_id == tenant_id
        )
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise CampaignNotFoundError(campaign_id)
    return campaign


async def create_campaign(db: AsyncSession, tenant_id: int, payload) -> Campaign:
    """नई कैंपेन बनाएँ (draft स्थिति में)।"""
    campaign = Campaign(
        tenant_id=tenant_id,  # ARCHITECTURE RULE
        name=payload.name,
        objective=payload.objective,
        ad_creative_id=payload.ad_creative_id,
        budget_total=payload.budget_total,
        budget_daily=payload.budget_daily,
        start_date=payload.start_date,
        end_date=payload.end_date,
        targeting=payload.targeting,
        status="draft",
    )
    db.add(campaign)
    await db.flush()
    return campaign


async def launch_campaign(
    db: AsyncSession, tenant_id: int, campaign_id: int
) -> Campaign:
    """
    कैंपेन लॉन्च करें - 2-लेयर पैटर्न।

    चरण:
    1. कैंपेन लाएँ (tenant_id से फ़िल्टर)
    2. वॉलेट बैलेंस जाँचें - अपर्याप्त हो तो त्रुटि
    3. वॉलेट से बजट काटें और WalletTransaction रिकॉर्ड करें
    4. प्रत्येक प्लेटफॉर्म के लिए एडाप्टर से प्लेटफॉर्म कैंपेन बनाएँ
       (PlatformCampaign row - लेयर 2)
    5. हमारी कैंपेन की स्थिति "active" करें
    """
    # 1. कैंपेन लाएँ
    campaign = await get_campaign(db, tenant_id, campaign_id)
    if campaign.status == "active":
        return campaign  # पहले से लाइव

    # 2. बजट जाँचें
    from app.modules.tenant.service import get_tenant
    tenant = await get_tenant(db, tenant_id)
    if tenant.wallet_balance < campaign.budget_total:
        raise InsufficientBudgetError(
            required=campaign.budget_total, available=tenant.wallet_balance
        )

    # 3. वॉलेट से बजट काटें + लेनदेन रिकॉर्ड
    tenant.wallet_balance -= campaign.budget_total
    db.add(WalletTransaction(
        tenant_id=tenant_id,
        transaction_type="campaign_spend",
        amount=campaign.budget_total,
        balance_after=tenant.wallet_balance,
        campaign_id=campaign.id,
        status="success",
        notes=f"कैंपेन '{campaign.name}' लॉन्च बजट",
    ))

    # 4. प्लेटफॉर्म कैंपेन बनाएँ (लेयर 2) - प्रत्येक प्लेटफॉर्म के लिए
    for platform in ["meta"]:  # MVP में केवल meta
        adapter = get_adapter(platform)
        config = CampaignConfig(
            name=campaign.name,
            objective=campaign.objective,
            daily_budget=campaign.budget_daily,
            total_budget=campaign.budget_total,
            start_date=campaign.start_date,
            end_date=campaign.end_date,
            targeting=campaign.targeting,
        )
        # एडाप्टर से प्लेटफॉर्म पर कैंपेन बनवाएँ
        platform_campaign_id = await adapter.create_campaign(config)

        # ── पूरी ad chain खड़ी करें: image → adset → creative → ad ──
        # (Meta पर सब PAUSED बनता है - बिना चालू किए खर्च ₹0)
        from app.models.campaign import AdCreative
        from app.models.product import Product

        creative = await db.get(AdCreative, campaign.ad_creative_id)
        product = (
            await db.get(Product, creative.product_id) if creative else None
        )

        # तस्वीर: product की फ़ोटो, नहीं तो डिफ़ॉल्ट
        image_path = await _resolve_image_path(product, creative)
        image_hash = await adapter.upload_ad_image(image_path)

        # Ad Set: दर्शक (जगह + उम्र) + रोज़ का बजट (₹ में)
        # Tenant ने चुना: शहर के आसपास | किसी खास जगह के घेरे में (सुई+घेरा)
        targeting = _parse_targeting(campaign)
        custom_locations = None
        if targeting.get("geo_type") == "place":
            # कई जगहें एक साथ (user की माँग 07-10: "Aakash, Dayal Singh, KV सब पर!")
            places = targeting.get("places") or []
            if not places and targeting.get("place_name"):  # पुराना single format
                places = [targeting["place_name"]]
            radius = max(1, int(targeting.get("radius_km", 1)))
            found = []
            for p in places[:10]:  # अधिकतम 10 सुएँ
                # नया (08-10): autocomplete से चुनी जगह की सुई पहले से
                # lock होती है — अंदाज़ा नहीं, पक्का पता सीधे चलता है
                if isinstance(p, dict):
                    lat, lon = p.get("latitude"), p.get("longitude")
                    if lat is not None and lon is not None:
                        found.append(
                            {
                                "latitude": float(lat),
                                "longitude": float(lon),
                                "radius_km": radius,
                            }
                        )
                        continue
                    pname = str(p.get("name", "")).strip()
                else:
                    pname = str(p).strip()
                if not pname:
                    continue
                point = await _geocode_place(pname, tenant.city)
                if point:
                    found.append({**point, "radius_km": radius})
                else:
                    logger.warning("place %r geocode नहीं हुआ — छोड़ा", pname)
            if found:
                custom_locations = found
            elif places:
                logger.warning("कोई जगह नहीं मिली — शहर targeting पर लौटे")
        adset_id = await adapter.create_ad_set(
            platform_campaign_id,
            f"{campaign.name} - दर्शक",
            daily_budget_rupees=campaign.budget_daily,
            geo_city_keys=[_city_geo_key(tenant.city)],
            age_min=int(targeting.get("age_min", 18)),
            age_max=int(targeting.get("age_max", 65)),
            custom_locations=custom_locations,
        )

        # Creative: हिंदी text + WhatsApp बटन
        wa_link = f"https://wa.me/91{tenant.phone}"
        meta_creative_id = await adapter.create_ad_creative(
            f"{campaign.name} - creative",
            image_hash,
            (creative.primary_text if creative and creative.primary_text
             else (product.description if product else campaign.name)),
            wa_link,
            (creative.headline if creative and creative.headline
             else (product.name if product else campaign.name)),
        )

        # अंतिम Ad
        meta_ad_id = await adapter.create_ad(
            adset_id, meta_creative_id, f"{campaign.name} - ad"
        )

        # PlatformCampaign row सेव करें (लेयर 2) - पूरी chain के IDs सहित
        db.add(PlatformCampaign(
            tenant_id=tenant_id,  # ARCHITECTURE RULE
            campaign_id=campaign.id,
            platform=platform,
            platform_campaign_id=platform_campaign_id,
            platform_adset_id=adset_id,
            platform_creative_id=meta_creative_id,
            platform_ad_id=meta_ad_id,
            platform_status="PAUSED",  # Meta पर PAUSED बना - सच दर्ज करें
            last_synced_at=datetime.now(timezone.utc),
        ))

    # 5. हमारी कैंपेन सक्रिय
    campaign.status = "active"
    await db.flush()
    return campaign


async def pause_campaign(
    db: AsyncSession, tenant_id: int, campaign_id: int
) -> Campaign:
    """कैंपेन रोकें - प्रत्येक प्लेटफॉर्म पर PAUSE भेजें।"""
    campaign = await get_campaign(db, tenant_id, campaign_id)

    for pc in campaign.platform_campaigns:
        adapter = get_adapter(pc.platform)
        await adapter.pause_campaign(pc.platform_campaign_id)
        pc.platform_status = "PAUSED"

    campaign.status = "paused"
    await db.flush()
    return campaign


async def delete_campaign(db: AsyncSession, tenant_id: int, campaign_id: int) -> None:
    """
    कैंपेन मिटाएँ — सिर्फ़ draft मिट सकती है (08-10 user माँग: कचरा drafts साफ़)।

    Active/paused कैंपेन प्लेटफ़ॉर्म से जुड़ी होती हैं — उन्हें मिटाने से
    रिपोर्ट/खर्च का इतिहास खोएगा, इसलिए इनकार। पहले ⏸ रोकना ही रास्ता है।
    """
    campaign = await get_campaign(db, tenant_id, campaign_id)
    if campaign.status != "draft":
        raise CampaignNotDraftError(campaign_id)
    await db.delete(campaign)
    await db.flush()


# ─── Launch helpers ───────────────────────────────────────────

import json
import logging

import httpx

logger = logging.getLogger(__name__)

# शहर का नाम → Meta geo city key (MVP: प्रमुख शहर; डिफ़ॉल्ट Delhi)
_CITY_GEO_KEYS = {
    "delhi": "1023040", "new delhi": "1023040", "दिल्ली": "1023040",
}


def _city_geo_key(city: str | None) -> str:
    """शहर का Meta geo key; अपरिचित शहर पर Delhi (सुरक्षित डिफ़ॉल्ट)।"""
    if not city:
        return "1023040"
    return _CITY_GEO_KEYS.get(city.strip().lower(), "1023040")


def _parse_targeting(campaign) -> dict:
    """कैंपेन का targeting JSON पढ़ें (खराब/खाली हो तो डिफ़ॉल्ट)।"""
    try:
        data = json.loads(campaign.targeting) if campaign.targeting else {}
        return data if isinstance(data, dict) else {}
    except (ValueError, TypeError):
        return {}


async def _geocode_place(place_name: str, city_hint: str | None) -> dict | None:
    """
    जगह का नाम → अक्षांश/देशांतर (सुई+घेरा targeting के लिए)।

    मुफ़्त Nominatim (OpenStreetMap) सेवा; शहर hint से सटीकता बढ़ती है।
    रणनीति: लंबा query असफल हो तो छोटा करके फिर कोशिश —
    Nominatim हर हिस्सा match न हो तो खाली लौटाता है (07-10: "Aakash
    Institute, Connaught Place, Delhi, India" ❌ पर "Aakash Institute Delhi" ✅)।
    असफल होने पर None (फिर शहर-स्तरीय targeting पर लौटते हैं)।
    """
    city = city_hint or "Delhi"
    queries = [
        f"{place_name}, {city}, India",
        f"{place_name} {city}",
        place_name,
    ]
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            for idx, query in enumerate(queries):
                resp = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": query, "format": "json", "limit": 1,
                            "countrycodes": "in"},
                    headers={"User-Agent": "SanskritiAds/1.0 (local business ads)"},
                )
                results = resp.json()
                if results:
                    # सुरक्षा: सिर्फ़ नाम वाली (कमज़ोर) query का नतीजा दूसरे
                    # शहर का हो सकता है (जैसे "Kendriya Vidyalaya" → Jaipur का KV!) —
                    # शहर का नाम नतीजे में न दिखे तो स्वीकार नहीं।
                    if idx == len(queries) - 1:
                        display = results[0].get("display_name", "").lower()
                        if city.lower() not in display:
                            continue
                    return {
                        "latitude": float(results[0]["lat"]),
                        "longitude": float(results[0]["lon"]),
                    }
    except Exception as exc:  # नेटवर्क/पार्स गड़बड़ी — launch नहीं रोकना
        logger.warning("geocode failed for %r: %s", place_name, exc)
    return None


async def _resolve_image_path(product, creative) -> str:
    """
    Ad के लिए तस्वीर का local path दें।
    क्रम: product.photo (data-URL/URL) → creative.image_url → डिफ़ॉल्ट तस्वीर।
    """
    import base64
    import tempfile

    import httpx

    candidate = None
    if product:
        # Product पर photo column नहीं — photos relationship (ProductPhoto rows) है।
        # primary फ़ोटो चुनें, नहीं तो पहली।
        photos = list(getattr(product, "photos", None) or [])
        chosen = next(
            (ph for ph in photos if getattr(ph, "is_primary", False)),
            photos[0] if photos else None,
        )
        if chosen is not None:
            candidate = chosen.url
        elif getattr(product, "photo", None):  # पुराना data हो तो
            candidate = product.photo
    elif creative and getattr(creative, "image_url", None):
        candidate = creative.image_url

    if candidate:
        if candidate.startswith("data:image"):
            # data-URL → अस्थायी फ़ाइल
            header, b64 = candidate.split(",", 1)
            ext = "png" if "png" in header else "jpg"
            tmp = tempfile.NamedTemporaryFile(
                delete=False, suffix=f".{ext}", prefix="sanskriti-ad-"
            )
            tmp.write(base64.b64decode(b64))
            tmp.close()
            return tmp.name
        if candidate.startswith(("http://", "https://")):
            # URL → download करके अस्थायी फ़ाइल
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(candidate)
                resp.raise_for_status()
            tmp = tempfile.NamedTemporaryFile(
                delete=False, suffix=".jpg", prefix="sanskriti-ad-"
            )
            tmp.write(resp.content)
            tmp.close()
            return tmp.name
        # local path है तो वही
        import os
        if os.path.exists(candidate):
            return candidate

    # डिफ़ॉल्ट तस्वीर (Sanskriti brand)
    from app.core.config import settings
    return settings.DEFAULT_AD_IMAGE_PATH
