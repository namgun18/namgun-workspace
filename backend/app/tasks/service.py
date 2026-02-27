"""Tasks service — async SQLAlchemy CRUD."""

from datetime import datetime, timezone

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TaskDB


def _task_to_dict(t: TaskDB) -> dict:
    return {
        "id": t.id,
        "user_id": t.user_id,
        "title": t.title,
        "description": t.description,
        "due_date": t.due_date,
        "priority": t.priority,
        "status": t.status,
        "calendar_event_id": t.calendar_event_id,
        "sort_order": t.sort_order,
        "created_at": t.created_at,
        "updated_at": t.updated_at,
    }


async def get_tasks(
    db: AsyncSession,
    user_id: str,
    status: str | None = None,
    priority: str | None = None,
    due_from: datetime | None = None,
    due_to: datetime | None = None,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
    page: int = 0,
    limit: int = 50,
) -> tuple[list[dict], int]:
    """Query tasks with optional filters. Returns (tasks, total)."""
    conditions = [TaskDB.user_id == user_id]

    if status:
        conditions.append(TaskDB.status == status)
    if priority:
        conditions.append(TaskDB.priority == priority)
    if due_from:
        conditions.append(TaskDB.due_date >= due_from)
    if due_to:
        conditions.append(TaskDB.due_date <= due_to)

    where = and_(*conditions)

    # Total count
    count_result = await db.execute(select(func.count(TaskDB.id)).where(where))
    total = count_result.scalar() or 0

    # Sort
    sort_column_map = {
        "due_date": TaskDB.due_date,
        "priority": TaskDB.priority,
        "created_at": TaskDB.created_at,
        "sort_order": TaskDB.sort_order,
        "title": TaskDB.title,
    }
    sort_col = sort_column_map.get(sort_by, TaskDB.created_at)
    order = sort_col.desc() if sort_dir == "desc" else sort_col.asc()

    # Fetch page
    result = await db.execute(
        select(TaskDB)
        .where(where)
        .order_by(order)
        .offset(page * limit)
        .limit(limit)
    )
    tasks = [_task_to_dict(t) for t in result.scalars().all()]
    return tasks, total


async def get_task(db: AsyncSession, user_id: str, task_id: str) -> dict | None:
    task = await db.get(TaskDB, task_id)
    if not task or task.user_id != user_id:
        return None
    return _task_to_dict(task)


async def create_task(db: AsyncSession, user_id: str, data: dict) -> dict:
    task = TaskDB(
        user_id=user_id,
        title=data["title"],
        description=data.get("description"),
        due_date=data.get("due_date"),
        priority=data.get("priority", "medium"),
        status=data.get("status", "todo"),
        calendar_event_id=data.get("calendar_event_id"),
        sort_order=data.get("sort_order", 0),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return _task_to_dict(task)


async def update_task(
    db: AsyncSession, user_id: str, task_id: str, data: dict
) -> dict | None:
    task = await db.get(TaskDB, task_id)
    if not task or task.user_id != user_id:
        return None

    for field in ("title", "description", "due_date", "priority", "status",
                  "calendar_event_id", "sort_order"):
        if field in data and data[field] is not None:
            setattr(task, field, data[field])

    task.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(task)
    return _task_to_dict(task)


async def delete_task(db: AsyncSession, user_id: str, task_id: str) -> bool:
    task = await db.get(TaskDB, task_id)
    if not task or task.user_id != user_id:
        return False
    await db.delete(task)
    await db.commit()
    return True


async def toggle_task(db: AsyncSession, user_id: str, task_id: str) -> dict | None:
    """Toggle task between 'todo' and 'done'."""
    task = await db.get(TaskDB, task_id)
    if not task or task.user_id != user_id:
        return None

    task.status = "done" if task.status != "done" else "todo"
    task.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(task)
    return _task_to_dict(task)
