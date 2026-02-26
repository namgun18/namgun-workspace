"""Mail API endpoints — IMAP/SMTP client based (multi-account)."""

import logging
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db.models import MailAccount, MailSignature, User
from app.db.session import get_db
from app.mail import imap_client, smtp_client
from app.mail.crypto import encrypt_password, decrypt_password
from app.mail.schemas import (
    Mailbox,
    MailboxListResponse,
    MessageDetail,
    MessageListResponse,
    MessageSummary,
    MessageUpdateRequest,
    SendMessageRequest,
    BulkActionRequest,
    SignatureCreate,
    SignatureUpdate,
    SignatureResponse,
    EmailAddress,
    Attachment,
    MailAccountCreate,
    MailAccountUpdate,
    MailAccountResponse,
)
from app.modules.registry import require_module

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/mail", tags=["mail"])


# ─── Helpers ───


async def _get_account(
    db: AsyncSession, user: User, account_id: str | None = None
) -> MailAccount:
    """Get user's mail account (default if account_id not specified)."""
    if account_id:
        account = await db.get(MailAccount, account_id)
        if not account or account.user_id != user.id:
            raise HTTPException(status_code=404, detail="메일 계정을 찾을 수 없습니다")
        return account

    # Get default account
    result = await db.execute(
        select(MailAccount)
        .where(MailAccount.user_id == user.id, MailAccount.is_default == True)
    )
    account = result.scalar_one_or_none()
    if account:
        return account

    # Get first account
    result = await db.execute(
        select(MailAccount)
        .where(MailAccount.user_id == user.id)
        .order_by(MailAccount.created_at)
        .limit(1)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(
            status_code=404,
            detail="메일 계정이 설정되지 않았습니다. 설정에서 메일 계정을 추가해주세요.",
        )
    return account


def _account_response(account: MailAccount) -> dict:
    return {
        "id": account.id,
        "display_name": account.display_name,
        "email": account.email,
        "imap_host": account.imap_host,
        "imap_port": account.imap_port,
        "imap_security": account.imap_security,
        "smtp_host": account.smtp_host,
        "smtp_port": account.smtp_port,
        "smtp_security": account.smtp_security,
        "username": account.username,
        "is_default": account.is_default,
        "last_sync_at": account.last_sync_at.isoformat() if account.last_sync_at else None,
        "sync_error": account.sync_error,
    }


# ─── Mail Account CRUD ───


@router.get("/accounts", response_model=list[MailAccountResponse])
@require_module("mail")
async def list_accounts(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MailAccount)
        .where(MailAccount.user_id == user.id)
        .order_by(MailAccount.created_at)
    )
    return [_account_response(a) for a in result.scalars().all()]


