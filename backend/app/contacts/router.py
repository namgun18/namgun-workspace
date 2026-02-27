"""Contacts API endpoints — PostgreSQL backend."""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db.models import AddressBookDB, ContactDB, User
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
from app.dav.vcard_utils import contact_to_vcard, vcard_to_contact_data
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


# ─── vCard Import / Export ───


@router.post("/import-vcf")
@require_module("contacts")
async def import_vcf(
    file: UploadFile = File(...),
    book_id: str = Query(..., description="Target address book ID"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Import contacts from a .vcf file into the specified address book."""
    import vobject

    # Verify address book ownership
    ab = await db.get(AddressBookDB, book_id)
    if not ab or ab.user_id != user.id:
        raise HTTPException(status_code=404, detail="Address book not found")

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = content.decode("latin-1")
        except Exception:
            raise HTTPException(status_code=400, detail="파일 인코딩을 읽을 수 없습니다")

    imported = 0
    errors = 0
    for component in vobject.readComponents(text):
        if component.name != "VCARD":
            continue
        data = vcard_to_contact_data(component.serialize())
        if not data:
            errors += 1
            continue
        data["address_book_id"] = book_id
        if not data.get("name"):
            data["name"] = data.get("first_name", "") or "Unknown"
        result = await service.create_contact(db, user.id, data)
        if result:
            imported += 1
        else:
            errors += 1

    return {"ok": True, "imported": imported, "errors": errors}


@router.get("/export-vcf")
@require_module("contacts")
async def export_vcf(
    book_id: str = Query(..., description="Address book ID to export"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export all contacts in an address book as a single .vcf file."""
    # Verify address book ownership
    ab = await db.get(AddressBookDB, book_id)
    if not ab or ab.user_id != user.id:
        raise HTTPException(status_code=404, detail="Address book not found")

    # Fetch all contacts in the book
    result = await db.execute(
        select(ContactDB)
        .where(ContactDB.address_book_id == book_id)
        .order_by(ContactDB.full_name)
    )
    contacts = result.scalars().all()

    # Build combined vCard output
    vcf_parts = []
    for c in contacts:
        vcf_parts.append(contact_to_vcard(c))

    vcf_content = "\r\n".join(vcf_parts)
    safe_name = ab.name.replace('"', '').replace('\n', '').replace('\r', '')

    return Response(
        content=vcf_content.encode("utf-8"),
        media_type="text/vcard; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}.vcf"',
        },
    )
