"""
एडाप्टर आधार - 6-विधि अनुबंध (6-method contract)

हर प्लेटफॉर्म एडाप्टर (Meta, Google, ...) को यह 6 विधियाँ
लागू करनी अनिवार्य हैं। यही एडाप्टर अनुबंध है:

    1. create_campaign(config)  -> platform_campaign_id
    2. update_campaign(id, config) -> updated
    3. pause_campaign(id)      -> paused
    4. resume_campaign(id)     -> resumed
    5. get_campaign_status(id)  -> status dict
    6. get_campaign_metrics(id, date_range) -> metrics dict

इस अनुबंध से runner मॉड्यूल किसी भी प्लेटफॉर्म को
एक जैसे तरीके से चला सकता है (pluggable architecture)।
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict


@dataclass
class CampaignConfig:
    """
    प्लेटफॉर्म-स्वतंत्र कैंपेन सेटिंग्स।

    यह हमारी कैंपेन (लेयर 1) से बनता है और एडाप्टर
    इसे प्लेटफॉर्म के अपने प्रारूप में बदलता है।
    """

    name: str
    objective: str  # leads | traffic | awareness | sales
    daily_budget: float  # ₹ में
    total_budget: float  # ₹ में
    start_date: datetime | None = None
    end_date: datetime | None = None
    targeting: str | None = None  # लक्षित दर्शक विवरण
    creative: Dict[str, Any] = field(default_factory=dict)  # क्रिएटिव डेटा
    extra: Dict[str, Any] = field(default_factory=dict)  # प्लेटफॉर्म-विशिष्ट


class BasePlatformAdapter(ABC):
    """
    सभी प्लेटफॉर्म एडाप्टरों का आधार वर्ग।

    6-विधि अनुबंध (6-method contract) - हर उपवर्ग को सभी 6
    abstract विधियाँ लागू करनी होंगी।
    """

    # उपवर्ग में प्लेटफॉर्म का नाम सेट करें - जैसे "meta", "google"
    platform_name: str = "base"

    @abstractmethod
    async def create_campaign(self, config: CampaignConfig) -> str:
        """
        विधि 1: प्लेटफॉर्म पर नई कैंपेन बनाएँ।

        लौटाएँ: प्लेटफॉर्म की कैंपेन ID (स्ट्रिंग)।
        """
        ...

    @abstractmethod
    async def update_campaign(
        self, platform_campaign_id: str, config: CampaignConfig
    ) -> bool:
        """
        विधि 2: मौजूदा कैंपेन अपडेट करें (बजट, नाम आदि)।

        लौटाएँ: सफलता पर True।
        """
        ...

    @abstractmethod
    async def pause_campaign(self, platform_campaign_id: str) -> bool:
        """
        विधि 3: कैंपेन रोकें (PAUSE)।

        लौटाएँ: सफलता पर True।
        """
        ...

    @abstractmethod
    async def resume_campaign(self, platform_campaign_id: str) -> bool:
        """
        विधि 4: रुकी कैंपेन पुनः चालू करें (RESUME)।

        लौटाएँ: सफलता पर True।
        """
        ...

    @abstractmethod
    async def get_campaign_status(self, platform_campaign_id: str) -> Dict[str, Any]:
        """
        विधि 5: कैंपेन की वर्तमान स्थिति लाएँ।

        लौटाएँ: जैसे {"status": "ACTIVE", "effective_status": "ACTIVE"}
        """
        ...

    @abstractmethod
    async def get_campaign_metrics(
        self,
        platform_campaign_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> Dict[str, Any]:
        """
        विधि 6: कैंपेन मेट्रिक्स लाएँ (खर्च, रीच, क्लिक, लीड)।

        लौटाएँ: जैसे {"spend": 150.0, "impressions": 12000,
                        "clicks": 340, "leads": 25}
        """
        ...
