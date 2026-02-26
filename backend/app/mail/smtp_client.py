"""SMTP client for sending mail via user's SMTP server."""

import logging
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders

import aiosmtplib

from app.db.models import MailAccount
from app.mail.crypto import decrypt_password

logger = logging.getLogger(__name__)


async def send_message(
    account: MailAccount,
    from_name: str,
    to: list[dict],
    cc: list[dict] | None = None,
    bcc: list[dict] | None = None,
    subject: str = "",
    text_body: str = "",
    html_body: str | None = None,
    in_reply_to: str | None = None,
    references: list[str] | None = None,
    attachments: list[dict] | None = None,
) -> bool:
    """Send email via SMTP. Returns True on success."""
    from app.config import get_settings

    settings = get_settings()

    # Master user for builtin mailserver, per-account for external
    is_builtin = (
        account.smtp_host == "mailserver"
        and settings.dovecot_master_user
        and settings.dovecot_master_password
    )
    if is_builtin:
        smtp_user = f"{account.username}*{settings.dovecot_master_user}"
        password = settings.dovecot_master_password
    else:
        smtp_user = account.username
        password = decrypt_password(account.password_encrypted)

    # Build the email message
    if attachments:
        msg = MIMEMultipart("mixed")
        if html_body:
            alt = MIMEMultipart("alternative")
            alt.attach(MIMEText(text_body, "plain", "utf-8"))
            alt.attach(MIMEText(html_body, "html", "utf-8"))
            msg.attach(alt)
        else:
            msg.attach(MIMEText(text_body, "plain", "utf-8"))

        for att in attachments:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(att["data"])
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                "attachment",
                filename=att.get("name", "attachment"),
            )
            if att.get("type"):
                part.replace_header("Content-Type", att["type"])
            msg.attach(part)
    elif html_body:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))
    else:
        msg = MIMEText(text_body, "plain", "utf-8")

    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{account.email}>" if from_name else account.email
    msg["To"] = ", ".join(
        f"{a['name']} <{a['email']}>" if a.get("name") else a["email"]
        for a in to
    )
    if cc:
        msg["Cc"] = ", ".join(
            f"{a['name']} <{a['email']}>" if a.get("name") else a["email"]
            for a in cc
        )
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
    if references:
        msg["References"] = " ".join(references)

    # Collect all recipients
    recipients = [a["email"] for a in to]
    if cc:
        recipients.extend(a["email"] for a in cc)
    if bcc:
        recipients.extend(a["email"] for a in bcc)

    # Determine TLS mode
    use_tls = account.smtp_security == "ssl"
    start_tls = account.smtp_security == "starttls"

    import ssl as _ssl
    tls_context = _ssl.create_default_context()
    tls_context.check_hostname = False
    tls_context.verify_mode = _ssl.CERT_NONE

    try:
        await aiosmtplib.send(
            msg,
            hostname=account.smtp_host,
            port=account.smtp_port,
            username=smtp_user,
            password=password,
            use_tls=use_tls,
            start_tls=start_tls,
            tls_context=tls_context,
            recipients=recipients,
            timeout=30,
        )
        return True
    except Exception as e:
        logger.error("SMTP send failed for %s: %s", account.email, e)
        raise


async def test_connection(account: MailAccount) -> tuple[bool, str]:
    """Test SMTP connection. Returns (success, message)."""
    import ssl as _ssl
    from app.config import get_settings

    settings = get_settings()

    is_builtin = (
        account.smtp_host == "mailserver"
        and settings.dovecot_master_user
        and settings.dovecot_master_password
    )
    if is_builtin:
        smtp_user = f"{account.username}*{settings.dovecot_master_user}"
        password = settings.dovecot_master_password
    else:
        smtp_user = account.username
        password = decrypt_password(account.password_encrypted)

    use_tls = account.smtp_security == "ssl"
    start_tls = account.smtp_security == "starttls"
    tls_context = _ssl.create_default_context()
    tls_context.check_hostname = False
    tls_context.verify_mode = _ssl.CERT_NONE

    try:
        smtp = aiosmtplib.SMTP(
            hostname=account.smtp_host,
            port=account.smtp_port,
            use_tls=use_tls,
            start_tls=start_tls,
            tls_context=tls_context,
            timeout=15,
        )
        await smtp.connect()
        await smtp.login(smtp_user, password)
        await smtp.quit()
        return True, "연결 성공"
    except Exception as e:
        return False, str(e)
