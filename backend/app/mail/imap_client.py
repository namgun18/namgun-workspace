"""IMAP client for reading mail via aioimaplib.

aioimaplib strips the '* ' untagged response prefix from lines,
so parsing must NOT expect '* LIST', '* N FETCH', etc.
Body data is returned as bytearray, metadata lines as bytes.
"""

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


def _decode_header(raw: str | None) -> str:
    """Decode RFC 2047 encoded header."""
    if not raw:
        return ""
    decoded_parts = email.header.decode_header(raw)
    result = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            try:
                result.append(part.decode(charset or "utf-8", errors="replace"))
            except (LookupError, UnicodeDecodeError):
                result.append(part.decode("utf-8", errors="replace"))
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


def _line_to_str(line) -> str:
    """Convert a response line (bytes, bytearray, or str) to str."""
    if isinstance(line, (bytes, bytearray)):
        return line.decode("utf-8", errors="replace")
    return str(line)


async def _connect(account: MailAccount) -> aioimaplib.IMAP4_SSL | aioimaplib.IMAP4:
    """Connect and authenticate to IMAP server."""
    import ssl as _ssl
    from app.config import get_settings

    settings = get_settings()

    # Determine login credentials: master user for builtin, per-account for external
    is_builtin = (
        account.imap_host == "mailserver"
        and settings.dovecot_master_user
        and settings.dovecot_master_password
    )
    if is_builtin:
        login_user = f"{account.username}*{settings.dovecot_master_user}"
        login_password = settings.dovecot_master_password
    else:
        login_user = account.username
        login_password = decrypt_password(account.password_encrypted)

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

    response = await imap.login(login_user, login_password)
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

        seen_roles: set[str] = set()

        for line in response.lines:
            if not line or line == b")" or line == b"":
                continue
            line_str = _line_to_str(line)

            # aioimaplib strips "* LIST " prefix.
            # Lines: (\flags) "delimiter" name  OR  * LIST (\flags) "delimiter" name
            match = re.match(r'(?:\* LIST )?\(([^)]*)\) "([^"]*)" (.+)', line_str)
            if not match:
                continue

            flags = match.group(1)
            name = match.group(3).strip('"')

            # Skip legacy/duplicate folders (Dovecot default aliases)
            if name.startswith("_"):
                continue
            name_lower = name.lower()
            if name_lower in ("sent items", "junk mail", "deleted items"):
                continue

            # Detect role from IMAP special-use flags or folder name
            role = None
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

            # Skip if we already have a folder for this role
            if role and role in seen_roles:
                continue
            if role:
                seen_roles.add(role)

            # Get message counts
            total = 0
            unread = 0
            try:
                status_resp = await imap.status(f'"{name}"', "(MESSAGES UNSEEN)")
                if status_resp.result == "OK":
                    status_line = _line_to_str(status_resp.lines[0])
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

        # Search (returns sequence numbers)
        if query:
            search_resp = await imap.search(f'(OR SUBJECT "{query}" FROM "{query}")')
        else:
            search_resp = await imap.search("ALL")

        if search_resp.result != "OK":
            return [], 0

        # Parse sequence numbers
        seq_line = _line_to_str(search_resp.lines[0])
        seqs = seq_line.strip().split() if seq_line.strip() else []

        total = len(seqs)
        if total == 0:
            return [], 0

        # Reverse for newest first, paginate
        seqs.reverse()
        start = page * limit
        end = start + limit
        page_seqs = seqs[start:end]

        if not page_seqs:
            return [], total

        seq_range = ",".join(page_seqs)
        # Request UID so we can use it as stable message ID
        fetch_resp = await imap.fetch(seq_range, "(UID FLAGS BODY.PEEK[HEADER])")
        if fetch_resp.result != "OK":
            return [], total

        messages = []
        current_uid = None
        current_flags = ""
        current_header_data = b""

        for line in fetch_resp.lines:
            line_str = _line_to_str(line)

            # aioimaplib strips "* " prefix.
            # Lines: N FETCH (UID xxx FLAGS (...) BODY[HEADER] {size})
            fetch_match = re.match(
                r"\d+ FETCH \(.*?UID (\d+).*?FLAGS \(([^)]*)\)",
                line_str,
            )
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
            elif isinstance(line, (bytes, bytearray)) and current_uid:
                current_header_data += bytes(line) + b"\r\n"

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
        fetch_resp = await imap.fetch(uid, "(UID FLAGS BODY[])")
        if fetch_resp.result != "OK":
            return None

        # Parse: first bytes line has metadata, bytearray has body, ')' closes
        raw_data = b""
        flags = ""
        found_uid = None
        for line in fetch_resp.lines:
            line_str = _line_to_str(line)
            # Metadata line: N FETCH (UID xxx FLAGS (...) BODY[] {size})
            uid_match = re.search(r"UID (\d+)", line_str)
            flag_match = re.search(r"FLAGS \(([^)]*)\)", line_str)
            if uid_match:
                found_uid = uid_match.group(1)
            if flag_match:
                flags = flag_match.group(1)
            if isinstance(line, bytearray):
                raw_data += bytes(line)

        if not raw_data:
            return None

        msg = email.message_from_bytes(raw_data)
        text_body, html_body = _extract_body(msg)
        attachments = _extract_attachments(msg)

        is_unread = "\\Seen" not in flags
        is_flagged = "\\Flagged" in flags

        msg_uid = found_uid or uid

        # Mark as read
        if is_unread:
            await imap.store(uid, "+FLAGS", "(\\Seen)")

        # MDN: extract Disposition-Notification-To and $MDNSent flag
        dnt = msg.get("Disposition-Notification-To")
        if dnt:
            dnt = _decode_header(dnt).strip()
        mdn_sent = "$MDNSent" in flags

        return {
            "id": msg_uid,
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
                    "blob_id": f"{msg_uid}:{att['part_index']}",
                    "name": att["name"],
                    "type": att["type"],
                    "size": att["size"],
                }
                for att in attachments
            ],
            "in_reply_to": msg.get("In-Reply-To"),
            "references": msg.get("References"),
            "disposition_notification_to": dnt or None,
            "mdn_sent": mdn_sent,
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
            if isinstance(line, bytearray):
                raw_data += bytes(line)

        if not raw_data:
            return None

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


