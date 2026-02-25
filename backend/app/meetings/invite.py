"""Meeting invitation utilities — ICS generation, invite email, calendar event."""

import asyncio
import logging
import smtplib
import uuid
from datetime import datetime, timedelta, timezone
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders

from app.config import get_settings
from app.calendar import jmap_calendar
from app.mail.jmap import resolve_account_id

logger = logging.getLogger(__name__)
settings = get_settings()


# ─── ICS generation ───


def generate_ics(
    summary: str,
    description: str,
    location: str,
    start: datetime,
    end: datetime,
    organizer_name: str,
    organizer_email: str,
) -> str:
    """Generate an ICS (iCalendar) string for a meeting invitation."""
    uid = f"{uuid.uuid4()}@{settings.domain}"

    def _fmt(dt: datetime) -> str:
        utc = dt.astimezone(timezone.utc)
        return utc.strftime("%Y%m%dT%H%M%SZ")

    now = _fmt(datetime.now(timezone.utc))
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//{settings.domain}//Meeting//KO",
        "CALSCALE:GREGORIAN",
        "METHOD:REQUEST",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now}",
        f"DTSTART:{_fmt(start)}",
        f"DTEND:{_fmt(end)}",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:{description}",
        f"LOCATION:{location}",
        f"ORGANIZER;CN={organizer_name}:mailto:{organizer_email}",
        "STATUS:CONFIRMED",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(lines)


# ─── SMTP invite email ───


def _smtp_send(msg) -> None:
    """Send email via SMTP (blocking)."""
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)


async def send_invite_email(
    to_email: str,
    meeting_name: str,
    host_name: str,
    join_url: str,
    scheduled_at: datetime,
    duration_minutes: int,
    ics_content: str,
) -> None:
    """Send a meeting invitation email with ICS attachment."""
    end_time = scheduled_at + timedelta(minutes=duration_minutes)
    time_str = scheduled_at.strftime("%Y-%m-%d %H:%M") + " ~ " + end_time.strftime("%H:%M") + " (UTC)"

    html_body = f"""\
<div style="font-family: sans-serif; max-width: 560px;">
  <h2 style="color: #1a1a1a; margin-bottom: 4px;">{meeting_name}</h2>
  <p style="color: #666; margin-top: 0;">회의 초대</p>
  <table style="border-collapse: collapse; margin: 16px 0;">
    <tr><td style="padding: 4px 12px 4px 0; color: #888;">호스트</td><td>{host_name}</td></tr>
    <tr><td style="padding: 4px 12px 4px 0; color: #888;">시간</td><td>{time_str}</td></tr>
    <tr><td style="padding: 4px 12px 4px 0; color: #888;">시간(분)</td><td>{duration_minutes}분</td></tr>
  </table>
  <p>
    <a href="{join_url}"
       style="display: inline-block; padding: 10px 24px; background: #2563eb; color: #fff;
              text-decoration: none; border-radius: 6px; font-weight: 600;">
      회의 참여하기
    </a>
  </p>
  <p style="color: #999; font-size: 12px; margin-top: 24px;">
    이 메일은 {settings.domain} 포털에서 자동 발송되었습니다.
  </p>
</div>"""

    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"[회의 초대] {meeting_name}"
    msg["From"] = settings.smtp_from
    msg["To"] = to_email

    msg.attach(MIMEText(html_body, "html", "utf-8"))

    # ICS attachment
    ics_part = MIMEBase("text", "calendar", method="REQUEST")
    ics_part.set_payload(ics_content.encode("utf-8"))
    encoders.encode_base64(ics_part)
    ics_part.add_header("Content-Disposition", "attachment", filename="invite.ics")
    msg.attach(ics_part)

    await asyncio.to_thread(_smtp_send, msg)


# ─── Calendar event creation (internal users) ───


async def create_calendar_event(
    username: str,
    meeting_name: str,
    join_url: str,
    scheduled_at: datetime,
    duration_minutes: int,
) -> bool:
    """Create a calendar event for an internal user via JMAP."""
    account_id = await resolve_account_id(username)
    if not account_id:
        logger.warning("Cannot create calendar event: no JMAP account for %s", username)
        return False

    # Get first calendar (default)
    calendars = await jmap_calendar.get_calendars(account_id)
    if not calendars:
        logger.warning("No calendars found for %s", username)
        return False
    calendar_id = calendars[0]["id"]

    end_dt = scheduled_at + timedelta(minutes=duration_minutes)
    event_data = {
        "calendar_id": calendar_id,
        "title": f"[회의] {meeting_name}",
        "description": f"회의 참여: {join_url}",
        "location": join_url,
        "start": scheduled_at.isoformat(),
        "end": end_dt.isoformat(),
    }
    result = await jmap_calendar.create_event(account_id, event_data)
    return result is not None
