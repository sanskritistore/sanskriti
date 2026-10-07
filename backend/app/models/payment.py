"""
भुगतान मॉडल - वॉलेट रिचार्ज और लेनदेन

UPI से वॉलेट रिचार्ज → वॉलेट से कैंपेन बजट कटता है।
"""

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TenantMixin, TimestampMixin


class WalletTransaction(Base, TimestampMixin, TenantMixin):
    """
    वॉलेट लेनदेन।

    प्रकार:
    - "recharge": UPI से पैसे जोड़े गए
    - "campaign_spend": कैंपेन बजट कटा
    - "refund": कैंपेन रद्द होने पर वापसी
    """

    __tablename__ = "wallet_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # tenant_id TenantMixin से - ARCHITECTURE RULE
    # लेनदेन प्रकार
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # राशि (₹) - recharge में positive, spend में negative नहीं, अलग कॉलम से पता
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    # लेनदेन के बाद बैलेंस (audit के लिए)
    balance_after: Mapped[float] = mapped_column(Float, nullable=True)
    # भुगतान गेटवे का संदर्भ (Razorpay order_id/payment_id आदि)
    gateway_order_id: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    gateway_payment_id: Mapped[str] = mapped_column(String(255), nullable=True)
    # संबंधित कैंपेन (spend/refund के लिए)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True
    )
    # स्थिति - "pending" | "success" | "failed"
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    # नोट्स/विवरण
    notes: Mapped[str] = mapped_column(Text, nullable=True)


class Lead(Base, TimestampMixin, TenantMixin):
    """
    लीड - WhatsApp कनेक्टर से आया ग्राहक।

    "WhatsApp से लीड" पैटर्न: विज्ञापन पर CTA दबाने वाला ग्राहक
    WhatsApp पर आता है, उसका विवरण यहाँ सेव होता है।
    """

    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # tenant_id TenantMixin से - ARCHITECTURE RULE
    # ग्राहक का नाम और फ़ोन
    name: Mapped[str] = mapped_column(String(255), nullable=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # लीड किस कैंपेन से आई
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # WhatsApp संदेश सारांश
    message: Mapped[str] = mapped_column(Text, nullable=True)
    # लीड स्थिति - "new" | "contacted" | "converted" | "lost"
    status: Mapped[str] = mapped_column(String(50), default="new", nullable=False)
