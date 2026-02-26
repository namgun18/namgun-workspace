"""Calendar service — PostgreSQL CRUD (replaces JMAP)."""

import json
from datetime import datetime

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CalendarDB, CalendarEventDB, CalendarShareDB, User


# ─── Calendar CRUD ───


async def get_calendars(db: AsyncSession, user_id: str) -> list[dict]:
    """Get all calendars owned by or shared with the user.
    Auto-creates a default calendar if the user has none.
    """
    # Own calendars
    result = await db.execute(
        select(CalendarDB)
        .where(CalendarDB.user_id == user_id)
        .order_by(CalendarDB.sort_order, CalendarDB.name)
    )
    calendars = []
    for cal in result.scalars().all():
        calendars.append({
            "id": cal.id,
            "name": cal.name,
            "color": cal.color,
            "is_visible": cal.is_visible,
            "sort_order": cal.sort_order,
        })

    # Auto-create default calendar if none exist
    if not calendars:
        default = await create_calendar(db, user_id, "내 캘린더", "#3b82f6")
        calendars.append({**default, "is_visible": True, "sort_order": 0})

    # Shared calendars
    shared_result = await db.execute(
        select(CalendarDB)
        .join(CalendarShareDB, CalendarShareDB.calendar_id == CalendarDB.id)
        .where(CalendarShareDB.shared_with_user_id == user_id)
        .order_by(CalendarDB.name)
    )
    for cal in shared_result.scalars().all():
        if not any(c["id"] == cal.id for c in calendars):
            calendars.append({
                "id": cal.id,
                "name": cal.name,
                "color": cal.color,
                "is_visible": cal.is_visible,
                "sort_order": cal.sort_order,
            })

    return calendars


async def create_calendar(
    db: AsyncSession, user_id: str, name: str, color: str | None = None
) -> dict:
    cal = CalendarDB(user_id=user_id, name=name, color=color)
    db.add(cal)
    await db.commit()
    await db.refresh(cal)
    return {"id": cal.id, "name": cal.name, "color": cal.color}


async def update_calendar(
    db: AsyncSession, user_id: str, calendar_id: str, updates: dict
) -> bool:
    cal = await db.get(CalendarDB, calendar_id)
    if not cal or cal.user_id != user_id:
        return False
    if "name" in updates and updates["name"] is not None:
        cal.name = updates["name"]
    if "color" in updates and updates["color"] is not None:
        cal.color = updates["color"]
    if "is_visible" in updates and updates["is_visible"] is not None:
        cal.is_visible = updates["is_visible"]
    await db.commit()
    return True


async def delete_calendar(db: AsyncSession, user_id: str, calendar_id: str) -> bool:
    cal = await db.get(CalendarDB, calendar_id)
    if not cal or cal.user_id != user_id:
        return False
    await db.delete(cal)
    await db.commit()
    return True


# ─── Calendar Sharing ───


async def get_calendar_shares(
    db: AsyncSession, user_id: str, calendar_id: str
) -> list[dict]:
    """Get shares for a calendar. Only owner can see shares."""
    cal = await db.get(CalendarDB, calendar_id)
    if not cal or cal.user_id != user_id:
        return []
    result = await db.execute(
        select(CalendarShareDB, User.email, User.username)
        .join(User, User.id == CalendarShareDB.shared_with_user_id)
        .where(CalendarShareDB.calendar_id == calendar_id)
    )
    shares = []
    for row in result.all():
        share = row[0]
        email = row[1]
        shares.append({
            "email": email or row[2],
            "can_write": share.can_write,
        })
    return shares


async def share_calendar(
    db: AsyncSession, user_id: str, calendar_id: str, shares: list[dict]
) -> bool:
    """Set shares on a calendar. Replace all existing shares."""
    cal = await db.get(CalendarDB, calendar_id)
    if not cal or cal.user_id != user_id:
        return False

    # Delete existing shares
    result = await db.execute(
        select(CalendarShareDB).where(CalendarShareDB.calendar_id == calendar_id)
    )
    for share in result.scalars().all():
        await db.delete(share)

    # Create new shares
    for s in shares:
        email = s.get("email", "")
        # Look up user by email or username
        user_result = await db.execute(
            select(User).where(
                or_(User.email == email, User.username == email)
            )
        )
        target_user = user_result.scalar_one_or_none()
        if target_user and target_user.id != user_id:
            share = CalendarShareDB(
                calendar_id=calendar_id,
                shared_with_user_id=target_user.id,
                can_write=s.get("can_write", False),
            )
            db.add(share)

    await db.commit()
    return True


async def unshare_calendar(
    db: AsyncSession, user_id: str, calendar_id: str, email: str
) -> bool:
    """Remove a single user from calendar sharing."""
    cal = await db.get(CalendarDB, calendar_id)
    if not cal or cal.user_id != user_id:
        return False

    # Find user by email or username
    user_result = await db.execute(
        select(User).where(or_(User.email == email, User.username == email))
    )
    target_user = user_result.scalar_one_or_none()
    if not target_user:
        return False

    result = await db.execute(
        select(CalendarShareDB).where(
            CalendarShareDB.calendar_id == calendar_id,
            CalendarShareDB.shared_with_user_id == target_user.id,
        )
    )
    share = result.scalar_one_or_none()
    if share:
        await db.delete(share)
        await db.commit()
    return True


