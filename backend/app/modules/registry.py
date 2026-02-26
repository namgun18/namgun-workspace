"""Module registry — built-in module definitions + DB-backed enable/disable."""

import json
import logging
from functools import wraps
from typing import Any

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SystemSetting

logger = logging.getLogger(__name__)

# ─── Built-in module definitions ───

BUILTIN_MODULES: list[dict[str, Any]] = [
    {
        "id": "mail",
        "name": "메일",
        "icon": "mail",
        "route": "/mail",
        "api_prefix": "/api/mail",
        "type": "builtin",
        "requires": [],
        "default_enabled": True,
    },
    {
        "id": "chat",
        "name": "채팅",
        "icon": "message-square",
        "route": "/chat",
        "api_prefix": "/api/chat",
        "type": "builtin",
        "requires": [],
        "default_enabled": True,
    },
    {
        "id": "meetings",
        "name": "화상회의",
        "icon": "video",
        "route": "/meetings",
        "api_prefix": "/api/meetings",
        "type": "builtin",
        "requires": [],
        "default_enabled": True,
    },
    {
        "id": "files",
        "name": "파일",
        "icon": "folder",
        "route": "/files",
        "api_prefix": "/api/files",
        "type": "builtin",
        "requires": [],
        "default_enabled": True,
    },
    {
        "id": "calendar",
        "name": "캘린더",
        "icon": "calendar",
        "route": "/calendar",
        "api_prefix": "/api/calendar",
        "type": "builtin",
        "requires": [],
        "default_enabled": True,
    },
    {
        "id": "contacts",
        "name": "연락처",
        "icon": "users",
        "route": "/contacts",
        "api_prefix": "/api/contacts",
        "type": "builtin",
        "requires": [],
        "default_enabled": True,
    },
    {
        "id": "git",
        "name": "Git",
        "icon": "git-branch",
        "route": "/git",
        "api_prefix": "/api/git",
        "type": "builtin",
        "requires": [],
        "default_enabled": True,
    },
]

# ─── In-memory cache ───

_module_states: dict[str, bool] = {}
_cache_loaded = False


def _module_key(module_id: str) -> str:
    return f"module.{module_id}.enabled"


async def load_module_states(db: AsyncSession) -> None:
    """Load module enabled/disabled states from DB into cache."""
    global _cache_loaded
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key.like("module.%.enabled"))
    )
    settings = result.scalars().all()

    # Start with defaults
    _module_states.clear()
    for mod in BUILTIN_MODULES:
        _module_states[mod["id"]] = mod["default_enabled"]

    # Override with DB values
    for s in settings:
        # key = "module.xxx.enabled"
        parts = s.key.split(".")
        if len(parts) == 3:
            module_id = parts[1]
            try:
                _module_states[module_id] = json.loads(s.value)
            except (json.JSONDecodeError, TypeError):
                pass

    _cache_loaded = True
    logger.info("[Modules] loaded states: %s", _module_states)


def is_module_enabled(module_id: str) -> bool:
    """Fast cached check. Falls back to default_enabled if cache not loaded."""
    if module_id in _module_states:
        return _module_states[module_id]
    # Fallback: find in BUILTIN_MODULES
    for mod in BUILTIN_MODULES:
        if mod["id"] == module_id:
            return mod["default_enabled"]
    return False


async def get_enabled_modules() -> list[dict]:
    """Return list of all modules with their enabled status."""
    result = []
    for mod in BUILTIN_MODULES:
        enabled = is_module_enabled(mod["id"])
        result.append({
            "id": mod["id"],
            "name": mod["name"],
            "icon": mod["icon"],
            "route": mod["route"],
            "type": mod["type"],
            "requires": mod["requires"],
            "enabled": enabled,
        })
    return result


async def set_module_enabled(db: AsyncSession, module_id: str, enabled: bool) -> bool:
    """Set module enabled/disabled in DB + update cache."""
    # Validate module exists
    found = any(m["id"] == module_id for m in BUILTIN_MODULES)
    if not found:
        return False

    key = _module_key(module_id)
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()

    if setting:
        setting.value = json.dumps(enabled)
    else:
        setting = SystemSetting(key=key, value=json.dumps(enabled))
        db.add(setting)

    await db.commit()
    _module_states[module_id] = enabled
    logger.info("[Modules] %s → %s", module_id, "enabled" if enabled else "disabled")
    return True


# ─── Decorator: require_module ───


def require_module(module_id: str):
    """Decorator for FastAPI endpoints — returns 403 if module is disabled."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not is_module_enabled(module_id):
                raise HTTPException(
                    status_code=403,
                    detail="이 기능은 비활성화되어 있습니다",
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator
