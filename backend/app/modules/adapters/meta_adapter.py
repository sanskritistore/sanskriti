"""
Meta एडाप्टर - Facebook/Instagram कैंपेन एडाप्टर

Meta Marketing API (Graph API) के जरिए:
- कैंपेन बनाना (act_<id>/campaigns)
- कैंपेन रोकना/चालू करना
- स्थिति और मेट्रिक्स लाना (insights)

6-विधि अनुबंध का Meta कार्यान्वयन।
"""

from datetime import datetime
from typing import Any, Dict

import httpx

from app.core.config import settings
from app.core.exceptions import AdapterError
from app.modules.adapters.base import BasePlatformAdapter, CampaignConfig

# Meta उद्देश्य मानचित्रण - हमारे उद्देश्य → Meta के उद्देश्य
OBJECTIVE_MAP = {
    "leads": "LEAD_GENERATION",     # WhatsApp लीड या फॉर्म लीड
    "traffic": "OUTCOME_TRAFFIC",   # वेबसाइट ट्रैफ़िक
    "awareness": "OUTCOME_AWARENESS",  # ब्रांड जागरूकता
    "sales": "OUTCOME_SALES",       # बिक्री/कन्वर्ज़न
}


class MetaAdapter(BasePlatformAdapter):
    """
    Meta (Facebook/Instagram) एडाप्टर।

    6-विधि अनुबंध लागू करता है। सभी कॉल Graph API को जाती हैं।
    """

    platform_name = "meta"

    def __init__(self):
        self.graph_url = settings.META_GRAPH_URL
        self.api_version = settings.META_API_VERSION
        self.access_token = settings.META_ACCESS_TOKEN
        # act_ prefix हटाकर शुद्ध account ID रखें (भाई का बग पक्का ठीक!)
        self.ad_account_id = settings.META_AD_ACCOUNT_ID.replace("act_", "")
        self.page_id = settings.META_PAGE_ID

    async def _request(
        self, method: str, path: str, params: Dict = None, json: Dict = None
    ) -> Dict[str, Any]:
        """Graph API कॉल का सामान्य तरीका (त्रुटियों के साथ)।"""
        url = f"{self.graph_url}/{self.api_version}/{path}"
        params = params or {}
        params["access_token"] = self.access_token

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method, url, params=params, json=json
            )
            if response.status_code >= 400:
                raise AdapterError(
                    "meta",
                    f"Graph API त्रुटि ({response.status_code}): {response.text}",
                )
            return response.json()

    # ── विधि 1: कैंपेन बनाएँ ──────────────────────────────
    async def create_campaign(self, config: CampaignConfig) -> str:
        """
        Meta पर नई कैंपेन बनाएँ।

        हमारे उद्देश्य को Meta के उद्देश्य में बदलें,
        फिर act_<id>/campaigns एंडपॉइंट पर POST करें।
        """
        # उद्देश्य मानचित्रण - हमारा "leads" → Meta का "LEAD_GENERATION"
        meta_objective = OBJECTIVE_MAP.get(config.objective, "OUTCOME_AWARENESS")

        # बजट ₹ → Meta विशेष_सीमित (special ad category) नियम आदि यहाँ लागू हों
        payload = {
            "name": config.name,
            "objective": meta_objective,
            "status": "PAUSED",  # सुरक्षा: पहले PAUSED बनाकर, फिर जाँच कर चालू करें
            "special_ad_categories": [],  # भारत में क्रेडिट/आवास श्रेणियाँ नहीं
            "is_adset_budget_sharing_enabled": False,  # Meta v26 अनिवार्य फ़ील्ड
        }
        response = await self._request(
            "POST", f"act_{self.ad_account_id}/campaigns", json=payload
        )
        return response["id"]  # platform_campaign_id

    # ── विधि 2: कैंपेन अपडेट करें ──────────────────────────
    async def update_campaign(
        self, platform_campaign_id: str, config: CampaignConfig
    ) -> bool:
        """Meta कैंपेन अपडेट करें (नाम/स्थिति)।"""
        payload = {"name": config.name}
        await self._request("POST", platform_campaign_id, json=payload)
        return True

    # ── विधि 3: कैंपेन रोकें ──────────────────────────────
    async def pause_campaign(self, platform_campaign_id: str) -> bool:
        """Meta कैंपेन PAUSED करें।"""
        await self._request(
            "POST", platform_campaign_id, json={"status": "PAUSED"}
        )
        return True

    # ── विधि 4: कैंपेन पुनः चालू करें ──────────────────────
    async def resume_campaign(self, platform_campaign_id: str) -> bool:
        """Meta कैंपेन ACTIVE करें।"""
        await self._request(
            "POST", platform_campaign_id, json={"status": "ACTIVE"}
        )
        return True

    # ── विधि 4ब: पूरी chain चालू करें (campaign+adset+ad) ──────
    async def activate_campaign_chain(
        self, platform_campaign_id: str, adset_id: str, ad_id: str
    ) -> bool:
        """Launch के बाद तीनों स्तर ACTIVE करें।

        Chain सुरक्षा के लिए PAUSED बनती है; सब बन जाने पर चालू करना
        भूल गए थे — 10-10 launch Meta पर PAUSED ही रह गई थी!
        """
        for object_id in (ad_id, adset_id, platform_campaign_id):
            await self._request("POST", object_id, json={"status": "ACTIVE"})
        return True

    # ── विधि 5: कैंपेन स्थिति लाएँ ─────────────────────────
    async def get_campaign_status(self, platform_campaign_id: str) -> Dict[str, Any]:
        """Meta कैंपेन की स्थिति लाएँ।"""
        response = await self._request(
            "GET",
            platform_campaign_id,
            params={"fields": "status,effective_status"},
        )
        return {
            "status": response.get("status"),
            "effective_status": response.get("effective_status"),
        }

    # ── विधि 6: कैंपेन मेट्रिक्स लाएँ ─────────────────────
    async def get_campaign_metrics(
        self,
        platform_campaign_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> Dict[str, Any]:
        """
        Meta insights से मेट्रिक्स लाएँ।

        खर्च USD में आता है - INR में बदलना आवश्यक (विनिमय दर सेटिंग से)।
        """
        params = {"fields": "spend,impressions,clicks,actions"}
        if start_date:
            params["time_since"] = start_date.strftime("%Y-%m-%d")
        if end_date:
            params["time_until"] = end_date.strftime("%Y-%m-%d")

        response = await self._request(
            "GET", f"{platform_campaign_id}/insights", params=params
        )
        data = (response.get("data") or [{}])[0]
        return {
            "spend": float(data.get("spend", 0.0)),
            "impressions": int(data.get("impressions", 0)),
            "clicks": int(data.get("clicks", 0)),
            "actions": data.get("actions", []),
        }

    # ══ पूरी विज्ञापन शृंखला: Ad Set → Creative → Ad ════════

    async def _upload_multipart(
        self, path: str, field: str, file_path: str, params: Dict = None
    ) -> Dict[str, Any]:
        """फ़ाइल अपलोड वाली Graph API कॉल (तस्वीर/वीडियो)।"""
        url = f"{self.graph_url}/{self.api_version}/{path}"
        params = params or {}
        params["access_token"] = self.access_token
        with open(file_path, "rb") as fh:
            files = {field: fh}
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, data=params, files=files)
        if response.status_code >= 400:
            raise AdapterError(
                "meta",
                f"Graph API अपलोड त्रुटि ({response.status_code}): {response.text}",
            )
        return response.json()

    async def upload_ad_image(self, image_path: str) -> str:
        """
        तस्वीर को विज्ञापन खाते में अपलोड करें → image_hash लौटाएँ।

        यही hash बाद में creative में लगता है।
        """
        response = await self._upload_multipart(
            f"act_{self.ad_account_id}/adimages", "filename", image_path
        )
        # जवाब: {"images": {"<filename>": {"hash": "..."}}}
        images = response.get("images", {})
        first = next(iter(images.values()), {})
        if "hash" not in first:
            raise AdapterError("meta", f"image_hash नहीं मिला: {response}")
        return first["hash"]

    async def create_ad_set(
        self,
        campaign_id: str,
        name: str,
        daily_budget_rupees: float,
        geo_city_keys: list[str],
        age_min: int = 18,
        age_max: int = 65,
        custom_locations: list[dict] | None = None,
        custom_audience_ids: list[str] | None = None,
        optimization_goal: str = "REACH",
        billing_event: str = "IMPRESSIONS",
    ) -> str:
        """
        Ad Set बनाएँ — दर्शक (शहर/उम्र) + रोज़ का बजट।

        Meta बजट पैसे में माँगता है: ₹1 = 100 पैसे।
        सुरक्षा: हमेशा PAUSED बनता है।
        custom_locations: [{"latitude","longitude","radius_km"}] — सुई+घेरा
        targeting (जैसे किसी coaching institute के 1 km घेरे में)।
        custom_audience_ids: ग्राहक-सूची (phone numbers) वालों को दिखाएँ —
        यह चुनी हो तो geo targeting नहीं लगती (सूची ही दर्शक है)।
        """
        if custom_audience_ids:
            # ग्राहक सूची = पूरा दर्शक — शहर/जगह की geo बाध्यता नहीं
            targeting = {
                "custom_audiences": [{"id": aid} for aid in custom_audience_ids],
                "age_min": age_min,
                "age_max": age_max,
            }
        else:
            if custom_locations:
                geo = {
                    "custom_locations": [
                        {
                            "latitude": loc["latitude"],
                            "longitude": loc["longitude"],
                            "radius": loc.get("radius_km", 1),
                            "distance_unit": "kilometer",
                        }
                        for loc in custom_locations
                    ],
                }
            else:
                geo = {
                    "cities": [
                        {"key": key, "radius": 25, "distance_unit": "mile"}
                        for key in geo_city_keys
                    ],
                }
            targeting = {
                "geo_locations": geo,
                "age_min": age_min,
                "age_max": age_max,
            }
        payload = {
            "name": name,
            "campaign_id": campaign_id,
            "daily_budget": int(daily_budget_rupees * 100),
            "billing_event": billing_event,
            "optimization_goal": optimization_goal,
            "bid_strategy": "LOWEST_COST_WITHOUT_CAP",  # बिना सीमा वाली सबसे-सस्ती बोली (v26 अनिवार्य)
            "targeting": targeting,
            "status": "PAUSED",
            "is_adset_budget_sharing_enabled": False,
        }
        response = await self._request(
            "POST", f"act_{self.ad_account_id}/adsets", json=payload
        )
        return response["id"]

    async def create_ad_creative(
        self,
        name: str,
        image_hash: str,
        message: str,
        link: str,
        headline: str,
        cta_type: str = "WHATSAPP_MESSAGE",
    ) -> str:
        """
        Ad Creative बनाएँ — page की तरफ़ से तस्वीर + हिंदी text + बटन।

        link: WhatsApp wa.me लिंक (या कोई भी गंतव्य URL)।
        """
        object_story_spec = {
            "page_id": self.page_id,
            "link_data": {
                "image_hash": image_hash,
                "link": link,
                "message": message,
                "name": headline,
                "call_to_action": {
                    "type": cta_type,
                    "value": {"link": link},
                },
            },
        }
        payload = {"name": name, "object_story_spec": object_story_spec}
        response = await self._request(
            "POST", f"act_{self.ad_account_id}/adcreatives", json=payload
        )
        return response["id"]

    async def create_ad(
        self, adset_id: str, creative_id: str, name: str
    ) -> str:
        """
        अंतिम Ad बनाएँ — Ad Set + Creative को जोड़ें।

        सुरक्षा: हमेशा PAUSED बनती है; चालू करने से पहले जाँच!
        """
        payload = {
            "name": name,
            "adset_id": adset_id,
            "creative": {"creative_id": creative_id},
            "status": "PAUSED",
        }
        response = await self._request(
            "POST", f"act_{self.ad_account_id}/ads", json=payload
        )
        return response["id"]
