"""
WhatsApp राउटर - लीड कनेक्टर एंडपॉइंट

"WhatsApp से लीड" पैटर्न:
- विज्ञापन CTA → WhatsApp चैट → लीड हमारे सिस्टम में
- WhatsApp Business API के webhook से ग्राहक संदेश आते हैं
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id
from app.core.database import get_db
from app.models.payment import Lead
from app.modules.whatsapp import service

router = APIRouter()


@router.get("/leads")
async def list_leads(
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """अपनी सभी WhatsApp लीड देखें।"""
    result = await db.execute(
        select(Lead).where(Lead.tenant_id == tenant_id)
    )
    leads = result.scalars().all()
    return [
        {
            "id": l.id,
            "name": l.name,
            "phone": l.phone,
            "status": l.status,
            "message": l.message,
        }
        for l in leads
    ]


@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = None,
    hub_verify_token: str = None,
    hub_challenge: str = None,
):
    """
    WhatsApp webhook सत्यापन (Meta का प्रारूप)।

    Meta webhook सेट करते समय यह GET कॉल आती है -
    verify_token मिलने पर challenge लौटाना होता है।
    """
    from app.core.config import settings
    from fastapi import HTTPException

    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="सत्यापन विफल")


@router.post("/webhook")
async def receive_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    WhatsApp संदेश webhook - ग्राहक का संदेश लीड बनाता है।

    प्रवाह:
    1. ग्राहक विज्ञापन CTA से WhatsApp पर आता है
    2. उसका संदेश webhook से यहाँ आता है
    3. फ़ोन नंबर से टेनेंट पहचानकर Lead रिकॉर्ड बनता है
    """
    payload = await request.json()
    result = await service.handle_incoming_message(db, payload)
    return result
