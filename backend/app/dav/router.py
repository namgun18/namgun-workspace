"""CalDAV/CardDAV ASGI application.

Mounted at /dav via FastAPI app.mount().  Handles PROPFIND, REPORT,
GET, PUT, DELETE for calendar events (.ics) and contacts (.vcf).
"""

import xml.etree.ElementTree as ET

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import get_route_path

from app.db.session import async_session
from app.dav.auth import authenticate_dav
from app.dav import service as svc
from app.dav.ical_utils import event_to_ical, ical_to_event_data
from app.dav.vcard_utils import contact_to_vcard, vcard_to_contact_data
from app.dav.xml_utils import (
    D, C, CR, CSt,
    make_multistatus, add_propstat, serialize,
    parse_propfind, parse_report,
    CALDAV, CARDDAV,
)

_DAV_HEADERS = {
    "DAV": "1, 3, calendar-access, addressbook",
    "Allow": "OPTIONS, PROPFIND, REPORT, GET, PUT, DELETE",
}
_XML_CT = "application/xml; charset=utf-8"


# ── Path parser ──

def _parse_path(path: str) -> dict:
    """Parse sub-app path into structured route info."""
    parts = [p for p in path.strip("/").split("/") if p]
    n = len(parts)

    if n == 0:
        return {"type": "root"}
    if parts[0] == "principals" and n == 2:
        return {"type": "principal", "username": parts[1]}

    if parts[0] == "calendars":
        if n == 2:
            return {"type": "cal-home", "username": parts[1]}
        if n == 3:
            return {"type": "calendar", "username": parts[1], "col": parts[2]}
        if n == 4 and parts[3].endswith(".ics"):
            return {
                "type": "event",
                "username": parts[1],
                "col": parts[2],
                "rid": parts[3][:-4],
            }

    if parts[0] == "addressbooks":
        if n == 2:
            return {"type": "ab-home", "username": parts[1]}
        if n == 3:
            return {"type": "addressbook", "username": parts[1], "col": parts[2]}
        if n == 4 and parts[3].endswith(".vcf"):
            return {
                "type": "contact",
                "username": parts[1],
                "col": parts[2],
                "rid": parts[3][:-4],
            }

    return {"type": "unknown"}


def _href(root_path: str, *segments: str) -> str:
    """Build an absolute href from root_path + segments."""
    return root_path + "/" + "/".join(segments) + "/"


def _href_res(root_path: str, *segments: str) -> str:
    """Build href for a resource (no trailing slash)."""
    return root_path + "/" + "/".join(segments)


# ── PROPFIND builders ──

def _prop_root(root_path: str, username: str) -> ET.Element:
    prop = ET.Element(D("prop"))
    rt = ET.SubElement(prop, D("resourcetype"))
    ET.SubElement(rt, D("collection"))
    cup = ET.SubElement(prop, D("current-user-principal"))
    h = ET.SubElement(cup, D("href"))
    h.text = _href(root_path, "principals", username)
    dn = ET.SubElement(prop, D("displayname"))
    dn.text = "WebDAV Root"
    return prop


def _prop_principal(root_path: str, username: str) -> ET.Element:
    prop = ET.Element(D("prop"))
    rt = ET.SubElement(prop, D("resourcetype"))
    ET.SubElement(rt, D("collection"))
    ET.SubElement(rt, D("principal"))
    dn = ET.SubElement(prop, D("displayname"))
    dn.text = username

    chs = ET.SubElement(prop, C("calendar-home-set"))
    h1 = ET.SubElement(chs, D("href"))
    h1.text = _href(root_path, "calendars", username)

    ahs = ET.SubElement(prop, CR("addressbook-home-set"))
    h2 = ET.SubElement(ahs, D("href"))
    h2.text = _href(root_path, "addressbooks", username)
    return prop


def _prop_calendar_home(root_path: str, username: str) -> ET.Element:
    prop = ET.Element(D("prop"))
    rt = ET.SubElement(prop, D("resourcetype"))
    ET.SubElement(rt, D("collection"))
    dn = ET.SubElement(prop, D("displayname"))
    dn.text = f"{username} calendars"
    return prop


