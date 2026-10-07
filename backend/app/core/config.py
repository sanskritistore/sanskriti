"""
कॉन्फ़िगरेशन - सेटिंग्स
पर्यावरण वेरिएबल्स से सभी सेटिंग्स लोड होती हैं।
"""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """एप्लीकेशन की सभी सेटिंग्स एक जगह।"""

    # एप्लीकेशन
    APP_NAME: str = "Sanskriti"
    APP_ENV: str = "development"  # development | staging | production
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # डेटाबेस (PostgreSQL - async)
    DATABASE_URL: str = "postgresql+asyncpg://sanskriti:sanskriti@localhost:5432/sanskriti"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Redis (कैश + Celery ब्रोकर)
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT / प्रमाणीकरण
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 घंटे

    # OTP लॉगिन (फ़ोन + OTP)
    OTP_LENGTH: int = 6
    OTP_TTL_MINUTES: int = 5  # OTP की वैधता 5 मिनट
    OTP_MAX_ATTEMPTS: int = 5  # एक OTP पर अधिकतम 5 प्रयास
    # डेवलपमेंट मोड: OTP उत्तर में लौटा देता है (SMS गेटवे के बिना टेस्ट के लिए)
    # उत्पादन में कड़ाई से false रखें!
    OTP_DEV_MODE: bool = False

    # Meta (Facebook/Instagram) API
    META_APP_ID: str = ""
    META_APP_SECRET: str = ""
    META_ACCESS_TOKEN: str = ""
    META_AD_ACCOUNT_ID: str = ""  # उदा. act_1234567890 (act_ prefix चलेगा)
    META_PAGE_ID: str = ""  # फ़ेसबुक पेज की ID
    META_API_VERSION: str = "v26.0"
    META_GRAPH_URL: str = "https://graph.facebook.com"

    # Google Ads API
    GOOGLE_ADS_CUSTOMER_ID: str = ""
    GOOGLE_ADS_DEVELOPER_TOKEN: str = ""
    GOOGLE_ADS_REFRESH_TOKEN: str = ""
    GOOGLE_ADS_CLIENT_ID: str = ""
    GOOGLE_ADS_CLIENT_SECRET: str = ""

    # AI (विज्ञापन निर्माण के लिए)
    OPENAI_API_KEY: str = ""
    AI_MODEL: str = "gpt-4o-mini"

    # WhatsApp Business API (लीड कनेक्टर)
    WHATSAPP_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_VERIFY_TOKEN: str = ""

    # भुगतान (UPI)
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    UPI_VPA: str = ""  # जैसे sanskriti@upi

    # i18n - समर्थित भाषाएँ
    SUPPORTED_LANGUAGES: List[str] = ["hi", "en", "mr", "gu", "bn", "ta", "te"]

    # डिफ़ॉल्ट ad तस्वीर (product फ़ोटो न हो तो) — repo के अंदर, हर server पर चले
    DEFAULT_AD_IMAGE_PATH: str = str(
        Path(__file__).resolve().parents[2] / "assets" / "default-ad-image.png"
    )

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """सेटिंग्स का सिंगलटन इंस्टेंस।"""
    return Settings()


settings = get_settings()
