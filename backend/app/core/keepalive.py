"""
Keep-alive (स्वयं-जागरण) — Render free plan की समस्या का इलाज
================================================================

समस्या (8 Nov 2026 को पता चली):
  Render का free plan 15 मिनट कोई request न आए तो instance बंद कर देता है,
  और कभी-कभी वापस शुरू ही नहीं होता — कोई error भी नहीं दिखता।

पहले GitHub Actions का cron लगाया था, पर वह चला ही नहीं (जाँचा गया —
एक छोटा test workflow भी 7 slots तक नहीं चला)। इसलिए अब ऐप खुद को जगाए रखती है।

तरीक़ा:
  ऐप हर KEEPALIVE_INTERVAL_MINUTES मिनट पर अपने ही public URL को call करती है।
  ⚠️ public URL ज़रूरी है — localhost (127.0.0.1) पर call करने से Render के
  proxy तक request नहीं पहुँचती, इसलिए idle timer reset नहीं होगा।

सुरक्षा:
  - पूरा loop try/except में — कभी ऐप को नहीं गिराएगा
  - KEEPALIVE_ENABLED=false करके तुरंत बंद किया जा सकता है
  - सिर्फ़ दुकान के समय (KEEPALIVE_HOURS_UTC) चलता है, ताकि
    Render के 750 instance-hours/महीना की limit न टूटे
"""

import asyncio
import logging
import os
from datetime import datetime, timezone

# ⚠️ 8 Nov 2026: सादा getLogger(__name__) से Render के logs में कुछ नहीं दिखा
# (root logger का level WARNING था, इसलिए INFO lines गिर जाती थीं)।
# इसलिए अपना handler लगाकर propagate बंद कर दिया — logs में साफ़ दिखेगा।
logger = logging.getLogger("sanskriti.keepalive")
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(levelname)s:     keepalive: %(message)s"))
    logger.addHandler(_h)
    logger.setLevel(logging.INFO)
    logger.propagate = False

_task: asyncio.Task | None = None


def _in_active_window(hours_spec: str) -> bool:
    """क्या अभी (UTC) सक्रिय घंटों में हैं? hours_spec जैसे '3-17' या '3-17,20'।"""
    try:
        hour = datetime.now(timezone.utc).hour
        for part in hours_spec.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                lo, hi = part.split("-", 1)
                if int(lo) <= hour <= int(hi):
                    return True
            elif int(part) == hour:
                return True
    except Exception as exc:  # ग़लत spec → चलते रहो, बंद मत करो
        logger.warning("keepalive: hours spec पढ़ नहीं पाया (%s): %s", hours_spec, exc)
        return True
    return False


def _resolve_url() -> str:
    """किस URL को call करना है। खाली हो तो Render के अपने env var से बनाओ।"""
    from app.core.config import settings

    if settings.KEEPALIVE_URL:
        return settings.KEEPALIVE_URL
    base = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
    if base:
        return f"{base}/health"
    return ""


async def _loop() -> None:
    """मुख्य loop — हर interval पर एक ping।"""
    import httpx

    from app.core.config import settings

    interval = max(1, settings.KEEPALIVE_INTERVAL_MINUTES) * 60
    # पहला ping थोड़ी देर बाद — ऐप पूरी तरह तैयार हो जाए
    await asyncio.sleep(min(60, interval))

    ok = fail = skip = 0
    while True:
        try:
            if not _in_active_window(settings.KEEPALIVE_HOURS_UTC):
                skip += 1
                if skip % 30 == 1:
                    logger.info("keepalive: सक्रिय समय के बाहर — रुका हुआ (skipped=%d)", skip)
            else:
                url = _resolve_url()
                if not url:
                    logger.warning("keepalive: URL नहीं मिला — RENDER_EXTERNAL_URL या KEEPALIVE_URL सेट करें")
                else:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        resp = await client.get(url)
                    if resp.status_code == 200:
                        ok += 1
                        if ok % 12 == 1:
                            logger.info("keepalive: ठीक है (ok=%d fail=%d)", ok, fail)
                    else:
                        fail += 1
                        logger.warning("keepalive: HTTP %s — %s", resp.status_code, url)
        except asyncio.CancelledError:
            logger.info("keepalive: बंद किया गया")
            raise
        except Exception as exc:
            fail += 1
            logger.warning("keepalive: ping असफल (#%d): %s", fail, exc)

        await asyncio.sleep(interval)


def start_keepalive() -> None:
    """startup पर बुलाएँ। KEEPALIVE_ENABLED=false हो तो कुछ नहीं करता।"""
    global _task
    from app.core.config import settings

    if not settings.KEEPALIVE_ENABLED:
        logger.info("keepalive: बंद है (KEEPALIVE_ENABLED=false)")
        return
    if _task and not _task.done():
        return
    try:
        _task = asyncio.create_task(_loop(), name="keepalive")
        logger.info(
            "keepalive: चालू — हर %d मिनट, सक्रिय घंटे (UTC) %s",
            settings.KEEPALIVE_INTERVAL_MINUTES,
            settings.KEEPALIVE_HOURS_UTC,
        )
    except Exception as exc:
        logger.warning("keepalive: शुरू नहीं कर पाया: %s", exc)
