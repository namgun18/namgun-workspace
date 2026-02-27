"""Authentication dependencies."""

import time as _time

from fastapi import Cookie, Depends, HTTPException, status
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import User
from app.db.session import get_db

settings = get_settings()
signer = URLSafeTimedSerializer(settings.secret_key)

SESSION_COOKIE = "ws_session"
PKCE_COOKIE = "ws_pkce"
SESSION_MAX_AGE_DEFAULT = 3600 * 8    # 8 hours
SESSION_MAX_AGE_REMEMBER = 86400 * 30  # 30 days
SESSION_MAX_AGE = SESSION_MAX_AGE_REMEMBER  # max for unsign validation

# ── Dynamic session durations (DB-backed, cached) ──────────
_session_cache: dict[str, tuple[float, int]] = {}
_SESSION_CACHE_TTL = 300  # 5 minutes


async def get_session_max_age_default(db: AsyncSession) -> int:
    """Return session max_age in seconds from DB (cached 5 min)."""
    entry = _session_cache.get("default")
    if entry and _time.monotonic() - entry[0] < _SESSION_CACHE_TTL:
        return entry[1]
    from app.admin.settings import get_setting
    val = await get_setting(db, "auth.session_hours")
    hours = int(val) if val else 8
    result = hours * 3600
    _session_cache["default"] = (_time.monotonic(), result)
    return result


async def get_session_max_age_remember(db: AsyncSession) -> int:
    """Return remember-me max_age in seconds from DB (cached 5 min)."""
    entry = _session_cache.get("remember")
    if entry and _time.monotonic() - entry[0] < _SESSION_CACHE_TTL:
        return entry[1]
    from app.admin.settings import get_setting
    val = await get_setting(db, "auth.session_remember_days")
    days = int(val) if val else 30
    result = days * 86400
    _session_cache["remember"] = (_time.monotonic(), result)
    return result


def sign_value(data: dict) -> str:
    return signer.dumps(data)


def unsign_value(token: str, max_age: int = SESSION_MAX_AGE) -> dict | None:
    try:
        return signer.loads(token, max_age=max_age)
    except BadSignature:
        return None


async def get_current_user(
    ws_session: str | None = Cookie(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not ws_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    data = unsign_value(ws_session)
    if not data or "user_id" not in data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    user = await db.get(User, data["user_id"])
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return user
