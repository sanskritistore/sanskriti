"""
टेनेंट मॉडल - व्यवसाय प्रोफ़ाइल और उपयोगकर्ता

Tenant = संस्कृति पर एक व्यवसाय (दुकान, ब्रांड, विक्रेता)।
हर अन्य टेबल tenant_id से इससे जुड़ता है।
"""

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TenantMixin, TimestampMixin


class Tenant(Base, TimestampMixin):
    """
    व्यवसाय प्रोफ़ाइल (टेनेंट)।

    नोट: यही टेबल tenant_id का स्रोत है, इसलिए TenantMixin नहीं लगाया गया।
    """

    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # व्यवसाय का नाम (हिंदी/अंग्रेज़ी/क्षेत्रीय भाषा में)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # संपर्क - फ़ोन नंबर प्राथमिक कुंजी जैसा काम करता है (OTP लॉगिन)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    # व्यवसाय श्रेणी - जैसे "कपड़े", "मिठाई", "फर्नीचर", "इलेक्ट्रॉनिक्स"
    business_category: Mapped[str] = mapped_column(String(100), nullable=True)
    # व्यवसाय विवरण - AI विज्ञापन निर्माण में उपयोग होता है
    business_description: Mapped[str] = mapped_column(Text, nullable=True)
    # पता और स्थान
    city: Mapped[str] = mapped_column(String(100), nullable=True)
    state: Mapped[str] = mapped_column(String(100), nullable=True)
    address: Mapped[str] = mapped_column(Text, nullable=True)
    # भाषा प्राथमिकता - AI कंटेंट इसी भाषा में बनेगा
    language: Mapped[str] = mapped_column(String(10), default="hi", nullable=False)
    # वॉलेट बैलेंस (₹ में) - कैंपेन बजट यहीं से कटता है
    wallet_balance: Mapped[float] = mapped_column(default=0.0, nullable=False)

    # ⭐ असली Google rating (10-10 user माँग: "reviews दिखें ताकि लोग जानें fake नहीं")
    # भरी हो तो carousel ad के आख़िरी card में review card अपने-आप जुड़ता है
    google_rating: Mapped[float] = mapped_column(Float, nullable=True)
    google_reviews_count: Mapped[int] = mapped_column(Integer, nullable=True)
    # खाता सक्रिय है या नहीं
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class User(Base, TimestampMixin, TenantMixin):
    """
    टेनेंट के अंतर्गत उपयोगकर्ता।

    MVP में सामान्यतः 1 टेनेंट = 1 उपयोगकर्ता (मालिक),
    पर संरचना भविष्य के लिए कई उपयोगकर्ताओं को समर्थन देती है।
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # tenant_id TenantMixin से आता है - ARCHITECTURE RULE
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=True)  # OTP लॉगिन में null
    role: Mapped[str] = mapped_column(String(50), default="owner", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
