"""Tasks API schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    title: str = Field(..., max_length=500)
    description: str | None = None
    due_date: datetime | None = None
    priority: str = Field("medium", pattern="^(low|medium|high)$")
    status: str = Field("todo", pattern="^(todo|in_progress|done)$")
    calendar_event_id: str | None = None
    sort_order: int = 0


class TaskUpdate(BaseModel):
    title: str | None = Field(None, max_length=500)
    description: str | None = None
    due_date: datetime | None = None
    priority: str | None = Field(None, pattern="^(low|medium|high)$")
    status: str | None = Field(None, pattern="^(todo|in_progress|done)$")
    calendar_event_id: str | None = None
    sort_order: int | None = None


class TaskResponse(BaseModel):
    id: str
    user_id: str
    title: str
    description: str | None = None
    due_date: datetime | None = None
    priority: str
    status: str
    calendar_event_id: str | None = None
    sort_order: int
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    total: int = 0
