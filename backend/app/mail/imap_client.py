"""IMAP client for reading mail from external IMAP servers."""

import asyncio
import email
import email.header
import email.utils
import logging
import re
from datetime import datetime, timezone
from email.message import Message as EmailMessage
from typing import Any

import aioimaplib

from app.db.models import MailAccount
from app.mail.crypto import decrypt_password

logger = logging.getLogger(__name__)

FETCH_HEADERS = "(FLAGS BODY.PEEK[HEADER.FIELDS (FROM TO CC BCC SUBJECT DATE MESSAGE-ID REFERENCES IN-REPLY-TO)] BODYSTRUCTURE)"
FETCH_FULL = "(FLAGS BODY[])"


def _decode_header(raw: str | None) -> str:
    """Decode RFC 2047 encoded header."""
    if not raw:
        return ""
    decoded_parts = email.header.decode_header(raw)
    result = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(part)
    return " ".join(result)


def _parse_address(raw: str | None) -> list[dict]:
    """Parse email address header into list of {name, email}."""
    if not raw:
        return []
    decoded = _decode_header(raw)
    addresses = email.utils.getaddresses([decoded])
    return [{"name": name or None, "email": addr} for name, addr in addresses if addr]


def _parse_date(raw: str | None) -> str | None:
    """Parse email date header to ISO 8601."""
    if not raw:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(raw)
        return parsed.isoformat()
    except Exception:
        return raw


def _has_attachments(msg: EmailMessage) -> bool:
    """Check if message has attachments."""
    if msg.is_multipart():
        for part in msg.walk():
            disposition = part.get_content_disposition()
            if disposition == "attachment":
                return True
            ct = part.get_content_type()
            if disposition == "inline" and ct not in ("text/plain", "text/html"):
                return True
    return False


def _extract_body(msg: EmailMessage) -> tuple[str | None, str | None]:
    """Extract text and HTML body from email message."""
    text_body = None
    html_body = None

    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            disposition = part.get_content_disposition()
            if disposition == "attachment":
                continue
            try:
                payload = part.get_payload(decode=True)
                if payload is None:
                    continue
                charset = part.get_content_charset() or "utf-8"
                decoded = payload.decode(charset, errors="replace")
                if ct == "text/plain" and text_body is None:
                    text_body = decoded
                elif ct == "text/html" and html_body is None:
                    html_body = decoded
            except Exception:
                continue
    else:
        ct = msg.get_content_type()
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                decoded = payload.decode(charset, errors="replace")
                if ct == "text/html":
                    html_body = decoded
                else:
                    text_body = decoded
        except Exception:
            pass

    return text_body, html_body


def _extract_attachments(msg: EmailMessage) -> list[dict]:
    """Extract attachment metadata from email message."""
    attachments = []
    if not msg.is_multipart():
        return attachments

    for i, part in enumerate(msg.walk()):
        disposition = part.get_content_disposition()
        ct = part.get_content_type()
        if disposition == "attachment" or (
            disposition == "inline" and ct not in ("text/plain", "text/html")
        ):
            filename = part.get_filename()
            if filename:
                filename = _decode_header(filename)
            size = len(part.get_payload(decode=True) or b"")
            attachments.append({
                "part_index": i,
                "name": filename or f"attachment_{i}",
                "type": ct,
                "size": size,
            })
    return attachments


async def _connect(account: MailAccount) -> aioimaplib.IMAP4_SSL | aioimaplib.IMAP4:
    """Connect and authenticate to IMAP server."""
    import ssl as _ssl
    password = decrypt_password(account.password_encrypted)

    # Create SSL context that doesn't verify certificates for internal servers
    ssl_context = _ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = _ssl.CERT_NONE

    if account.imap_security == "ssl":
        imap = aioimaplib.IMAP4_SSL(
            host=account.imap_host,
            port=account.imap_port,
            timeout=30,
            ssl_context=ssl_context,
        )
    else:
        imap = aioimaplib.IMAP4(
            host=account.imap_host,
            port=account.imap_port,
            timeout=30,
        )

    await imap.wait_hello_from_server()

    if account.imap_security == "starttls":
        await imap.starttls(ssl_context=ssl_context)

    response = await imap.login(account.username, password)
    if response.result != "OK":
        raise ConnectionError(f"IMAP login failed: {response.result}")

    return imap


