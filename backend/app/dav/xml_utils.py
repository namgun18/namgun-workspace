"""WebDAV XML parsing and generation helpers."""

import xml.etree.ElementTree as ET

DAV = "DAV:"
CALDAV = "urn:ietf:params:xml:ns:caldav"
CARDDAV = "urn:ietf:params:xml:ns:carddav"
CS = "http://calendarserver.org/ns/"

ET.register_namespace("D", DAV)
ET.register_namespace("C", CALDAV)
ET.register_namespace("CR", CARDDAV)
ET.register_namespace("CS", CS)


# ── Shortcuts ──

def D(tag: str) -> str:
    return f"{{{DAV}}}{tag}"


def C(tag: str) -> str:
    return f"{{{CALDAV}}}{tag}"


def CR(tag: str) -> str:
    return f"{{{CARDDAV}}}{tag}"


def CSt(tag: str) -> str:
    return f"{{{CS}}}{tag}"


# ── Builder helpers ──

def make_multistatus() -> ET.Element:
    return ET.Element(D("multistatus"))


def add_propstat(
    ms: ET.Element, href: str, prop: ET.Element,
    status: str = "HTTP/1.1 200 OK",
) -> ET.Element:
    resp = ET.SubElement(ms, D("response"))
    h = ET.SubElement(resp, D("href"))
    h.text = href
    ps = ET.SubElement(resp, D("propstat"))
    ps.append(prop)
    st = ET.SubElement(ps, D("status"))
    st.text = status
    return resp


def serialize(root: ET.Element) -> bytes:
    return (
        b'<?xml version="1.0" encoding="UTF-8"?>\n'
        + ET.tostring(root, encoding="unicode").encode("utf-8")
    )


# ── Parsers ──

def parse_propfind(body: bytes) -> set[str] | None:
    """Return requested property tags, or None for allprop / empty body."""
    if not body or not body.strip():
        return None
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return None
    if root.find(D("allprop")) is not None:
        return None
    prop = root.find(D("prop"))
    if prop is None:
        return None
    return {child.tag for child in prop}


def parse_report(body: bytes) -> tuple[str, set[str], list[str]]:
    """Parse REPORT body → (report_tag, requested_props, href_list)."""
    root = ET.fromstring(body)
    report_tag = root.tag
    prop = root.find(D("prop"))
    props = {child.tag for child in prop} if prop is not None else set()
    hrefs = [h.text for h in root.findall(D("href")) if h.text]
    return report_tag, props, hrefs
