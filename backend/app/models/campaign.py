"""
कैंपेन मॉडल - 2-लेयर कैंपेन पैटर्न

ARCHITECTURE PATTERN (आर्किटेक्चर पैटर्न):
हमारी कैंपेन (Campaign) हमेशा प्लेटफॉर्म की कैंपेन (PlatformCampaign)
से अलग होती है। संबंध इस प्रकार है:

    Campaign (हमारी कैंपेन - टेनेंट की एक कैंपेन)
        └── PlatformCampaign (प्लेटफॉर्म की कैंपेन - Meta/Google पर बनी)
                └── PlatformAdSet / PlatformAd (प्लेटफॉर्म के अंदर के स्तर)

क्यों 2 लेयर?
- हमारी कैंपेन टेनेंट का बिज़नेस व्यू है (बजट, उद्देश्य, रिपोर्ट)
- प्लेटफॉर्म कैंपेन तकनीकी व्यू है (platform_campaign_id, स्टेटस, sync)
- एक ही हमारी कैंपेन कई प्लेटफॉर्मों पर लाइव हो सकती है (भविष्य में)
- प्लेटफॉर्म API बदले तो हमारी कैंपेन अप्रभावित रहे
"""

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TenantMixin, TimestampMixin


class Campaign(Base, TimestampMixin, TenantMixin):
    """
    हमारी कैंपेन (लेयर 1) - टेनेंट के व्यवसाय की कैंपेन।

    यह हमारे सिस्टम की कैंपेन है। इसका platform_campaign_id
    सीधे नहीं रखा जाता - वह PlatformCampaign (लेयर 2) में है।
    """

    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # tenant_id TenantMixin से - ARCHITECTURE RULE
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # कैंपेन का उद्देश्य - "leads" | "traffic" | "awareness" | "sales"
    objective: Mapped[str] = mapped_column(String(50), default="leads", nullable=False)
    # लक्षित दर्शक - जैसे "18-65, मुंबई, रुचि: फैशन"
    targeting: Mapped[str] = mapped_column(Text, nullable=True)
    # कुल बजट (₹) - वॉलेट से कटा हुआ
    budget_total: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # दैनिक बजट (₹)
    budget_daily: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # अब तक खर्च (₹) - प्लेटफॉर्म से sync होता है
    budget_spent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # अवधि
    start_date: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)
    # स्थिति - "draft" | "pending" | "active" | "paused" | "completed" | "failed"
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    # कैंपेन बनाने के लिए उपयोग किया गया AI विज्ञापन (ad_studio से)
    ad_creative_id: Mapped[int] = mapped_column(
        ForeignKey("ad_creatives.id", ondelete="SET NULL"), nullable=True
    )

    # संबंध: एक कैंपेन की कई प्लेटफॉर्म कैंपेन हो सकती हैं (लेयर 2)
    platform_campaigns = relationship(
        "PlatformCampaign",
        back_populates="campaign",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class PlatformCampaign(Base, TimestampMixin, TenantMixin):
    """
    प्लेटफॉर्म कैंपेन (लेयर 2) - Meta/Google पर बनी कैंपेन।

    हर प्लेटफॉर्म के लिए एक अलग row। platform_campaign_id
    प्लेटफॉर्म का अपना ID है (जैसे Meta का act_<id>/campaigns/<id>)।
    """

    __tablename__ = "platform_campaigns"
    __table_args__ = (
        # एक प्लेटफॉर्म पर एक ही platform_campaign_id एक बार
        UniqueConstraint("platform", "platform_campaign_id", name="uq_platform_campaign"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # tenant_id TenantMixin से - ARCHITECTURE RULE
    # हमारी कैंपेन से लिंक (लेयर 1 → लेयर 2)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # प्लेटफॉर्म - "meta" | "google" (भविष्य में और)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    # प्लेटफॉर्म की कैंपेन ID (उनके सिस्टम की)
    platform_campaign_id: Mapped[str] = mapped_column(String(255), nullable=False)
    # पूरी ad chain के प्लेटफ़ॉर्म IDs (campaign → adset → creative → ad)
    platform_adset_id: Mapped[str] = mapped_column(String(255), nullable=True)
    platform_creative_id: Mapped[str] = mapped_column(String(255), nullable=True)
    platform_ad_id: Mapped[str] = mapped_column(String(255), nullable=True)
    # प्लेटफॉर्म पर स्थिति - "ACTIVE" | "PAUSED" | "DELETED" ...
    platform_status: Mapped[str] = mapped_column(String(50), nullable=True)
    # अंतिम sync समय - खर्च/स्टेटस यहाँ अपडेट होते हैं
    last_synced_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)
    # प्लेटफॉर्म से मिली अंतिम त्रुटि (यदि कोई)
    last_error: Mapped[str] = mapped_column(Text, nullable=True)

    campaign = relationship("Campaign", back_populates="platform_campaigns")


class AdCreative(Base, TimestampMixin, TenantMixin):
    """
    AI विज्ञापन क्रिएटिव (ad_studio का आउटपुट)।

    AI से बना हुआ विज्ञापन कंटेंट - हेडलाइन, विवरण, फ़ोटो आदि।
    कैंपेन लॉन्च करते समय यही क्रिएटिव प्लेटफॉर्म पर भेजा जाता है।
    """

    __tablename__ = "ad_creatives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # tenant_id TenantMixin से - ARCHITECTURE RULE
    # विज्ञापन किस उत्पाद के लिए है
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # AI जनरेशन प्रॉम्प्ट/संस्करण
    headline: Mapped[str] = mapped_column(String(255), nullable=True)
    primary_text: Mapped[str] = mapped_column(Text, nullable=True)  # मुख्य विज्ञापन टेक्स्ट
    description: Mapped[str] = mapped_column(Text, nullable=True)
    # उपयोग की गई फ़ोटो (यदि)
    image_url: Mapped[str] = mapped_column(String(512), nullable=True)
    # 🎠 Carousel cards (10-10 user माँग) — JSON list: [{"image_url","headline","description"}]
    # भरा हो (≥2 items) तो launch Meta carousel creative बनाता है
    carousel_items: Mapped[str] = mapped_column(Text, nullable=True)
    # किस भाषा में बना
    language: Mapped[str] = mapped_column(String(10), default="hi", nullable=False)
    # टेनेंट ने स्वीकार किया या नहीं (संशोधन के बाद)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # जनरेशन मेटाडेटा
    ai_model: Mapped[str] = mapped_column(String(100), nullable=True)