async def list_mailboxes(account: MailAccount) -> list[dict]:
    """List IMAP mailboxes with unread counts."""
    imap = await _connect(account)
    try:
        response = await imap.list('""', "*")
        if response.result != "OK":
            return []

        mailboxes = []
        role_map = {
            "inbox": "inbox",
            "sent": "sent", "sent mail": "sent", "sent items": "sent",
            "drafts": "drafts", "draft": "drafts",
            "junk": "junk", "spam": "junk",
            "trash": "trash", "deleted": "trash", "deleted items": "trash",
            "archive": "archive",
        }
        role_order = {"inbox": 0, "drafts": 1, "sent": 2, "junk": 3, "trash": 4, "archive": 5}

        for line in response.lines:
            if not line or line == b")" or line == b"":
                continue
            line_str = line.decode("utf-8", errors="replace") if isinstance(line, bytes) else str(line)

            # Parse LIST response: (* (\flags) "delimiter" "name")
            match = re.match(r'\* LIST \(([^)]*)\) "([^"]*)" (.+)', line_str)
            if not match:
                continue

            flags = match.group(1)
            name = match.group(3).strip('"')

            # Detect role from IMAP flags or name
            role = None
            name_lower = name.lower()
            if "\\Inbox" in flags or name_lower == "inbox":
                role = "inbox"
            elif "\\Sent" in flags:
                role = "sent"
            elif "\\Drafts" in flags:
                role = "drafts"
            elif "\\Junk" in flags:
                role = "junk"
            elif "\\Trash" in flags:
                role = "trash"
            elif "\\Archive" in flags:
                role = "archive"
            else:
                role = role_map.get(name_lower)

            # Get message counts
            total = 0
            unread = 0
            try:
                status_resp = await imap.status(f'"{name}"', "(MESSAGES UNSEEN)")
                if status_resp.result == "OK":
                    status_line = status_resp.lines[0]
                    if isinstance(status_line, bytes):
                        status_line = status_line.decode("utf-8", errors="replace")
                    m_total = re.search(r"MESSAGES (\d+)", status_line)
                    m_unseen = re.search(r"UNSEEN (\d+)", status_line)
                    if m_total:
                        total = int(m_total.group(1))
                    if m_unseen:
                        unread = int(m_unseen.group(1))
            except Exception:
                pass

            sort_order = role_order.get(role, 99) if role else 99

            mailboxes.append({
                "id": name,
                "name": name.split("/")[-1] if "/" in name else name,
                "role": role,
                "unread_count": unread,
                "total_count": total,
                "sort_order": sort_order,
            })

        mailboxes.sort(key=lambda m: (m["sort_order"], m["name"]))
        return mailboxes
    finally:
        try:
            await imap.logout()
        except Exception:
            pass


