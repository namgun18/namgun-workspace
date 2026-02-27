"""Auth API routes: login, me, logout, register, profile, password management, 2FA."""

import logging
import secrets
from datetime import datetime, timezone
from pathlib import Path

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import User
from app.db.session import get_db
from app.rate_limit import limiter
from app.auth.deps import (
    SESSION_COOKIE,
    SESSION_MAX_AGE_DEFAULT,
    SESSION_MAX_AGE_REMEMBER,
    get_current_user,
    get_session_max_age_default,
    get_session_max_age_remember,
    sign_value,
    unsign_value,
)
from app.auth.password import hash_password, verify_password
from app.auth.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    ProfileUpdateRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TwoFactorDisableRequest,
    TwoFactorEnableRequest,
    TwoFactorVerifyRequest,
    UserResponse,
)

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Helper: session cookie response ──────────────────────────


def _session_response(
    user: User,
    body: dict | None = None,
    max_age: int = SESSION_MAX_AGE_DEFAULT,
) -> JSONResponse:
    session_data = sign_value({"user_id": user.id})
    response = JSONResponse(content=body or {"status": "ok"})
    is_https = settings.app_url.startswith("https://")
    response.set_cookie(
        SESSION_COOKIE,
        session_data,
        httponly=True,
        secure=is_https,
        samesite="lax",
        max_age=max_age,
        path="/",
    )
    return response


# ── POST /api/auth/login ─────────────────────────────────────


TEMP_TOKEN_MAX_AGE = 300  # 5 minutes for 2FA temp tokens


