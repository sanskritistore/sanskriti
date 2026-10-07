"""
प्रमाणीकरण सर्विस - OTP बनाना, भेजना, जाँचना

फ़्लो (3-चरण नियम):
1. send_otp: फ़ोन पर 6 अंकों का OTP बनाकर SMS ईंट से भेजें
2. verify_otp: OTP जाँचें - सही हो तो User + Tenant find-or-create
3. JWT टोकन बनाकर लौटाएँ (sub=user_id, tenant_id सहित)
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.models.otp import OtpCode
from app.models.tenant import Tenant, User
from app.modules.auth.sms import get_sms_sender

logger = logging.getLogger("sanskriti.auth")


def _generate_otp() -> str:
    """settings.OTP_LENGTH अंकों का सुरक्षित यादृच्छिक OTP बनाएँ।"""
    length = settings.OTP_LENGTH
    # secrets आधारित - random module से सुरक्षित
    return "".join(secrets.choice("0123456789") for _ in range(length))


async def send_otp(db: AsyncSession, phone: str) -> str:
    """
    फ़ोन नंबर के लिए OTP बनाकर भेजें।

    नियम:
    - एक फ़ोन का सिर्फ़ एक सक्रिय OTP (पुराने सब is_used)
    - TTL 5 मिनट (settings.OTP_TTL_MINUTES)
    - भेजने का काम SMS ईंट (swappable) का है
    """
    # पुराने अप्रयुक्त OTP निष्क्रिय करें (एक फ़ोन = एक सक्रिय OTP)
    result = await db.execute(
        select(OtpCode).where(OtpCode.phone == phone, OtpCode.is_used == False)  # noqa: E712
    )
    for old in result.scalars().all():
        old.is_used = True

    # नया OTP बनाएँ
    otp = _generate_otp()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.OTP_TTL_MINUTES
    )
    db.add(OtpCode(phone=phone, code=otp, expires_at=expires_at))
    await db.flush()

    # SMS ईंट से भेजें (स्टब अभी, MSG91/Twilio बाद में इसी अनुबंध पर)
    await get_sms_sender().send_otp(phone, otp)

    # डेवलपमेंट मोड में OTP लॉग करें (उत्पादन में OTP_DEV_MODE=false अनिवार्य)
    if settings.OTP_DEV_MODE:
        logger.info("OTP_DEV_MODE: phone=%s otp=%s", phone, otp)

    return otp


async def verify_otp(db: AsyncSession, phone: str, otp: str) -> User:
    """
    OTP जाँचें। सही होने पर User find-or-create करके लौटाएँ।

    त्रुटियाँ:
    - OTP नहीं मिला / समाप्त / अधिकतम प्रयास पार → 400
    - OTP ग़लत → प्रयास बढ़ाकर 400
    """
    # इस फ़ोन का सबसे नया OTP लाएँ
    result = await db.execute(
        select(OtpCode)
        .where(OtpCode.phone == phone, OtpCode.is_used == False)  # noqa: E712
        .order_by(OtpCode.id.desc())
        .limit(1)
    )
    otp_row = result.scalar_one_or_none()

    if otp_row is None:
        raise ValueError("OTP नहीं मिला - पहले OTP भेजें")

    # समाप्ति जाँच (UTC में तुलना)
    now = datetime.now(timezone.utc)
    if otp_row.expires_at.tzinfo is None:  # sqlite/smallest timezone-naive सुरक्षा
        expires = otp_row.expires_at.replace(tzinfo=timezone.utc)
    else:
        expires = otp_row.expires_at
    if now > expires:
        raise ValueError("OTP समाप्त हो गया - दोबारा भेजें")

    # प्रयास सीमा जाँच
    if otp_row.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise ValueError("बहुत अधिक ग़लत प्रयास - दोबारा OTP भेजें")

    # कोड जाँच
    if otp_row.code != otp:
        otp_row.attempts += 1
        await db.flush()
        remaining = settings.OTP_MAX_ATTEMPTS - otp_row.attempts
        raise ValueError(f"ग़लत OTP - {remaining} प्रयास शेष")

    # सफल - OTP ख़र्च (दोबारा उपयोग रोकें)
    otp_row.is_used = True
    user = await get_or_create_user(db, phone)
    await db.flush()
    return user


async def get_or_create_user(db: AsyncSession, phone: str) -> User:
    """
    फ़ोन से User ढूँढें, न मिले तो User + Tenant बनाएँ।

    नया व्यवसाय (Tenant) प्लेसहोल्डर नाम के साथ स्वतः बनता है -
    मालिक बाद में Settings (3-चरण) में पूरा नाम भरता है।
    """
    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    # नया टेनेंट (व्यवसाय) - प्लेसहोल्डर नाम
    tenant = Tenant(name="मेरी दुकान", phone=phone)
    db.add(tenant)
    await db.flush()  # tenant.id मिलना ज़रूरी

    # नया उपयोगकर्ता (मालिक)
    user = User(
        tenant_id=tenant.id,  # ARCHITECTURE RULE: हर row में tenant_id
        full_name="दुकान मालिक",  # प्लेसहोल्डर - Settings में बदलेगा
        phone=phone,
        role="owner",
    )
    db.add(user)
    await db.flush()
    return user


def build_token(user: User) -> str:
    """User के लिए JWT बनाएँ - sub=user_id, tenant_id एम्बेडेड।"""
    return create_access_token(
        {
            "sub": str(user.id),
            "tenant_id": user.tenant_id,
            "phone": user.phone,
        }
    )
