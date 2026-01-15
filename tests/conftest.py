import sys
import os
import asyncio
import pytest

# Ensure the project root is on sys.path so `import app` works in tests
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.db import engine, Base

# Provide a fresh event loop for pytest-asyncio
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

# Create and drop DB schema once per test session
@pytest.fixture(scope="session", autouse=True)
def setup_db():
    # Ensure models are imported so their tables are registered
    import app.models  # noqa: F401
    # Run async create_all in a fresh loop
    async def _create():
        async with engine.begin() as conn:
            # Ensure a clean schema for tests by dropping existing tables first
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
            # Make sure users_api exists
            try:
                from app.models.user import User
                await conn.run_sync(User.__table__.create, checkfirst=True)
            except Exception:
                pass
    asyncio.run(_create())
    yield
    async def _drop():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    asyncio.run(_drop())

# Ensure FastAPI startup/shutdown handlers run so on_startup creates schema as needed
from app.main import app as _app

@pytest.fixture(scope="session", autouse=True)
def app_lifespan():
    # Run startup/shutdown using asyncio.run so we do not require an async pytest plugin for autouse fixtures
    asyncio.run(_app.router.startup())
    yield
    asyncio.run(_app.router.shutdown())
