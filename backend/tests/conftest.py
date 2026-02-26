"""
Shared test fixtures for backend tests.

- Overrides DATABASE_URL to use SQLite in-memory (via aiosqlite)
- Provides an async FastAPI TestClient via httpx.AsyncClient
- Sets safe environment variables for testing
"""

import os

# Set test environment BEFORE any app imports
os.environ.update({
    "DATABASE_URL": "sqlite+aiosqlite:///",
    "SECRET_KEY": "test-secret-key-not-for-production",
    "DEBUG": "true",
    "APP_URL": "http://localhost:8000",
    "DOMAIN": "localhost",
    "REDIS_URL": "redis://localhost:6379/0",
})

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Base


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture()
async def db_engine():
    """Create a fresh in-memory SQLite engine per test."""
    engine = create_async_engine("sqlite+aiosqlite:///", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture()
async def db_session(db_engine):
    """Provide an async DB session bound to the test engine."""
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture()
async def client():
    """Async HTTP client that talks to the FastAPI app without lifespan.

    We skip lifespan to avoid PostgreSQL/Redis connections in tests.
    The /api/health endpoint does not require DB or Redis.
    """
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
