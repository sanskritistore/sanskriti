"""
⭐ Review Card Generator — carousel ad का आख़िरी card।

(10-10 user माँग: "reviews भी दिखें ताकि लोगों को पता चले यह fake नहीं है")

Tenant की असली Google rating से 1080x1080 तस्वीर बनाता है — PIL से,
कोई बाहरी service नहीं। Devanagari font repo में bundled है ताकि
Render (या किसी भी server) पर चले।
"""

import tempfile
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

_FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
_FONT_BOLD = str(_FONT_DIR / "NotoSansDevanagari-Bold.ttf")
_FONT_REG = str(_FONT_DIR / "NotoSansDevanagari-Regular.ttf")
_FONT_LATIN = str(_FONT_DIR / "DejaVuSans-Bold.ttf")  # Latin नामों के लिए

# User की पसंद (09-10): dark professional blue/navy, कोई खाली जगह नहीं
_BG = (13, 27, 62)        # गहरा navy
_GOLD = (255, 193, 7)     # सितारों का सुनहरा
_WHITE = (245, 247, 250)
_SOFT = (160, 175, 200)   # हल्का नीला-स्लेट


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def _draw_star(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float, fill):
    """5-नुकीला सुनहरा सितारा — font ★ glyph नहीं देती, इसलिए खुद बनाते हैं।"""
    points = []
    for i in range(10):
        radius = r if i % 2 == 0 else r * 0.42
        angle = math.radians(i * 36 - 90)
        points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    d.polygon(points, fill=fill)


def generate_review_card(
    business_name: str,
    rating: float,
    reviews_count: int,
) -> str:
    """
    1080x1080 review card बनाकर local JPEG path लौटाएँ।

    Layout (ऊपर→नीचे, कोई खाली जगह नहीं):
      ★★★★★  (PIL से बने सुनहरे सितारे)
      5.0 / 5   (बहुत बड़ी rating)
      गूगल पर {n} असली रिव्यू
      "हमारे ग्राहक, हमारी पहचान"
      — {business_name} —
    """
    size = 1080
    img = Image.new("RGB", (size, size), _BG)
    d = ImageDraw.Draw(img)

    # हल्की सुनहरी border — premium एहसास
    d.rectangle([24, 24, size - 24, size - 24], outline=_GOLD, width=6)

    full_stars = int(round(rating))
    f_rating = _font(_FONT_BOLD, 260)
    f_count = _font(_FONT_REG, 62)
    f_tag = _font(_FONT_BOLD, 66)
    f_biz = _font(_FONT_LATIN, 74)

    def _center(text: str, font, y: int, fill):
        box = d.textbbox((0, 0), text, font=font)
        w = box[2] - box[0]
        d.text(((size - w) / 2, y), text, font=font, fill=fill)

    def _fit_font(path: str, text: str, start: int, max_w: int):
        """लंबी line किनारों से न कटे — font छोटा करके fit करो।"""
        s = start
        while s > 30:
            f = _font(path, s)
            if d.textbbox((0, 0), text, font=f)[2] <= max_w:
                return f
            s -= 4
        return _font(path, 30)

    # सुनहरे सितारे (PIL से — हर font पर चलते हैं)
    star_r, gap = 62, 170
    start_x = (size - gap * 4) / 2
    for i in range(5):
        fill = _GOLD if i < full_stars else (70, 82, 110)
        _draw_star(d, start_x + i * gap, 200, star_r, fill)

    _center(f"{rating:.1f} / 5", f_rating, 300, _WHITE)
    count_text = f"गूगल पर {reviews_count} असली रिव्यू"
    _center(count_text, _fit_font(_FONT_REG, count_text, 62, size - 140), 640, _SOFT)
    _center("हमारे ग्राहक, हमारी पहचान", f_tag, 760, _GOLD)

    # नीचे कारोबार का नाम (लंबा हो तो छोटा करो)
    name = business_name if len(business_name) <= 24 else business_name[:22] + "…"
    _center(f"— {name} —", f_biz, 900, _WHITE)

    tmp = tempfile.NamedTemporaryFile(
        delete=False, suffix=".jpg", prefix="sanskriti-review-"
    )
    img.save(tmp.name, "JPEG", quality=92)
    return tmp.name
