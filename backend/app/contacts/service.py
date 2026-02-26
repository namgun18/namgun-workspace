"""Contacts service — PostgreSQL CRUD (replaces JMAP)."""

import json

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AddressBookDB, ContactDB


# ─── Address Book CRUD ───


async def get_address_books(db: AsyncSession, user_id: str) -> list[dict]:
    result = await db.execute(
        select(AddressBookDB)
        .where(AddressBookDB.user_id == user_id)
        .order_by(AddressBookDB.name)
    )
    return [{"id": ab.id, "name": ab.name} for ab in result.scalars().all()]


async def create_address_book(db: AsyncSession, user_id: str, name: str) -> dict:
    ab = AddressBookDB(user_id=user_id, name=name)
    db.add(ab)
    await db.commit()
    await db.refresh(ab)
    return {"id": ab.id, "name": ab.name}


async def delete_address_book(db: AsyncSession, user_id: str, book_id: str) -> bool:
    ab = await db.get(AddressBookDB, book_id)
    if not ab or ab.user_id != user_id:
        return False
    await db.delete(ab)
    await db.commit()
    return True


# ─── Contact CRUD ───


def _contact_to_dict(c: ContactDB) -> dict:
    return {
        "id": c.id,
        "address_book_id": c.address_book_id,
        "name": c.full_name,
        "first_name": c.given_name,
        "last_name": c.surname,
        "organization": c.organization,
        "emails": json.loads(c.emails) if c.emails else [],
        "phones": json.loads(c.phones) if c.phones else [],
        "addresses": json.loads(c.addresses) if c.addresses else [],
        "notes": c.notes,
        "created": c.created_at.isoformat() if c.created_at else None,
        "updated": c.updated_at.isoformat() if c.updated_at else None,
    }


async def get_contacts(
    db: AsyncSession, user_id: str,
    q: str | None = None, book_id: str | None = None,
    page: int = 0, limit: int = 50,
) -> tuple[list[dict], int]:
    """Query contacts with optional search/filter. Returns (contacts, total)."""
    # Get user's address book IDs
    ab_result = await db.execute(
        select(AddressBookDB.id).where(AddressBookDB.user_id == user_id)
    )
    ab_ids = [row[0] for row in ab_result.all()]
    if not ab_ids:
        return [], 0

    conditions = [ContactDB.address_book_id.in_(ab_ids)]
    if book_id:
        conditions.append(ContactDB.address_book_id == book_id)
    if q:
        pattern = f"%{q}%"
        conditions.append(
            or_(
                ContactDB.full_name.ilike(pattern),
                ContactDB.organization.ilike(pattern),
                ContactDB.emails.ilike(pattern),
            )
        )

    where = and_(*conditions)

    # Total count
    count_result = await db.execute(select(func.count(ContactDB.id)).where(where))
    total = count_result.scalar() or 0

    # Fetch page
    result = await db.execute(
        select(ContactDB)
        .where(where)
        .order_by(ContactDB.full_name)
        .offset(page * limit)
        .limit(limit)
    )
    contacts = [_contact_to_dict(c) for c in result.scalars().all()]
    return contacts, total


async def get_contact(db: AsyncSession, user_id: str, contact_id: str) -> dict | None:
    contact = await db.get(ContactDB, contact_id)
    if not contact:
        return None
    # Verify ownership
    ab = await db.get(AddressBookDB, contact.address_book_id)
    if not ab or ab.user_id != user_id:
        return None
    return _contact_to_dict(contact)


async def create_contact(db: AsyncSession, user_id: str, data: dict) -> dict | None:
    # Verify address book ownership
    ab = await db.get(AddressBookDB, data["address_book_id"])
    if not ab or ab.user_id != user_id:
        return None

    contact = ContactDB(
        address_book_id=data["address_book_id"],
        full_name=data.get("name", ""),
        given_name=data.get("first_name"),
        surname=data.get("last_name"),
        organization=data.get("organization"),
        emails=json.dumps(data.get("emails", []), ensure_ascii=False) if data.get("emails") else None,
        phones=json.dumps(data.get("phones", []), ensure_ascii=False) if data.get("phones") else None,
        addresses=json.dumps(data.get("addresses", []), ensure_ascii=False) if data.get("addresses") else None,
        notes=data.get("notes"),
    )
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return _contact_to_dict(contact)


async def update_contact(
    db: AsyncSession, user_id: str, contact_id: str, data: dict
) -> bool:
    contact = await db.get(ContactDB, contact_id)
    if not contact:
        return False
    ab = await db.get(AddressBookDB, contact.address_book_id)
    if not ab or ab.user_id != user_id:
        return False

    if "name" in data and data["name"] is not None:
        contact.full_name = data["name"]
    if "first_name" in data:
        contact.given_name = data.get("first_name")
    if "last_name" in data:
        contact.surname = data.get("last_name")
    if "organization" in data:
        contact.organization = data.get("organization")
    if "emails" in data and data["emails"] is not None:
        contact.emails = json.dumps(data["emails"], ensure_ascii=False)
    if "phones" in data and data["phones"] is not None:
        contact.phones = json.dumps(data["phones"], ensure_ascii=False)
    if "addresses" in data and data["addresses"] is not None:
        contact.addresses = json.dumps(data["addresses"], ensure_ascii=False)
    if "notes" in data:
        contact.notes = data.get("notes")
    if "address_book_id" in data and data["address_book_id"] is not None:
        contact.address_book_id = data["address_book_id"]

    await db.commit()
    return True


async def delete_contact(db: AsyncSession, user_id: str, contact_id: str) -> bool:
    contact = await db.get(ContactDB, contact_id)
    if not contact:
        return False
    ab = await db.get(AddressBookDB, contact.address_book_id)
    if not ab or ab.user_id != user_id:
        return False
    await db.delete(contact)
    await db.commit()
    return True