async def fetch_messages(
    account: MailAccount,
    mailbox: str,
    page: int = 0,
    limit: int = 50,
    query: str | None = None,
) -> tuple[list[dict], int]:
    """Fetch message summaries from a mailbox. Returns (messages, total)."""
    imap = await _connect(account)
    try:
        response = await imap.select(mailbox)
        if response.result != "OK":
            return [], 0

        # Search
        if query:
            search_resp = await imap.search(f'(OR SUBJECT "{query}" FROM "{query}")')
        else:
            search_resp = await imap.search("ALL")

        if search_resp.result != "OK":
            return [], 0

        # Parse UIDs
        uid_line = search_resp.lines[0]
        if isinstance(uid_line, bytes):
            uid_line = uid_line.decode("utf-8", errors="replace")
        uids = uid_line.strip().split() if uid_line.strip() else []

        total = len(uids)
        if total == 0:
            return [], 0

        # Reverse for newest first, paginate
        uids.reverse()
        start = page * limit
        end = start + limit
        page_uids = uids[start:end]

        if not page_uids:
            return [], total

        uid_range = ",".join(page_uids)
        fetch_resp = await imap.fetch(uid_range, "(FLAGS BODY.PEEK[HEADER])")
        if fetch_resp.result != "OK":
            return [], total

        messages = []
        current_uid = None
        current_flags = ""
        current_header_data = b""

        for line in fetch_resp.lines:
            if isinstance(line, bytes):
                line_str = line.decode("utf-8", errors="replace")
            else:
                line_str = str(line)

            # Match fetch response line: * N FETCH (UID xxx FLAGS (...) BODY[HEADER] {size})
            fetch_match = re.match(r"\* \d+ FETCH \(.*?UID (\d+).*?FLAGS \(([^)]*)\)", line_str)
            if fetch_match:
                # Save previous message
                if current_uid and current_header_data:
                    msg = email.message_from_bytes(current_header_data)
                    is_unread = "\\Seen" not in current_flags
                    is_flagged = "\\Flagged" in current_flags
                    messages.append({
                        "id": current_uid,
                        "thread_id": None,
                        "mailbox_ids": [mailbox],
                        "from_": _parse_address(msg.get("From")),
                        "to": _parse_address(msg.get("To")),
                        "subject": _decode_header(msg.get("Subject")),
                        "preview": None,
                        "received_at": _parse_date(msg.get("Date")),
                        "is_unread": is_unread,
                        "is_flagged": is_flagged,
                        "has_attachment": False,
                    })

                current_uid = fetch_match.group(1)
                current_flags = fetch_match.group(2)
                current_header_data = b""
            elif isinstance(line, bytes) and current_uid:
                current_header_data += line + b"\r\n"

        # Process last message
        if current_uid and current_header_data:
            msg = email.message_from_bytes(current_header_data)
            is_unread = "\\Seen" not in current_flags
            is_flagged = "\\Flagged" in current_flags
            messages.append({
                "id": current_uid,
                "thread_id": None,
                "mailbox_ids": [mailbox],
                "from_": _parse_address(msg.get("From")),
                "to": _parse_address(msg.get("To")),
                "subject": _decode_header(msg.get("Subject")),
                "preview": None,
                "received_at": _parse_date(msg.get("Date")),
                "is_unread": is_unread,
                "is_flagged": is_flagged,
                "has_attachment": False,
            })

        return messages, total
    finally:
        try:
            await imap.logout()
        except Exception:
            pass


async def fetch_message(account: MailAccount, mailbox: str, uid: str) -> dict | None:
    """Fetch full message detail by UID."""
    imap = await _connect(account)
    try:
        await imap.select(mailbox)
        fetch_resp = await imap.fetch(uid, "(FLAGS BODY[])")
        if fetch_resp.result != "OK":
            return None

        # Parse the raw message data
        raw_data = b""
        flags = ""
        for line in fetch_resp.lines:
            if isinstance(line, bytes):
                line_str = line.decode("utf-8", errors="replace")
                flag_match = re.search(r"FLAGS \(([^)]*)\)", line_str)
                if flag_match:
                    flags = flag_match.group(1)
                raw_data += line + b"\r\n"

        msg = email.message_from_bytes(raw_data)
        text_body, html_body = _extract_body(msg)
        attachments = _extract_attachments(msg)

        is_unread = "\\Seen" not in flags
        is_flagged = "\\Flagged" in flags

        # Mark as read
        if is_unread:
            await imap.store(uid, "+FLAGS", "(\\Seen)")

        return {
            "id": uid,
            "thread_id": None,
            "mailbox_ids": [mailbox],
            "from_": _parse_address(msg.get("From")),
            "to": _parse_address(msg.get("To")),
            "cc": _parse_address(msg.get("Cc")),
            "bcc": _parse_address(msg.get("Bcc")),
            "reply_to": _parse_address(msg.get("Reply-To")),
            "subject": _decode_header(msg.get("Subject")),
            "text_body": text_body,
            "html_body": html_body,
            "preview": (text_body or "")[:200] if text_body else None,
            "received_at": _parse_date(msg.get("Date")),
            "is_unread": False,  # Just marked as read
            "is_flagged": is_flagged,
            "attachments": [
                {
                    "blob_id": f"{uid}:{att['part_index']}",
                    "name": att["name"],
                    "type": att["type"],
                    "size": att["size"],
                }
                for att in attachments
            ],
            "in_reply_to": msg.get("In-Reply-To"),
            "references": msg.get("References"),
        }
    finally:
        try:
            await imap.logout()
        except Exception:
            pass


