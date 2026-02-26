"""Gitea webhook → chat notification channel."""

import hashlib
import hmac
import logging
import uuid

from fastapi import APIRouter, Request, HTTPException

from app.config import get_settings
from app.db.session import async_session
from app.db.models import Channel, ChannelMember, Message, User
from app.chat import service
from app.chat.websocket import manager

from sqlalchemy import select

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

CHANNEL_NAME = settings.gitea_webhook_channel or "git-notifications"


def _verify_signature(body: bytes, signature: str) -> bool:
    """Verify HMAC-SHA256 signature from Gitea."""
    expected = hmac.new(
        settings.gitea_webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _parse_event(event_type: str, payload: dict) -> str | None:
    """Parse Gitea event into a human-readable message. Returns None to skip."""
    repo_name = payload.get("repository", {}).get("full_name", "")

    if event_type == "push":
        pusher = payload.get("pusher", {}).get("login", "unknown")
        commits = payload.get("commits", [])
        ref = payload.get("ref", "").replace("refs/heads/", "")
        lines = [f"[{repo_name}] {pusher}님이 {ref} 브랜치에 {len(commits)}개 커밋을 push했습니다."]
        for c in commits[:5]:
            msg = c.get("message", "").split("\n")[0][:80]
            sha = c.get("id", "")[:7]
            lines.append(f"  • {sha} {msg}")
        if len(commits) > 5:
            lines.append(f"  ... 외 {len(commits) - 5}개")
        return "\n".join(lines)

    if event_type == "pull_request":
        action = payload.get("action", "")
        pr = payload.get("pull_request", {})
        title = pr.get("title", "")
        number = pr.get("number", "")
        user = pr.get("user", {}).get("login", "unknown")
        return f"[{repo_name}] PR #{number} {action}: {title} (by {user})"

    if event_type in ("issues", "issue_comment"):
        action = payload.get("action", "")
        issue = payload.get("issue", {})
        title = issue.get("title", "")
        number = issue.get("number", "")
        user = payload.get("sender", {}).get("login", "unknown")
        if event_type == "issue_comment":
            return f"[{repo_name}] Issue #{number} 댓글: {title} (by {user})"
        return f"[{repo_name}] Issue #{number} {action}: {title} (by {user})"

    if event_type == "create":
        ref_type = payload.get("ref_type", "")
        ref = payload.get("ref", "")
        user = payload.get("sender", {}).get("login", "unknown")
        return f"[{repo_name}] {user}님이 {ref_type} '{ref}'을 생성했습니다."

    if event_type == "delete":
        ref_type = payload.get("ref_type", "")
        ref = payload.get("ref", "")
        user = payload.get("sender", {}).get("login", "unknown")
        return f"[{repo_name}] {user}님이 {ref_type} '{ref}'을 삭제했습니다."

    return None


async def _get_or_create_webhook_channel(db) -> str:
    """Get or create the git-notifications channel. Returns channel_id."""
    ch = (
        await db.execute(
            select(Channel).where(Channel.name == CHANNEL_NAME).limit(1)
        )
    ).scalar_one_or_none()

    if ch:
        return ch.id

    # Find an admin user to be the creator
    admin = (
        await db.execute(
            select(User).where(User.is_admin == True).limit(1)  # noqa: E712
        )
    ).scalar_one_or_none()

    creator_id = admin.id if admin else str(uuid.uuid4())

    channel = Channel(
        id=str(uuid.uuid4()),
        name=CHANNEL_NAME,
        type="public",
        description="Git 저장소 알림 (자동 생성)",
        created_by=creator_id,
    )
    db.add(channel)

    # Add creator as owner
    if admin:
        db.add(ChannelMember(
            id=str(uuid.uuid4()),
            channel_id=channel.id,
            user_id=creator_id,
            role="owner",
        ))

    db.add(Message(
        id=str(uuid.uuid4()),
        channel_id=channel.id,
        sender_id=None,
        content="Git 알림 채널이 생성되었습니다.",
        message_type="system",
    ))

    await db.commit()
    return channel.id


@router.post("/gitea")
async def gitea_webhook(request: Request):
    """Receive Gitea webhook events and post to chat channel."""
    body = await request.body()

    # Verify signature
    sig = request.headers.get("X-Gitea-Signature", "")
    if not settings.gitea_webhook_secret:
        raise HTTPException(403, "Webhook secret not configured")
    if not _verify_signature(body, sig):
        raise HTTPException(403, "Invalid signature")

    event_type = request.headers.get("X-Gitea-Event", "")
    if not event_type:
        return {"ok": True, "skipped": "no event type"}

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON")

    content = _parse_event(event_type, payload)
    if not content:
        return {"ok": True, "skipped": f"unhandled event: {event_type}"}

    async with async_session() as db:
        channel_id = await _get_or_create_webhook_channel(db)
        msg = await service.create_message(
            db, channel_id, sender_id=None,
            content=content, message_type="system",
        )

    # Broadcast to WS
    await manager.publish_to_channel(channel_id, {
        "type": "new_message",
        "message": msg,
    })

    return {"ok": True, "event": event_type}
