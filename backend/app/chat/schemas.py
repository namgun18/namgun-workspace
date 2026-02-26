"""Chat Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


# ─── Channel ───

class ChannelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field("public", pattern=r"^(public|private)$")
    description: str | None = Field(None, max_length=500)
    member_ids: list[str] = Field(default_factory=list)


class ChannelUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    is_archived: bool | None = None


class ChannelResponse(BaseModel):
    id: str
    name: str
    type: str
    description: str | None
    created_by: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    member_count: int = 0
    unread_count: int = 0


# ─── Message ───

class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    message_type: str = Field("text", pattern=r"^(text|file|system)$")
    file_meta: str | None = None
    parent_id: str | None = None


class MessageUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


class MessageSender(BaseModel):
    id: str
    username: str
    display_name: str | None
    avatar_url: str | None


class MessageResponse(BaseModel):
    id: str
    channel_id: str
    sender: MessageSender | None
    content: str
    message_type: str
    file_meta: str | None
    parent_id: str | None = None
    reply_count: int = 0
    is_edited: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class MessageListResponse(BaseModel):
    messages: list[MessageResponse]
    has_more: bool


# ─── Member ───

class MemberAdd(BaseModel):
    user_ids: list[str] = Field(..., min_length=1)


# ─── DM ───

class DMRequest(BaseModel):
    user_id: str


# ─── Notifications ───

# ─── Reactions ───

class ReactionToggle(BaseModel):
    emoji: str = Field(..., max_length=10)


class NotificationReadRequest(BaseModel):
    notification_ids: list[str] | None = None
