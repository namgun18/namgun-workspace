"""Contacts API endpoints — PostgreSQL backend."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.contacts import service
from app.contacts.schemas import (
    AddressBook,
    AddressBookCreate,
    AddressBookListResponse,
    Contact,
    ContactCreate,
    ContactUpdate,
    ContactListResponse,
)
from app.modules.registry import require_module

router = APIRouter(prefix="/api/contacts", tags=["contacts"])


# ─── Address Books ───


@router.get("/address-books", response_model=AddressBookListResponse)
@require_module("contacts")
async def list_address_books(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    books = await service.get_address_books(db, user.id)
    return {"address_books": [AddressBook(**b) for b in books]}


@router.post("/address-books", response_model=AddressBook)
@require_module("contacts")
async def create_address_book(
    body: AddressBookCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await service.create_address_book(db, user.id, body.name)
    return AddressBook(**result)


@router.delete("/address-books/{book_id}", response_model=dict)
@require_module("contacts")
async def delete_address_book(
    book_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ok = await service.delete_address_book(db, user.id, book_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Address book not found")
    return {"ok": True}


# ─── Contacts ───


@router.get("/", response_model=ContactListResponse)
@require_module("contacts")
async def list_contacts(
    q: str | None = Query(None),
    book_id: str | None = Query(None),
    page: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    contacts, total = await service.get_contacts(db, user.id, q, book_id, page, limit)
    return {"contacts": [Contact(**c) for c in contacts], "total": total}


@router.get("/{contact_id}", response_model=Contact)
@require_module("contacts")
async def get_contact(
    contact_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    contact = await service.get_contact(db, user.id, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return Contact(**contact)


@router.post("/", response_model=Contact)
@require_module("contacts")
async def create_contact(
    body: ContactCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = body.model_dump()
    if data.get("emails"):
        data["emails"] = [{"type": v["type"], "value": v["value"]} for v in data["emails"]]
    if data.get("phones"):
        data["phones"] = [{"type": v["type"], "value": v["value"]} for v in data["phones"]]
    if data.get("addresses"):
        data["addresses"] = [{"type": v["type"], "value": v["value"]} for v in data["addresses"]]
    result = await service.create_contact(db, user.id, data)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to create contact")
    return Contact(**result)


@router.patch("/{contact_id}", response_model=dict)
@require_module("contacts")
async def update_contact(
    contact_id: str,
    body: ContactUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = body.model_dump(exclude_none=True)
    for field in ["emails", "phones", "addresses"]:
        if data.get(field):
            data[field] = [{"type": v["type"], "value": v["value"]} for v in data[field]]
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    ok = await service.update_contact(db, user.id, contact_id, data)
    if not ok:
        raise HTTPException(status_code=404, detail="Contact not found")
    return {"ok": True}


@router.delete("/{contact_id}", response_model=dict)
@require_module("contacts")
async def delete_contact(
    contact_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ok = await service.delete_contact(db, user.id, contact_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Contact not found")
    return {"ok": True}
