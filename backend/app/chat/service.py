"""Chat business logic — channel/message/member CRUD."""

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Channel, ChannelMember, Message, User


# ─── Channel ───

async def create_channel(
    db: AsyncSession,
    name: str,
    type: str,
    created_by: str,
    description: str | None = None,
    member_ids: list[str] | None = None,
) -> Channel:
    channel = Channel(
        id=str(uuid.uuid4()),
        name=name,
        type=type,
        description=description,
        created_by=created_by,
    )
    db.add(channel)

    # Add creator as owner
    db.add(ChannelMember(
        id=str(uuid.uuid4()),
        channel_id=channel.id,
        user_id=created_by,
        role="owner",
    ))

    # Add extra members
    if member_ids:
        for uid in member_ids:
            if uid != created_by:
                db.add(ChannelMember(
                    id=str(uuid.uuid4()),
                    channel_id=channel.id,
                    user_id=uid,
                    role="member",
                ))

    # System message
    db.add(Message(
        id=str(uuid.uuid4()),
        channel_id=channel.id,
        sender_id=None,
        content="채널이 생성되었습니다.",
        message_type="system",
    ))

    await db.commit()
    await db.refresh(channel)
    return channel


async def get_user_channels(db: AsyncSession, user_id: str) -> list[dict]:
    """Get channels the user is a member of, with unread counts."""
    # Subquery: member's last_read_message_id
    member_sq = (
        select(ChannelMember.channel_id, ChannelMember.last_read_message_id)
        .where(ChannelMember.user_id == user_id)
        .subquery()
    )

    # Subquery: member count per channel
    count_sq = (
        select(
            ChannelMember.channel_id,
            func.count(ChannelMember.id).label("member_count"),
        )
        .group_by(ChannelMember.channel_id)
        .subquery()
    )

    rows = (
        await db.execute(
            select(Channel, member_sq.c.last_read_message_id, count_sq.c.member_count)
            .join(member_sq, Channel.id == member_sq.c.channel_id)
            .outerjoin(count_sq, Channel.id == count_sq.c.channel_id)
            .where(Channel.is_archived == False)  # noqa: E712
            .order_by(Channel.created_at)
        )
    ).all()

    result = []
    for ch, last_read_id, member_count in rows:
        # Count unread messages
        unread_q = select(func.count(Message.id)).where(
            Message.channel_id == ch.id,
            Message.is_deleted == False,  # noqa: E712
        )
        if last_read_id:
            # Messages created after last_read message
            last_read_msg = await db.get(Message, last_read_id)
            if last_read_msg:
                unread_q = unread_q.where(Message.created_at > last_read_msg.created_at)
        unread = (await db.execute(unread_q)).scalar() or 0

        result.append({
            "id": ch.id,
            "name": ch.name,
            "type": ch.type,
            "description": ch.description,
            "created_by": ch.created_by,
            "is_archived": ch.is_archived,
            "created_at": ch.created_at,
            "updated_at": ch.updated_at,
            "member_count": member_count or 0,
            "unread_count": unread,
        })
    return result


async def get_channel(db: AsyncSession, channel_id: str) -> Channel | None:
    return await db.get(Channel, channel_id)


async def update_channel(
    db: AsyncSession, channel_id: str, **kwargs
) -> Channel | None:
    ch = await db.get(Channel, channel_id)
    if not ch:
        return None
    for k, v in kwargs.items():
        if v is not None:
            setattr(ch, k, v)
    ch.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(ch)
    return ch


async def delete_channel(db: AsyncSession, channel_id: str) -> bool:
    ch = await db.get(Channel, channel_id)
    if not ch:
        return False
    await db.delete(ch)
    await db.commit()
    return True


# ─── Members ───

async def get_channel_members(db: AsyncSession, channel_id: str) -> list[dict]:
    rows = (
        await db.execute(
            select(ChannelMember, User)
            .join(User, ChannelMember.user_id == User.id)
            .where(ChannelMember.channel_id == channel_id)
            .order_by(ChannelMember.joined_at)
        )
    ).all()
    return [
        {
            "user_id": u.id,
            "username": u.username,
            "display_name": u.display_name,
            "avatar_url": u.avatar_url,
            "role": cm.role,
        }
        for cm, u in rows
    ]


async def add_members(
    db: AsyncSession, channel_id: str, user_ids: list[str]
) -> list[str]:
    added = []
    for uid in user_ids:
        # Check already member
        existing = (
            await db.execute(
                select(ChannelMember).where(
                    ChannelMember.channel_id == channel_id,
                    ChannelMember.user_id == uid,
                )
            )
        ).scalar_one_or_none()
        if existing:
            continue
        db.add(ChannelMember(
            id=str(uuid.uuid4()),
            channel_id=channel_id,
            user_id=uid,
            role="member",
        ))
        added.append(uid)
    if added:
        await db.commit()
    return added


async def remove_member(
    db: AsyncSession, channel_id: str, user_id: str
) -> bool:
    result = await db.execute(
        delete(ChannelMember).where(
            ChannelMember.channel_id == channel_id,
            ChannelMember.user_id == user_id,
        )
    )
    await db.commit()
    return result.rowcount > 0


