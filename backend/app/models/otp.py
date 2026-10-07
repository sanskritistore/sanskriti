"""
OTP मॉडल - फ़ोन नंबर लॉगिन के कोड

नोट (ARCHITECTURE RULE का एकमात्र अपवाद):
यह टेबल login से *पहले* उपयोग होती है - तब टेनेंट की
पहचान ही नहीं बनी होती। इसलिए इसमें tenant_id नहीं है।
लॉगिन के बाद बनने वाली हर दूसरी टेबल में tenant_id अनिवार्य है।
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin


class OtpCode(Base, TimestampMixin):
    """फ़ोन नंबर पर भेजा गया OTP — TTL 5 मिनट, प्रयास सीमित।"""

    __tablename__ = "otp_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # फ़ोन नंबर (भारतीय 10 अंकों का)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # 6 अंकों का OTP (हैश करके रखना बेहतर है, MVP में सादा)
    code: Mapped[str] = mapped_column(String(10), nullable=False)
    # OTP की वैधता समाप्ति (UTC) - 5 मिनट TTL
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    # ग़लत प्रयासों की गिनती - MAX_ATTEMPTS के बाद अमान्य
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # OTP उपयोग हो चुका (सफल verify पर true)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