async def create_mailbox(account: MailAccount, name: str) -> bool:
    """Create a new IMAP mailbox."""
    imap = await _connect(account)
    try:
        resp = await imap.create(name)
        return resp.result == "OK"
    except Exception:
        return False
    finally:
        try:
            await imap.logout()
        except Exception:
            pass


async def rename_mailbox(account: MailAccount, old_name: str, new_name: str) -> bool:
    """Rename an IMAP mailbox."""
    imap = await _connect(account)
    try:
        resp = await imap.rename(old_name, new_name)
        return resp.result == "OK"
    except Exception:
        return False
    finally:
        try:
            await imap.logout()
        except Exception:
            pass


async def delete_mailbox(account: MailAccount, name: str) -> bool:
    """Delete an IMAP mailbox."""
    imap = await _connect(account)
    try:
        resp = await imap.delete(name)
        return resp.result == "OK"
    except Exception:
        return False
    finally:
        try:
            await imap.logout()
        except Exception:
            pass


async def fetch_raw_headers(account: MailAccount, mailbox: str, uid: str) -> str | None:
    """Fetch raw RFC headers for a message by UID."""
    imap = await _connect(account)
    try:
        await imap.select(mailbox)
        fetch_resp = await imap.fetch(uid, "(BODY.PEEK[HEADER])")
        if fetch_resp.result != "OK":
            return None

        raw_data = b""
        for line in fetch_resp.lines:
            if isinstance(line, (bytes, bytearray)):
                raw_data += bytes(line)

        if not raw_data:
            return None

        return raw_data.decode("utf-8", errors="replace")
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
