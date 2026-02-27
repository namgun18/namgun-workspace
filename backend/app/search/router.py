"""Global search API — unified search across posts, contacts, messages, files."""

from pathlib import Path

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.config import get_settings
from app.db.models import (
    AddressBookDB,
    Channel,
    ChannelMember,
    ContactDB,
    Message,
    Post,
    User,
)
from app.db.session import get_db

settings = get_settings()

router = APIRouter(prefix="/api/search", tags=["search"])

VALID_MODULES = {"board", "contacts", "chat", "files"}
PER_MODULE_LIMIT = 10
TOTAL_LIMIT = 50


def _snippet(text: str | None, query: str, max_len: int = 120) -> str:
    """Extract a snippet around the query match."""
    if not text:
        return ""
    lower_text = text.lower()
    lower_q = query.lower()
    idx = lower_text.find(lower_q)
    if idx == -1:
        return text[:max_len] + ("..." if len(text) > max_len else "")
    start = max(0, idx - 40)
    end = min(len(text), idx + len(query) + 80)
    snippet = text[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


def _escape_like(q: str) -> str:
    """Escape LIKE wildcards for safe search."""
    return q.replace("%", "\\%").replace("_", "\\_")


@router.get("")
async def global_search(
    q: str = Query(..., min_length=1, max_length=200),
    modules: str = Query("board,contacts,chat,files"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Unified search across multiple modules.

    Parameters:
        q: Search query string
        modules: Comma-separated list of modules to search (board, contacts, chat, files)

    Returns:
        {results: [{type, id, title, snippet, url}], total}
    """
    requested = {m.strip() for m in modules.split(",") if m.strip() in VALID_MODULES}
    if not requested:
        requested = VALID_MODULES

    results: list[dict] = []

    escaped = _escape_like(q)
    pattern = f"%{escaped}%"

    # ─── Board (posts) ───
    if "board" in requested:
        post_rows = (
            await db.execute(
                select(Post)
                .where(
                    Post.is_deleted == False,  # noqa: E712
                    or_(
                        Post.title.ilike(pattern, escape="\\"),
                        Post.content.ilike(pattern, escape="\\"),
                    ),
                )
                .order_by(Post.created_at.desc())
                .limit(PER_MODULE_LIMIT)
            )
        ).scalars().all()

        for p in post_rows:
            results.append({
                "type": "post",
                "id": p.id,
                "title": p.title,
                "snippet": _snippet(p.content, q),
                "url": f"/board/posts/{p.id}",
            })

    # ─── Contacts ───
    if "contacts" in requested:
        # Only search user's own contacts
        ab_ids_result = await db.execute(
            select(AddressBookDB.id).where(AddressBookDB.user_id == user.id)
        )
        ab_ids = [row[0] for row in ab_ids_result.all()]

        if ab_ids:
            contact_rows = (
                await db.execute(
                    select(ContactDB)
                    .where(
                        ContactDB.address_book_id.in_(ab_ids),
                        or_(
                            ContactDB.full_name.ilike(pattern, escape="\\"),
                            ContactDB.emails.ilike(pattern, escape="\\"),
                            ContactDB.organization.ilike(pattern, escape="\\"),
                        ),
                    )
                    .order_by(ContactDB.full_name)
                    .limit(PER_MODULE_LIMIT)
                )
            ).scalars().all()

            for c in contact_rows:
                snippet_parts = []
                if c.organization:
                    snippet_parts.append(c.organization)
                if c.emails:
                    snippet_parts.append(c.emails[:80])
                results.append({
                    "type": "contact",
                    "id": c.id,
                    "title": c.full_name,
                    "snippet": " | ".join(snippet_parts) if snippet_parts else "",
                    "url": f"/contacts/{c.id}",
                })

    # ─── Chat (messages) ───
    if "chat" in requested:
        # Only search channels the user is a member of
        user_channels_q = select(ChannelMember.channel_id).where(
            ChannelMember.user_id == user.id
        )

        msg_rows = (
            await db.execute(
                select(Message, Channel)
                .join(Channel, Message.channel_id == Channel.id)
                .where(
                    Message.channel_id.in_(user_channels_q),
                    Message.is_deleted == False,  # noqa: E712
                    Message.content.ilike(pattern, escape="\\"),
                )
                .order_by(Message.created_at.desc())
                .limit(PER_MODULE_LIMIT)
            )
        ).all()

        for msg, ch in msg_rows:
            results.append({
                "type": "message",
                "id": msg.id,
                "title": f"#{ch.name}",
                "snippet": _snippet(msg.content, q),
                "url": f"/chat/channels/{ch.id}",
            })

    # ─── Files (path names) ───
    if "files" in requested:
        storage_root = Path(settings.storage_root)
        user_dir = storage_root / "users" / user.id
        shared_dir = storage_root / "shared"

        file_results: list[dict] = []
        lower_q = q.lower()

        for base_dir, virtual_prefix in [(user_dir, "my"), (shared_dir, "shared")]:
            if not base_dir.is_dir():
                continue
            count = 0
            try:
                for entry in base_dir.rglob("*"):
                    if count >= PER_MODULE_LIMIT:
                        break
                    if entry.name.lower().find(lower_q) != -1:
                        rel = entry.relative_to(base_dir)
                        vpath = f"{virtual_prefix}/{rel}"
                        file_results.append({
                            "type": "file",
                            "id": vpath,
                            "title": entry.name,
                            "snippet": str(vpath),
                            "url": f"/files?path={virtual_prefix}/{rel.parent}" if entry.is_file() else f"/files?path={vpath}",
                        })
                        count += 1
            except OSError:
                pass

        results.extend(file_results[:PER_MODULE_LIMIT])

    # Enforce total limit
    results = results[:TOTAL_LIMIT]

    return {"results": results, "total": len(results)}
