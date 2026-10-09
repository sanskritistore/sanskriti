# -*- coding: utf-8 -*-
"""फ़ोटो स्टूडियो — दुकानदार की साधारण photo → studio जैसी photo।

पाइपलाइन (सब अपने server पर, ₹0 खर्च):
  1. rembg (u2netp) से background हटाओ
  2. सफ़ेद background पर लगाओ, product को centre करो
  3. हल्की sharpening — photo crisp दिखे
  4. चाहो तो नीचे पट्टी में नाम/दाम लिखो (हिंदी+English दोनों)

ध्यान: Render free tier (512MB) पर चलता है — input पहले 900px पर
छोटा करते हैं ताकि memory में रहे। एक ही rembg session बार-बार
इस्तेमाल होता है (module singleton)।
"""
import base64
import io
import logging
import textwrap
from pathlib import Path

import anyio
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.core.images import compress_data_uri

logger = logging.getLogger(__name__)

# fonts — repo में bundled (Docker slim image में system fonts नहीं होते)
_FONTS_DIR = Path(__file__).resolve().parents[2] / "assets" / "fonts"
_FONT_HI = _FONTS_DIR / "NotoSansDevanagari-Bold.ttf"
_FONT_LAT = _FONTS_DIR / "DejaVuSans-Bold.ttf"

# rembg session — पहली बार बनाने में model load होता है, फिर तेज़
_session = None

# रंग (CSC/संस्कृति brand)
_NAVY = (13, 27, 42)
_YELLOW = (255, 196, 0)
_WHITE = (255, 255, 255)


def _get_session():
    """u2netp session — हल्का model (4.7MB), free tier पर भी चलता है।"""
    global _session
    if _session is None:
        from rembg import new_session

        logger.info("photo_studio: rembg u2netp session बन रहा है…")
        _session = new_session("u2netp")
    return _session


def _decode_image(data_uri: str) -> Image.Image:
    """data URI या plain base64 → PIL RGB image (≤900px)।"""
    if data_uri.startswith("data:"):
        data_uri = data_uri.split(",", 1)[1]
    raw = base64.b64decode(data_uri)
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    img.thumbnail((900, 900), Image.LANCZOS)  # memory बचत
    return img


def _remove_background(img: Image.Image) -> Image.Image:
    """rembg से background हटाओ → RGBA (alpha channel के साथ)।"""
    from rembg import remove

    return remove(img, session=_get_session())


def _on_white_centered(rgba: Image.Image, margin_ratio: float = 0.10) -> Image.Image:
    """RGBA product → सफ़ेद canvas पर centred, चारों ओर हल्का margin।"""
    alpha = rgba.split()[-1]
    bbox = alpha.getbbox()
    if bbox:
        rgba = rgba.crop(bbox)
    pw, ph = rgba.size
    side = int(max(pw, ph) * (1 + 2 * margin_ratio))
    canvas = Image.new("RGB", (side, side), _WHITE)
    x = (side - pw) // 2
    y = (side - ph) // 2
    canvas.paste(rgba, (x, y), rgba)
    return canvas


def _runs(text: str, size: int):
    """Devanagari + Latin अलग-अलग fonts से (QR cards वाली तरकीब)।"""
    parts, cur, cur_dev = [], "", None
    for ch in text:
        dev = 0x0900 <= ord(ch) <= 0x097F
        if cur_dev is None or dev == cur_dev:
            cur += ch
            cur_dev = dev
        else:
            parts.append((cur, cur_dev))
            cur, cur_dev = ch, dev
    if cur:
        parts.append((cur, cur_dev))
    out = []
    for t, dev in parts:
        path = _FONT_HI if dev else _FONT_LAT
        try:
            f = ImageFont.truetype(str(path), size, layout_engine=ImageFont.Layout.RAQM)
        except Exception:
            f = ImageFont.load_default()
        out.append((t, f))
    return out


def _add_text_band(img: Image.Image, text: str) -> Image.Image:
    """नीचे navy पट्टी + yellow लिखावट (max 2 lines, छोटा करके fit)।"""
    text = text.strip()
    if not text:
        return img
    w, h = img.size
    band_h = int(h * 0.16)
    canvas = Image.new("RGB", (w, h + band_h), _WHITE)
    canvas.paste(img, (0, 0))
    d = ImageDraw.Draw(canvas)
    d.rectangle([0, h, w, h + band_h], fill=_NAVY)

    lines = textwrap.wrap(text, 24)[:2]
    size = int(band_h * (0.42 if len(lines) == 1 else 0.30))
    line_h = int(size * 1.35)
    y = h + (band_h - line_h * len(lines)) // 2
    for line in lines:
        parts = _runs(line, size)
        total = sum(d.textlength(t, font=f) for t, f in parts)
        x = (w - total) / 2
        for t, f in parts:
            d.text((x, y), t, font=f, fill=_YELLOW)
            x += d.textlength(t, font=f)
        y += line_h
    return canvas


async def enhance_photo(image_data_uri: str, text: str | None = None) -> str:
    """मुख्य काम: साधारण photo → white-bg studio photo (+ वैकल्पिक लिखावट)।

    लौटाता है: compressed data URI (DB में सीधे सेव हो सके)।
    कोई भी step fail हो तो साफ़ error — photo कभी चुपचाप नहीं खोती।
    """
    img = _decode_image(image_data_uri)
    rgba = await anyio.to_thread.run_sync(_remove_background, img)
    photo = _on_white_centered(rgba)
    # हल्की sharpening — print/phone दोनों पर crisp दिखे
    photo = photo.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=3))
    if text:
        photo = _add_text_band(photo, text)

    buf = io.BytesIO()
    photo.save(buf, "WEBP", quality=88, method=6)
    uri = "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()
    return compress_data_uri(uri)
