"""
टारगेटिंग राउटर - जगह खोज सेवा (autocomplete)

Tenant को असली सुझाव दिखाने के लिए: नाम लिखते ही पते के साथ
सुझाव आते हैं (जैसे "Aakash Institute — Janakpuri, New Delhi")।
User सही जगह चुनता है → अक्षांश/देशांतर तुरंत lock → launch पर
अंदाज़ा नहीं, पक्का पता जाता है (user की माँग 08-10:
"pehle state, fir search bar, kai locations ek sath lock").

दो मुफ़्त सेवाएँ (08-10 सीख — user का "Homoeopathic Medical College"
केवल Photon पर मिला, Nominatim पर नहीं):
1. Photon (komoot) — मुख्य: fuzzy typeahead, आधे-अधूरे नाम भी पकड़ता है
2. Nominatim (OSM) — सहायक: सख़्त पर कभी-कभी अलग नतीजे देता है
दोनों OpenStreetMap data चलाती हैं — Google जितना India POI data
नहीं; जो सचमुच न मिले, उसके लिए frontend में "नक्शे से सुई" रास्ता है।
"""

import logging

import httpx
from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_tenant_id

logger = logging.getLogger("sanskriti.targeting")

router = APIRouter()

_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_PHOTON_URL = "https://photon.komoot.io/api/"
_HEADERS = {"User-Agent": "SanskritiAds/1.0 (local business ads)"}


def _simplify_nominatim(item: dict) -> dict:
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


def _simplify_photon(item: dict) -> dict | None:
    """Photon नतीजे को सरल आकार दें; भारत के बाहर का हो तो None।"""
    props = item.get("properties", {})
    if (props.get("countrycode") or "").lower() not in ("in", ""):
        return None
    name = props.get("name")
    if not name:
        return None
    area = ", ".join(
        p
        for p in [
            props.get("street") or props.get("locality") or "",
            props.get("district") or props.get("city") or "",
        ]
        if p
    )[:80]
    lon, lat = item["geometry"]["coordinates"][:2]
    return {"name": name, "area": area, "lat": float(lat), "lon": float(lon)}


def _dedupe(items: list[dict], limit: int = 6) -> list[dict]:
    """नाम+पता जोड़ी से नकल हटाकर सीमा तक लौटाएँ।"""
    seen: set[tuple] = set()
    out: list[dict] = []
    for s in items:
        key = (s["name"].lower(), s["area"].lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
        if len(out) >= limit:
            break
    return out


@router.get("/search-places")
async def search_places(
    q: str = Query(..., min_length=2, max_length=80),
    state: str = Query("Delhi", max_length=40),
    tenant_id: int = Depends(get_current_tenant_id),  # noqa: ARG001 - लॉगिन ज़रूरी
) -> list[dict]:
    """
    जगह के नाम से सुझाव खोजें (state के अंदर)।

    रणनीति: Photon (fuzzy) पहले — पूरा नाम, फिर आख़िरी शब्द गिराकर;
    कम नतीजों पर Nominatim से भरपाई। राज्य-मेल वाले पहले रखते हैं।
    """
    found: list[dict] = []
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            # ── 1. Photon: fuzzy typeahead (आधा नाम भी चलता है) ──
            words = q.split()
            queries = [q]
            if len(words) > 2:
                queries.append(" ".join(words[:-1]))  # आख़िरी शब्द गिराकर फिर
            for query in queries:
                resp = await client.get(
                    _PHOTON_URL,
                    params={"q": f"{query} {state}", "limit": 8},
                    headers=_HEADERS,
                )
                feats = resp.json().get("features", [])
                found.extend(s for s in (_simplify_photon(f) for f in feats) if s)
                if len(_dedupe(found)) >= 3:
                    break  # काफ़ी मिल गए

            # ── 2. Nominatim: भरपाई (कभी-कभी अलग नतीजे देता है) ──
            if len(_dedupe(found)) < 3:
                resp = await client.get(
                    _NOMINATIM_URL,
                    params={
                        "q": f"{q}, {state}, India",
                        "format": "json",
                        "limit": 6,
                        "countrycodes": "in",
                        "addressdetails": 1,
                    },
                    headers=_HEADERS,
                )
                found.extend(_simplify_nominatim(it) for it in resp.json())
    except Exception as exc:  # नेटवर्क/पार्स गड़बड़ी — खाली सुझाव, ऐप नहीं रुकेगी
        logger.warning("place search failed for %r: %s", q, exc)

    # राज्य-मेल वाले ऊपर, बाक़ी नीचे (दूसरे राज्य की गलत जगह न चुने)
    unique = _dedupe(found, limit=10)
    in_state = [s for s in unique if state.lower() in s["area"].lower()]
    others = [s for s in unique if state.lower() not in s["area"].lower()]
    return (in_state + others)[:6]
