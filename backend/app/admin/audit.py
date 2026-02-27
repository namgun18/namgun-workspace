"""Audit log helpers — record and query admin actions."""

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog, User


async def log_action(
    db: AsyncSession,
    actor_id: str | None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict | None = None,
    ip: str | None = None,
) -> AuditLog:
    """Record an audit log entry."""
    entry = AuditLog(
        id=str(uuid.uuid4()),
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=json.dumps(details, ensure_ascii=False) if details else None,
        ip_address=ip,
        created_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    await db.commit()
    return entry


async def get_audit_logs(
    db: AsyncSession,
    page: int = 0,
    limit: int = 50,
    actor_id: str | None = None,
    action: str | None = None,
) -> tuple[list[dict], int]:
    """Query audit logs with optional filters. Returns (logs, total)."""
    conditions = []
    if actor_id:
        conditions.append(AuditLog.actor_id == actor_id)
    if action:
        conditions.append(AuditLog.action == action)

    where = and_(*conditions) if conditions else True

    # Total count
    count_result = await db.execute(
        select(func.count(AuditLog.id)).where(where)
    )
    total = count_result.scalar() or 0

    # Fetch page with LEFT JOIN to get username
    offset = page * limit
    result = await db.execute(
        select(AuditLog, User.username, User.display_name)
        .outerjoin(User, AuditLog.actor_id == User.id)
        .where(where)
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    logs = []
    for entry, username, display_name in result.all():
        logs.append({
            "id": entry.id,
            "actor_id": entry.actor_id,
            "actor_username": username,
            "actor_display_name": display_name,
            "action": entry.action,
            "resource_type": entry.resource_type,
            "resource_id": entry.resource_id,
            "details": json.loads(entry.details) if entry.details else None,
            "ip_address": entry.ip_address,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
        })

    return logs, total