async def is_channel_member(
    db: AsyncSession, channel_id: str, user_id: str
) -> bool:
    row = (
        await db.execute(
            select(ChannelMember.id).where(
                ChannelMember.channel_id == channel_id,
                ChannelMember.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    return row is not None


async def get_member_role(
    db: AsyncSession, channel_id: str, user_id: str
) -> str | None:
    row = (
        await db.execute(
            select(ChannelMember.role).where(
                ChannelMember.channel_id == channel_id,
                ChannelMember.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    return row


# ─── Messages ───

async def create_message(
    db: AsyncSession,
    channel_id: str,
    sender_id: str,
    content: str,
    message_type: str = "text",
    file_meta: str | None = None,
) -> dict:
    msg = Message(
        id=str(uuid.uuid4()),
        channel_id=channel_id,
        sender_id=sender_id,
        content=content,
        message_type=message_type,
        file_meta=file_meta,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    # Fetch sender info
    sender = await db.get(User, sender_id)
    return _message_to_dict(msg, sender)


async def get_messages(
    db: AsyncSession,
    channel_id: str,
    before: str | None = None,
    after: str | None = None,
    limit: int = 50,
) -> tuple[list[dict], bool]:
    q = (
        select(Message, User)
        .outerjoin(User, Message.sender_id == User.id)
        .where(
            Message.channel_id == channel_id,
            Message.is_deleted == False,  # noqa: E712
        )
    )

    if before:
        ref = await db.get(Message, before)
        if ref:
            q = q.where(Message.created_at < ref.created_at)

    if after:
        ref = await db.get(Message, after)
        if ref:
            q = q.where(Message.created_at > ref.created_at)

    if after:
        q = q.order_by(Message.created_at.asc())
    else:
        q = q.order_by(Message.created_at.desc())

    q = q.limit(limit + 1)
    rows = (await db.execute(q)).all()

    has_more = len(rows) > limit
    rows = rows[:limit]

    if not after:
        rows = list(reversed(rows))

    return [_message_to_dict(msg, user) for msg, user in rows], has_more


async def update_message(
    db: AsyncSession, message_id: str, content: str
) -> dict | None:
    msg = await db.get(Message, message_id)
    if not msg:
        return None
    msg.content = content
    msg.is_edited = True
    msg.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(msg)
    sender = await db.get(User, msg.sender_id) if msg.sender_id else None
    return _message_to_dict(msg, sender)


async def soft_delete_message(
    db: AsyncSession, message_id: str
) -> bool:
    msg = await db.get(Message, message_id)
    if not msg:
        return False
    msg.is_deleted = True
    msg.content = ""
    msg.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return True


async def mark_read(
    db: AsyncSession, channel_id: str, user_id: str, message_id: str
) -> None:
    await db.execute(
        update(ChannelMember)
        .where(
            ChannelMember.channel_id == channel_id,
            ChannelMember.user_id == user_id,
        )
        .values(last_read_message_id=message_id)
    )
    await db.commit()


# ─── DM ───

async def get_or_create_dm(
    db: AsyncSession, user_id: str, other_user_id: str
) -> Channel:
    """Find existing DM channel between two users, or create one."""
    # Find channels where both users are members and type is dm
    my_channels = select(ChannelMember.channel_id).where(
        ChannelMember.user_id == user_id
    ).subquery()
    their_channels = select(ChannelMember.channel_id).where(
        ChannelMember.user_id == other_user_id
    ).subquery()

    row = (
        await db.execute(
            select(Channel)
            .where(
                Channel.type == "dm",
                Channel.id.in_(select(my_channels.c.channel_id)),
                Channel.id.in_(select(their_channels.c.channel_id)),
            )
            .limit(1)
        )
    ).scalar_one_or_none()

    if row:
        return row

    # Create new DM
    other = await db.get(User, other_user_id)
    me = await db.get(User, user_id)
    dm_name = f"{me.username},{other.username}" if me and other else "DM"

    channel = Channel(
        id=str(uuid.uuid4()),
        name=dm_name,
        type="dm",
        created_by=user_id,
    )
    db.add(channel)
    db.add(ChannelMember(
        id=str(uuid.uuid4()), channel_id=channel.id,
        user_id=user_id, role="member",
    ))
    db.add(ChannelMember(
        id=str(uuid.uuid4()), channel_id=channel.id,
        user_id=other_user_id, role="member",
    ))
    await db.commit()
    await db.refresh(channel)
    return channel


# ─── User Search ───

async def search_users(
    db: AsyncSession, query: str | None = None, limit: int = 50
) -> list[dict]:
    q = select(User).where(User.is_active == True)  # noqa: E712
    if query:
        q = q.where(
            (User.username.ilike(f"%{query}%"))
            | (User.display_name.ilike(f"%{query}%"))
        )
    q = q.order_by(User.display_name, User.username).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "display_name": u.display_name,
            "avatar_url": u.avatar_url,
        }
        for u in rows
    ]


# ─── Helpers ───

def _message_to_dict(msg: Message, sender: User | None) -> dict:
    return {
        "id": msg.id,
        "channel_id": msg.channel_id,
        "sender": {
            "id": sender.id,
            "username": sender.username,
            "display_name": sender.display_name,
            "avatar_url": sender.avatar_url,
        } if sender else None,
        "content": msg.content,
        "message_type": msg.message_type,
        "file_meta": msg.file_meta,
        "is_edited": msg.is_edited,
        "is_deleted": msg.is_deleted,
        "created_at": msg.created_at.isoformat(),
        "updated_at": msg.updated_at.isoformat(),
    }
