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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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


def _frame_dict(f: StoreFrame) -> dict:
    """Store frontend को चाहिए fields (config frames.json जैसी shape)।"""
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
        "img": f"/api/v1/store/frames/{f.id}/img" if (f.img_path or f.img_data) else "",
        "samp": f"/api/v1/store/frames/{f.id}/sample" if f.samp_data else "",
        "samp_pos": f.samp_pos or "",
        "glare_set": f.glare_set or "",
        "glare": f"/api/v1/store/frames/{f.id}/glare" if f.glare_data else "",
        "draw": json.loads(f.draw) if f.draw else None,
        "ptype": f.ptype,
    }


@router.get("/frames")
async def list_custom_frames(db: AsyncSession = Depends(get_db)):
    """PUBLIC: सभी active custom frames — store pages इन्हें static config से merge करते हैं।"""
    rows = (
        await db.execute(
            select(StoreFrame).where(StoreFrame.active == True)  # noqa: E712
            .order_by(StoreFrame.id)
        )
    ).scalars().all()
    return [_frame_dict(f) for f in rows]


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
    elif not draw:
        raise SanskritiException(400, "PNG या draw — दोनों में से एक चाहिए")
    if sample_file is not None:
        sdata = await sample_file.read()
        if len(sdata) > 10 * 1024 * 1024:
            raise SanskritiException(400, "sample photo बहुत बड़ी है (10MB तक)")
        f.samp_data = sdata
        f.samp_ct = sample_file.content_type or "image/webp"

    await db.commit()
    return {"ok": True, "frame": _frame_dict(f)}


@router.get("/frames/{fid}/img")
async def frame_image(fid: int, db: AsyncSession = Depends(get_db)):
    """PUBLIC: frame की PNG border (store pages पर दिखती है)।"""
    f = (
        await db.execute(select(StoreFrame).where(StoreFrame.id == fid))
    ).scalar_one_or_none()
    if f and f.img_data:
        return Response(content=bytes(f.img_data), media_type=f.img_ct or "image/png")
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
    g["gv"] = int(time.time())
    f.glare_set = json.dumps(g)
    await db.commit()
    return {"ok": True, "glare": f"/api/v1/store/frames/{f.id}/glare"}


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
            f.glare_set = json.dumps({"on": 1 if g.get("on", 1) else 0,
                                      "op": max(10, min(100, int(g.get("op", 55)))),
                                      "x": max(0, min(100, int(g.get("x", 30))))})
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
    await db.commit()
    return {"ok": True, "frame": _frame_dict(f)}


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
