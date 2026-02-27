"""Tasks API endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.tasks import service
from app.tasks.schemas import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskListResponse,
)
from app.modules.registry import require_module

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/", response_model=TaskListResponse)
@require_module("tasks")
async def list_tasks(
    status: str | None = Query(None, pattern="^(todo|in_progress|done)$"),
    priority: str | None = Query(None, pattern="^(low|medium|high)$"),
    due_from: datetime | None = Query(None),
    due_to: datetime | None = Query(None),
    sort_by: str = Query("created_at", pattern="^(due_date|priority|created_at|sort_order|title)$"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tasks, total = await service.get_tasks(
        db, user.id, status, priority, due_from, due_to,
        sort_by, sort_dir, page, limit,
    )
    return {"tasks": [TaskResponse(**t) for t in tasks], "total": total}


@router.post("/", response_model=TaskResponse, status_code=201)
@require_module("tasks")
async def create_task(
    body: TaskCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = body.model_dump()
    result = await service.create_task(db, user.id, data)
    return TaskResponse(**result)


@router.get("/{task_id}", response_model=TaskResponse)
@require_module("tasks")
async def get_task(
    task_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await service.get_task(db, user.id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(**task)


@router.patch("/{task_id}", response_model=TaskResponse)
@require_module("tasks")
async def update_task(
    task_id: str,
    body: TaskUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = body.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = await service.update_task(db, user.id, task_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(**result)


@router.delete("/{task_id}", response_model=dict)
@require_module("tasks")
async def delete_task(
    task_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ok = await service.delete_task(db, user.id, task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"ok": True}


@router.post("/{task_id}/toggle", response_model=TaskResponse)
@require_module("tasks")
async def toggle_task(
    task_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await service.toggle_task(db, user.id, task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(**result)
