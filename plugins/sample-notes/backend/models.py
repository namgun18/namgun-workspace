"""Note model for the sample-notes plugin."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class PluginBase(DeclarativeBase):
    pass


class Note(PluginBase):
    __tablename__ = "plugin_notes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_plugin_notes_user_created", "user_id", "created_at"),
    )
