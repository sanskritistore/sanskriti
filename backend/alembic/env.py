"""
एलेम्बिक env - माइग्रेशन पर्यावरण

DATABASE_URL .env से आता है (sync ड्राइवर में बदला जाता है
क्योंकि alembic sync इंजन उपयोग करता है)।
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.models import Base  # सभी मॉडल import - महत्वपूर्ण!

# Alembic Config ऑब्जेक्ट
config = context.config

# .env से डेटाबेस URL सेट करें
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# लॉगिंग
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# MetaData - ऑटो-जनरेट के लिए सभी मॉडल की टेबल यहाँ आती हैं
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """ऑफ़लाइन मोड - SQL स्क्रिप्ट बनाएँ (DB कनेक्शन के बिना)।"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """कनेक्शन के साथ माइग्रेशन चलाएँ।"""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Async इंजन से माइग्रेशन (asyncpg ड्राइवर)।"""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """ऑनलाइन मोड - DB से जुड़कर माइग्रेशन।"""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
