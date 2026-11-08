"""
अस्थायी (TEMPORARY) — Render Postgres → Neon Postgres डेटा migration।

क्यों ज़रूरी है:
    Render का free Postgres 6 Nov 2026 को expire हो गया था। डेटा बचाने के लिए
    paid plan (₹530/महीना) चालू किया गया। अब डेटा Neon (free, Singapore) पर
    ले जाना है और Render का DB हटाना है।

Render के बाहर से DB तक connection बंद है ("SSL connection has been closed
unexpectedly"), इसलिए migration Render के अंदर से ही चलानी पड़ती है — यानी
इसी backend से। इसलिए यह module।

सुरक्षा: हर request में header `X-Migrate-Token` चाहिए, जो service env var
`MIGRATE_TOKEN` से मिलना चाहिए। NEON_DATABASE_URL भी env var से आता है।

⚠️ काम पूरा होने पर यह पूरा module + दोनों env vars हटा दिए जाएंगे।
"""

import os

from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import MetaData, select, text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.database import engine

router = APIRouter()


def _target_url() -> str:
    """NEON_DATABASE_URL को asyncpg-समझने वाले रूप में बदलें।"""
    raw = (os.environ.get("NEON_DATABASE_URL") or "").strip()
    if not raw:
        raise HTTPException(status_code=500, detail="NEON_DATABASE_URL not set")
    for prefix in ("postgresql+asyncpg://", "postgresql://", "postgres://"):
        if raw.startswith(prefix):
            raw = raw[len(prefix):]
            break
    # query params (sslmode / channel_binding) हटाएँ — asyncpg इन्हें नहीं समझता,
    # SSL हम connect_args से देते हैं।
    raw = raw.split("?", 1)[0]
    return "postgresql+asyncpg://" + raw


def _make_target():
    return create_async_engine(
        _target_url(),
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=0,
        connect_args={"ssl": "require"},
    )


def _check_token(token: str | None) -> None:
    expected = (os.environ.get("MIGRATE_TOKEN") or "").strip()
    if not expected:
        raise HTTPException(status_code=500, detail="MIGRATE_TOKEN not set")
    if not token or token != expected:
        raise HTTPException(status_code=403, detail="forbidden")


@router.get("/status")
async def status(x_migrate_token: str | None = Header(default=None)):
    """दोनों DB ज़िंदा हैं या नहीं — और गिनती का मुक़ाबला।"""
    _check_token(x_migrate_token)

    src_meta = MetaData()
    async with engine.connect() as conn:
        await conn.run_sync(lambda c: src_meta.reflect(bind=c, views=False))
        src_counts = {}
        for name, table in src_meta.tables.items():
            src_counts[name] = await conn.scalar(select(text("count(*)")).select_from(table))

    target = _make_target()
    dst_counts = {}
    dst_error = None
    try:
        async with target.connect() as conn:
            for name in src_meta.tables:
                try:
                    dst_counts[name] = await conn.scalar(
                        text(f'SELECT count(*) FROM "{name}"')
                    )
                except Exception as exc:  # table मौजूद नहीं
                    await conn.rollback()
                    dst_counts[name] = f"missing ({type(exc).__name__})"
    except Exception as exc:
        dst_error = f"{type(exc).__name__}: {exc}"
    finally:
        await target.dispose()

    return {
        "source_tables": len(src_meta.tables),
        "source_counts": src_counts,
        "target_counts": dst_counts,
        "target_error": dst_error,
    }


@router.post("/run")
async def run(
    wipe: bool = False,
    x_migrate_token: str | None = Header(default=None),
):
    """
    पूरा डेटा source (Render) से target (Neon) पर copy करें।

    wipe=true → पहले target tables खाली करें (दोबारा चलाने पर सुरक्षित)।
    """
    _check_token(x_migrate_token)

    report: dict = {"wipe": wipe, "tables": [], "errors": []}

    # 1) source schema पढ़ें (जैसा असल में है — models से नहीं)
    src_meta = MetaData()
    async with engine.connect() as conn:
        await conn.run_sync(lambda c: src_meta.reflect(bind=c, views=False))

    # 2) target पर वही schema बनाएँ
    target = _make_target()
    try:
        async with target.begin() as conn:
            await conn.run_sync(lambda c: src_meta.create_all(bind=c))
    except Exception as exc:
        await target.dispose()
        raise HTTPException(
            status_code=500, detail=f"schema create failed: {type(exc).__name__}: {exc}"
        )

    # 3) हर table की rows copy करें
    async with engine.connect() as src_conn, target.connect() as dst_conn:
        for name, table in src_meta.tables.items():
            entry = {"table": name, "rows": 0, "bytes": 0}
            try:
                rows = (await src_conn.execute(select(table))).mappings().all()
                entry["rows"] = len(rows)
                entry["bytes"] = sum(
                    len(v) for r in rows for v in r.values() if isinstance(v, (bytes, bytearray))
                )
                if wipe:
                    await dst_conn.execute(text(f'TRUNCATE TABLE "{name}" CASCADE'))
                if rows:
                    await dst_conn.execute(table.insert(), [dict(r) for r in rows])
                await dst_conn.commit()
            except Exception as exc:
                await dst_conn.rollback()
                entry["error"] = f"{type(exc).__name__}: {exc}"
                report["errors"].append(f"{name}: {entry['error']}")
            report["tables"].append(entry)

        # 4) sequences ठीक करें — वरना नया row डालते समय duplicate key error
        seqs = []
        for name, table in src_meta.tables.items():
            for col in table.primary_key.columns:
                try:
                    seq = await dst_conn.scalar(
                        text("SELECT pg_get_serial_sequence(:t, :c)"),
                        {"t": name, "c": col.name},
                    )
                    if not seq:
                        continue
                    await dst_conn.execute(
                        text(
                            f'SELECT setval(:s, COALESCE((SELECT MAX("{col.name}") '
                            f'FROM "{name}"), 1))'
                        ),
                        {"s": seq},
                    )
                    seqs.append(f"{name}.{col.name}")
                except Exception as exc:
                    await dst_conn.rollback()
                    report["errors"].append(f"seq {name}.{col.name}: {exc}")
        await dst_conn.commit()
        report["sequences_reset"] = seqs

    await target.dispose()
    report["ok"] = not report["errors"]
    return report
