"""
Custom Audience राउटर — phone numbers की list से Meta Custom Audience

तीन काम:
1. GET  /audiences              → Meta पर बनी सारी audience lists
2. POST /audiences              → नई list बनाओ (खाली डिब्बा)
3. POST /audiences/{id}/upload  → उसमें phone numbers डालो

Privacy: numbers कभी plain नहीं जाते — पहले normalize (919873152325),
फिर SHA256 hash, फिर Meta। Meta भी hash से ही match करता है।

ईमानदारी (user को 09-10 समझाया था): 100+ numbers = ठीक, 1000 = दमदार;
match rate ~60-70% (हर number का FB/IG account नहीं मिलता)।
"""

import hashlib
import random
import re
import time

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import get_current_tenant_id
from app.core.config import settings
from app.core.exceptions import AdapterError

router = APIRouter()


class AudienceCreate(BaseModel):
    """नई audience list का नाम (+ वैकल्पिक विवरण)।"""

    name: str = Field(min_length=2, max_length=120)
    description: str | None = None


class PhonesUpload(BaseModel):
    """एक line में एक number — raw text या list दोनों चलेंगे।"""

    phones: list[str] = Field(min_length=1, max_length=5000)


def _normalize_indian_phone(raw: str) -> str | None:
    """
    भारतीय number को Meta-मानक रूप दो: देश-कोड सहित केवल digits।

    "98731 52325" → "919873152325"
    "09873152325" → "919873152325"
    "+91 98731-52325" → "919873152325"
    अजीब/छोटा number → None (skip, user को गिनती बताएँगे)
    """
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 10 and digits[0] in "6789":
        return "91" + digits
    if len(digits) == 11 and digits.startswith("0"):
        rest = digits[1:]
        if rest[0] in "6789":
            return "91" + rest
    if len(digits) == 12 and digits.startswith("91"):
        return digits
    return None


def _hash(phone: str) -> str:
    return hashlib.sha256(phone.encode("utf-8")).hexdigest()


async def _graph(method: str, path: str, **kwargs) -> dict:
    """छोटा Graph API helper (billing वाले pattern पर)।"""
    params = kwargs.pop("params", {})
    params["access_token"] = settings.META_ACCESS_TOKEN
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(
                method,
                f"{settings.META_GRAPH_URL}/{settings.META_API_VERSION}/{path}",
                params=params,
                **kwargs,
            )
    except Exception as exc:  # network त्रुटि — साफ़ बताओ
        raise AdapterError("meta", f"नेटवर्क त्रुटि: {exc}") from exc
    if resp.status_code >= 400:
        raise AdapterError("meta", f"Meta त्रुटि ({resp.status_code}): {resp.text}")
    return resp.json()


def _account_path() -> str:
    account_id = settings.META_AD_ACCOUNT_ID.replace("act_", "")
    if not account_id or not settings.META_ACCESS_TOKEN:
        raise AdapterError("meta", "Meta खाता जुड़ा नहीं है")
    return f"act_{account_id}"


@router.get("")
async def list_audiences(
    tenant_id: int = Depends(get_current_tenant_id),  # noqa: ARG001 - लॉगिन ज़रूरी
) -> dict:
    """Meta पर मौजूद सारी custom audience lists (नाम + अंदाज़ा-गिनती)।"""
    data = await _graph(
        "GET",
        f"{_account_path()}/customaudiences",
        params={
            "fields": "name,description,approximate_count_lower_bound,"
            "approximate_count_upper_bound,time_updated,delivery_status",
            "limit": "50",
        },
    )
    items = []
    for a in data.get("data", []):
        items.append(
            {
                "id": a.get("id"),
                "name": a.get("name"),
                "description": a.get("description") or "",
                # Meta privacy के लिए range देता है; शुरुआत में null (processing)
                "size_low": a.get("approximate_count_lower_bound"),
                "size_high": a.get("approximate_count_upper_bound"),
                "updated": a.get("time_updated"),
            }
        )
    return {"audiences": items}


@router.post("")
async def create_audience(
    body: AudienceCreate,
    tenant_id: int = Depends(get_current_tenant_id),  # noqa: ARG001
) -> dict:
    """खाली audience list बनाओ — फिर /upload से numbers डालो।"""
    data = await _graph(
        "POST",
        f"{_account_path()}/customaudiences",
        json={
            "name": body.name,
            "description": body.description or "Sanskriti ग्राहक सूची",
            "subtype": "CUSTOM",
            "customer_file_source": "USER_PROVIDED_ONLY",
        },
    )
    return {"id": data.get("id"), "name": body.name}


@router.post("/{audience_id}/upload")
async def upload_phones(
    audience_id: str,
    body: PhonesUpload,
    tenant_id: int = Depends(get_current_tenant_id),  # noqa: ARG001
) -> dict:
    """
    Audience में phone numbers जोड़ो (hash करके)।

    Meta को session metadata भी चाहिए (batch tracking) — हम एक ही batch
    में भेजते हैं (5000 numbers तक एक call काफी है)।
    """
    valid, invalid = [], 0
    seen = set()
    for raw in body.phones:
        norm = _normalize_indian_phone(raw)
        if norm is None or norm in seen:
            invalid += 1
            continue
        seen.add(norm)
        valid.append(norm)
    if not valid:
        raise AdapterError(
            "meta",
            "कोई सही Indian mobile number नहीं मिला — 10 अंकों वाला number डालें "
            "(जैसे 9873152325)।",
        )

    data = await _graph(
        "POST",
        f"{audience_id}/users",
        json={
            "payload": {
                "schema": ["PHONE"],
                "data": [[_hash(p)] for p in valid],
            },
            "session": {
                "session_id": random.randint(10**9, 2**31 - 1),
                "batch_seq": 1,
                "last_batch_flag": True,
                "estimated_num_total": len(valid),
            },
        },
    )
    return {
        "audience_id": data.get("audience_id", audience_id),
        "received": data.get("num_received", len(valid)),
        "invalid": invalid + data.get("num_invalid_entries", 0),
        "uploaded_at": int(time.time()),
        # ईमानदार hint: audience भरने में Meta को थोड़ा समय लगता है
        "note": "Numbers पहुँच गए! Meta अब match करेगा — गिनती कुछ घंटों में दिखेगी।",
    }
