"""Board Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


# ─── Board ───

class BoardCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9\-]+$")
    description: str | None = Field(None, max_length=500)
    categories: list[str] | None = None
    write_permission: str = Field("all", pattern=r"^(all|admin)$")
    notice_permission: str = Field("admin", pattern=r"^(all|admin)$")
    comment_permission: str = Field("all", pattern=r"^(all|admin)$")
    allow_comments: bool = True
    allow_reactions: bool = True


class BoardUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    categories: list[str] | None = None
    sort_order: int | None = None
    write_permission: str | None = Field(None, pattern=r"^(all|admin)$")
    notice_permission: str | None = Field(None, pattern=r"^(all|admin)$")
    comment_permission: str | None = Field(None, pattern=r"^(all|admin)$")
    allow_comments: bool | None = None
    allow_reactions: bool | None = None


# ─── Post ───

class PostCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    category: str | None = Field(None, max_length=50)
    is_pinned: bool = False
    is_must_read: bool = False
    must_read_expires_at: datetime | None = None
    attachments: list[dict] | None = None


class PostUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    content: str | None = None
    category: str | None = None
    is_pinned: bool | None = None
    is_must_read: bool | None = None
    must_read_expires_at: datetime | None = None
    attachments: list[dict] | None = None


# ─── Comment ───

class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    parent_id: str | None = None
    attachments: list[dict] | None = None


class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


# ─── Reaction ───

class ReactionToggle(BaseModel):
    emoji: str = Field(..., max_length=10)
