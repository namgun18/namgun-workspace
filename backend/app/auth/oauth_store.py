"""Authorization code store for Portal OIDC provider.

Uses Redis if available (survives restart), falls back to in-memory.
"""

import json
import time
from dataclasses import dataclass, asdict

CODE_TTL = 300  # 5 minutes


@dataclass
class AuthorizationCode:
    user_id: str
    client_id: str
    redirect_uri: str
    scope: str
    code_challenge: str | None
    nonce: str | None
    expires_at: float


# ── In-memory fallback ──
_codes: dict[str, AuthorizationCode] = {}


def _cleanup() -> None:
    now = time.time()
    expired = [k for k, v in _codes.items() if v.expires_at < now]
    for k in expired:
        del _codes[k]


async def _get_redis():
    """Try to get Redis connection, return None if unavailable."""
    try:
        from app.chat.redis_client import get_redis
        return await get_redis()
    except Exception:
        return None


async def store_code_async(code: str, data: AuthorizationCode) -> None:
    """Store authorization code in Redis (preferred) or memory."""
    r = await _get_redis()
    if r:
        payload = json.dumps(asdict(data))
        await r.setex(f"oauth:code:{code}", CODE_TTL, payload)
    else:
        _cleanup()
        _codes[code] = data


async def consume_code_async(code: str) -> AuthorizationCode | None:
    """Return and remove code (one-time use)."""
    r = await _get_redis()
    if r:
        key = f"oauth:code:{code}"
        raw = await r.getdel(key)
        if not raw:
            return None
        d = json.loads(raw)
        ac = AuthorizationCode(**d)
        if ac.expires_at < time.time():
            return None
        return ac
    else:
        _cleanup()
        return _codes.pop(code, None)


# ── Sync wrappers for backward compatibility ──

def store_code(code: str, data: AuthorizationCode) -> None:
    """Sync wrapper — stores in memory only (legacy)."""
    _cleanup()
    _codes[code] = data


def consume_code(code: str) -> AuthorizationCode | None:
    """Sync wrapper — consumes from memory only (legacy)."""
    _cleanup()
    return _codes.pop(code, None)
