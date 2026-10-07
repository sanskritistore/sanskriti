"""
मॉडल आधार - सभी टेबलों के लिए सामान्य कॉलम

ARCHITECTURE RULE (आर्किटेक्चर नियम):
हर टेबलल में tenant_id अनिवार्य है। इसलिए यह मिक्सिन
सभी मॉडल्स में tenant_id, created_at, updated_at देता है।
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, func
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


class TimestampMixin:
    """created_at / updated_at स्वतः प्रबंधित करता है।"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class TenantMixin:
    """
    हर टेबल में tenant_id देता है - MULTI-TENANCY का आधार।

    नियम:
    - tenant_id कभी null नहीं हो सकता
    - हर क्वेरी में tenant_id से फ़िल्टर अनिवार्य
    - इंडेक्स स्वतः बनता है ताकि क्वेरी तेज़ रहे
    """

    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,  # हर क्वेरी tenant_id से फ़िल्टर होती है
        comment="टेनेंट (व्यवसाय) ID - multi-tenancy कुंजी",
    )
