"""
उत्पाद मॉडल - आइटम और फ़ोटो

व्यवसाय अपने उत्पाद यहाँ जोड़ता है।
AI विज्ञापन निर्माण (ad_studio) इन्हीं उत्पादों से कंटेंट बनाता है।
"""

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TenantMixin, TimestampMixin


class Product(Base, TimestampMixin, TenantMixin):
    """
    उत्पाद (आइटम)।

    tenant_id TenantMixin से - ARCHITECTURE RULE।
    """

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # tenant_id TenantMixin से
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    # मूल्य (₹ में)
    price: Mapped[float] = mapped_column(Float, nullable=True)
    # विशेषताएँ - AI को संकेत देने के लिए
    tags: Mapped[str] = mapped_column(Text, nullable=True)  # comma-separated
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # संबंध: एक उत्पाद की कई फ़ोटो
    photos = relationship(
        "ProductPhoto",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ProductPhoto(Base, TimestampMixin, TenantMixin):
    """
    उत्पाद की फ़ोटो।

    tenant_id TenantMixin से - ARCHITECTURE RULE।
    """

    __tablename__ = "product_photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # tenant_id TenantMixin से
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # S3/स्थानीय स्टोरेज URL
    url: Mapped[str] = mapped_column(Text, nullable=False)
    # फ़ोटो का प्रकार - "original" | "ai_enhanced" | "ad_creative"
    photo_type: Mapped[str] = mapped_column(String(50), default="original", nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    product = relationship("Product", back_populates="photos")
