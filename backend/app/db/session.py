import asyncio

from sqlalchemy import inspect, text
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


# ── SQLAlchemy type → PostgreSQL DDL ──

def _col_ddl(col) -> str:
    """Convert a SQLAlchemy Column to a PostgreSQL DDL type string."""
    type_cls = col.type.__class__.__name__.upper()
    if type_cls == "VARCHAR" or type_cls == "STRING":
        length = getattr(col.type, "length", None)
        return f"VARCHAR({length})" if length else "VARCHAR"
    if type_cls == "TEXT":
        return "TEXT"
    if type_cls in ("INTEGER", "INT"):
        return "INTEGER"
    if type_cls == "BOOLEAN":
        return "BOOLEAN"
    if type_cls in ("DATETIME", "TIMESTAMP"):
        if getattr(col.type, "timezone", False):
            return "TIMESTAMPTZ"
        return "TIMESTAMP"
    if type_cls == "FLOAT":
        return "DOUBLE PRECISION"
    return "TEXT"


def _diff_columns(sync_conn) -> list[str]:
    """Compare model metadata with live DB schema. Returns ALTER TABLE SQL list.

    Runs synchronously inside run_sync().
    """
    insp = inspect(sync_conn)
    db_tables = set(insp.get_table_names())
    alter_stmts: list[str] = []

    for table in Base.metadata.sorted_tables:
        if table.name not in db_tables:
            continue  # New table — create_all handles it

        existing = {c["name"] for c in insp.get_columns(table.name)}

        for col in table.columns:
            if col.name in existing:
                continue

            ddl_type = _col_ddl(col)
            # Always make new columns nullable to avoid breaking existing rows
            default = ""
            type_cls = col.type.__class__.__name__.upper()
            if type_cls == "BOOLEAN" and col.default is not None:
                arg = col.default.arg
                if not callable(arg):
                    default = f" DEFAULT {'TRUE' if arg else 'FALSE'}"
            elif type_cls in ("INTEGER", "INT") and col.default is not None:
                arg = col.default.arg
                if not callable(arg):
                    default = f" DEFAULT {arg}"

            sql = f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {ddl_type}{default}'
            alter_stmts.append((table.name, col.name, ddl_type, sql))

    return alter_stmts


async def _auto_migrate():
    """Inspect live DB schema and add missing columns from models.

    Replaces manual migration lists. Safe because:
    - Only ADDs columns (never drops/renames)
    - New columns are always NULLable
    - Each ALTER runs independently
    """
    # Step 1: Diff inside run_sync (uses sync inspector)
    async with engine.begin() as conn:
        stmts = await conn.run_sync(_diff_columns)

    if not stmts:
        return

    # Step 2: Execute ALTER TABLE statements
    for table_name, col_name, ddl_type, sql in stmts:
        async with engine.begin() as conn:
            try:
                await conn.execute(text(sql))
                print(f"[DB] auto-migrate: added {table_name}.{col_name} ({ddl_type})")
            except Exception as e:
                err_str = str(e).lower()
                if "already exists" not in err_str and "duplicate" not in err_str:
                    print(f"[DB] auto-migrate FAILED: {table_name}.{col_name} — {e}")


async def _run_legacy_migrations():
    """One-time legacy migrations for constraints/indexes (idempotent)."""
    migrations = [
        "CREATE INDEX IF NOT EXISTS ix_reactions_message_id ON reactions(message_id)",
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_reactions_unique ON reactions(message_id, user_id, emoji)",
        "CREATE INDEX IF NOT EXISTS ix_messages_parent_id ON messages(parent_id)",
    ]
    async with engine.begin() as conn:
        for sql in migrations:
            try:
                await conn.execute(text(sql))
            except Exception:
                pass


async def init_db():
    for attempt in range(5):
        try:
            # Step 1: create new tables
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            # Step 2: auto-migrate missing columns
            await _auto_migrate()

            # Step 3: legacy index migrations
            await _run_legacy_migrations()

            print(f"[DB] init_db 완료 (attempt {attempt + 1})")
            return
        except Exception as e:
            print(f"[DB] init_db 실패 (attempt {attempt + 1}): {e}")
            if attempt < 4:
                await asyncio.sleep(2)


async def get_db():
    async with async_session() as session:
        yield session
