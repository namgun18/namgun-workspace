"""Platform module API — module listing + admin toggle."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.modules.registry import get_enabled_modules, set_module_enabled

router = APIRouter(tags=["platform"])


# ─── GET /api/platform/modules (public, no auth) ───


@router.get("/api/platform/modules")
async def list_modules():
    """Return all modules with enabled status. Called at frontend boot."""
    modules = await get_enabled_modules()
    return {"modules": modules}


# ─── PATCH /api/admin/modules/{module_id} (admin only) ───


class ModuleToggleRequest(BaseModel):
    enabled: bool


@router.patch("/api/admin/modules/{module_id}")
async def toggle_module(
    module_id: str,
    body: ModuleToggleRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enable or disable a module. Admin only."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")

    ok = await set_module_enabled(db, module_id, body.enabled)
    if not ok:
        raise HTTPException(status_code=404, detail="모듈을 찾을 수 없습니다")

    status = "활성화" if body.enabled else "비활성화"
    return {"ok": True, "message": f"{module_id} 모듈이 {status}되었습니다"}