@router.post("/accounts", response_model=MailAccountResponse, status_code=201)
@require_module("mail")
async def create_account(
    body: MailAccountCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Test connection first
    test_account = MailAccount(
        imap_host=body.imap_host,
        imap_port=body.imap_port,
        imap_security=body.imap_security,
        smtp_host=body.smtp_host,
        smtp_port=body.smtp_port,
        smtp_security=body.smtp_security,
        username=body.username,
        password_encrypted=encrypt_password(body.password),
    )

    imap_ok, imap_msg = await imap_client.test_connection(test_account)
    if not imap_ok:
        raise HTTPException(
            status_code=400,
            detail=f"IMAP 연결 실패: {imap_msg}",
        )

    smtp_ok, smtp_msg = await smtp_client.test_connection(test_account)
    if not smtp_ok:
        raise HTTPException(
            status_code=400,
            detail=f"SMTP 연결 실패: {smtp_msg}",
        )

    # If setting as default, unset other defaults
    if body.is_default:
        result = await db.execute(
            select(MailAccount).where(
                MailAccount.user_id == user.id, MailAccount.is_default == True
            )
        )
        for a in result.scalars():
            a.is_default = False

    account = MailAccount(
        user_id=user.id,
        display_name=body.display_name,
        email=body.email,
        imap_host=body.imap_host,
        imap_port=body.imap_port,
        imap_security=body.imap_security,
        smtp_host=body.smtp_host,
        smtp_port=body.smtp_port,
        smtp_security=body.smtp_security,
        username=body.username,
        password_encrypted=encrypt_password(body.password),
        is_default=body.is_default,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return _account_response(account)


@router.patch("/accounts/{account_id}", response_model=MailAccountResponse)
@require_module("mail")
async def update_account(
    account_id: str,
    body: MailAccountUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await db.get(MailAccount, account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="메일 계정을 찾을 수 없습니다")

    if body.display_name is not None:
        account.display_name = body.display_name
    if body.email is not None:
        account.email = body.email
    if body.imap_host is not None:
        account.imap_host = body.imap_host
    if body.imap_port is not None:
        account.imap_port = body.imap_port
    if body.imap_security is not None:
        account.imap_security = body.imap_security
    if body.smtp_host is not None:
        account.smtp_host = body.smtp_host
    if body.smtp_port is not None:
        account.smtp_port = body.smtp_port
    if body.smtp_security is not None:
        account.smtp_security = body.smtp_security
    if body.username is not None:
        account.username = body.username
    if body.password is not None:
        account.password_encrypted = encrypt_password(body.password)
    if body.is_default is not None:
        if body.is_default:
            result = await db.execute(
                select(MailAccount).where(
                    MailAccount.user_id == user.id,
                    MailAccount.is_default == True,
                    MailAccount.id != account_id,
                )
            )
            for a in result.scalars():
                a.is_default = False
        account.is_default = body.is_default

    await db.commit()
    await db.refresh(account)
    return _account_response(account)


@router.delete("/accounts/{account_id}")
@require_module("mail")
async def delete_account(
    account_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await db.get(MailAccount, account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="메일 계정을 찾을 수 없습니다")
    await db.delete(account)
    await db.commit()
    return {"ok": True}


@router.post("/accounts/{account_id}/test")
@require_module("mail")
async def test_account(
    account_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await db.get(MailAccount, account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="메일 계정을 찾을 수 없습니다")

    imap_ok, imap_msg = await imap_client.test_connection(account)
    smtp_ok, smtp_msg = await smtp_client.test_connection(account)

    return {
        "imap": {"ok": imap_ok, "message": imap_msg},
        "smtp": {"ok": smtp_ok, "message": smtp_msg},
    }


# ─── Mailboxes ───


@router.get("/mailboxes", response_model=MailboxListResponse)
@require_module("mail")
async def list_mailboxes(
    account_id: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await _get_account(db, user, account_id)
    try:
        raw_mailboxes = await imap_client.list_mailboxes(account)
    except Exception as e:
        logger.error("IMAP list_mailboxes failed: %s", e)
        raise HTTPException(status_code=502, detail="메일 서버에 연결할 수 없습니다")

    mailboxes = [Mailbox(**mb) for mb in raw_mailboxes]
    return MailboxListResponse(mailboxes=mailboxes)


# ─── Messages list ───


@router.get("/messages", response_model=MessageListResponse)
@require_module("mail")
async def list_messages(
    mailbox_id: str = Query(...),
    page: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    q: str | None = Query(None),
    account_id: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await _get_account(db, user, account_id)
    try:
        raw_messages, total = await imap_client.fetch_messages(
            account, mailbox_id, page, limit, query=q
        )
    except Exception as e:
        logger.error("IMAP fetch_messages failed: %s", e)
        raise HTTPException(status_code=502, detail="메일 서버에 연결할 수 없습니다")

    messages = [
        MessageSummary(
            id=msg["id"],
            thread_id=msg.get("thread_id"),
            mailbox_ids=msg.get("mailbox_ids", []),
            from_=[EmailAddress(**a) for a in msg.get("from_", [])],
            to=[EmailAddress(**a) for a in msg.get("to", [])],
            subject=msg.get("subject"),
            preview=msg.get("preview"),
            received_at=msg.get("received_at"),
            is_unread=msg.get("is_unread", False),
            is_flagged=msg.get("is_flagged", False),
            has_attachment=msg.get("has_attachment", False),
        )
        for msg in raw_messages
    ]
    return MessageListResponse(messages=messages, total=total, page=page, limit=limit)


# ─── Message detail ───


@router.get("/messages/{message_uid}", response_model=MessageDetail)
@require_module("mail")
async def get_message(
    message_uid: str,
    mailbox_id: str = Query("INBOX"),
    account_id: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await _get_account(db, user, account_id)
    try:
        msg = await imap_client.fetch_message(account, mailbox_id, message_uid)
    except Exception as e:
        logger.error("IMAP fetch_message failed: %s", e)
        raise HTTPException(status_code=502, detail="메일 서버에 연결할 수 없습니다")

    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    return MessageDetail(
        id=msg["id"],
        thread_id=msg.get("thread_id"),
        mailbox_ids=msg.get("mailbox_ids", []),
        from_=[EmailAddress(**a) for a in msg.get("from_", [])],
        to=[EmailAddress(**a) for a in msg.get("to", [])],
        cc=[EmailAddress(**a) for a in msg.get("cc", [])],
        bcc=[EmailAddress(**a) for a in msg.get("bcc", [])],
        reply_to=[EmailAddress(**a) for a in msg.get("reply_to", [])],
        subject=msg.get("subject"),
        text_body=msg.get("text_body"),
        html_body=msg.get("html_body"),
        preview=msg.get("preview"),
        received_at=msg.get("received_at"),
        is_unread=msg.get("is_unread", False),
        is_flagged=msg.get("is_flagged", False),
        attachments=[Attachment(**a) for a in msg.get("attachments", [])],
    )


# ─── Update message (read/star/move) ───


@router.patch("/messages/{message_uid}")
@require_module("mail")
async def update_message(
    message_uid: str,
    body: MessageUpdateRequest,
    mailbox_id: str = Query("INBOX"),
    account_id: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await _get_account(db, user, account_id)

    # Handle flag changes
    add_flags = []
    remove_flags = []

    if body.is_unread is not None:
        if body.is_unread:
            remove_flags.append("\\Seen")
        else:
            add_flags.append("\\Seen")

    if body.is_flagged is not None:
        if body.is_flagged:
            add_flags.append("\\Flagged")
        else:
            remove_flags.append("\\Flagged")

    if add_flags or remove_flags:
        ok = await imap_client.update_flags(
            account, mailbox_id, message_uid,
            add_flags=add_flags or None,
            remove_flags=remove_flags or None,
        )
        if not ok:
            raise HTTPException(status_code=500, detail="Failed to update message flags")

    # Handle move
    if body.mailbox_ids and body.mailbox_ids[0] != mailbox_id:
        ok = await imap_client.move_message(
            account, mailbox_id, message_uid, body.mailbox_ids[0]
        )
        if not ok:
            raise HTTPException(status_code=500, detail="Failed to move message")

    return {"ok": True}


# ─── Delete message ───


@router.delete("/messages/{message_uid}")
@require_module("mail")
async def delete_message(
    message_uid: str,
    mailbox_id: str = Query("INBOX"),
    account_id: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await _get_account(db, user, account_id)

    # Find trash mailbox
    try:
        mailboxes = await imap_client.list_mailboxes(account)
    except Exception:
        mailboxes = []

    trash_mailbox = None
    for mb in mailboxes:
        if mb.get("role") == "trash":
            trash_mailbox = mb["id"]
            break

    result = await imap_client.delete_message(
        account, mailbox_id, message_uid, trash_mailbox
    )
    return result


# ─── Send message ───


@router.post("/send")
@require_module("mail")
async def send_message(
    body: SendMessageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await _get_account(db, user, body.account_id)

    from_name = user.display_name or user.username

    try:
        await smtp_client.send_message(
            account=account,
            from_name=from_name,
            to=[a.model_dump() for a in body.to],
            cc=[a.model_dump() for a in body.cc] if body.cc else None,
            bcc=[a.model_dump() for a in body.bcc] if body.bcc else None,
            subject=body.subject,
            text_body=body.text_body,
            html_body=body.html_body,
            in_reply_to=body.in_reply_to,
            references=body.references or None,
        )
    except Exception as e:
        logger.error("SMTP send failed: %s", e)
        raise HTTPException(status_code=502, detail=f"메일 전송 실패: {str(e)}")

    return {"ok": True}


# ─── Bulk operations ───


@router.post("/bulk")
@require_module("mail")
async def bulk_action(
    body: BulkActionRequest,
    mailbox_id: str = Query("INBOX"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await _get_account(db, user, body.account_id)

    if not body.message_ids:
        raise HTTPException(status_code=400, detail="메시지를 선택해주세요")

    for uid in body.message_ids:
        if body.action == "read":
            await imap_client.update_flags(account, mailbox_id, uid, add_flags=["\\Seen"])
        elif body.action == "unread":
            await imap_client.update_flags(account, mailbox_id, uid, remove_flags=["\\Seen"])
        elif body.action == "star":
            await imap_client.update_flags(account, mailbox_id, uid, add_flags=["\\Flagged"])
        elif body.action == "unstar":
            await imap_client.update_flags(account, mailbox_id, uid, remove_flags=["\\Flagged"])
        elif body.action == "delete":
            mailboxes = await imap_client.list_mailboxes(account)
            trash = next((mb["id"] for mb in mailboxes if mb.get("role") == "trash"), None)
            await imap_client.delete_message(account, mailbox_id, uid, trash)
        elif body.action == "move":
            if not body.mailbox_id:
                raise HTTPException(status_code=400, detail="이동할 메일함을 지정해주세요")
            await imap_client.move_message(account, mailbox_id, uid, body.mailbox_id)
        else:
            raise HTTPException(status_code=400, detail=f"지원하지 않는 작업: {body.action}")

    return {"ok": True, "count": len(body.message_ids)}


# ─── Attachment download (via IMAP FETCH) ───


@router.get("/attachments/{blob_id}")
@require_module("mail")
async def download_attachment(
    blob_id: str,
    mailbox_id: str = Query("INBOX"),
    account_id: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download attachment. blob_id format: {uid}:{part_index}"""
    account = await _get_account(db, user, account_id)

    parts = blob_id.split(":")
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid blob_id format")

    uid = parts[0]
    try:
        part_index = int(parts[1])
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid part index")

    result = await imap_client.download_attachment(account, mailbox_id, uid, part_index)
    if not result:
        raise HTTPException(status_code=404, detail="Attachment not found")

    data, content_type, filename = result
    safe_name = filename.replace('"', '').replace('\n', '').replace('\r', '')
    encoded_name = quote(safe_name, safe='')
    return Response(
        content=data,
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename=\"{safe_name}\"; filename*=UTF-8''{encoded_name}",
        },
    )


# ─── Signatures CRUD (unchanged, DB-based) ───


@router.get("/signatures", response_model=list[SignatureResponse])
@require_module("mail")
async def list_signatures(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MailSignature)
        .where(MailSignature.user_id == user.id)
        .order_by(MailSignature.created_at)
    )
    sigs = result.scalars().all()
    return [
        SignatureResponse(
            id=s.id,
            name=s.name,
            html_content=s.html_content,
            is_default=s.is_default,
            created_at=s.created_at.isoformat(),
        )
        for s in sigs
    ]


@router.get("/signatures/default", response_model=SignatureResponse | None)
@require_module("mail")
async def get_default_signature(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MailSignature).where(
            MailSignature.user_id == user.id, MailSignature.is_default == True
        )
    )
    sig = result.scalar_one_or_none()
    if not sig:
        return None
    return SignatureResponse(
        id=sig.id,
        name=sig.name,
        html_content=sig.html_content,
        is_default=sig.is_default,
        created_at=sig.created_at.isoformat(),
    )


@router.post("/signatures", response_model=SignatureResponse, status_code=201)
@require_module("mail")
async def create_signature(
    body: SignatureCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.is_default:
        result = await db.execute(
            select(MailSignature).where(
                MailSignature.user_id == user.id, MailSignature.is_default == True
            )
        )
        for s in result.scalars():
            s.is_default = False

    sig = MailSignature(
        user_id=user.id,
        name=body.name,
        html_content=body.html_content,
        is_default=body.is_default,
    )
    db.add(sig)
    await db.commit()
    await db.refresh(sig)
    return SignatureResponse(
        id=sig.id,
        name=sig.name,
        html_content=sig.html_content,
        is_default=sig.is_default,
        created_at=sig.created_at.isoformat(),
    )


@router.patch("/signatures/{sig_id}", response_model=SignatureResponse)
@require_module("mail")
async def update_signature(
    sig_id: str,
    body: SignatureUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sig = await db.get(MailSignature, sig_id)
    if not sig or sig.user_id != user.id:
        raise HTTPException(status_code=404, detail="서명을 찾을 수 없습니다")

    if body.name is not None:
        sig.name = body.name
    if body.html_content is not None:
        sig.html_content = body.html_content
    if body.is_default is not None:
        if body.is_default:
            result = await db.execute(
                select(MailSignature).where(
                    MailSignature.user_id == user.id,
                    MailSignature.is_default == True,
                    MailSignature.id != sig_id,
                )
            )
            for s in result.scalars():
                s.is_default = False
        sig.is_default = body.is_default

    await db.commit()
    await db.refresh(sig)
    return SignatureResponse(
        id=sig.id,
        name=sig.name,
        html_content=sig.html_content,
        is_default=sig.is_default,
        created_at=sig.created_at.isoformat(),
    )


@router.delete("/signatures/{sig_id}")
@require_module("mail")
async def delete_signature(
    sig_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sig = await db.get(MailSignature, sig_id)
    if not sig or sig.user_id != user.id:
        raise HTTPException(status_code=404, detail="서명을 찾을 수 없습니다")
    await db.delete(sig)
    await db.commit()
    return {"ok": True}