# ─── Event CRUD ───


def _event_to_dict(event: CalendarEventDB, color: str | None = None) -> dict:
    return {
        "id": event.id,
        "calendar_id": event.calendar_id,
        "title": event.title,
        "description": event.description,
        "location": event.location,
        "start": event.start.isoformat() if event.start else "",
        "end": event.end.isoformat() if event.end else "",
        "all_day": event.all_day,
        "color": color,
        "status": event.status,
        "created": event.created_at.isoformat() if event.created_at else None,
        "updated": event.updated_at.isoformat() if event.updated_at else None,
    }


async def get_events(
    db: AsyncSession, user_id: str,
    start: str | None = None, end: str | None = None,
    calendar_id: str | None = None,
) -> list[dict]:
    """Get events for the user's calendars within date range."""
    # Get user's calendar IDs (own + shared)
    calendars = await get_calendars(db, user_id)
    cal_ids = [c["id"] for c in calendars]
    color_map = {c["id"]: c.get("color") for c in calendars}

    if not cal_ids:
        return []

    conditions = [CalendarEventDB.calendar_id.in_(cal_ids)]
    if calendar_id:
        conditions.append(CalendarEventDB.calendar_id == calendar_id)
    if start:
        try:
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            conditions.append(CalendarEventDB.end >= start_dt)
        except ValueError:
            pass
    if end:
        try:
            end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
            conditions.append(CalendarEventDB.start <= end_dt)
        except ValueError:
            pass

    result = await db.execute(
        select(CalendarEventDB)
        .where(and_(*conditions))
        .order_by(CalendarEventDB.start)
        .limit(500)
    )
    return [
        _event_to_dict(e, color_map.get(e.calendar_id))
        for e in result.scalars().all()
    ]


async def get_event(db: AsyncSession, user_id: str, event_id: str) -> dict | None:
    event = await db.get(CalendarEventDB, event_id)
    if not event:
        return None
    # Verify the user has access
    calendars = await get_calendars(db, user_id)
    cal_ids = {c["id"] for c in calendars}
    if event.calendar_id not in cal_ids:
        return None
    color_map = {c["id"]: c.get("color") for c in calendars}
    return _event_to_dict(event, color_map.get(event.calendar_id))


async def create_event(db: AsyncSession, user_id: str, data: dict) -> dict | None:
    # Verify calendar belongs to user
    cal = await db.get(CalendarDB, data["calendar_id"])
    if not cal:
        return None
    # Allow if owner or has write access
    if cal.user_id != user_id:
        share_result = await db.execute(
            select(CalendarShareDB).where(
                CalendarShareDB.calendar_id == cal.id,
                CalendarShareDB.shared_with_user_id == user_id,
                CalendarShareDB.can_write == True,
            )
        )
        if not share_result.scalar_one_or_none():
            return None

    start_dt = datetime.fromisoformat(data["start"].replace("Z", "+00:00"))
    end_dt = datetime.fromisoformat(data["end"].replace("Z", "+00:00"))

    event = CalendarEventDB(
        calendar_id=data["calendar_id"],
        title=data.get("title", ""),
        description=data.get("description"),
        location=data.get("location"),
        start=start_dt,
        end=end_dt,
        all_day=data.get("all_day", False),
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return _event_to_dict(event, cal.color)


async def update_event(
    db: AsyncSession, user_id: str, event_id: str, data: dict
) -> bool:
    event = await db.get(CalendarEventDB, event_id)
    if not event:
        return False
    # Verify access
    cal = await db.get(CalendarDB, event.calendar_id)
    if not cal:
        return False
    if cal.user_id != user_id:
        share_result = await db.execute(
            select(CalendarShareDB).where(
                CalendarShareDB.calendar_id == cal.id,
                CalendarShareDB.shared_with_user_id == user_id,
                CalendarShareDB.can_write == True,
            )
        )
        if not share_result.scalar_one_or_none():
            return False

    if "title" in data and data["title"] is not None:
        event.title = data["title"]
    if "description" in data:
        event.description = data.get("description") or ""
    if "location" in data:
        event.location = data.get("location")
    if "start" in data and data["start"] is not None:
        event.start = datetime.fromisoformat(data["start"].replace("Z", "+00:00"))
    if "end" in data and data["end"] is not None:
        event.end = datetime.fromisoformat(data["end"].replace("Z", "+00:00"))
    if "all_day" in data and data["all_day"] is not None:
        event.all_day = data["all_day"]
    if "calendar_id" in data and data["calendar_id"] is not None:
        event.calendar_id = data["calendar_id"]

    await db.commit()
    return True


async def delete_event(db: AsyncSession, user_id: str, event_id: str) -> bool:
    event = await db.get(CalendarEventDB, event_id)
    if not event:
        return False
    cal = await db.get(CalendarDB, event.calendar_id)
    if not cal:
        return False
    if cal.user_id != user_id:
        share_result = await db.execute(
            select(CalendarShareDB).where(
                CalendarShareDB.calendar_id == cal.id,
                CalendarShareDB.shared_with_user_id == user_id,
                CalendarShareDB.can_write == True,
            )
        )
        if not share_result.scalar_one_or_none():
            return False
    await db.delete(event)
    await db.commit()
    return True
