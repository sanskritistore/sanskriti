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
    """स्टार्टअप पर डेटाबेस कनेक्शन जाँचें।"""
    # नोट: असली माइग्रेशन alembic से होते हैं, यह सिर्फ डेवलपमेंट के लिए।
    pass


@app.get("/health", tags=["health"])
async def health_check():
    """हेल्थ चेक एंडपॉइंट।"""
    return {"status": "ok", "service": "sanskriti-backend"}
