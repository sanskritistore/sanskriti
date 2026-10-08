# -*- coding: utf-8 -*-
"""फ़ोटो auto-compress — server-side सुरक्षा कवच।

नियम: कोई भी base64 photo DB में जाने से पहले यहाँ से गुज़रती है।
कितनी भी भारी photo आए, हमेशा हल्की (resize + JPEG) होकर सेव होती है,
ताकि धीमे network पर भी app तेज़ खुले।
"""
import base64
import io
import logging

from PIL import Image

logger = logging.getLogger(__name__)

# इतने बड़े आकार तक की photo पहले से हल्की मानी जाएगी (छू जाएगी नहीं)
_SKIP_BYTES = 300 * 1024
# अधिकतम आयाम (चौड़ाई/ऊँचाई) — ad/poster के लिए 900px काफ़ी है
_MAX_DIM = 900
# WebP गुणवत्ता — JPEG से ~30% छोटा, दिखने में बराबर
_WEBP_QUALITY = 70


def compress_data_uri(uri: str) -> str:
    """base64 data URI को compress करके लौटाएँ।

    - data URI नहीं है → जैसी है वैसी लौटाएँ
    - पहले से छोटी (<300KB) → वैसी लौटाएँ
    - कोई भी error → original लौटाएँ (photo कभी खोनी नहीं चाहिए)
    """
    if not isinstance(uri, str) or not uri.startswith("data:image"):
        return uri
    try:
        _header, b64 = uri.split(",", 1)
        raw = base64.b64decode(b64)
        if len(raw) <= _SKIP_BYTES:
            return uri
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        img.thumbnail((_MAX_DIM, _MAX_DIM), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, "WEBP", quality=_WEBP_QUALITY, method=6)
        new = buf.getvalue()
        if len(new) >= len(raw):
            return uri  # compress करके कोई फ़ायदा नहीं हुआ
        logger.info(
            "photo compress: %dKB -> %dKB", len(raw) // 1024, len(new) // 1024
        )
        return "data:image/webp;base64," + base64.b64encode(new).decode()
    except Exception:
        logger.warning("photo compress नहीं हो पाई — original रखी", exc_info=True)
        return uri


def data_uri_to_jpeg_bytes(uri: str) -> bytes:
    """data URI (WebP/JPEG/PNG) → JPEG bytes।

    Meta ads सिर्फ़ JPEG/PNG समझती है — WebP नहीं। इसलिए ad में
    photo भेजने से पहले यहाँ से JPEG बनाकर भेजें।
    कोई error हो तो original bytes लौटाएँ।
    """
    try:
        _header, b64 = uri.split(",", 1)
        raw = base64.b64decode(b64)
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=90)
        return buf.getvalue()
    except Exception:
        logger.warning("JPEG conversion fail — original bytes भेजे", exc_info=True)
        return base64.b64decode(uri.split(",", 1)[1])
