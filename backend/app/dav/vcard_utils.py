"""vCard serialization / deserialization."""

import json

import vobject
import vobject.vcard


def contact_to_vcard(c) -> str:
    """Convert a ContactDB row to a vCard 3.0 string."""
    v = vobject.vCard()

    v.add("fn").value = c.full_name or ""
    n = v.add("n")
    n.value = vobject.vcard.Name(
        family=c.surname or "",
        given=c.given_name or "",
    )
    v.add("uid").value = c.id

    if c.organization:
        v.add("org").value = [c.organization]

    for item_list, tag in (
        (c.emails, "email"),
        (c.phones, "tel"),
    ):
        if not item_list:
            continue
        try:
            items = json.loads(item_list) if isinstance(item_list, str) else item_list
        except (json.JSONDecodeError, TypeError):
            continue
        for entry in items:
            el = v.add(tag)
            el.value = entry.get("value", "")
            el.type_param = entry.get("type", "HOME").upper()

    if c.addresses:
        try:
            addrs = json.loads(c.addresses) if isinstance(c.addresses, str) else c.addresses
        except (json.JSONDecodeError, TypeError):
            addrs = []
        for addr in addrs:
            a = v.add("adr")
            a.value = vobject.vcard.Address(street=addr.get("value", ""))
            a.type_param = addr.get("type", "HOME").upper()

    if c.notes:
        v.add("note").value = c.notes

    if c.updated_at:
        v.add("rev").value = c.updated_at.strftime("%Y%m%dT%H%M%SZ")

    return v.serialize()


def _param_lower(obj, fallback="home") -> str:
    tp = getattr(obj, "type_param", None)
    if not tp:
        return fallback
    if isinstance(tp, str):
        return tp.lower()
    if isinstance(tp, list) and tp:
        return tp[0].lower()
    return fallback


def vcard_to_contact_data(vcard_text: str) -> dict | None:
    """Parse vCard text → dict of contact fields (or None on error)."""
    try:
        v = next(vobject.readComponents(vcard_text))
    except Exception:
        return None

    data: dict = {}

    uid = getattr(v, "uid", None)
    if uid:
        data["uid"] = uid.value

    fn = getattr(v, "fn", None)
    if fn:
        data["name"] = fn.value

    n = getattr(v, "n", None)
    if n:
        data["first_name"] = n.value.given or None
        data["last_name"] = n.value.family or None

    org = getattr(v, "org", None)
    if org:
        val = org.value
        if isinstance(val, list):
            data["organization"] = val[0] if val else None
        else:
            data["organization"] = str(val) if val else None

    emails = [
        {"type": _param_lower(em), "value": em.value}
        for em in v.contents.get("email", [])
    ]
    if emails:
        data["emails"] = emails

    phones = [
        {"type": _param_lower(ph), "value": ph.value}
        for ph in v.contents.get("tel", [])
    ]
    if phones:
        data["phones"] = phones

    addresses = []
    for adr in v.contents.get("adr", []):
        val = adr.value.street if hasattr(adr.value, "street") else str(adr.value)
        addresses.append({"type": _param_lower(adr), "value": val or ""})
    if addresses:
        data["addresses"] = addresses

    note = getattr(v, "note", None)
    if note:
        data["notes"] = note.value

    return data
