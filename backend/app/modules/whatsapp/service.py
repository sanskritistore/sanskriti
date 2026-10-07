"""
WhatsApp सर्विस - लीड कनेक्टर लॉजिक

WhatsApp Business API (Cloud API) से आने वाले संदेशों को
लीड में बदलता है।
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Lead


async def handle_incoming_message(db: AsyncSession, payload: dict) -> dict:
    """
    आया WhatsApp संदेश संभालें।

    Meta Cloud API webhook प्रारूप:
        entry[].changes[].value.messages[] में संदेश होता है
        - from: ग्राहक का फ़ोन (जैसे "919876543210")
        - text.body: संदेश टेक्स्ट

    नोट: टेनेंट पहचानने के लिए फ़ोन नंबर से मैपिंग आवश्यक है
    (MVP में: प्रत्येक टेनेंट का अपना WhatsApp नंबर)।
    """

    def _extract(db, payload):
        """webhook payload से संदेश विवरण निकालें।"""
        try:
            entry = payload["entry"][0]
            change = entry["changes"][0]
            value = change["value"]
            message = value["messages"][0]
            phone = message["from"]
            text = message.get("text", {}).get("body", "")
            # TODO: नंबर से टेनेंट पहचानें (टेनेंट WhatsApp नंबर मैपिंग)
            return phone, text
        except (KeyError, IndexError):
            return None, None

    phone, text = _extract(db, payload)
    if phone is None:
        return {"ok": False, "संदेश": "संदेश विवरण नहीं मिला"}

    # TODO: फ़ोन से tenant_id पहचानें - अभी stub के रूप में रिकॉर्ड नहीं बन रहा
    # असली कार्यान्वयन में:
    #   tenant_id = <फ़ोन → टेनेंट मैपिंग से>
    #   lead = Lead(tenant_id=tenant_id, phone=phone, message=text, status="new")
    #   db.add(lead)

    return {"ok": True, "फ़ोन": phone, "संदेश": "लीड दर्ज हुई (MVP stub)"}


async def send_whatsapp_message(to: str, text: str) -> bool:
    """
    ग्राहक को WhatsApp संदेश भेजें (उत्तर/स्वचालित उत्तर)।

    Meta Cloud API: POST /{phone_number_id}/messages
    """
    import httpx

    from app.core.config import settings

    url = (
        f"https://graph.facebook.com/{settings.META_API_VERSION}"
        f"/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"},
        )
        return response.status_code < 400
