"""
डेटाबेस - Async SQLAlchemy सेटअप
सभी मॉडल async engine के जरिए PostgreSQL से जुड़ते हैं।
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Async engine - PostgreSQL के लिए asyncpg ड्राइवर
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,  # कनेक्शन जीवित है या नहीं, जाँचें
)

# सेशन फैक्ट्री - हर रिक्वेस्ट का अपना सेशन
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """
    सभी मॉडल्स का आधार वर्ग।

    ARCHITECTURE RULE (आर्किटेक्चर नियम):
    हर टेबल में tenant_id अनिवार्य है - multi-tenancy के लिए।
    """

    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency - रिक्वेस्ट के लिए DB सेशन देता है।

    उपयोग:
        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
