"""
प्रमाणीकरण राउटर - फ़ोन + OTP लॉगिन

3-चरण नियम (architecture rule):
1. POST /auth/send-otp    → फ़ोन पर OTP भेजें
2. POST /auth/verify-otp  → OTP जाँचें, JWT लौटाएँ
3. टोकन के साथ ऐप में प्रवेश

ये एंडपॉइंट pre-auth हैं - इन पर tenant dependency नहीं है।
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.modules.auth import service

router = APIRouter()


class SendOtpRequest(BaseModel):
    """OTP भेजने का अनुरोध - भारतीय 10 अंकों का फ़ोन।"""

    phone: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip()
        # भारतीय मोबाइल: 10 अंक, 6-9 से शुरू
        if not (len(v) == 10 and v.isdigit() and v[0] in "6789"):
            raise ValueError("मान्य 10 अंकों का मोबाइल नंबर डालें")
        return v


class SendOtpResponse(BaseModel):
    """OTP भेजने का उत्तर।"""

    sent: bool
    # डेवलपमेंट सुविधा: OTP_DEV_MODE=true होने पर ही OTP उत्तर में आता है
    # उत्पादन में यह फ़ील्ड कभी नहीं भरी जाती (OTP_DEV_MODE=false अनिवार्य)
    dev_otp: str | None = None
    message: str = "OTP भेज दिया गया"


class VerifyOtpRequest(BaseModel):
    """OTP जाँचने का अनुरोध - फ़ोन + 6 अंकों का OTP।"""

    phone: str
    otp: str

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, v: str) -> str:
        v = v.strip()
        if not (len(v) == settings.OTP_LENGTH and v.isdigit()):
            raise ValueError(f"{settings.OTP_LENGTH} अंकों का OTP डालें")
        return v


class VerifyOtpResponse(BaseModel):
    """लॉगिन का उत्तर - JWT टोकन (फ्रंटएंड sanskriti_token में सेव करता है)।"""

    token: str
    user_id: int
    tenant_id: int
    is_new_user: bool


@router.post("/send-otp", response_model=SendOtpResponse)
async def send_otp(
    payload: SendOtpRequest,
    db: AsyncSession = Depends(get_db),
):
    """फ़ोन नंबर पर OTP भेजें (TTL 5 मिनट)।"""
    otp = await service.send_otp(db, payload.phone)
    return SendOtpResponse(
        sent=True,
        # OTP उत्तर में सिर्फ़ डेवलपमेंट मोड में (SMS गेटवे के बिना टेस्ट)
        dev_otp=otp if settings.OTP_DEV_MODE else None,
    )


@router.post("/verify-otp", response_model=VerifyOtpResponse)
async def verify_otp(
    payload: VerifyOtpRequest,
    db: AsyncSession = Depends(get_db),
):
    """OTP जाँचें - सही हो तो JWT टोकन लौटाएँ (User+Tenant स्वतः बनते हैं)।"""
    try:
        user = await service.verify_otp(db, payload.phone, payload.otp)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )

    return VerifyOtpResponse(
        token=service.build_token(user),
        user_id=user.id,
        tenant_id=user.tenant_id,
        is_new_user=False,  # MVP में नया/पुराना भेद उत्तर में ज़रूरी नहीं
    )