async def _prop_calendar(db, root_path: str, cal) -> ET.Element:
    prop = ET.Element(D("prop"))
    rt = ET.SubElement(prop, D("resourcetype"))
    ET.SubElement(rt, D("collection"))
    ET.SubElement(rt, C("calendar"))
    dn = ET.SubElement(prop, D("displayname"))
    dn.text = cal.name
    if cal.color:
        cc = ET.SubElement(prop, "{http://apple.com/ns/ical/}calendar-color")
        cc.text = cal.color
    ctag = ET.SubElement(prop, CSt("getctag"))
    ctag.text = await svc.calendar_ctag(db, cal.id)
    sccs = ET.SubElement(prop, C("supported-calendar-component-set"))
    comp = ET.SubElement(sccs, C("comp"))
    comp.set("name", "VEVENT")
    srs = ET.SubElement(prop, D("supported-report-set"))
    for rname in ("calendar-multiget", "calendar-query"):
        sr = ET.SubElement(srs, D("supported-report"))
        r = ET.SubElement(sr, D("report"))
        ET.SubElement(r, C(rname))
    return prop


def _prop_event(ev) -> ET.Element:
    prop = ET.Element(D("prop"))
    etag = ET.SubElement(prop, D("getetag"))
    etag.text = f'"{svc.compute_etag(ev.id, ev.updated_at)}"'
    ct = ET.SubElement(prop, D("getcontenttype"))
    ct.text = "text/calendar; charset=utf-8; component=VEVENT"
    return prop


def _prop_event_with_data(ev) -> ET.Element:
    prop = _prop_event(ev)
    cd = ET.SubElement(prop, C("calendar-data"))
    cd.text = event_to_ical(ev)
    return prop


def _prop_ab_home(root_path: str, username: str) -> ET.Element:
    prop = ET.Element(D("prop"))
    rt = ET.SubElement(prop, D("resourcetype"))
    ET.SubElement(rt, D("collection"))
    dn = ET.SubElement(prop, D("displayname"))
    dn.text = f"{username} address books"
    return prop


async def _prop_addressbook(db, root_path: str, ab) -> ET.Element:
    prop = ET.Element(D("prop"))
    rt = ET.SubElement(prop, D("resourcetype"))
    ET.SubElement(rt, D("collection"))
    ET.SubElement(rt, CR("addressbook"))
    dn = ET.SubElement(prop, D("displayname"))
    dn.text = ab.name
    ctag = ET.SubElement(prop, CSt("getctag"))
    ctag.text = await svc.addressbook_ctag(db, ab.id)
    srs = ET.SubElement(prop, D("supported-report-set"))
    for rname in ("addressbook-multiget", "addressbook-query"):
        sr = ET.SubElement(srs, D("supported-report"))
        r = ET.SubElement(sr, D("report"))
        ET.SubElement(r, CR(rname))
    return prop


def _prop_contact(c) -> ET.Element:
    prop = ET.Element(D("prop"))
    etag = ET.SubElement(prop, D("getetag"))
    etag.text = f'"{svc.compute_etag(c.id, c.updated_at)}"'
    ct = ET.SubElement(prop, D("getcontenttype"))
    ct.text = "text/vcard; charset=utf-8"
    return prop


def _prop_contact_with_data(c) -> ET.Element:
    prop = _prop_contact(c)
    ad = ET.SubElement(prop, CR("address-data"))
    ad.text = contact_to_vcard(c)
    return prop


# ── ASGI application ──

