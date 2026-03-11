"""Wiki REST API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.modules.registry import require_module
from app.wiki import service
from app.wiki.schemas import (
    MemberAdd, MemberUpdate, PageCreate, PageUpdate, SpaceCreate, SpaceUpdate,
)

router = APIRouter(prefix="/api/wiki", tags=["wiki"])


def _check_role(role: str | None, required: str):
    """Raise 403 if user lacks the required role."""
    levels = {"reader": 0, "writer": 1, "admin": 2}
    if role is None or levels.get(role, -1) < levels.get(required, 99):
        raise HTTPException(403, "접근 권한이 없습니다")


# ─── Spaces ───


@router.get("/spaces")
@require_module("wiki")
async def list_spaces(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_spaces(db, str(user.id))


@router.post("/spaces", status_code=201)
@require_module("wiki")
async def create_space(
    body: SpaceCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await service.get_space_by_slug(db, body.slug)
    if existing:
        raise HTTPException(400, "이미 사용 중인 슬러그입니다")
    return await service.create_space(db, str(user.id), **body.model_dump())


@router.get("/spaces/{space_id}")
@require_module("wiki")
async def get_space(
    space_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    role = await service.get_user_role(db, space_id, str(user.id))
    if not user.is_admin:
        _check_role(role, "reader")
    space = await service.get_space(db, space_id)
    if not space:
        raise HTTPException(404, "스페이스를 찾을 수 없습니다")
    return {
        "id": space.id, "name": space.name, "slug": space.slug,
        "description": space.description, "visibility": space.visibility,
        "icon": space.icon, "user_role": role,
    }


@router.patch("/spaces/{space_id}")
@require_module("wiki")
async def update_space(
    space_id: str,
    body: SpaceUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    role = await service.get_user_role(db, space_id, str(user.id))
    if not user.is_admin:
        _check_role(role, "admin")
    await service.update_space(db, space_id, **body.model_dump(exclude_unset=True))
    return {"ok": True}


@router.delete("/spaces/{space_id}")
@require_module("wiki")
async def delete_space(
    space_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    role = await service.get_user_role(db, space_id, str(user.id))
    if not user.is_admin:
        _check_role(role, "admin")
    await service.delete_space(db, space_id)
    return {"ok": True}


# ─── Members ───


@router.get("/spaces/{space_id}/members")
@require_module("wiki")
async def list_members(
    space_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    role = await service.get_user_role(db, space_id, str(user.id))
    if not user.is_admin:
        _check_role(role, "reader")
    return await service.get_members(db, space_id)


@router.post("/spaces/{space_id}/members")
@require_module("wiki")
async def add_member(
    space_id: str,
    body: MemberAdd,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    role = await service.get_user_role(db, space_id, str(user.id))
    if not user.is_admin:
        _check_role(role, "admin")
    await service.add_member(db, space_id, body.user_id, body.role)
    return {"ok": True}


@router.patch("/spaces/{space_id}/members/{member_user_id}")
@require_module("wiki")
async def update_member(
    space_id: str,
    member_user_id: str,
    body: MemberUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    role = await service.get_user_role(db, space_id, str(user.id))
    if not user.is_admin:
        _check_role(role, "admin")
    await service.update_member(db, space_id, member_user_id, body.role)
    return {"ok": True}


@router.delete("/spaces/{space_id}/members/{member_user_id}")
@require_module("wiki")
async def remove_member(
    space_id: str,
    member_user_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    role = await service.get_user_role(db, space_id, str(user.id))
    if not user.is_admin:
        _check_role(role, "admin")
    await service.remove_member(db, space_id, member_user_id)
    return {"ok": True}


# ─── Pages ───


@router.get("/spaces/{space_id}/pages")
@require_module("wiki")
async def list_pages(
    space_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    role = await service.get_user_role(db, space_id, str(user.id))
    if not user.is_admin:
        _check_role(role, "reader")
    return await service.get_page_tree(db, space_id)


@router.get("/pages/{page_id}")
@require_module("wiki")
async def get_page(
    page_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    page = await service.get_page(db, page_id)
    if not page:
        raise HTTPException(404, "페이지를 찾을 수 없습니다")
    role = await service.get_user_role(db, page["space_id"], str(user.id))
    if not user.is_admin:
        _check_role(role, "reader")
    page["user_role"] = role
    return page


@router.post("/spaces/{space_id}/pages", status_code=201)
@require_module("wiki")
async def create_page(
    space_id: str,
    body: PageCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    role = await service.get_user_role(db, space_id, str(user.id))
    if not user.is_admin:
        _check_role(role, "writer")
    return await service.create_page(db, space_id, str(user.id), **body.model_dump())


@router.patch("/pages/{page_id}")
@require_module("wiki")
async def update_page(
    page_id: str,
    body: PageUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    page = await service.get_page(db, page_id)
    if not page:
        raise HTTPException(404)
    role = await service.get_user_role(db, page["space_id"], str(user.id))
    if not user.is_admin:
        _check_role(role, "writer")
    return await service.update_page(db, page_id, str(user.id), **body.model_dump(exclude_unset=True))


@router.delete("/pages/{page_id}")
@require_module("wiki")
async def delete_page(
    page_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    page = await service.get_page(db, page_id)
    if not page:
        raise HTTPException(404)
    role = await service.get_user_role(db, page["space_id"], str(user.id))
    if not user.is_admin:
        _check_role(role, "writer")
    await service.delete_page(db, page_id)
    return {"ok": True}


# ─── Versions ───


@router.get("/pages/{page_id}/versions")
@require_module("wiki")
async def list_versions(
    page_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    page = await service.get_page(db, page_id)
    if not page:
        raise HTTPException(404)
    role = await service.get_user_role(db, page["space_id"], str(user.id))
    if not user.is_admin:
        _check_role(role, "reader")
    return await service.get_page_versions(db, page_id)


# ─── Search ───


@router.get("/spaces/{space_id}/search")
@require_module("wiki")
async def search_pages(
    space_id: str,
    q: str = Query("", min_length=1),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    role = await service.get_user_role(db, space_id, str(user.id))
    if not user.is_admin:
        _check_role(role, "reader")
    return await service.search_pages(db, space_id, q)