async def update_flags(
    account: MailAccount, mailbox: str, uid: str,
    add_flags: list[str] | None = None,
    remove_flags: list[str] | None = None,
) -> bool:
    """Update IMAP flags on a message."""
    imap = await _connect(account)
    try:
        await imap.select(mailbox)
        if add_flags:
            flags_str = " ".join(add_flags)
            await imap.store(uid, "+FLAGS", f"({flags_str})")
        if remove_flags:
            flags_str = " ".join(remove_flags)
            await imap.store(uid, "-FLAGS", f"({flags_str})")
        return True
    except Exception:
        return False
    finally:
        try:
            await imap.logout()
        except Exception:
            pass


async def delete_message(
    account: MailAccount, mailbox: str, uid: str, trash_mailbox: str | None = None
) -> dict:
    """Delete or move message to trash."""
    imap = await _connect(account)
    try:
        await imap.select(mailbox)

        if trash_mailbox and mailbox.lower() != trash_mailbox.lower():
            # Move to trash
            try:
                await imap.copy(uid, trash_mailbox)
                await imap.store(uid, "+FLAGS", "(\\Deleted)")
                await imap.expunge()
                return {"ok": True, "permanent": False}
            except Exception:
                pass

        # Permanent delete
        await imap.store(uid, "+FLAGS", "(\\Deleted)")
        await imap.expunge()
        return {"ok": True, "permanent": True}
    finally:
        try:
            await imap.logout()
        except Exception:
            pass


async def move_message(
    account: MailAccount, mailbox: str, uid: str, target_mailbox: str
) -> bool:
    """Move message to another mailbox."""
    imap = await _connect(account)
    try:
        await imap.select(mailbox)
        await imap.copy(uid, target_mailbox)
        await imap.store(uid, "+FLAGS", "(\\Deleted)")
        await imap.expunge()
        return True
    except Exception:
        return False
    finally:
        try:
            await imap.logout()
        except Exception:
            pass


async def download_attachment(
    account: MailAccount, mailbox: str, uid: str, part_index: int
) -> tuple[bytes, str, str] | None:
    """Download attachment by part index. Returns (data, content_type, filename)."""
    imap = await _connect(account)
    try:
        await imap.select(mailbox)
        fetch_resp = await imap.fetch(uid, "(BODY[])")
        if fetch_resp.result != "OK":
            return None

        raw_data = b""
        for line in fetch_resp.lines:
            if isinstance(line, bytes):
                raw_data += line + b"\r\n"

        msg = email.message_from_bytes(raw_data)
        for i, part in enumerate(msg.walk()):
            if i == part_index:
                data = part.get_payload(decode=True)
                ct = part.get_content_type()
                filename = _decode_header(part.get_filename() or f"attachment_{i}")
                return data or b"", ct, filename

        return None
    finally:
        try:
            await imap.logout()
        except Exception:
            pass


async def test_connection(account: MailAccount) -> tuple[bool, str]:
    """Test IMAP connection. Returns (success, message)."""
    try:
        imap = await _connect(account)
        await imap.logout()
        return True, "연결 성공"
    except Exception as e:
        return False, str(e)
