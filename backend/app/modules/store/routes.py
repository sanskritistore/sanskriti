"""
स्टोर ऑर्डर routes — customer ऑर्डर → 4K print file → admin pipeline।

11-10 user pipeline (verbatim): "jab customer apni photo frame me set karta he
size, thickness submit karta he to wo frame with photo jo customer ne set ki he
usi size ke according 4k printable admin me download hoga fir waha se second
team use print karegi or acrylic laga kar usme hanging set karke customer ko
dispatch karegi"

- POST /store/orders  → PUBLIC (customer, बिना login) — print file + details save
- GET  /store/orders  → admin (JWT) — ऑर्डर कतार
- GET  /store/orders/{id}/print|preview → admin (JWT) — file download
- PATCH /store/orders/{id} → admin (JWT) — status आगे बढ़ाओ
- DELETE /store/orders/{id} → admin (JWT) — test/रद्द ऑर्डर हटाओ

⚠️ Files अभी instance disk पर हैं (Render free = ephemeral) — production में
object storage (R2/B2) में ले जाना है। Admin को same-day download की आदत डलवाओ।
"""

import json
import time
from pathlib import Path

from fastapi import APIRouter, Body, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from app.api.deps import get_current_tenant_id
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import SanskritiException
from app.models.store_order import StoreOrder

router = APIRouter()

ALLOWED_STATUS = {"new", "printed", "ready", "dispatched", "done", "cancelled"}
SHAPES = {"rect", "rounded", "oval", "circle", "heart", "bean", "egg", "arch", "scallop"}


def valid_shape(s: str) -> bool:
    """Preset shapes + custom:TL,TR,BR,BL (0-100% हर कोना) — photo window कटाई का नियम।"""
    if s in SHAPES:
        return True
    if s.startswith("custom:"):
        try:
            parts = s[7:].split(",")
            return len(parts) == 4 and all(0 <= float(p) <= 100 for p in parts)
        except ValueError:
            return False
    return False


def _store_dir() -> Path:
    """Upload folder — हर call पर ensure (ephemeral disk पर restart के बाद भी)।"""
    d = Path(settings.STORE_UPLOAD_DIR)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _public_dict(o: StoreOrder) -> dict:
    """List में भेजने लायक fields (file paths internal रखो)।"""
    return {
        "id": o.id,
        "order_no": o.order_no,
        "customer_name": o.customer_name,
        "customer_phone": o.customer_phone,
        "customer_address": o.customer_address,
        "frame_id": o.frame_id,
        "frame_name": o.frame_name,
        "ratio": o.ratio,
        "size_label": o.size_label,
        "thickness_mm": o.thickness_mm,
        "price": o.price,
        "status": o.status,
        "has_files": bool(o.print_path or o.print_data),
        "created_at": o.created_at.isoformat() if o.created_at else None,
    }


@router.post("/orders", status_code=201)
async def create_order(
    name: str = Form(...),
    phone: str = Form(...),
    address: str = Form(""),
    frame_id: str = Form(...),
    frame_name: str = Form(...),
    ratio: str = Form("2:3"),
    size_label: str = Form(...),
    size_w: int = Form(...),
    size_h: int = Form(...),
    thickness_mm: int = Form(3),
    price: int = Form(...),
    settings_json: str = Form("{}", alias="settings"),
    print_file: UploadFile = File(...),
    preview_file: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
):
    """PUBLIC: customer का ऑर्डर — जैसी photo set की वैसी 4K file के साथ।"""
    # हल्की validation — गंदा data DB से दूर
    phone = "".join(ch for ch in phone if ch.isdigit())[-10:]
    if len(phone) != 10:
        raise SanskritiException(400, "सही 10 अंकों का मोबाइल भेजें")
    if not name.strip():
        raise SanskritiException(400, "नाम ज़रूरी है")
    try:
        json.loads(settings_json or "{}")
    except Exception:
        raise SanskritiException(400, "settings JSON खराब है")

    o = StoreOrder(
        tenant_id=settings.STORE_TENANT_ID,
        order_no="TMP",
        customer_name=name.strip()[:120],
        customer_phone=phone,
        customer_address=(address or "").strip()[:1000] or None,
        frame_id=frame_id[:40],
        frame_name=frame_name[:120],
        ratio=ratio[:8],
        size_label=size_label[:40],
        size_w=int(size_w),
        size_h=int(size_h),
        thickness_mm=int(thickness_mm),
        price=int(price),
        settings=settings_json,
        status="new",
    )
    db.add(o)
    await db.flush()  # id मिले ताकि order_no बने
    o.order_no = f"SS-{o.id:05d}"

    # files save
    d = _store_dir()
    pdata = await print_file.read()
    if len(pdata) > 60 * 1024 * 1024:  # 60MB से बड़ा नहीं
        raise SanskritiException(400, "print file बहुत बड़ी है")
    ppath = d / f"{o.order_no}_print.jpg"
    ppath.write_bytes(pdata)
    o.print_path = str(ppath)
    o.print_data = pdata
    if preview_file is not None:
        vdata = await preview_file.read()
        vpath = d / f"{o.order_no}_preview.jpg"
        vpath.write_bytes(vdata)
        o.preview_path = str(vpath)
        o.preview_data = vdata

    await db.commit()
    return {"ok": True, "order_no": o.order_no, "id": o.id}


