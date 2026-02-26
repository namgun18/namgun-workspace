import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models import Base, AccessLog, Channel, ChannelMember, Message, Notification, Reaction  # noqa: F401 — ensure all models registered

settings = get_settings()
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_recycle=300,
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _migrate_columns(conn):
    """Add missing columns to existing tables (lightweight migration)."""
    migrations = [
        ("users", "email_verified", "BOOLEAN DEFAULT TRUE"),
        ("users", "email_verify_token", "VARCHAR(64)"),
        ("users", "email_verify_sent_at", "TIMESTAMPTZ"),
        ("messages", "parent_id", "VARCHAR(36)"),
    ]
    for table, column, col_type in migrations:
        try:
            await conn.execute(
                text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            )
            print(f"[DB] migrate: added {table}.{column}")
        except Exception:
            pass  # Column already exists

    # Indexes & constraints
    extra_ddl = [
        "CREATE INDEX IF NOT EXISTS ix_messages_parent_id ON messages(parent_id)",
        "ALTER TABLE messages ADD CONSTRAINT fk_messages_parent_id FOREIGN KEY (parent_id) REFERENCES messages(id) ON DELETE SET NULL",
    ]
    for sql in extra_ddl:
        try:
            await conn.execute(text(sql))
        except Exception:
            pass


async def init_db():
    for attempt in range(5):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                await _migrate_columns(conn)
            print(f"[DB] init_db 완료 (attempt {attempt + 1})")
            return
        except Exception as e:
            print(f"[DB] init_db 실패 (attempt {attempt + 1}): {e}")
            if attempt < 4:
                await asyncio.sleep(2)


async def get_db():
    async with async_session() as session:
        yield session
