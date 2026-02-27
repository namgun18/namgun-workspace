"""Chat REST API endpoints."""

import json
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.config import get_settings
from app.db.models import User
from app.db.session import get_db
from app.chat import service
from app.chat.schemas import (
    ChannelCreate,
    ChannelUpdate,
    DMRequest,
    MemberAdd,
    MessageCreate,
    MessageUpdate,
    NotificationReadRequest,
    ReactionToggle,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])


# ─── Channels ───

@router.get("/channels")
async def list_channels(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    channels = await service.get_user_channels(db, user.id)
    return channels


@router.post("/channels", status_code=201)
async def create_channel(
    body: ChannelCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ch = await service.create_channel(
        db,
        name=body.name,
        type=body.type,
        created_by=user.id,
        description=body.description,
        member_ids=body.member_ids,
    )
    return {"id": ch.id, "name": ch.name, "type": ch.type}


@router.get("/channels/{channel_id}")
async def get_channel(
    channel_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ch = await service.get_channel(db, channel_id)
    if not ch:
        raise HTTPException(404, "채널을 찾을 수 없습니다")
    if not await service.is_channel_member(db, channel_id, user.id):
        raise HTTPException(403, "채널 멤버가 아닙니다")
    members = await service.get_channel_members(db, channel_id)
    return {
        "id": ch.id,
        "name": ch.name,
        "type": ch.type,
        "description": ch.description,
        "created_by": ch.created_by,
        "is_archived": ch.is_archived,
        "created_at": ch.created_at,
        "updated_at": ch.updated_at,
        "member_count": len(members),
        "members": members,
    }


@router.patch("/channels/{channel_id}")
async def update_channel(
    channel_id: str,
    body: ChannelUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    role = await service.get_member_role(db, channel_id, user.id)
    if role not in ("owner", "admin"):
        raise HTTPException(403, "권한이 없습니다")
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "변경할 내용이 없습니다")
    ch = await service.update_channel(db, channel_id, **updates)
    if not ch:
        raise HTTPException(404, "채널을 찾을 수 없습니다")
    return {"ok": True}


@router.delete("/channels/{channel_id}")
async def delete_channel(
    channel_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    role = await service.get_member_role(db, channel_id, user.id)
    if role != "owner":
        raise HTTPException(403, "채널 소유자만 삭제할 수 있습니다")
    await service.delete_channel(db, channel_id)
    return {"ok": True}


# ─── Members ───

@router.get("/channels/{channel_id}/members")
async def list_members(
    channel_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await service.is_channel_member(db, channel_id, user.id):
        raise HTTPException(403, "채널 멤버가 아닙니다")
    return await service.get_channel_members(db, channel_id)


@router.post("/channels/{channel_id}/members", status_code=201)
async def add_members(
    channel_id: str,
    body: MemberAdd,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    role = await service.get_member_role(db, channel_id, user.id)
    if not role:
        raise HTTPException(403, "채널 멤버가 아닙니다")
    added = await service.add_members(db, channel_id, body.user_ids)
    return {"added": added}


@router.delete("/channels/{channel_id}/members/{target_user_id}")
async def remove_member(
    channel_id: str,
    target_user_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Can remove self, or admin/owner can remove others
    if target_user_id != user.id:
        role = await service.get_member_role(db, channel_id, user.id)
        if role not in ("owner", "admin"):
            raise HTTPException(403, "권한이 없습니다")
    ok = await service.remove_member(db, channel_id, target_user_id)
    if not ok:
        raise HTTPException(404, "멤버를 찾을 수 없습니다")
    return {"ok": True}


# ─── Messages ───

@router.get("/channels/{channel_id}/messages")
async def list_messages(
    channel_id: str,
    before: str | None = Query(None),
    after: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await service.is_channel_member(db, channel_id, user.id):
        raise HTTPException(403, "채널 멤버가 아닙니다")
    messages, has_more = await service.get_messages(
        db, channel_id, before=before, after=after, limit=limit
    )
    return {"messages": messages, "has_more": has_more}


@router.post("/channels/{channel_id}/messages", status_code=201)
async def send_message(
    channel_id: str,
    body: MessageCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await service.is_channel_member(db, channel_id, user.id):
        raise HTTPException(403, "채널 멤버가 아닙니다")
    msg = await service.create_message(
        db, channel_id, user.id, body.content,
        message_type=body.message_type, file_meta=body.file_meta,
        parent_id=body.parent_id,
    )
    return msg


# ─── File Upload (chat attachments) ───

@router.post("/channels/{channel_id}/upload", status_code=201)
async def upload_chat_file(
    channel_id: str,
    file: UploadFile,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file and create a message with message_type='file'."""
    if not await service.is_channel_member(db, channel_id, user.id):
        raise HTTPException(403, "채널 멤버가 아닙니다")

    settings = get_settings()

    # Prepare storage directory
    chat_files_dir = Path(settings.storage_root) / "chat_files" / channel_id
    chat_files_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize filename
    raw_name = file.filename or "upload"
    safe_name = os.path.basename(raw_name).strip()
    if not safe_name or safe_name.startswith(".") or "\x00" in safe_name:
        raise HTTPException(400, "잘못된 파일명입니다")
    if ".." in safe_name or len(safe_name) > 255:
        raise HTTPException(400, "잘못된 파일명입니다")

    # Unique filename to avoid collisions
    import uuid as _uuid
    unique_prefix = _uuid.uuid4().hex[:8]
    disk_name = f"{unique_prefix}_{safe_name}"
    target = chat_files_dir / disk_name

    # Stream write with size limit (50 MB for chat files)
    max_bytes = 50 * 1024 * 1024
    written = 0
    with open(target, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            written += len(chunk)
            if written > max_bytes:
                f.close()
                target.unlink(missing_ok=True)
                raise HTTPException(413, "파일 크기가 50MB를 초과합니다")
            f.write(chunk)

    # Determine mime type
    import mimetypes
    mime_type = file.content_type or mimetypes.guess_type(safe_name)[0] or "application/octet-stream"

    # Build file URL (served via /api/files/download with a special path, or direct)
    file_url = f"/api/chat/channels/{channel_id}/files/{disk_name}"

    file_meta = json.dumps({
        "filename": safe_name,
        "size": written,
        "mime_type": mime_type,
        "url": file_url,
        "disk_name": disk_name,
    }, ensure_ascii=False)

    # Create file message
    msg = await service.create_message(
        db, channel_id, user.id,
        content=safe_name,
        message_type="file",
        file_meta=file_meta,
    )
    return msg


# ─── Chat file download ───

@router.get("/channels/{channel_id}/files/{filename}")
async def download_chat_file(
    channel_id: str,
    filename: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download a file uploaded to a chat channel."""
    if not await service.is_channel_member(db, channel_id, user.id):
        raise HTTPException(403, "채널 멤버가 아닙니다")

    settings = get_settings()
    chat_files_dir = Path(settings.storage_root) / "chat_files" / channel_id
    file_path = chat_files_dir / filename

    # Security: ensure path doesn't escape
    if not str(file_path.resolve()).startswith(str(chat_files_dir.resolve())):
        raise HTTPException(403, "경로 접근이 거부되었습니다")
    if not file_path.is_file():
        raise HTTPException(404, "파일을 찾을 수 없습니다")

    from fastapi.responses import FileResponse
    # Extract original filename from disk_name (strip uuid prefix)
    original_name = filename.split("_", 1)[1] if "_" in filename else filename
    return FileResponse(
        path=str(file_path),
        filename=original_name,
        media_type="application/octet-stream",
    )


@router.get("/messages/search")
async def search_messages(
    q: str = Query(..., min_length=1),
    channel_id: str | None = Query(None),
    limit: int = Query(20, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    results = await service.search_messages(
        db, user.id, q, channel_id=channel_id, limit=limit
    )
    return results


@router.get("/messages/{message_id}/thread")
async def get_thread(
    message_id: str,
    limit: int = Query(100, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.db.models import Message as MsgModel
    parent = await db.get(MsgModel, message_id)
    if not parent:
        raise HTTPException(404, "메시지를 찾을 수 없습니다")
    if not await service.is_channel_member(db, parent.channel_id, user.id):
        raise HTTPException(403, "채널 멤버가 아닙니다")
    replies = await service.get_thread_messages(db, message_id, limit=limit)
    return {"replies": replies}


@router.post("/messages/{message_id}/reactions")
async def toggle_reaction(
    message_id: str,
    body: ReactionToggle,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.db.models import Message as MsgModel
    msg = await db.get(MsgModel, message_id)
    if not msg:
        raise HTTPException(404, "메시지를 찾을 수 없습니다")
    if not await service.is_channel_member(db, msg.channel_id, user.id):
        raise HTTPException(403, "채널 멤버가 아닙니다")
    result = await service.toggle_reaction(db, message_id, user.id, body.emoji)
    return result


@router.patch("/messages/{message_id}")
async def edit_message(
    message_id: str,
    body: MessageUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.db.models import Message as MsgModel
    msg = await db.get(MsgModel, message_id)
    if not msg:
        raise HTTPException(404, "메시지를 찾을 수 없습니다")
    if msg.sender_id != user.id:
        raise HTTPException(403, "본인 메시지만 수정할 수 있습니다")
    updated = await service.update_message(db, message_id, body.content)
    return updated


@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.db.models import Message as MsgModel
    msg = await db.get(MsgModel, message_id)
    if not msg:
        raise HTTPException(404, "메시지를 찾을 수 없습니다")
    if msg.sender_id != user.id:
        raise HTTPException(403, "본인 메시지만 삭제할 수 있습니다")
    await service.soft_delete_message(db, message_id)
    return {"ok": True}


# ─── DM ───

@router.post("/dm")
async def get_or_create_dm(
    body: DMRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.user_id == user.id:
        raise HTTPException(400, "자기 자신에게 DM을 보낼 수 없습니다")
    other = await db.get(User, body.user_id)
    if not other:
        raise HTTPException(404, "사용자를 찾을 수 없습니다")
    ch = await service.get_or_create_dm(db, user.id, body.user_id)
    return {"id": ch.id, "name": ch.name, "type": ch.type}


# ─── Presence ───

@router.get("/presence")
async def get_presence(
    user: User = Depends(get_current_user),
):
    from app.chat.presence import get_online_users
    online = await get_online_users()
    return {"online_user_ids": list(online)}


# ─── User Search ───

# ─── Notifications ───

@router.get("/notifications")
async def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    notifications = await service.get_notifications(db, user.id, limit=limit, unread_only=unread_only)
    unread_count = await service.get_unread_notification_count(db, user.id)
    return {"notifications": notifications, "unread_count": unread_count}


@router.post("/notifications/read")
async def mark_notifications_read(
    body: NotificationReadRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = await service.mark_notifications_read(db, user.id, body.notification_ids)
    return {"ok": True, "updated": count}


@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = await service.mark_notifications_read(db, user.id)
    return {"ok": True, "updated": count}


# ─── User Search ───

@router.get("/users")
async def search_users(
    q: str = Query("", min_length=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.search_users(db, q.strip() if q.strip() else None)
