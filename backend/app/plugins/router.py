"""Plugin admin API — list installed plugins, enable/disable."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.plugins.loader import get_loaded_plugins
from app.modules.registry import is_module_enabled, set_module_enabled

router = APIRouter(tags=["plugins"])


@router.get("/api/admin/plugins")
async def list_plugins(user: User = Depends(get_current_user)):
    """Return installed plugins with their enabled status."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")

    plugins = get_loaded_plugins()
    result = []
    for p in plugins:
        result.append({
            "id": p["id"],
            "name": p["name"],
            "name_en": p.get("name_en", p["name"]),
            "icon": p["icon"],
            "route": p["route"],
            "api_prefix": p["api_prefix"],
            "version": p.get("version", "0.0.0"),
            "description": p.get("description", ""),
            "author": p.get("author", ""),
            "enabled": is_module_enabled(p["id"]),
        })
    return {"plugins": result}


class PluginToggleRequest(BaseModel):
    enabled: bool


@router.patch("/api/admin/plugins/{plugin_id}")
async def toggle_plugin(
    plugin_id: str,
    body: PluginToggleRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enable or disable a plugin. Admin only."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")

    # Check plugin is actually loaded
    plugins = get_loaded_plugins()
    found = any(p["id"] == plugin_id for p in plugins)
    if not found:
        raise HTTPException(status_code=404, detail="플러그인을 찾을 수 없습니다")

    ok = await set_module_enabled(db, plugin_id, body.enabled)
    if not ok:
        raise HTTPException(status_code=500, detail="상태 변경에 실패했습니다")

    status = "활성화" if body.enabled else "비활성화"
    return {"ok": True, "message": f"{plugin_id} 플러그인이 {status}되었습니다"}
