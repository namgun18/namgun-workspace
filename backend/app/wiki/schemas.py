"""Wiki Pydantic schemas."""

from pydantic import BaseModel


class SpaceCreate(BaseModel):
    name: str
    slug: str
    description: str | None = None
    visibility: str = "private"
    icon: str | None = None


class SpaceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    visibility: str | None = None
    icon: str | None = None


class PageCreate(BaseModel):
    title: str
    slug: str
    content: str = ""
    parent_id: str | None = None
    sort_order: int = 0


class PageUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    parent_id: str | None = None
    sort_order: int | None = None
    is_pinned: bool | None = None


class MemberAdd(BaseModel):
    user_id: str
    role: str = "reader"  # reader, writer, admin


class MemberUpdate(BaseModel):
    role: str