class DavApp:
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            resp = Response(status_code=400)
            await resp(scope, receive, send)
            return
        request = Request(scope, receive)
        response = await self._dispatch(request)
        await response(scope, receive, send)

    async def _dispatch(self, request: Request) -> Response:
        async with async_session() as db:
            user = await authenticate_dav(
                request.headers.get("authorization"), db,
            )
            if not user:
                return Response(
                    status_code=401,
                    headers={"WWW-Authenticate": 'Basic realm="WebDAV"'},
                )

            method = request.method.upper()
            root_path = request.scope.get("root_path", "")
            path = get_route_path(request.scope) or "/"
            route = _parse_path(path)

            # Verify URL username matches authenticated user
            url_user = route.get("username")
            if url_user and url_user != user.username:
                return Response(status_code=403)

            if method == "OPTIONS":
                return Response(status_code=200, headers=_DAV_HEADERS)
            if method == "PROPFIND":
                return await self._propfind(request, route, user, db, root_path)
            if method == "REPORT":
                return await self._report(request, route, user, db, root_path)
            if method == "GET":
                return await self._get(route, user, db)
            if method == "PUT":
                return await self._put(request, route, user, db, root_path)
            if method == "DELETE":
                return await self._delete(route, user, db)
            return Response(status_code=405)

    # ── PROPFIND ──

    async def _propfind(self, request, route, user, db, rp) -> Response:
        body = await request.body()
        depth = request.headers.get("depth", "1")
        ms = make_multistatus()
        rt = route["type"]
        un = user.username

        if rt == "root":
            add_propstat(ms, rp + "/", _prop_root(rp, un))
            if depth != "0":
                add_propstat(
                    ms, _href(rp, "principals", un),
                    _prop_principal(rp, un),
                )

        elif rt == "principal":
            add_propstat(
                ms, _href(rp, "principals", un),
                _prop_principal(rp, un),
            )

        elif rt == "cal-home":
            add_propstat(
                ms, _href(rp, "calendars", un),
                _prop_calendar_home(rp, un),
            )
            if depth != "0":
                for cal in await svc.get_user_calendars(db, user.id):
                    add_propstat(
                        ms,
                        _href(rp, "calendars", un, cal.id),
                        await _prop_calendar(db, rp, cal),
                    )

        elif rt == "calendar":
            cal = await svc.get_calendar(db, route["col"])
            if not cal or cal.user_id != user.id:
                return Response(status_code=404)
            add_propstat(
                ms,
                _href(rp, "calendars", un, cal.id),
                await _prop_calendar(db, rp, cal),
            )
            if depth != "0":
                for ev in await svc.get_calendar_events(db, cal.id):
                    add_propstat(
                        ms,
                        _href_res(rp, "calendars", un, cal.id, f"{ev.id}.ics"),
                        _prop_event(ev),
                    )

        elif rt == "event":
            ev = await svc.get_event(db, route["rid"])
            if not ev:
                return Response(status_code=404)
            cal = await svc.get_calendar(db, ev.calendar_id)
            if not cal or cal.user_id != user.id:
                return Response(status_code=404)
            add_propstat(
                ms,
                _href_res(rp, "calendars", un, cal.id, f"{ev.id}.ics"),
                _prop_event(ev),
            )

        elif rt == "ab-home":
            add_propstat(
                ms, _href(rp, "addressbooks", un),
                _prop_ab_home(rp, un),
            )
            if depth != "0":
                for ab in await svc.get_user_address_books(db, user.id):
                    add_propstat(
                        ms,
                        _href(rp, "addressbooks", un, ab.id),
                        await _prop_addressbook(db, rp, ab),
                    )

        elif rt == "addressbook":
            ab = await svc.get_address_book(db, route["col"])
            if not ab or ab.user_id != user.id:
                return Response(status_code=404)
            add_propstat(
                ms,
                _href(rp, "addressbooks", un, ab.id),
                await _prop_addressbook(db, rp, ab),
            )
            if depth != "0":
                for c in await svc.get_book_contacts(db, ab.id):
                    add_propstat(
                        ms,
                        _href_res(rp, "addressbooks", un, ab.id, f"{c.id}.vcf"),
                        _prop_contact(c),
                    )

        elif rt == "contact":
            c = await svc.get_contact(db, route["rid"])
            if not c:
                return Response(status_code=404)
            ab = await svc.get_address_book(db, c.address_book_id)
            if not ab or ab.user_id != user.id:
                return Response(status_code=404)
            add_propstat(
                ms,
                _href_res(rp, "addressbooks", un, ab.id, f"{c.id}.vcf"),
                _prop_contact(c),
            )

        else:
            return Response(status_code=404)

        return Response(
            status_code=207,
            content=serialize(ms),
            media_type=_XML_CT,
            headers=_DAV_HEADERS,
        )

    # ── REPORT ──

    async def _report(self, request, route, user, db, rp) -> Response:
        body = await request.body()
        try:
            report_tag, props, hrefs = parse_report(body)
        except Exception:
            return Response(status_code=400)

        ms = make_multistatus()
        rt = route["type"]
        un = user.username

        # Calendar multiget / query
        if rt == "calendar" and report_tag == C("calendar-multiget"):
            ids = []
            for h in hrefs:
                r = _parse_path(h.split("/dav")[-1] if "/dav" in h else h)
                if r.get("rid"):
                    ids.append(r["rid"])
            events = await svc.get_events_by_ids(db, ids)
            for ev in events:
                cal = await svc.get_calendar(db, ev.calendar_id)
                if cal and cal.user_id == user.id:
                    add_propstat(
                        ms,
                        _href_res(rp, "calendars", un, cal.id, f"{ev.id}.ics"),
                        _prop_event_with_data(ev),
                    )

        elif rt == "calendar" and report_tag == C("calendar-query"):
            cal = await svc.get_calendar(db, route["col"])
            if cal and cal.user_id == user.id:
                for ev in await svc.get_calendar_events(db, cal.id):
                    add_propstat(
                        ms,
                        _href_res(rp, "calendars", un, cal.id, f"{ev.id}.ics"),
                        _prop_event_with_data(ev),
                    )

        # Addressbook multiget / query
        elif rt == "addressbook" and report_tag == CR("addressbook-multiget"):
            ids = []
            for h in hrefs:
                r = _parse_path(h.split("/dav")[-1] if "/dav" in h else h)
                if r.get("rid"):
                    ids.append(r["rid"])
            contacts = await svc.get_contacts_by_ids(db, ids)
            for c in contacts:
                ab = await svc.get_address_book(db, c.address_book_id)
                if ab and ab.user_id == user.id:
                    add_propstat(
                        ms,
                        _href_res(rp, "addressbooks", un, ab.id, f"{c.id}.vcf"),
                        _prop_contact_with_data(c),
                    )

        elif rt == "addressbook" and report_tag == CR("addressbook-query"):
            ab = await svc.get_address_book(db, route["col"])
            if ab and ab.user_id == user.id:
                for c in await svc.get_book_contacts(db, ab.id):
                    add_propstat(
                        ms,
                        _href_res(rp, "addressbooks", un, ab.id, f"{c.id}.vcf"),
                        _prop_contact_with_data(c),
                    )
        else:
            return Response(status_code=403)

        return Response(
            status_code=207,
            content=serialize(ms),
            media_type=_XML_CT,
            headers=_DAV_HEADERS,
        )

    # ── GET ──

    async def _get(self, route, user, db) -> Response:
        rt = route["type"]

        if rt == "event":
            ev = await svc.get_event(db, route["rid"])
            if not ev:
                return Response(status_code=404)
            cal = await svc.get_calendar(db, ev.calendar_id)
            if not cal or cal.user_id != user.id:
                return Response(status_code=404)
            etag = svc.compute_etag(ev.id, ev.updated_at)
            return Response(
                content=event_to_ical(ev),
                media_type="text/calendar; charset=utf-8",
                headers={"ETag": f'"{etag}"'},
            )

        if rt == "contact":
            c = await svc.get_contact(db, route["rid"])
            if not c:
                return Response(status_code=404)
            ab = await svc.get_address_book(db, c.address_book_id)
            if not ab or ab.user_id != user.id:
                return Response(status_code=404)
            etag = svc.compute_etag(c.id, c.updated_at)
            return Response(
                content=contact_to_vcard(c),
                media_type="text/vcard; charset=utf-8",
                headers={"ETag": f'"{etag}"'},
            )

        return Response(status_code=404)

    # ── PUT ──

    async def _put(self, request, route, user, db, rp) -> Response:
        body = (await request.body()).decode("utf-8")
        rt = route["type"]

        if rt == "event":
            cal = await svc.get_calendar(db, route["col"])
            if not cal or cal.user_id != user.id:
                return Response(status_code=403)
            data = ical_to_event_data(body)
            if not data:
                return Response(status_code=400)
            event_id = route["rid"]
            ev = await svc.upsert_event(db, event_id, cal.id, data)
            etag = svc.compute_etag(ev.id, ev.updated_at)
            href = _href_res(
                rp, "calendars", user.username, cal.id, f"{ev.id}.ics",
            )
            return Response(
                status_code=201,
                headers={"ETag": f'"{etag}"', "Location": href},
            )

        if rt == "contact":
            ab = await svc.get_address_book(db, route["col"])
            if not ab or ab.user_id != user.id:
                return Response(status_code=403)
            data = vcard_to_contact_data(body)
            if not data:
                return Response(status_code=400)
            contact_id = route["rid"]
            c = await svc.upsert_contact(db, contact_id, ab.id, data)
            etag = svc.compute_etag(c.id, c.updated_at)
            href = _href_res(
                rp, "addressbooks", user.username, ab.id, f"{c.id}.vcf",
            )
            return Response(
                status_code=201,
                headers={"ETag": f'"{etag}"', "Location": href},
            )

        return Response(status_code=403)

    # ── DELETE ──

    async def _delete(self, route, user, db) -> Response:
        rt = route["type"]

        if rt == "event":
            ev = await svc.get_event(db, route["rid"])
            if not ev:
                return Response(status_code=404)
            cal = await svc.get_calendar(db, ev.calendar_id)
            if not cal or cal.user_id != user.id:
                return Response(status_code=403)
            await svc.delete_event(db, route["rid"])
            return Response(status_code=204)

        if rt == "contact":
            c = await svc.get_contact(db, route["rid"])
            if not c:
                return Response(status_code=404)
            ab = await svc.get_address_book(db, c.address_book_id)
            if not ab or ab.user_id != user.id:
                return Response(status_code=403)
            await svc.delete_contact(db, route["rid"])
            return Response(status_code=204)

        return Response(status_code=403)


dav_app = DavApp()
