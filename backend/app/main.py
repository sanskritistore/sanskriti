"""
Sanskriti Backend - Main Application
संस्कृति बैकएंड - मुख्य एप्लीकेशन

यह FastAPI एप्लीकेशन का एंट्री पॉइंट है।
हर रिक्वेस्ट के साथ tenant context सेट होता है।
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1 import api_router

# एप्लीकेशन बनाएँ
app = FastAPI(
    title="Sanskriti API",
    description=(
        "Sanskriti MVP Backend - भारतीय व्यापारिक विज्ञापन प्लेटफॉर्म। "
        "AI विज्ञापन निर्माण, कैंपेन लॉन्च और रिपोर्टिंग के लिए API।"
    ),
    version="0.1.0",
)

# CORS मिडलवेयर - फ्रंटएंड के लिए
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# सभी मॉड्यूल राउटर /api/v1 पर जुड़ें (versioned API - दिन-एक से)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.on_event("startup")
async def startup():
    """स्टार्टअप पर डेटाबेस तैयार रखें।"""
    # नई tables auto-create (checkfirst=True — मौजूदा tables छूता नहीं)।
    # असली schema बदलाव alembic से; नए मॉडल यहाँ से तुरंत live।
    from app import models  # noqa: F401 — सभी मॉडल register हों

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # छोटे column adds (create_all मौजूदा table नहीं बदलता)
        from sqlalchemy import text
        await conn.execute(text(
            "ALTER TABLE store_frames ADD COLUMN IF NOT EXISTS draw VARCHAR(1000) NOT NULL DEFAULT ''"
        ))
        await conn.execute(text(
            "ALTER TABLE store_frames ADD COLUMN IF NOT EXISTS ptype VARCHAR(20) NOT NULL DEFAULT 'frame'"
        ))
        await conn.execute(text("ALTER TABLE store_frames ADD COLUMN IF NOT EXISTS img_data BYTEA"))
        await conn.execute(text("ALTER TABLE store_frames ADD COLUMN IF NOT EXISTS img_ct VARCHAR(50) NOT NULL DEFAULT 'image/png'"))
        await conn.execute(text("ALTER TABLE store_frames ALTER COLUMN shape TYPE VARCHAR(30)"))
        await conn.execute(text("ALTER TABLE store_frames ADD COLUMN IF NOT EXISTS samp_data BYTEA"))
        await conn.execute(text("ALTER TABLE store_frames ADD COLUMN IF NOT EXISTS samp_ct VARCHAR(50) NOT NULL DEFAULT 'image/webp'"))
        await conn.execute(text("ALTER TABLE store_frames ADD COLUMN IF NOT EXISTS samp_pos VARCHAR(80) NOT NULL DEFAULT ''"))
        await conn.execute(text("ALTER TABLE store_frames ADD COLUMN IF NOT EXISTS glare_set VARCHAR(80) NOT NULL DEFAULT ''"))
        await conn.execute(text("ALTER TABLE store_frames ADD COLUMN IF NOT EXISTS glare_data BYTEA"))
        await conn.execute(text("ALTER TABLE store_frames ADD COLUMN IF NOT EXISTS glare_ct VARCHAR(50) NOT NULL DEFAULT 'image/png'"))
        await conn.execute(text("ALTER TABLE store_frames ADD COLUMN IF NOT EXISTS glare2_data BYTEA"))
        await conn.execute(text("ALTER TABLE store_frames ADD COLUMN IF NOT EXISTS glare2_ct VARCHAR(50) NOT NULL DEFAULT 'image/png'"))
        await conn.execute(text("ALTER TABLE store_frames ALTER COLUMN glare_set TYPE VARCHAR(255)"))
        await conn.execute(text("ALTER TABLE store_frames ADD COLUMN IF NOT EXISTS code VARCHAR(12) NOT NULL DEFAULT ''"))
        await conn.execute(text("ALTER TABLE store_orders ADD COLUMN IF NOT EXISTS print_data BYTEA"))
        await conn.execute(text("ALTER TABLE store_orders ADD COLUMN IF NOT EXISTS preview_data BYTEA"))

    # Frame masks पहले से गर्म (warm) रखो — 12-10 रात: पहला visitor cold-mask generation का इंतज़ार न करे।
    # Background thread: startup कभी block न हो, free server पर धीरे-धीरे cache भरे।
    import asyncio

    asyncio.get_event_loop().run_in_executor(None, _warm_frame_masks)


def _warm_frame_masks():
    """सभी PNG frames के masks background में generate करके _MASK_CACHE भर दो।"""
    import asyncio as _a

    from sqlalchemy import select as _sel

    from app.core.database import AsyncSessionLocal
    from app.models import StoreFrame
    from app.modules.store.routes import _MASK_CACHE, _frame_mask_png

    async def _go():
        async with AsyncSessionLocal() as db:
            frames = (await db.execute(_sel(StoreFrame).where(StoreFrame.img_data.isnot(None)))).scalars().all()
            for f in frames:
                data = bytes(f.img_data)
                if f.id in _MASK_CACHE and _MASK_CACHE[f.id][0] == len(data):
                    continue
                try:
                    m = _frame_mask_png(data)
                except Exception:
                    m = None
                if m:
                    _MASK_CACHE[f.id] = (len(data), m)

    try:
        _a.run(_go())
    except Exception:
        pass  # warm-up fail हो तो lazy generation ही चलेगा — कोई नुकसान नहीं


@app.get("/health", tags=["health"])
async def health_check():
    """हेल्थ चेक एंडपॉइंट।"""
    return {"status": "ok", "service": "sanskriti-backend"}