@router.get("/orders")
async def list_orders(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Admin: ऑर्डर कतार — नए सबसे ऊपर।"""
    rows = (
        await db.execute(
            select(StoreOrder)
            .where(StoreOrder.tenant_id == tenant_id)
            .order_by(StoreOrder.id.desc())
            .limit(200)
        )
    ).scalars().all()
    return [_public_dict(o) for o in rows]


def _get_order_or_404(o: StoreOrder | None, tenant_id: int) -> StoreOrder:
    if not o or o.tenant_id != tenant_id:
        raise SanskritiException(404, "ऑर्डर नहीं मिला")
    return o


@router.get("/orders/{oid}/print")
async def download_print(
    oid: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Admin: 4K print file download — यही print team को जाती है।"""
    o = _get_order_or_404(
        (await db.execute(select(StoreOrder).where(StoreOrder.id == oid))).scalar_one_or_none(),
        tenant_id,
    )
    if o.print_data:
        return Response(content=bytes(o.print_data), media_type="image/jpeg",
                        headers={"Content-Disposition": f'attachment; filename="{o.order_no}_print.jpg"'})
    if not o.print_path or not Path(o.print_path).exists():
        raise SanskritiException(404, "print file नहीं मिली (disk साफ हुई होगी)")
    dpi = ""
    try:
        dpi = f"_{json.loads(o.settings or '{}').get('dpi', 300)}dpi"
    except Exception:
        pass
    return FileResponse(
        o.print_path,
        media_type="image/jpeg",
        filename=f"{o.order_no}_{o.size_label.replace(' ', '')}{dpi}.jpg",
    )


@router.get("/orders/{oid}/preview")
async def download_preview(
    oid: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Admin: छोटी preview image (list में दिखाने के लिए)।"""
    o = _get_order_or_404(
        (await db.execute(select(StoreOrder).where(StoreOrder.id == oid))).scalar_one_or_none(),
        tenant_id,
    )
    if o.preview_data or o.print_data:
        return Response(content=bytes(o.preview_data or o.print_data), media_type="image/jpeg")
    path = o.preview_path or o.print_path
    if not path or not Path(path).exists():
        raise SanskritiException(404, "preview नहीं मिली")
    return FileResponse(path, media_type="image/jpeg")


class StatusUpdate(BaseModel):
    """status बदलने की स्कीमा।"""

    status: str


@router.patch("/orders/{oid}")
async def update_status(
    oid: int,
    payload: StatusUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Admin: pipeline status आगे बढ़ाओ (new→printed→ready→dispatched→done)।"""
    if payload.status not in ALLOWED_STATUS:
        raise SanskritiException(400, f"status इनमें से हो: {sorted(ALLOWED_STATUS)}")
    o = _get_order_or_404(
        (await db.execute(select(StoreOrder).where(StoreOrder.id == oid))).scalar_one_or_none(),
        tenant_id,
    )
    o.status = payload.status
    await db.commit()
    return {"ok": True, "order_no": o.order_no, "status": o.status}


@router.delete("/orders/{oid}")
async def delete_order(
    oid: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Admin: test/रद्द ऑर्डर हटाओ (files भी)।"""
    o = _get_order_or_404(
        (await db.execute(select(StoreOrder).where(StoreOrder.id == oid))).scalar_one_or_none(),
        tenant_id,
    )
    for p in (o.print_path, o.preview_path):
        if p and Path(p).exists():
            try:
                Path(p).unlink()
            except Exception:
                pass
    await db.delete(o)
    await db.commit()
    return {"ok": True}


# ============================================================
# Frame Maker — owner खुद नए frames बनाए (11-10 user माँग)
# ============================================================

from app.models.store_frame import StoreFrame  # noqa: E402


def _frame_dict(
    f: StoreFrame,
    img_len: int | None = None,
    samp_len: int | None = None,
    glare_len: int | None = None,
    glare2_len: int | None = None,
    mask_len: int | None = None,
) -> dict:
    """Store frontend को चाहिए fields (config frames.json जैसी shape)।
    list endpoint lengths पास करता है (octet_length — भारी bytes load किए बिना पता चलता है)।"""
    has_img = (img_len > 0) if img_len is not None else bool(f.img_path or f.img_data)
    has_img = has_img or bool(f.img_path)
    has_samp = (samp_len > 0) if samp_len is not None else bool(f.samp_data)
    has_glare = (glare_len > 0) if glare_len is not None else bool(f.glare_data)
    has_glare2 = (glare2_len > 0) if glare2_len is not None else bool(f.glare2_data)
    return {
        "id": f.frame_id,
        "name": f.name,
        "en": "Custom",
        "shape": f.shape,
        "style": "stl-img",
        "ratio": f.ratio,
        "ar": f.ar,
        "base": f.base,
        "rating": f.rating,
        "window": json.loads(f.window),
        "img": f"/api/v1/store/frames/{f.id}/img" if has_img else "",
        "samp": f"/api/v1/store/frames/{f.id}/sample" if has_samp else "",
        # ?v=mask_len — mask बदलते ही URL बदल जाए → browser पुराना cached mask कभी न दिखाए
        # (12-10 रात bug: टूटा 19B mask 24h cache हो गया था, server ठीक होने के बाद भी photo गायब रही)
        "mask": f"/api/v1/store/frames/{f.id}/mask?v={mask_len or 0}" if has_img else "",
        "samp_pos": f.samp_pos or "",
        "glare_set": f.glare_set or "",
        "glare": f"/api/v1/store/frames/{f.id}/glare" if has_glare else "",
        "glare2": f"/api/v1/store/frames/{f.id}/glare2" if has_glare2 else "",
        "draw": json.loads(f.draw) if f.draw else None,
        "ptype": f.ptype,
        "code": f.code or "",
    }


# भारी binary columns — list endpoint इन्हें load नहीं करता (45 frames × 1-2MB = RAM खत्म, 12-10 रात)
_FRAME_HEAVY = (
    defer(StoreFrame.img_data),
    defer(StoreFrame.samp_data),
    defer(StoreFrame.glare_data),
    defer(StoreFrame.glare2_data),
    defer(StoreFrame.mask_data),
    defer(StoreFrame.thumb_data),
)


@router.get("/frames")
async def list_custom_frames(db: AsyncSession = Depends(get_db)):
    """PUBLIC: सभी active custom frames — store pages इन्हें static config से merge करते हैं।
    भारी bytes की जगह सिर्फ उनकी LENGTH आती है — हज़ार frames पर भी list हल्की रहेगी।"""
    rows = (
        await db.execute(
            select(
                StoreFrame,
                func.octet_length(StoreFrame.img_data).label("img_len"),
                func.octet_length(StoreFrame.samp_data).label("samp_len"),
                func.octet_length(StoreFrame.glare_data).label("glare_len"),
                func.octet_length(StoreFrame.glare2_data).label("glare2_len"),
                func.octet_length(StoreFrame.mask_data).label("mask_len"),
            )
            .options(*_FRAME_HEAVY)
            .where(StoreFrame.active == True)  # noqa: E712
            .order_by(StoreFrame.id)
        )
    ).all()
    return [
        _frame_dict(f, img_len=il or 0, samp_len=sl or 0, glare_len=gl or 0, glare2_len=g2 or 0, mask_len=ml or 0)
        for f, il, sl, gl, g2, ml in rows
    ]


@router.post("/frames", status_code=201)
async def create_frame(
    name: str = Form(...),
    shape: str = Form("rect"),
    ratio: str = Form("2:3"),
    ar: str = Form("2/3"),
    base: int = Form(399),
    rating: float = Form(4.5),
    window: str = Form("{}"),
    draw: str = Form(""),
    ptype: str = Form("frame"),
    img_file: UploadFile = File(None),
    sample_file: UploadFile = File(None),
    sample_settings: str = Form(""),
    mask_file: UploadFile = File(None),
    thumb_file: UploadFile = File(None),
    display_file: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Admin: नया custom frame — PNG border + photo window (%) + pricing + sample photo (card में दिखने वाली)।"""
    if not valid_shape(shape):
        raise SanskritiException(400, "shape अमान्य — preset या custom:TL,TR,BR,BL (0-100)")
    try:
        w = json.loads(window)
        for k in ("x", "y", "w", "h"):
            float(w[k])
    except Exception:
        raise SanskritiException(400, "window JSON खराब है — {x,y,w,h} चाहिए")

    if ptype not in {"frame", "acrylic", "album"}:
        raise SanskritiException(400, "ptype: frame/acrylic/album")
    f = StoreFrame(
        tenant_id=tenant_id,
        frame_id="TMP",
        ptype=ptype,
        name=name.strip()[:120],
        shape=shape, ratio=ratio[:8], ar=ar[:12],
        base=int(base), rating=float(rating),
        img_path="", window=window,
    )
    db.add(f)
    await db.flush()
    f.frame_id = f"fr-c{f.id}"
    # पहचान नंबर auto — सबसे छोटा खाली नंबर (12-10 Dev: delete हुए frame का code नए frame को मिले)
    existing = (
        await db.execute(
            select(StoreFrame.code).where(
                StoreFrame.tenant_id == tenant_id,
                StoreFrame.active == True,  # noqa: E712 — delete हुए (soft-off) frames के code छूट जाते हैं
            )
        )
    ).scalars().all()
    used = set()
    for c in existing:
        if c and c.startswith("S") and c[1:].isdigit():
            used.add(int(c[1:]))
    n = 1
    while n in used:
        n += 1
    f.code = f"S{n:03d}"

    if draw:
        try:
            json.loads(draw)
        except Exception:
            raise SanskritiException(400, "draw JSON खराब है")
        f.draw = draw
    if img_file is not None:
        data = await img_file.read()
        if len(data) > 20 * 1024 * 1024:
            raise SanskritiException(400, "PNG बहुत बड़ी है (20MB तक)")
        path = _store_dir() / f"{f.frame_id}.png"
        path.write_bytes(data)
        f.img_path = str(path)
        f.img_data = path.read_bytes()
        f.img_ct = img_file.content_type or "image/png"
        # Client (Maker/browser) से बने variants पहले — server पर decode तभी जब client ने न भेजे हो
        if mask_file is not None:
            f.mask_data = await mask_file.read()
            if not _valid_mask(f.mask_data):
                f.mask_data = None
        if thumb_file is not None:
            f.thumb_data = await thumb_file.read()
        if display_file is not None:
            f.display_data = await display_file.read()
        if f.mask_data is None or f.thumb_data is None or f.display_data is None:
            await _regen_frame_variants(f, data)  # missing/invalid variants server बनाए (2600px तक — OOM guard)
    elif not draw:
        raise SanskritiException(400, "PNG या draw — दोनों में से एक चाहिए")
    if sample_file is not None:
        sdata = await sample_file.read()
        if len(sdata) > 10 * 1024 * 1024:
            raise SanskritiException(400, "sample photo बहुत बड़ी है (10MB तक)")
        f.samp_data = sdata
        f.samp_ct = sample_file.content_type or "image/webp"

    await db.commit()
    return {"ok": True, "frame": _frame_dict(f, mask_len=len(f.mask_data) if f.mask_data else 0)}


# Downscaled card-size frame imgs — 12-10 रात: cards को 5400px PNG नहीं, 600px webp चाहिए (20x हल्का)
_IMG_THUMB_CACHE: dict = {}  # (fid, w) -> (img_len, webp_bytes)


def _frame_thumb_webp(data: bytes, w: int):
    """frame PNG को w px चौड़ा webp में बदलो (alpha रखो — border transparent होती है)।"""
    import io as _io

    from PIL import Image
    im = Image.open(_io.BytesIO(data))
    if max(im.size) > 2600:  # OOM guard (12-10 रात) — बड़ी PNG का thumb Maker (browser) से आता है
        return None
    im = im.convert("RGBA")
    if im.width > w:
        im = im.resize((w, max(1, round(im.height * w / im.width))), Image.LANCZOS)
    out = _io.BytesIO()
    im.save(out, "WEBP", quality=82, method=4)
    return out.getvalue()


@router.get("/frames/{fid}/img")
async def frame_image(fid: int, w: int = 0, db: AsyncSession = Depends(get_db)):
    """PUBLIC: frame की PNG border (store pages पर दिखती है)। ?w=600 = छोटा webp (cards)।"""
    import asyncio

    f = (
        await db.execute(select(StoreFrame).where(StoreFrame.id == fid))
    ).scalar_one_or_none()
    if f and f.img_data:
        data = bytes(f.img_data)
        if w and 60 <= w <= 2000:
            thumb = None
            if w == 600 and f.thumb_data:  # standard card size — DB से हमेशा तुरंत
                thumb = bytes(f.thumb_data)
            elif w == 1600 and f.display_data:  # preview page size — DB से (12-10 रात)
                thumb = bytes(f.display_data)
            else:
                key = (f.id, w)
                hit = _IMG_THUMB_CACHE.get(key)
                if hit and hit[0] == len(data):
                    thumb = hit[1]
            if thumb is None:
                thumb = await asyncio.to_thread(_frame_thumb_webp, data, w)
                if thumb is not None and w in (600, 1600):  # एक बार generate → DB में हमेशा के लिए
                    if w == 600:
                        f.thumb_data = thumb
                    else:
                        f.display_data = thumb
                    try:
                        await db.commit()
                    except Exception:
                        pass
                if thumb is not None:
                    if len(_IMG_THUMB_CACHE) > 400:
                        _IMG_THUMB_CACHE.pop(next(iter(_IMG_THUMB_CACHE)))
                    _IMG_THUMB_CACHE[(f.id, w)] = (len(data), thumb)
            if thumb is None:  # PNG बहुत बड़ी (OOM guard) — full PNG ही भेजो (काम चले, धीमा पर सही)
                return Response(
                    content=data,
                    media_type=f.img_ct or "image/png",
                    headers={"Cache-Control": "public, max-age=86400"},
                )
            return Response(
                content=thumb,
                media_type="image/webp",
                headers={"Cache-Control": "public, max-age=86400"},
            )
        return Response(
            content=data,
            media_type=f.img_ct or "image/png",
            headers={"Cache-Control": "public, max-age=86400"},
        )
    if not f or not Path(f.img_path).exists():
        raise SanskritiException(404, "frame image नहीं मिली")
    return FileResponse(f.img_path, media_type="image/png")


@router.get("/frames/{fid}/sample")
async def frame_sample(fid: int, db: AsyncSession = Depends(get_db)):
    """PUBLIC: frame की sample photo (cards में photo की जगह दिखती है)।"""
    f = (
        await db.execute(select(StoreFrame).where(StoreFrame.id == fid))
    ).scalar_one_or_none()
    if not f or not f.samp_data:
        raise SanskritiException(404, "sample photo नहीं मिली")
    return Response(content=bytes(f.samp_data), media_type=f.samp_ct or "image/webp")


# --- PNG transparency → photo mask (12-10 शाम, Dev: "PNG का अंदरूनी हिस्सा अपने-आप photo area बने") ---
# हर frame की heart/design अलग है — fixed shape dropdown कभी fit नहीं होता।
# इसलिए PNG के अंदरूनी transparent हिस्से से ही mask बनता है: white = photo area, black = बाकी।
# कोई भी shape चलेगी — heart, star, flower, multi-curve — कुछ hardcode नहीं।
# SPEED (12-10 रात, Dev: "site slow ho gai"): 320px + bytes-based alpha + to_thread —
# free server पर event loop कभी block न हो, हर mask ~100ms में।


def _frame_mask_png(data: bytes):
    """PNG border के अंदरूनी transparent window का mask बनाओ (window bbox तक cropped)।
    center से flood-fill — Frame Maker के autoWindow जैसा ही तरीका, server-side।
    None = कोई अंदरूनी transparent हिस्सा नहीं (mask ज़रूरी नहीं)।"""
    import io as _io

    from PIL import Image
    im = Image.open(_io.BytesIO(data))
    # OOM guard (12-10 रात): 5400px RGBA decode = 116MB+ — free server (512MB) मर जाता है।
    # बड़ी PNG का mask Maker (browser) से आता है; server सिर्फ छोटी PNG के लिए fallback।
    if max(im.size) > 2600:
        return None
    im = im.convert("RGBA")
    sc = min(1.0, 320 / max(im.size))
    w = max(60, round(im.width * sc))
    h = max(60, round(im.height * sc))
    alpha = im.resize((w, h)).getchannel("A").tobytes()  # bytes indexing — px[x,y] से कई गुना तेज़
    wh = w * h

    def tr(p):
        return alpha[p] < 16

    c0 = (h // 2) * w + (w // 2)
    if not tr(c0):  # center opaque — पास से transparent शुरुआत ढूँढो (नोक वाली shapes)
        found = -1
        cx, cy = w // 2, h // 2
        r = 2
        while r < min(w, h) // 3 and found < 0:
            for dx in range(-r, r + 1, 3):
                for dy in range(-r, r + 1, 3):
                    x, y = cx + dx, cy + dy
                    if 0 <= x < w and 0 <= y < h and tr(y * w + x):
                        found = y * w + x
                        break
                if found >= 0:
                    break
            r += 3
        if found < 0:
            return None
        c0 = found
    seen = bytearray(wh)
    stack = [c0]
    seen[c0] = 1
    n = 0
    x0, y0, x1, y1 = w, h, -1, -1
    while stack:
        p = stack.pop()
        n += 1
        x = p % w
        y = p // w
        if x < x0:
            x0 = x
        if x > x1:
            x1 = x
        if y < y0:
            y0 = y
        if y > y1:
            y1 = y
        if x > 0 and not seen[p - 1] and tr(p - 1):
            seen[p - 1] = 1
            stack.append(p - 1)
        if x < w - 1 and not seen[p + 1] and tr(p + 1):
            seen[p + 1] = 1
            stack.append(p + 1)
        if y > 0 and not seen[p - w] and tr(p - w):
            seen[p - w] = 1
            stack.append(p - w)
        if y < h - 1 and not seen[p + w] and tr(p + w):
            seen[p + w] = 1
            stack.append(p + w)
    if n < wh * 0.005:  # बहुत छोटा हिस्सा — असली window नहीं
        return None
    # mask = window bbox तक crop — storefront photo div भी वही bbox होता है (100% fill = perfect fit)
    # RGBA: CSS mask alpha channel देखता है — window = opaque white, बाकी = पूरी transparent
    mw, mh = x1 - x0 + 1, y1 - y0 + 1
    buf = bytearray(mw * mh * 4)
    for yy in range(y0, y1 + 1):
        base = yy * w
        ob = (yy - y0) * mw * 4
        for xx in range(x0, x1 + 1):
            if seen[base + xx]:
                o = ob + (xx - x0) * 4
                buf[o] = buf[o + 1] = buf[o + 2] = buf[o + 3] = 255
    mk = Image.frombytes("RGBA", (mw, mh), bytes(buf))
    out = _io.BytesIO()
    mk.save(out, "PNG", optimize=True)
    return out.getvalue()


@router.post("/frames/{fid}/variants")
async def upload_frame_variants(
    fid: int,
    mask_file: UploadFile | None = File(None),
    thumb_file: UploadFile | None = File(None),
    display_file: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Admin: browser/Maker से बने mask + card thumb सीधे save करो (12-10 रात)।
    भारी काम client-side — free server कभी 5400px PNG decode करके OOM न मरे।"""
    f = (
        await db.execute(select(StoreFrame).where(StoreFrame.id == fid))
    ).scalar_one_or_none()
    if not f or f.tenant_id != tenant_id:
        raise SanskritiException(404, "frame नहीं मिला")
    saved = []
    if mask_file is not None:
        f.mask_data = await mask_file.read()
        if not _valid_mask(f.mask_data):
            f.mask_data = None
        saved.append("mask")
    if thumb_file is not None:
        f.thumb_data = await thumb_file.read()
        saved.append("thumb")
    if display_file is not None:
        f.display_data = await display_file.read()
        saved.append("display")
    if not saved:
        raise SanskritiException(400, "mask_file या thumb_file चाहिए")
    await db.commit()
    return {"ok": True, "saved": saved}


def _valid_mask(b: bytes | None) -> bool:
    """असली PNG mask है? (12-10 रात: client bug से 19-byte कचरा mask save हुआ था —
    photo गायब हो गई थी। अब टूटा mask = None मानो → server खुद सही बनाए।)"""
    return bool(b) and len(b) >= 100 and b[:4] == b"\x89PNG"


async def _regen_frame_variants(f: StoreFrame, data: bytes) -> None:
    """PNG बदलते ही mask + card thumb दोबारा बनाकर DB में save करो (background thread में CPU)।"""
    import asyncio

    try:
        f.mask_data = await asyncio.to_thread(_frame_mask_png, data)
    except Exception:
        f.mask_data = None
    try:
        f.thumb_data = await asyncio.to_thread(_frame_thumb_webp, data, 600)
    except Exception:
        f.thumb_data = None
    try:
        f.display_data = await asyncio.to_thread(_frame_thumb_webp, data, 1600)  # preview page
    except Exception:
        f.display_data = None


@router.get("/frames/{fid}/mask")
async def frame_mask(fid: int, db: AsyncSession = Depends(get_db)):
    """PUBLIC: frame PNG के अंदरूनी transparent हिस्से का mask (photo इसी shape में कटेगी)।
    एक बार generate → DB में हमेशा के लिए — cold start पर दोबारा CPU काम नहीं (12-10 रात)।"""
    import asyncio

    f = (
        await db.execute(select(StoreFrame).where(StoreFrame.id == fid))
    ).scalar_one_or_none()
    if not f:
        raise SanskritiException(404, "frame नहीं मिला")
    m = bytes(f.mask_data) if f.mask_data else None
    if m is None:
        data = bytes(f.img_data) if f.img_data else None
        if data is None and f.img_path and Path(f.img_path).exists():
            data = Path(f.img_path).read_bytes()
        if not data:
            raise SanskritiException(404, "frame image नहीं मिली")
        # CPU काम अलग thread में — free server पर बाकी requests (site) कभी अटकें नहीं
        m = await asyncio.to_thread(_frame_mask_png, data)
        if m is None:
            raise SanskritiException(404, "इस PNG में अंदरूनी transparent window नहीं")
        f.mask_data = m  # अगली बार तुरंत DB से — generation सिर्फ एक बार
        try:
            await db.commit()
        except Exception:
            pass  # save fail हो तो भी इस request का जवाब मिले
    return Response(
        content=m,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},  # browser एक दिन cache रखे — बार-बार server बोझ नहीं
    )


@router.post("/frames/{fid}/sample")
async def update_frame_sample(
    fid: int,
    sample_file: UploadFile = File(...),
    settings: str = Form(None),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Admin: मौजूदा frame की sample photo बदलो (frame दोबारा बनाने की ज़रूरत नहीं)।"""
    f = (
        await db.execute(select(StoreFrame).where(StoreFrame.id == fid))
    ).scalar_one_or_none()
    if not f or f.tenant_id != tenant_id:
        raise SanskritiException(404, "frame नहीं मिला")
    sdata = await sample_file.read()
    if len(sdata) > 10 * 1024 * 1024:
        raise SanskritiException(400, "sample photo बहुत बड़ी है (10MB तक)")
    f.samp_data = sdata
    f.samp_ct = sample_file.content_type or "image/webp"
    if settings:
        try:
            sp = json.loads(settings)
            f.samp_pos = json.dumps({"z": max(100, min(300, int(sp.get("z", 100)))),
                                     "mx": max(0, min(100, int(sp.get("mx", 50)))),
                                     "my": max(0, min(100, int(sp.get("my", 50))))})
        except Exception:
            pass
    await db.commit()
    return {"ok": True, "samp": f"/api/v1/store/frames/{f.id}/sample"}



@router.post("/frames/{fid}/img")
async def update_frame_img(
    fid: int,
    img_file: UploadFile = File(...),
    mask_file: UploadFile = File(None),
    thumb_file: UploadFile = File(None),
    display_file: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Admin: मौजूदा frame की PNG border बदलो/वापस लाओ — frame दोबारा बनाने की ज़रूरत नहीं।
    img_data DB में भी लिखते हैं ताकि ephemeral disk साफ होने पर भी PNG बची रहे (11-10, fr-c25 घायल हुआ था)।"""
    f = (
        await db.execute(select(StoreFrame).where(StoreFrame.id == fid))
    ).scalar_one_or_none()
    if not f or f.tenant_id != tenant_id:
        raise SanskritiException(404, "frame नहीं मिला")
    data = await img_file.read()
    if len(data) > 20 * 1024 * 1024:
        raise SanskritiException(400, "PNG बहुत बड़ी है (20MB तक)")
    path = _store_dir() / f"{f.frame_id}.png"
    path.write_bytes(data)
    f.img_path = str(path)
    f.img_data = data
    f.img_ct = img_file.content_type or "image/png"
    if mask_file is not None:
        f.mask_data = await mask_file.read()
        if not _valid_mask(f.mask_data):
            f.mask_data = None
    if thumb_file is not None:
        f.thumb_data = await thumb_file.read()
    if display_file is not None:
        f.display_data = await display_file.read()
    if f.mask_data is None or f.thumb_data is None or f.display_data is None:
        await _regen_frame_variants(f, data)  # missing/invalid variants server बनाए (2600px तक — OOM guard)
    await db.commit()
    return {"ok": True, "img": f"/api/v1/store/frames/{f.id}/img"}


@router.get("/frames/{fid}/glare")
async def get_frame_glare(fid: int, db: AsyncSession = Depends(get_db)):
    """Public: frame की custom reflection PNG (DB से — deploy-proof)।"""
    f = (
        await db.execute(select(StoreFrame).where(StoreFrame.id == fid))
    ).scalar_one_or_none()
    if not f or not f.glare_data:
        raise SanskritiException(404, "custom reflection नहीं है")
    return Response(content=f.glare_data, media_type=f.glare_ct or "image/png",
                    headers={"Cache-Control": "public, max-age=3600"})


@router.post("/frames/{fid}/glare")
async def upload_frame_glare(
    fid: int,
    glare_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Admin: frame की अपनी window-reflection PNG upload करो (Dev 11-10)।
    glare_set.gv = version timestamp — browser cache अपने-आप टूटे।"""
    f = (
        await db.execute(select(StoreFrame).where(StoreFrame.id == fid))
    ).scalar_one_or_none()
    if not f or f.tenant_id != tenant_id:
        raise SanskritiException(404, "frame नहीं मिला")
    data = await glare_file.read()
    if len(data) > 5 * 1024 * 1024:
        raise SanskritiException(400, "reflection PNG बहुत बड़ी है (5MB तक)")
    f.glare_data = data
    f.glare_ct = glare_file.content_type or "image/png"
    # version bump → नया URL, पुरानी cache टूटे
    try:
        g = json.loads(f.glare_set) if f.glare_set else {}
    except Exception:
        g = {}
    if not isinstance(g.get("L"), dict):
        g["L"] = {}
    g["L"]["gv"] = int(time.time())
    f.glare_set = json.dumps(g)
    await db.commit()
    return {"ok": True, "glare": f"/api/v1/store/frames/{f.id}/glare"}


@router.get("/frames/{fid}/glare2")
async def get_frame_glare2(fid: int, db: AsyncSession = Depends(get_db)):
    """Public: frame की दाएँ-तरफ़ की custom reflection PNG (दो-खिड़की system, Dev 11-10)।"""
    f = (
        await db.execute(select(StoreFrame).where(StoreFrame.id == fid))
    ).scalar_one_or_none()
    if not f or not f.glare2_data:
        raise SanskritiException(404, "custom reflection नहीं है")
    return Response(content=f.glare2_data, media_type=f.glare2_ct or "image/png",
                    headers={"Cache-Control": "public, max-age=3600"})


@router.post("/frames/{fid}/glare2")
async def upload_frame_glare2(
    fid: int,
    glare_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Admin: दाएँ खिड़की की अपनी PNG upload — glare_set.R.gv bump।"""
    f = (
        await db.execute(select(StoreFrame).where(StoreFrame.id == fid))
    ).scalar_one_or_none()
    if not f or f.tenant_id != tenant_id:
        raise SanskritiException(404, "frame नहीं मिला")
    data = await glare_file.read()
    if len(data) > 5 * 1024 * 1024:
        raise SanskritiException(400, "reflection PNG बहुत बड़ी है (5MB तक)")
    f.glare2_data = data
    f.glare2_ct = glare_file.content_type or "image/png"
    try:
        g = json.loads(f.glare_set) if f.glare_set else {}
    except Exception:
        g = {}
    if not isinstance(g.get("R"), dict):
        g["R"] = {}
    g["R"]["gv"] = int(time.time())
    f.glare_set = json.dumps(g)
    await db.commit()
    return {"ok": True, "glare2": f"/api/v1/store/frames/{f.id}/glare2"}


@router.patch("/frames/{fid}")
async def update_frame(
    fid: int,
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Admin: frame edit — shape/name/base/rating/ratio बदलो (delete की ज़रूरत नहीं)।"""
    f = (
        await db.execute(select(StoreFrame).where(StoreFrame.id == fid))
    ).scalar_one_or_none()
    if not f or f.tenant_id != tenant_id:
        raise SanskritiException(404, "frame नहीं मिला")
    if "shape" in payload:
        if not valid_shape(payload["shape"]):
            raise SanskritiException(400, "shape अमान्य — preset या custom:TL,TR,BR,BL (0-100)")
        f.shape = payload["shape"]
    if "name" in payload:
        name = str(payload["name"]).strip()
        if not name:
            raise SanskritiException(400, "नाम खाली नहीं हो सकता")
        f.name = name[:60]
    if "base" in payload:
        f.base = max(0, int(payload["base"]))
    if "rating" in payload:
        f.rating = min(5.0, max(0.0, float(payload["rating"])))
    if "ratio" in payload:
        r = str(payload["ratio"]).strip()
        f.ratio = r[:8]
        if ":" in r:
            f.ar = r.replace(":", "/")
    if "glare_set" in payload:
        try:
            g = payload["glare_set"]
            old = json.loads(f.glare_set) if f.glare_set else {}
            def _win(w, dflt):
                if not isinstance(w, dict):
                    return dflt
                return {"on": 1 if w.get("on", 1) else 0,
                        "op": max(10, min(100, int(w.get("op", 55)))),
                        "x": max(0, min(100, int(w.get("x", 30)))),
                        "y": max(0, min(100, int(w.get("y", 0)))),
                        "s": max(15, min(300, int(w.get("s", 100)))),
                        "kx": max(-30, min(30, int(w.get("kx", 0)))),
                        "ky": max(-20, min(20, int(w.get("ky", 0)))),
                        "h": max(40, min(200, int(w.get("h", 100)))),
                        "h": max(40, min(200, int(w.get("h", 100)))),
                        **({"gv": int(w["gv"])} if w.get("gv") else {})}
            if isinstance(g.get("L"), dict) or isinstance(g.get("R"), dict):
                old["on"] = 1 if g.get("on", 1) else 0
                keepL = old.get("L") if isinstance(old.get("L"), dict) else {}
                keepR = old.get("R") if isinstance(old.get("R"), dict) else {}
                old["L"] = {**keepL, **_win(g.get("L"), keepL)} if g.get("L") is not None else keepL
                old["R"] = {**keepR, **_win(g.get("R"), keepR)} if g.get("R") is not None else keepR
            else:  # पुराना flat format → बाएँ खिड़की मानो
                old.update({"on": 1 if g.get("on", 1) else 0,
                            "op": max(10, min(100, int(g.get("op", 55)))),
                            "x": max(0, min(100, int(g.get("x", 30)))),
                            "y": max(0, min(100, int(g.get("y", 0)))),
                            "s": max(40, min(300, int(g.get("s", 100))))})
            f.glare_set = json.dumps(old)
        except Exception:
            pass
    if "window" in payload:
        try:
            w = payload["window"]
            f.window = json.dumps({"x": float(w["x"]), "y": float(w["y"]),
                                   "w": float(w["w"]), "h": float(w["h"]),
                                   "shape": str(w.get("shape", "rect"))})
        except Exception:
            raise SanskritiException(400, "window JSON खराब — {x,y,w,h}")
    if "draw" in payload:
        d = payload["draw"]
        if d is None or d == "":
            f.draw = ""
        else:
            try:
                f.draw = json.dumps(d) if not isinstance(d, str) else (json.dumps(json.loads(d)))
            except Exception:
                raise SanskritiException(400, "draw JSON खराब है")
    if "ptype" in payload:
        p = str(payload["ptype"])
        if p not in {"frame", "acrylic", "album"}:
            raise SanskritiException(400, "ptype: frame/acrylic/album")
        f.ptype = p
    if "ar" in payload:
        f.ar = str(payload["ar"])[:12]
    if "code" in payload:  # manual सुधार चाहिए तो; normal flow में create पर auto लगता है
        c = str(payload["code"]).strip().upper()[:12]
        if c:
            f.code = c
    await db.commit()
    return {"ok": True, "frame": _frame_dict(f, mask_len=len(f.mask_data) if f.mask_data else 0)}


@router.delete("/frames/{fid}")
async def delete_frame(
    fid: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """Admin: custom frame हटाओ (soft-off + file delete)।"""
    f = (
        await db.execute(select(StoreFrame).where(StoreFrame.id == fid))
    ).scalar_one_or_none()
    if not f or f.tenant_id != tenant_id:
        raise SanskritiException(404, "frame नहीं मिला")
    f.active = False
    if f.img_path and Path(f.img_path).exists():
        try:
            Path(f.img_path).unlink()
        except Exception:
            pass
    await db.commit()
    return {"ok": True}
