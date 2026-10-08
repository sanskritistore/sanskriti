"""
टारगेटिंग राउटर - जगह खोज सेवा (autocomplete)

Tenant को असली सुझाव दिखाने के लिए: नाम लिखते ही पते के साथ
सुझाव आते हैं (जैसे "Aakash Institute — Janakpuri, New Delhi")।
User सही जगह चुनता है → अक्षांश/देशांतर तुरंत lock → launch पर
अंदाज़ा नहीं, पक्का पता जाता है (user की माँग 08-10:
"pehle state, fir search bar, kai locations ek sath lock").

मुफ़्त Nominatim (OpenStreetMap) — वही सेवा जो geocoding में चलती है।
"""

import logging

import httpx
from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_tenant_id

logger = logging.getLogger("sanskriti.targeting")

router = APIRouter()

_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_HEADERS = {"User-Agent": "SanskritiAds/1.0 (local business ads)"}


def _simplify(item: dict) -> dict:
    """Nominatim नतीजे को सरल आकार दें: नाम + छोटा पता + सुई।"""
    display = item.get("display_name", "")
    parts = [p.strip() for p in display.split(", ") if p.strip()]
    name = parts[0] if parts else display
    # पता: नाम के बाद के 2 हिस्से (इलाका + शहर) — pincode/desh छोड़ें
    area_parts = [p for p in parts[1:3] if not p.isdigit()]
    return {
        "name": name,
        "area": ", ".join(area_parts),
        "lat": float(item["lat"]),
        "lon": float(item["lon"]),
    }


@router.get("/search-places")
async def search_places(
    q: str = Query(..., min_length=2, max_length=80),
    state: str = Query("Delhi", max_length=40),
    tenant_id: int = Depends(get_current_tenant_id),  # noqa: ARG001 - लॉगिन ज़रूरी
) -> list[dict]:
    """
    जगह के नाम से सुझाव खोजें (state के अंदर)।

    रणनीति: पहले "नाम, राज्य, भारत" से सटीक खोज; खाली रहे तो
    "नाम राज्य" से ढीली खोज — पर नतीजे में राज्य का नाम होना चाहिए
    (दूसरे राज्य की गलत जगह न चुने — _geocode_place वाली ही सीख)।
    """
    queries = [
        (f"{q}, {state}, India", False),
        (f"{q} {state}", False),
        (q, True),  # सिर्फ़ नाम — राज्य-जाँच के साथ
    ]
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            for query, need_state_check in queries:
                resp = await client.get(
                    _NOMINATIM_URL,
                    params={
                        "q": query,
                        "format": "json",
                        "limit": 6,
                        "countrycodes": "in",
                        "addressdetails": 1,
                    },
                    headers=_HEADERS,
                )
                items = resp.json()
                if not items:
                    continue
                if need_state_check:
                    items = [
                        it
                        for it in items
                        if state.lower() in it.get("display_name", "").lower()
                    ]
                if items:
                    # नाम+पता जोड़ी से नकल हटाएँ
                    seen: set[tuple] = set()
                    out: list[dict] = []
                    for it in items:
                        s = _simplify(it)
                        key = (s["name"].lower(), s["area"].lower())
                        if key in seen:
                            continue
                        seen.add(key)
                        out.append(s)
                        if len(out) >= 6:
                            break
                    return out
    except Exception as exc:  # नेटवर्क/पार्स गड़बड़ी — खाली सुझाव, ऐप नहीं रुकेगी
        logger.warning("place search failed for %r: %s", q, exc)
    return []
