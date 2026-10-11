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
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
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
        "has_files": bool(o.print_path),
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
    if preview_file is not None:
        vdata = await preview_file.read()
        vpath = d / f"{o.order_no}_preview.jpg"
        vpath.write_bytes(vdata)
        o.preview_path = str(vpath)

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
