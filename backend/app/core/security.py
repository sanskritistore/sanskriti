"""
सुरक्षा - JWT टोकन और पासवर्ड हैशिंग

- JWT टोकन में tenant_id एम्बेडेड होता है (sub = user_id, tenant = tenant_id)
- पासवर्ड bcrypt से हैश होते हैं
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# पासवर्ड हैशिंग कॉन्टेक्स्ट (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """पासवर्ड को हैश करें।"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """पासवर्ड जाँचें।"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    JWT एक्सेस टोकन बनाएँ।

    data में सामान्यतः शामिल होंगे:
        - "sub": user ID (स्ट्रिंग)
        - "tenant_id": टेनेंट ID (हर टोकन टेनेंट-बाउंड है)
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """JWT टोकन डिकोड करें। अमान्य होने पर None।"""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None
