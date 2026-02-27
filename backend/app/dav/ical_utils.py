"""iCalendar serialization / deserialization."""

from datetime import date, datetime, timezone

from icalendar import Calendar, Event


def event_to_ical(ev) -> str:
    """Convert a CalendarEventDB row to a VCALENDAR string."""
    cal = Calendar()
    cal.add("prodid", "-//namgun-workspace//CalDAV//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")

    vevent = Event()
    vevent.add("uid", ev.id)
    vevent.add("summary", ev.title or "")

    if ev.description:
        vevent.add("description", ev.description)
    if ev.location:
        vevent.add("location", ev.location)

    if ev.all_day:
        start = ev.start.date() if isinstance(ev.start, datetime) else ev.start
        end = ev.end.date() if isinstance(ev.end, datetime) else ev.end
        vevent.add("dtstart", start)
        vevent.add("dtend", end)
    else:
        vevent.add("dtstart", ev.start)
        vevent.add("dtend", ev.end)

    if ev.status:
        vevent.add("status", ev.status.upper())
    if ev.created_at:
        vevent.add("created", ev.created_at)
    if ev.updated_at:
        vevent.add("last-modified", ev.updated_at)
        vevent.add("dtstamp", ev.updated_at)

    cal.add_component(vevent)
    return cal.to_ical().decode("utf-8")


def ical_to_event_data(ical_text: str) -> dict | None:
    """Parse iCalendar text → dict of event fields (or None on error)."""
    try:
        cal = Calendar.from_ical(ical_text)
    except Exception:
        return None

    for component in cal.walk():
        if component.name != "VEVENT":
            continue

        data: dict = {}
        uid = component.get("uid")
        if uid:
            data["uid"] = str(uid)

        summary = component.get("summary")
        data["title"] = str(summary) if summary else ""

        desc = component.get("description")
        if desc:
            data["description"] = str(desc)

        loc = component.get("location")
        if loc:
            data["location"] = str(loc)

        dtstart = component.get("dtstart")
        if dtstart:
            dt = dtstart.dt
            if isinstance(dt, date) and not isinstance(dt, datetime):
                data["all_day"] = True
                data["start"] = datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc)
            else:
                data["all_day"] = False
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                data["start"] = dt

        dtend = component.get("dtend")
        if dtend:
            dt = dtend.dt
            if isinstance(dt, date) and not isinstance(dt, datetime):
                data["end"] = datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc)
            else:
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                data["end"] = dt

        status = component.get("status")
        if status:
            data["status"] = str(status).lower()

        return data

    return None
