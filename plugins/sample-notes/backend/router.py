"""Notes plugin — CRUD API endpoints."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

# Import from the main app
from app.auth.deps import get_current_user
from app.db.models import User
from app.db.session import get_db, engine
from app.modules.registry import is_module_enabled

from plugin_notes_models import Note, PluginBase

router = APIRouter()

# Ensure table is created at import time
_table_created = False


async def _ensure_table():
    global _table_created
    if not _table_created:
        async with engine.begin() as conn:
            await conn.run_sync(PluginBase.metadata.create_all)
        _table_created = True


def _check_enabled():
    if not is_module_enabled("notes"):
        raise HTTPException(status_code=403, detail="이 기능은 비활성화되어 있습니다")


# ─── Schemas ───

class NoteCreate(BaseModel):
    title: str = ""
    content: str = ""


class NoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None


class NoteResponse(BaseModel):
    id: str
    title: str
    content: str
    created_at: str
    updated_at: str


# ─── Endpoints ───

@router.get("")
async def list_notes(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all notes for the current user."""
    _check_enabled()
    await _ensure_table()

    result = await db.execute(
        select(Note)
        .where(Note.user_id == user.id)
        .order_by(desc(Note.updated_at))
    )
    notes = result.scalars().all()
    return {
        "notes": [
            {
                "id": n.id,
                "title": n.title,
                "content": n.content,
                "created_at": n.created_at.isoformat(),
                "updated_at": n.updated_at.isoformat(),
            }
            for n in notes
        ]
    }


@router.post("")
async def create_note(
    body: NoteCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new note."""
    _check_enabled()
    await _ensure_table()

    note = Note(
        id=str(uuid.uuid4()),
        user_id=user.id,
        title=body.title,
        content=body.content,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)

    return {
        "id": note.id,
        "title": note.title,
        "content": note.content,
        "created_at": note.created_at.isoformat(),
        "updated_at": note.updated_at.isoformat(),
    }


@router.get("/{note_id}")
async def get_note(
    note_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific note."""
    _check_enabled()
    await _ensure_table()

    result = await db.execute(
        select(Note).where(Note.id == note_id, Note.user_id == user.id)
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="메모를 찾을 수 없습니다")

    return {
        "id": note.id,
        "title": note.title,
        "content": note.content,
        "created_at": note.created_at.isoformat(),
        "updated_at": note.updated_at.isoformat(),
    }


@router.patch("/{note_id}")
async def update_note(
    note_id: str,
    body: NoteUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a note."""
    _check_enabled()
    await _ensure_table()

    result = await db.execute(
        select(Note).where(Note.id == note_id, Note.user_id == user.id)
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="메모를 찾을 수 없습니다")

    if body.title is not None:
        note.title = body.title
    if body.content is not None:
        note.content = body.content
    note.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(note)

    return {
        "id": note.id,
        "title": note.title,
        "content": note.content,
        "created_at": note.created_at.isoformat(),
        "updated_at": note.updated_at.isoformat(),
    }


@router.delete("/{note_id}")
async def delete_note(
    note_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a note."""
    _check_enabled()
    await _ensure_table()

    result = await db.execute(
        select(Note).where(Note.id == note_id, Note.user_id == user.id)
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="메모를 찾을 수 없습니다")

    await db.delete(note)
    await db.commit()

    return {"ok": True}
