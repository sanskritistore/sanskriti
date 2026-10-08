"""
बिलिंग राउटर — Meta ad खाते की पैसा-स्थिति (08-10 user माँग)

User की चिंता: "गलती से किसी और खाते में payment न चली जाए"।
इलाज: software खुद बताए कि पैसा किस खाते में जा रहा है (नाम + आख़िरी
4 अंक) और सीधा उसी खाते का billing link दे — menu से ढूँढना ही न पड़े।

सब कुछ settings (env) से — कोई account id code में गड़ी नहीं (बिंदु 18)।
"""

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import get_current_tenant_id
from app.core.config import settings
from app.core.exceptions import AdapterError

router = APIRouter()

# Meta खाते की स्थिति संख्या → सरल शब्द (Graph API account_status)
_STATUS_WORDS = {
    1: "active",
    2: "disabled",
    3: "unsettled",
    7: "pending_risk",
    8: "pending_settlement",
    9: "in_grace",
    100: "pending_closure",
    101: "closed",
    201: "any_active",
    202: "any_closed",
}


@router.get("/status")
async def billing_status(
    tenant_id: int = Depends(get_current_tenant_id),  # noqa: ARG001 - लॉगिन ज़रूरी
) -> dict:
    """
    जुड़े Meta ad खाते की पैसा-स्थिति लौटाएँ:
    कौन सा खाता (नाम + आख़िरी अंक), कितना पैसा बचा, कितना खर्च,
    और सीधा पैसा-डालने का link (asset_id lock — गलत खाता असंभव)।
    """
    account_id = settings.META_AD_ACCOUNT_ID.replace("act_", "")
    if not account_id or not settings.META_ACCESS_TOKEN:
        raise AdapterError("meta", "Meta खाता जुड़ा नहीं है")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{settings.META_GRAPH_URL}/{settings.META_API_VERSION}/act_{account_id}",
                params={
                    "fields": "name,currency,balance,amount_spent,spend_cap,account_status,business_name",
                    "access_token": settings.META_ACCESS_TOKEN,
                },
            )
    except Exception as exc:
        raise AdapterError("meta", f"नेटवर्क त्रुटि: {exc}") from exc
    if resp.status_code >= 400:
        raise AdapterError("meta", f"Graph API त्रुटि ({resp.status_code}): {resp.text}")
    data = resp.json()

    # Meta राशि खाते की मुद्रा की छोटी इकाई में देता है (INR → पैसे)
    balance = round(int(data.get("balance") or 0) / 100, 2)
    spent = round(int(data.get("amount_spent") or 0) / 100, 2)
    # खर्च-रोक सीमा: spend_cap जन्म से खर्च (amount_spent) पर लगती है।
    # दुकानदार के लिए मायने = "अब से कितना और चल सकता है" (cap - spent)
    cap = int(data.get("spend_cap") or 0) / 100
    cap_remaining = round(max(cap - spent, 0), 2) if cap else None

    # आज का खर्च (insights) — अलग कॉल; फेल हो तो चुपचाप None
    today_spend = None
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            ins = await client.get(
                f"{settings.META_GRAPH_URL}/{settings.META_API_VERSION}/act_{account_id}/insights",
                params={
                    "fields": "spend",
                    "date_preset": "today",
                    "access_token": settings.META_ACCESS_TOKEN,
                },
            )
            if ins.status_code < 400:
                rows = ins.json().get("data") or []
                if rows:
                    today_spend = round(float(rows[0].get("spend") or 0), 2)
    except Exception:
        pass

    return {
        # सुरक्षा: पूरा account id नहीं, बस आख़िरी 4 अंक (पहचान के लिए काफ़ी)
        "account_last4": account_id[-4:],
        "account_name": data.get("business_name") or data.get("name") or "Ad खाता",
        "currency": data.get("currency", "INR"),
        "balance_rupees": balance,
        "spent_rupees": spent,
        "today_spend_rupees": today_spend,
        # None = सीमा नहीं लगी; संख्या = अब से इतने ₹ और खर्च हो सकते हैं
        "cap_remaining_rupees": cap_remaining,
        "account_status": _STATUS_WORDS.get(data.get("account_status"), "unknown"),
        "low_balance": balance < 100,
        # asset_id से खाता पहले से चुना खुलता है — गलत खाते में पैसा असंभव
        "add_money_url": (
            "https://business.facebook.com/billing_hub/payment_settings"
            f"?asset_id=act_{account_id}"
        ),
    }


class SpendCapSet(BaseModel):
    """अब से आगे कुल कितने ₹ और खर्च की इजाज़त (जन्म से खर्च में जुड़ जाता है)।"""

    extra_rupees: float = Field(gt=0, le=10_000_000)


@router.post("/spend-cap")
async def set_spend_cap(
    payload: SpendCapSet,
    tenant_id: int = Depends(get_current_tenant_id),  # noqa: ARG001
) -> dict:
    """
    खाता खर्च-रोक सीमा लगाओ/बदलो — user की माँग (08-10):
    "limit ham apne hisab se set kar sake"।

    Meta की spend_cap जन्म से कुल खर्च (amount_spent) पर चढ़ती है,
    इसलिए नई सीमा = अब तक खर्च + user की गुंजाइश। सीमा छूते ही
    Meta सारी ads अपने आप रोक देता है — पैसे की पूरी सुरक्षा।
    """
    account_id = settings.META_AD_ACCOUNT_ID.replace("act_", "")
    if not account_id or not settings.META_ACCESS_TOKEN:
        raise AdapterError("meta", "Meta खाता जुड़ा नहीं है")

    # पहले अब तक का खर्च पढ़ो — सीमा उसके ऊपर चढ़ेगी
    async with httpx.AsyncClient(timeout=15.0) as client:
        read = await client.get(
            f"{settings.META_GRAPH_URL}/{settings.META_API_VERSION}/act_{account_id}",
            params={
                "fields": "amount_spent",
                "access_token": settings.META_ACCESS_TOKEN,
            },
        )
        if read.status_code >= 400:
            raise AdapterError("meta", f"Graph API त्रुटि ({read.status_code})")
        spent_paise = int(read.json().get("amount_spent") or 0)

        new_cap_paise = spent_paise + round(payload.extra_rupees * 100)
        write = await client.post(
            f"{settings.META_GRAPH_URL}/{settings.META_API_VERSION}/act_{account_id}",
            params={"access_token": settings.META_ACCESS_TOKEN},
            data={"spend_cap": str(new_cap_paise)},
        )
        if write.status_code >= 400 or not write.json().get("success", False):
            raise AdapterError(
                "meta", f"सीमा नहीं लगी ({write.status_code}): {write.text}"
            )

    # नई स्थिति लौटाओ — UI तुरंत सच दिखाए
    return await billing_status(tenant_id)
