"""
API Dependencies - रिक्वेस्ट स्तर की निर्भरताएँ

- get_current_user: JWT से वर्तमान उपयोगकर्ता + टेनेंट
- get_tenant_id: वर्तमान टेनेंट ID (हर एंडपॉइंट में अनिवार्य)
"""

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.core.tenant_context import set_current_tenant


async def get_current_user_id(
    authorization: str = Header(None, description="Bearer <JWT टोकन>"),
) -> int:
    """
    JWT टोकन से उपयोगकर्ता ID निकालें।

    टोकन प्रारूप: "Bearer <token>"
    टोकन न मिले/अमान्य हो → 401 (422 नहीं)
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="अमान्य प्रमाणीकरण - Bearer टोकन आवश्यक",
        )
    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="टोकन अमान्य या समाप्त",
        )
    return int(payload["sub"])


async def get_current_tenant_id(
    user_id: int = Depends(get_current_user_id),
    authorization: str = Header(None),
) -> int:
    """
    वर्तमान टेनेंट ID लौटाएँ और tenant context सेट करें।

    ARCHITECTURE RULE: हर एंडपॉइंट टेनेंट-बाउंड है।
    इस dependency के जरिए request-scope tenant context सेट होता है,
    जिसे मॉडल्स और सर्विसेज़ उपयोग करती हैं।
    """
    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)
    tenant_id = payload.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="टोकन में tenant_id नहीं मिला",
        )
    # request-scope tenant context सेट करें
    set_current_tenant(int(tenant_id))
    return int(tenant_id)


# संयुक्त dependency - DB सेशन + टेनेंट
CommonDeps = Depends(get_current_tenant_id)
