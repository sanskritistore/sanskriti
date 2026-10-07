"""
Celery वर्कर - पृष्ठभूमि कार्य

Redis ब्रोकर के साथ पृष्ठभूमि कार्य:
- कैंपेन स्थिति/खर्च sync (हर कुछ घंटे)
- रिपोर्ट तैयार करना
- WhatsApp संदेश भेजना

चलाना:
    celery -A app.workers.celery_app worker --loglevel=info
"""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "sanskriti",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kolkata",  # भारतीय समय
    enable_utc=True,
)


@celery_app.task(name="sync_campaign_metrics")
def sync_campaign_metrics():
    """
    सभी सक्रिय कैंपेनों के खर्च/स्थिति को प्लेटफॉर्म से sync करें।

    शेड्यूल: हर 6 घंटे (अनुशंसित)
    TODO: असली कार्यान्वयन - सक्रिय PlatformCampaign rows लेकर
    एडाप्टर से मेट्रिक्स लाएँ और budget_spent अपडेट करें।
    """
    return {"status": "sync_completed", "note": "MVP stub"}


@celery_app.task(name="send_daily_report")
def send_daily_report():
    """टेनेंट को दैनिक कैंपेन रिपोर्ट भेजें (WhatsApp/ईमेल)।"""
    return {"status": "report_sent", "note": "MVP stub"}
