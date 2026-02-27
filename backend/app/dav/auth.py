"""HTTP Basic Auth for WebDAV clients."""

import base64

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.auth.password import verify_password


async def authenticate_dav(
    authorization: str | None, db: AsyncSession
) -> User | None:
    """Validate HTTP Basic Auth header and return User or None."""
    if not authorization or not authorization.startswith("Basic "):
        return None
    try:
        decoded = base64.b64decode(authorization[6:]).decode("utf-8")
        username, password = decoded.split(":", 1)
    except Exception:
        return None

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user or not user.is_active or not user.password_hash:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
