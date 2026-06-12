from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from engine.shared.config import get_settings

settings = get_settings()

# Async (FastAPI)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
    connect_args={"timeout": 10, "command_timeout": 30},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Sync (Celery workers) - same DB, sync driver
_sync_url = (
    settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql")
    if "asyncpg" in settings.DATABASE_URL
    else settings.DATABASE_URL
)
sync_engine = create_engine(
    _sync_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine, class_=Session)

# Check database connection on initialization
from sqlalchemy import text
import sys

try:
    with sync_engine.connect() as conn:
        res = conn.execute(text('SELECT 1'))
        if res.fetchone():
            print("Database Connected Successfully!")
except Exception as e:
    print(f"Failed to connect to the database: {e}")
