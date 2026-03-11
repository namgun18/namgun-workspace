"""Dashboard API router — aggregated summary for the dashboard page."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db.models import (
    Notification, Post, Message, ShareLink, TaskDB, User,
    CalendarEventDB, CalendarDB,
)
from app.db.session import get_db

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
async def dashboard_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return an aggregated dashboard summary for the current user."""
    uid = str(user.id)
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    # Unread notifications
    unread_notifs = await db.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == uid,
            Notification.is_read == False,  # noqa: E712
        )
    ) or 0

    # Tasks by status
    task_rows = (await db.execute(
        select(TaskDB.status, func.count(TaskDB.id))
        .where(TaskDB.user_id == uid)
        .group_by(TaskDB.status)
    )).all()
    tasks = {row[0]: row[1] for row in task_rows}

    # Recent posts (last 7 days)
    recent_posts = await db.scalar(
        select(func.count(Post.id)).where(Post.created_at >= week_ago)
    ) or 0

    # Recent chat messages (last 7 days)
    recent_messages = await db.scalar(
        select(func.count(Message.id)).where(Message.created_at >= week_ago)
    ) or 0

    # Active share links
    active_shares = await db.scalar(
        select(func.count(ShareLink.id)).where(
            ShareLink.created_by == uid,
            ShareLink.is_active == True,  # noqa: E712
        )
    ) or 0

    # Upcoming events (next 7 days)
    next_week = now + timedelta(days=7)
    my_calendars = (await db.execute(
        select(CalendarDB.id).where(CalendarDB.owner_id == uid)
    )).scalars().all()
    upcoming_events = 0
    if my_calendars:
        upcoming_events = await db.scalar(
            select(func.count(CalendarEventDB.id)).where(
                CalendarEventDB.calendar_id.in_(my_calendars),
                CalendarEventDB.start_time >= now,
                CalendarEventDB.start_time <= next_week,
            )
        ) or 0

    return {
        "status": "ok",
        "unread_notifications": unread_notifs,
        "tasks": {
            "todo": tasks.get("todo", 0),
            "in_progress": tasks.get("in_progress", 0),
            "done": tasks.get("done", 0),
        },
        "recent_posts_7d": recent_posts,
        "recent_messages_7d": recent_messages,
        "active_share_links": active_shares,
        "upcoming_events_7d": upcoming_events,
    }
