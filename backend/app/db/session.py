import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models import (  # noqa: F401 — ensure all models registered
    Base, AccessLog, AuditLog, Channel, ChannelMember, Message, Notification, Reaction,
    SystemSetting, MailAccount, MailDraft, CalendarDB, CalendarEventDB, CalendarShareDB,
    AddressBookDB, ContactDB, TaskDB,
    Board, Post, PostComment, PostReaction, PostBookmark, PostReadLog,
)

settings = get_settings()
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_recycle=300,
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _run_migrations():
    """Add missing columns/tables/indexes to existing DB (lightweight migration).

    Runs in a SEPARATE connection from create_all to avoid transaction conflicts.
    Each statement runs in its own sub-transaction (SAVEPOINT) so failures don't
    abort the whole batch.
    """
    migrations = [
        "ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT TRUE",
        "ALTER TABLE users ADD COLUMN email_verify_token VARCHAR(64)",
        "ALTER TABLE users ADD COLUMN email_verify_sent_at TIMESTAMPTZ",
        "ALTER TABLE messages ADD COLUMN parent_id VARCHAR(36)",
        # reactions table (idempotent)
        """CREATE TABLE IF NOT EXISTS reactions (
            id VARCHAR(36) PRIMARY KEY,
            message_id VARCHAR(36) NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
            user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            emoji VARCHAR(10) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )""",
        "CREATE INDEX IF NOT EXISTS ix_reactions_message_id ON reactions(message_id)",
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_reactions_unique ON reactions(message_id, user_id, emoji)",
        "CREATE INDEX IF NOT EXISTS ix_messages_parent_id ON messages(parent_id)",
        "ALTER TABLE messages ADD CONSTRAINT fk_messages_parent_id FOREIGN KEY (parent_id) REFERENCES messages(id) ON DELETE SET NULL",
        "ALTER TABLE users ADD COLUMN totp_secret VARCHAR(64)",
    ]

    async with engine.begin() as conn:
        for sql in migrations:
            try:
                await conn.execute(text(sql))
                # Only log meaningful additions (ALTER/CREATE)
                if "ADD COLUMN" in sql:
                    col = sql.split("ADD COLUMN")[1].strip().split()[0]
                    tbl = sql.split("TABLE")[1].strip().split()[0]
                    print(f"[DB] migrate: added {tbl}.{col}")
                elif "CREATE TABLE" in sql and "IF NOT EXISTS" in sql:
                    tbl = sql.split("IF NOT EXISTS")[1].strip().split()[0]
                    print(f"[DB] migrate: created table {tbl}")
            except Exception:
                pass  # Already exists


async def init_db():
    for attempt in range(5):
        try:
            # Step 1: create_all for new tables defined in models
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            # Step 2: lightweight migrations (separate connection)
            await _run_migrations()

            print(f"[DB] init_db 완료 (attempt {attempt + 1})")
            return
        except Exception as e:
            print(f"[DB] init_db 실패 (attempt {attempt + 1}): {e}")
            if attempt < 4:
                await asyncio.sleep(2)


async def get_db():
    async with async_session() as session:
        yield session
