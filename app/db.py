import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# Ensure the DB schema is initialized once before any session is used.
_db_init_lock = asyncio.Lock()
_db_initialized = False

async def ensure_db_initialized():
    from loguru import logger
    global _db_initialized
    logger.debug("ensure_db_initialized start (initialized=%s)", _db_initialized)
    if _db_initialized:
        logger.debug("DB already initialized")
        return
    async with _db_init_lock:
        if _db_initialized:
            logger.debug("DB initialization raced and is now done")
            return
        async with engine.begin() as conn:
            logger.debug("Creating DB schema (url=%s)", settings.database_url)
            if 'sqlite' in str(settings.database_url):
                logger.debug("SQLite detected - dropping existing tables to refresh schema")
                await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        _db_initialized = True
        logger.debug("DB schema created and initialized")

async def get_db():
    await ensure_db_initialized()
    async with AsyncSessionLocal() as session:
        yield session
