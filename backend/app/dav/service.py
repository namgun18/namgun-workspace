"""DAV-specific database queries."""

import hashlib
import json
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    CalendarDB, CalendarEventDB,
    AddressBookDB, ContactDB, User,
)


# ── Helpers ──

def compute_etag(row_id: str, updated_at: datetime | None) -> str:
    raw = f"{row_id}:{updated_at.isoformat() if updated_at else ''}"
    return hashlib.md5(raw.encode()).hexdigest()


async def calendar_ctag(db: AsyncSession, calendar_id: str) -> str:
    result = await db.execute(
        select(func.max(CalendarEventDB.updated_at))
        .where(CalendarEventDB.calendar_id == calendar_id)
    )
    mx = result.scalar()
    if mx:
        return hashlib.md5(mx.isoformat().encode()).hexdigest()
    return "empty"


async def addressbook_ctag(db: AsyncSession, book_id: str) -> str:
    result = await db.execute(
        select(func.max(ContactDB.updated_at))
        .where(ContactDB.address_book_id == book_id)
    )
    mx = result.scalar()
    if mx:
        return hashlib.md5(mx.isoformat().encode()).hexdigest()
    return "empty"


# ── User lookup ──

async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


# ── Calendar queries ──

async def get_user_calendars(db: AsyncSession, user_id: str) -> list[CalendarDB]:
    result = await db.execute(
        select(CalendarDB)
        .where(CalendarDB.user_id == user_id)
        .order_by(CalendarDB.sort_order, CalendarDB.name)
    )
    return list(result.scalars().all())


async def get_calendar(db: AsyncSession, cal_id: str) -> CalendarDB | None:
    return await db.get(CalendarDB, cal_id)


async def get_calendar_events(db: AsyncSession, cal_id: str) -> list[CalendarEventDB]:
    result = await db.execute(
        select(CalendarEventDB)
        .where(CalendarEventDB.calendar_id == cal_id)
        .order_by(CalendarEventDB.start)
    )
    return list(result.scalars().all())


async def get_event(db: AsyncSession, event_id: str) -> CalendarEventDB | None:
    return await db.get(CalendarEventDB, event_id)


async def get_events_by_ids(
    db: AsyncSession, ids: list[str],
) -> list[CalendarEventDB]:
    if not ids:
        return []
    result = await db.execute(
        select(CalendarEventDB).where(CalendarEventDB.id.in_(ids))
    )
    return list(result.scalars().all())


async def upsert_event(
    db: AsyncSession, event_id: str, cal_id: str, data: dict,
) -> CalendarEventDB:
    ev = await db.get(CalendarEventDB, event_id)
    if ev:
        for k in ("title", "description", "location", "start", "end", "all_day", "status"):
            if k in data:
                setattr(ev, k, data[k])
    else:
        ev = CalendarEventDB(
            id=event_id,
            calendar_id=cal_id,
            title=data.get("title", ""),
            description=data.get("description"),
            location=data.get("location"),
            start=data.get("start"),
            end=data.get("end"),
            all_day=data.get("all_day", False),
            status=data.get("status", "confirmed"),
        )
        db.add(ev)
    await db.commit()
    await db.refresh(ev)
    return ev


async def delete_event(db: AsyncSession, event_id: str) -> bool:
    ev = await db.get(CalendarEventDB, event_id)
    if not ev:
        return False
    await db.delete(ev)
    await db.commit()
    return True


# ── Address Book queries ──

async def get_user_address_books(db: AsyncSession, user_id: str) -> list[AddressBookDB]:
    result = await db.execute(
        select(AddressBookDB)
        .where(AddressBookDB.user_id == user_id)
        .order_by(AddressBookDB.name)
    )
    return list(result.scalars().all())


async def get_address_book(db: AsyncSession, book_id: str) -> AddressBookDB | None:
    return await db.get(AddressBookDB, book_id)


async def get_book_contacts(db: AsyncSession, book_id: str) -> list[ContactDB]:
    result = await db.execute(
        select(ContactDB)
        .where(ContactDB.address_book_id == book_id)
        .order_by(ContactDB.full_name)
    )
    return list(result.scalars().all())


async def get_contact(db: AsyncSession, contact_id: str) -> ContactDB | None:
    return await db.get(ContactDB, contact_id)


async def get_contacts_by_ids(
    db: AsyncSession, ids: list[str],
) -> list[ContactDB]:
    if not ids:
        return []
    result = await db.execute(
        select(ContactDB).where(ContactDB.id.in_(ids))
    )
    return list(result.scalars().all())


async def upsert_contact(
    db: AsyncSession, contact_id: str, book_id: str, data: dict,
) -> ContactDB:
    c = await db.get(ContactDB, contact_id)
    if c:
        if "name" in data:
            c.full_name = data["name"]
        if "first_name" in data:
            c.given_name = data["first_name"]
        if "last_name" in data:
            c.surname = data["last_name"]
        if "organization" in data:
            c.organization = data["organization"]
        if "emails" in data:
            c.emails = json.dumps(data["emails"], ensure_ascii=False) if data["emails"] else None
        if "phones" in data:
            c.phones = json.dumps(data["phones"], ensure_ascii=False) if data["phones"] else None
        if "addresses" in data:
            c.addresses = json.dumps(data["addresses"], ensure_ascii=False) if data["addresses"] else None
        if "notes" in data:
            c.notes = data["notes"]
    else:
        c = ContactDB(
            id=contact_id,
            address_book_id=book_id,
            full_name=data.get("name", ""),
            given_name=data.get("first_name"),
            surname=data.get("last_name"),
            organization=data.get("organization"),
            emails=json.dumps(data["emails"], ensure_ascii=False) if data.get("emails") else None,
            phones=json.dumps(data["phones"], ensure_ascii=False) if data.get("phones") else None,
            addresses=json.dumps(data["addresses"], ensure_ascii=False) if data.get("addresses") else None,
            notes=data.get("notes"),
        )
        db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


async def delete_contact(db: AsyncSession, contact_id: str) -> bool:
    c = await db.get(ContactDB, contact_id)
    if not c:
        return False
    await db.delete(c)
    await db.commit()
    return True