@router.post("/login")
@limiter.limit("10/minute")
async def login_post(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with username and password (bcrypt). Returns temp_token if 2FA is enabled."""
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="사용자명 또는 비밀번호가 올바르지 않습니다")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="계정이 비활성 상태입니다. 관리자 승인을 기다려주세요.")

    # If 2FA is enabled, return a temp token instead of session cookie
    if user.totp_secret:
        temp_token = sign_value({
            "user_id": user.id,
            "purpose": "2fa",
            "remember_me": body.remember_me,
        })
        return JSONResponse(content={
            "requires_2fa": True,
            "temp_token": temp_token,
        })

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    if body.remember_me:
        max_age = await get_session_max_age_remember(db)
    else:
        max_age = await get_session_max_age_default(db)
    return _session_response(user, max_age=max_age)


# ── POST /api/auth/demo-login ─────────────────────────────────


@router.post("/demo-login")
async def demo_login(db: AsyncSession = Depends(get_db)):
    """Auto-login as demo admin. Only available when DEMO_MODE=true."""
    if not settings.demo_mode:
        raise HTTPException(status_code=404, detail="Not found")
    import os
    admin_user = os.environ.get("ADMIN_USERNAME", "admin")
    result = await db.execute(select(User).where(User.username == admin_user))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=500, detail="Demo user not found")
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    return _session_response(user, max_age=86400 * 7)


# ── GET /api/auth/me ─────────────────────────────────────────


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    """Return current authenticated user info."""
    return UserResponse.from_user(user)


# ── POST /api/auth/logout ───────────────────────────────────


@router.post("/logout")
async def logout():
    """Clear session cookie."""
    response = JSONResponse(content={"status": "ok"})
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


# ── POST /api/auth/register — 회원가입 ──────────────────────


@router.post("/register", status_code=201)
@limiter.limit("5/minute")
async def register(request: Request, body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user (respects registration_mode: open/approval/closed)."""
    from app.admin.settings import get_setting

    reg_mode = await get_setting(db, "auth.registration_mode") or "approval"
    if reg_mode == "closed":
        raise HTTPException(status_code=403, detail="현재 회원가입이 비활성화되어 있습니다")

    email = f"{body.username}@{settings.domain}"

    # Check if username already exists in DB
    result = await db.execute(select(User).where(User.username == body.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="이미 사용 중인 사용자명입니다")

    # Generate email verification token
    verify_token = secrets.token_urlsafe(32)

    # Create DB record with bcrypt password hash
    is_active = reg_mode == "open"  # open: immediate activation, approval: pending
    user = User(
        username=body.username,
        display_name=body.display_name,
        email=email,
        recovery_email=body.recovery_email,
        password_hash=hash_password(body.password),
        email_verified=False,
        email_verify_token=verify_token,
        email_verify_sent_at=datetime.now(timezone.utc),
        is_active=is_active,
    )
    db.add(user)
    await db.commit()

    # Create mail account in docker-mailserver if built-in mail server is enabled
    if getattr(settings, 'feature_builtin_mailserver', False):
        try:
            from app.mail.mailserver import create_account
            await create_account(email, body.password)
        except Exception as e:
            logger.warning("Failed to create mail account for %s: %s", email, e)

    # Send verification email to recovery_email
    try:
        verify_url = f"{settings.app_url}/verify-email?token={verify_token}"
        await _send_verify_email(body.recovery_email, body.username, verify_url)
    except Exception as e:
        logger.warning("Failed to send verification email to %s: %s", body.recovery_email, e)

    # Notify admins of new registration
    try:
        await _send_admin_registration_notify(body.username, body.display_name, email, body.recovery_email)
    except Exception as e:
        logger.warning("Failed to send admin registration notification for %s: %s", body.username, e)

    if reg_mode == "open":
        return {"message": "가입이 완료되었습니다. 로그인해주세요."}
    return {"message": "가입 신청이 완료되었습니다. 복구 이메일로 전송된 인증 링크를 확인해주세요."}


# ── GET /api/auth/verify-email — 이메일 인증 ────────────────


@router.get("/verify-email")
@limiter.limit("10/minute")
async def verify_email(request: Request, token: str = Query(...), db: AsyncSession = Depends(get_db)):
    """Verify recovery email via token link."""
    result = await db.execute(
        select(User).where(User.email_verify_token == token)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=400, detail="유효하지 않은 인증 링크입니다.")

    # Check token expiry (24 hours)
    if user.email_verify_sent_at:
        elapsed = (datetime.now(timezone.utc) - user.email_verify_sent_at).total_seconds()
        if elapsed > 86400:
            raise HTTPException(status_code=400, detail="인증 링크가 만료되었습니다. 다시 가입해주세요.")

    user.email_verified = True
    user.email_verify_token = None
    await db.commit()

    return {"message": "이메일 인증이 완료되었습니다. 관리자 승인 후 로그인이 가능합니다."}


# ── PATCH /api/auth/profile — 프로필 수정 ────────────────────


@router.patch("/profile")
async def update_profile(
    body: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update display name and/or recovery email."""
    if body.display_name is not None:
        user.display_name = body.display_name

    if body.recovery_email is not None:
        user.recovery_email = body.recovery_email

    await db.commit()
    await db.refresh(user)
    return {"message": "프로필이 수정되었습니다"}


# ── POST /api/auth/avatar — 아바타 업로드 ────────────────────

AVATAR_DIR = Path(settings.storage_root) / "avatars"
AVATAR_MAX_BYTES = 5 * 1024 * 1024
AVATAR_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload or replace user profile avatar."""
    if file.content_type not in AVATAR_ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="jpg/png/webp/gif 이미지만 허용됩니다")

    data = await file.read()
    if len(data) > AVATAR_MAX_BYTES:
        raise HTTPException(status_code=413, detail="이미지 크기는 5MB 이하여야 합니다")

    import asyncio
    from io import BytesIO

    def _resize(raw: bytes) -> bytes:
        from PIL import Image
        img = Image.open(BytesIO(raw))
        img = img.convert("RGB")
        img.thumbnail((256, 256), Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue()

    resized = await asyncio.to_thread(_resize, data)

    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{user.id}.jpg"
    (AVATAR_DIR / filename).write_bytes(resized)

    user.avatar_url = f"/api/auth/avatar/{filename}"
    await db.commit()

    return {"avatar_url": user.avatar_url}


# ── GET /api/auth/avatar/{filename} — 아바타 서빙 ────────────


@router.get("/avatar/{filename}")
async def serve_avatar(filename: str):
    """Serve avatar image file."""
    import re
    if not re.match(r'^[\w-]+\.jpg$', filename):
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = AVATAR_DIR / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Avatar not found")
    return FileResponse(str(path), media_type="image/jpeg")


# ── POST /api/auth/change-password — 비밀번호 변경 ──────────


@router.post("/change-password")
@limiter.limit("5/minute")
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):  # noqa: E501
    """Change password (requires current password verification)."""
    if not user.password_hash or not verify_password(body.current_password, user.password_hash):
        raise HTTPException(
            status_code=400, detail="현재 비밀번호가 올바르지 않습니다"
        )

    user.password_hash = hash_password(body.new_password)
    await db.commit()

    # Sync password to built-in mail server if enabled
    if getattr(settings, 'feature_builtin_mailserver', False):
        try:
            from app.mail.mailserver import update_password as mail_update_password
            await mail_update_password(user.email, body.new_password)
        except Exception as e:
            logger.warning("Failed to sync password change to mail server for %s: %s", user.email, e)

    return {"message": "비밀번호가 변경되었습니다"}


# ── POST /api/auth/forgot-password — 비밀번호 찾기 ──────────


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(
    request: Request, body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)
):
    """Send password reset link to recovery email."""
    result = await db.execute(
        select(User).where(User.username == body.username, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    # Always return success to prevent username enumeration
    success_msg = "등록된 복구 이메일로 비밀번호 재설정 링크를 전송했습니다."

    if not user or not user.recovery_email:
        return {"message": success_msg}

    # Generate self-managed reset token
    token = secrets.token_urlsafe(32)
    user.password_reset_token = token
    user.password_reset_sent_at = datetime.now(timezone.utc)
    await db.commit()

    reset_url = f"{settings.app_url}/reset-password?token={token}"
    try:
        await _send_recovery_email(user.recovery_email, user.username, reset_url)
    except Exception as e:
        logger.warning("Failed to send recovery email to %s: %s", user.recovery_email, e)

    return {"message": success_msg}


# ── POST /api/auth/reset-password — 비밀번호 재설정 ──────────


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(request: Request, body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Reset password using a token from forgot-password email."""
    result = await db.execute(
        select(User).where(User.password_reset_token == body.token)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=400, detail="유효하지 않은 재설정 링크입니다")

    # Check expiry (1 hour)
    if user.password_reset_sent_at:
        elapsed = (datetime.now(timezone.utc) - user.password_reset_sent_at).total_seconds()
        if elapsed > 3600:
            raise HTTPException(status_code=400, detail="재설정 링크가 만료되었습니다")

    user.password_hash = hash_password(body.new_password)
    user.password_reset_token = None
    user.password_reset_sent_at = None
    await db.commit()

    # Sync password to built-in mail server if enabled
    if getattr(settings, 'feature_builtin_mailserver', False):
        try:
            from app.mail.mailserver import update_password as mail_update_password
            await mail_update_password(user.email, body.new_password)
        except Exception as e:
            logger.warning("Failed to sync password reset to mail server for %s: %s", user.email, e)

    return {"message": "비밀번호가 재설정되었습니다. 로그인해주세요."}


# ── GET /api/auth/users/search — 사용자 검색 ─────────────────


@router.get("/users/search")
async def search_users(
    q: str = Query(..., min_length=1, max_length=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Search active users by username or display_name (for meeting invitations etc.)."""
    safe_q = q.replace('%', '\\%').replace('_', '\\_')
    pattern = f"%{safe_q}%"
    result = await db.execute(
        select(User)
        .where(
            User.is_active == True,  # noqa: E712
            User.id != user.id,
            or_(
                User.username.ilike(pattern, escape='\\'),
                User.display_name.ilike(pattern, escape='\\'),
            ),
        )
        .limit(10)
    )
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "display_name": u.display_name or u.username,
            "email": u.email,
        }
        for u in users
    ]


# ── 2FA (TOTP) endpoints ─────────────────────────────────────


@router.post("/2fa/setup")
async def setup_2fa(
    user: User = Depends(get_current_user),
):
    """Generate a new TOTP secret and return the otpauth URI for QR code display."""
    if user.totp_secret:
        raise HTTPException(status_code=400, detail="2단계 인증이 이미 활성화되어 있습니다")

    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    otpauth_url = totp.provisioning_uri(
        name=user.username,
        issuer_name=settings.app_name,
    )
    return {"secret": secret, "otpauth_url": otpauth_url}


@router.post("/2fa/enable")
async def enable_2fa(
    body: TwoFactorEnableRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify a TOTP code against the pending secret and enable 2FA."""
    if user.totp_secret:
        raise HTTPException(status_code=400, detail="2단계 인증이 이미 활성화되어 있습니다")

    # Validate the code against the secret provided during setup
    totp = pyotp.TOTP(body.secret)
    if not totp.verify(body.code, valid_window=1):
        raise HTTPException(status_code=400, detail="인증 코드가 올바르지 않습니다")

    # Store the secret only after successful verification
    user.totp_secret = body.secret
    await db.commit()
    return {"message": "2단계 인증이 활성화되었습니다"}


@router.post("/2fa/disable")
@limiter.limit("5/minute")
async def disable_2fa(
    request: Request,
    body: TwoFactorDisableRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disable 2FA after verifying the TOTP code."""
    if not user.totp_secret:
        raise HTTPException(status_code=400, detail="2단계 인증이 활성화되어 있지 않습니다")

    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(body.code, valid_window=1):
        raise HTTPException(status_code=400, detail="인증 코드가 올바르지 않습니다")

    user.totp_secret = None
    await db.commit()
    return {"message": "2단계 인증이 비활성화되었습니다"}


@router.post("/2fa/verify")
@limiter.limit("10/minute")
async def verify_2fa(
    request: Request,
    body: TwoFactorVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """Verify TOTP code during login flow using the temp_token."""
    data = unsign_value(body.temp_token, max_age=TEMP_TOKEN_MAX_AGE)
    if not data or data.get("purpose") != "2fa" or "user_id" not in data:
        raise HTTPException(status_code=401, detail="유효하지 않거나 만료된 임시 토큰입니다")

    user = await db.get(User, data["user_id"])
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="유효하지 않은 사용자입니다")

    if not user.totp_secret:
        raise HTTPException(status_code=400, detail="2단계 인증이 설정되어 있지 않습니다")

    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(body.code, valid_window=1):
        raise HTTPException(status_code=401, detail="인증 코드가 올바르지 않습니다")

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    remember_me = data.get("remember_me", False)
    if remember_me:
        max_age = await get_session_max_age_remember(db)
    else:
        max_age = await get_session_max_age_default(db)
    return _session_response(user, max_age=max_age)


# ── Email helpers ────────────────────────────────────────────


async def _send_verify_email(
    to_email: str, username: str, verify_url: str
) -> None:
    """Send email verification link via system SMTP."""
    import asyncio
    from email.mime.text import MIMEText
    from app.admin.settings import get_smtp_config, send_system_email
    from app.db.session import async_session

    async with async_session() as db:
        cfg = await get_smtp_config(db)

    msg = MIMEText(
        f"{username}님, 아래 링크를 클릭하여 이메일을 인증해주세요:\n\n"
        f"{verify_url}\n\n"
        f"이 링크는 24시간 후 만료됩니다.\n"
        f"본인이 요청하지 않은 경우 이 메일을 무시하세요.",
        "plain",
        "utf-8",
    )
    msg["Subject"] = f"[{settings.domain}] 이메일 인증"
    msg["From"] = cfg.from_addr
    msg["To"] = to_email

    await asyncio.to_thread(send_system_email, cfg, msg)


async def _send_recovery_email(
    to_email: str, username: str, recovery_link: str
) -> None:
    """Send recovery email via system SMTP."""
    import asyncio
    from email.mime.text import MIMEText
    from app.admin.settings import get_smtp_config, send_system_email
    from app.db.session import async_session

    async with async_session() as db:
        cfg = await get_smtp_config(db)

    msg = MIMEText(
        f"{username}님, 아래 링크를 클릭하여 비밀번호를 재설정하세요:\n\n"
        f"{recovery_link}\n\n"
        f"이 링크는 1시간 후 만료됩니다.\n"
        f"본인이 요청하지 않은 경우 이 메일을 무시하세요.",
        "plain",
        "utf-8",
    )
    msg["Subject"] = f"[{settings.domain}] 비밀번호 재설정"
    msg["From"] = cfg.from_addr
    msg["To"] = to_email

    await asyncio.to_thread(send_system_email, cfg, msg)


async def _send_admin_registration_notify(
    username: str, display_name: str, email: str, recovery_email: str
) -> None:
    """Notify admins when a new user registers."""
    import asyncio
    from email.mime.text import MIMEText
    from app.admin.settings import get_smtp_config, send_system_email
    from app.db.session import async_session

    admin_list = [e.strip() for e in settings.admin_emails.split(",") if e.strip()]
    if not admin_list:
        return

    async with async_session() as db:
        cfg = await get_smtp_config(db)

    msg = MIMEText(
        f"새로운 가입 신청이 접수되었습니다.\n\n"
        f"  사용자명: {username}\n"
        f"  표시 이름: {display_name or '(없음)'}\n"
        f"  포털 메일: {email}\n"
        f"  복구 이메일: {recovery_email}\n\n"
        f"포털 관리 페이지에서 승인/거절해주세요:\n"
        f"{settings.app_url}/admin/users",
        "plain",
        "utf-8",
    )
    msg["Subject"] = f"[{settings.domain}] 새 가입 신청: {username}"
    msg["From"] = cfg.from_addr
    msg["To"] = ", ".join(admin_list)

    await asyncio.to_thread(send_system_email, cfg, msg)
