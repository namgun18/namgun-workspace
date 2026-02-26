"""Calendar API endpoints — PostgreSQL backend."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.calendar import service
from app.calendar.schemas import (
    CalendarInfo,
    CalendarCreate,
    CalendarUpdate,
    CalendarEvent,
    EventCreate,
    EventUpdate,
    CalendarListResponse,
    EventListResponse,
    CalendarShareRequest,
    CalendarShareInfo,
)
from app.modules.registry import require_module

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


# ─── Calendars ───


@router.get("/calendars", response_model=CalendarListResponse)
@require_module("calendar")
async def list_calendars(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    calendars = await service.get_calendars(db, user.id)
    return {"calendars": [CalendarInfo(**c) for c in calendars]}


@router.post("/calendars", response_model=CalendarInfo)
@require_module("calendar")
async def create_calendar(
    body: CalendarCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await service.create_calendar(db, user.id, body.name, body.color)
    return CalendarInfo(**result)


@router.patch("/calendars/{calendar_id}", response_model=dict)
@require_module("calendar")
async def update_calendar(
    calendar_id: str,
    body: CalendarUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    ok = await service.update_calendar(db, user.id, calendar_id, updates)
    if not ok:
        raise HTTPException(status_code=404, detail="Calendar not found or no permission")
    return {"ok": True}


@router.delete("/calendars/{calendar_id}", response_model=dict)
@require_module("calendar")
async def delete_calendar(
    calendar_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ok = await service.delete_calendar(db, user.id, calendar_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Calendar not found or no permission")
    return {"ok": True}


# ─── Calendar Sharing ───


@router.get("/calendars/{calendar_id}/shares", response_model=list[CalendarShareInfo])
@require_module("calendar")
async def list_calendar_shares(
    calendar_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    shares = await service.get_calendar_shares(db, user.id, calendar_id)
    return [CalendarShareInfo(**s) for s in shares]


@router.post("/calendars/{calendar_id}/shares", response_model=dict)
@require_module("calendar")
async def set_calendar_shares(
    calendar_id: str,
    body: CalendarShareRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    shares = [s.model_dump() for s in body.shares]
    ok = await service.share_calendar(db, user.id, calendar_id, shares)
    if not ok:
        raise HTTPException(status_code=404, detail="Calendar not found or no permission")
    return {"ok": True}


@router.delete("/calendars/{calendar_id}/shares/{email}", response_model=dict)
@require_module("calendar")
async def remove_calendar_share(
    calendar_id: str,
    email: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ok = await service.unshare_calendar(db, user.id, calendar_id, email)
    if not ok:
        raise HTTPException(status_code=404, detail="Share not found")
    return {"ok": True}


# ─── Events ───


@router.get("/events", response_model=EventListResponse)
@require_module("calendar")
async def list_events(
    start: str | None = Query(None, description="ISO 8601 start date"),
    end: str | None = Query(None, description="ISO 8601 end date"),
    calendar_id: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    events = await service.get_events(db, user.id, start, end, calendar_id)
    return {"events": [CalendarEvent(**e) for e in events]}


@router.get("/events/{event_id}", response_model=CalendarEvent)
@require_module("calendar")
async def get_event(
    event_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    event = await service.get_event(db, user.id, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return CalendarEvent(**event)


@router.post("/events", response_model=CalendarEvent)
@require_module("calendar")
async def create_event(
    body: EventCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await service.create_event(db, user.id, body.model_dump())
    if not result:
        raise HTTPException(status_code=400, detail="Failed to create event")
    return CalendarEvent(**result)


@router.patch("/events/{event_id}", response_model=dict)
@require_module("calendar")
async def update_event(
    event_id: str,
    body: EventUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    ok = await service.update_event(db, user.id, event_id, updates)
    if not ok:
        raise HTTPException(status_code=404, detail="Event not found or no permission")
    return {"ok": True}


@router.delete("/events/{event_id}", response_model=dict)
@require_module("calendar")
async def delete_event(
    event_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ok = await service.delete_event(db, user.id, event_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Event not found or no permission")
    return {"ok": True}
