"""Chat business logic — channel/message/member CRUD."""

import json
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Channel, ChannelMember, Message, Notification, Reaction, User


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
    sender_id: str | None,
    content: str,
    message_type: str = "text",
    file_meta: str | None = None,
    parent_id: str | None = None,
) -> dict:
    msg = Message(
        id=str(uuid.uuid4()),
        channel_id=channel_id,
        sender_id=sender_id,
        content=content,
        message_type=message_type,
        file_meta=file_meta,
        parent_id=parent_id,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    # Fetch sender info
    sender = await db.get(User, sender_id) if sender_id else None
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
            Message.parent_id == None,  # noqa: E711 — exclude thread replies from main view
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

    # Build read_by map: member → last_read created_at
    read_by_map = await _build_read_by_map(db, channel_id)

    # Get reply counts for these messages
    msg_ids = [msg.id for msg, _ in rows]
    reply_counts = await get_thread_reply_count(db, msg_ids)

    # Get reactions for these messages
    reactions_map = await get_reactions_for_messages(db, msg_ids)

    result = []
    for msg, user in rows:
        d = _message_to_dict(msg, user)
        d["reply_count"] = reply_counts.get(msg.id, 0)
        d["reactions"] = reactions_map.get(msg.id, [])
        # Compute who has read this message (exclude sender)
        readers = []
        for member_info, read_up_to in read_by_map:
            if read_up_to and read_up_to >= msg.created_at:
                if member_info["id"] != (msg.sender_id or ""):
                    readers.append(member_info)
        d["read_by"] = readers
        result.append(d)

    return result, has_more


async def _build_read_by_map(
    db: AsyncSession, channel_id: str
) -> list[tuple[dict, datetime | None]]:
    """Return [(user_info_dict, last_read_created_at), ...] for all channel members."""
    member_rows = (
        await db.execute(
            select(ChannelMember, User)
            .join(User, ChannelMember.user_id == User.id)
            .where(ChannelMember.channel_id == channel_id)
        )
    ).all()

    result = []
    for cm, u in member_rows:
        read_ts = None
        if cm.last_read_message_id:
            last_msg = await db.get(Message, cm.last_read_message_id)
            if last_msg:
                read_ts = last_msg.created_at
        result.append((
            {
                "id": u.id,
                "username": u.username,
                "display_name": u.display_name,
                "avatar_url": u.avatar_url,
            },
            read_ts,
        ))
    return result


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
            (User.username.ilike(f"%{query.replace('%', '\\%').replace('_', '\\_')}%", escape='\\'))
            | (User.display_name.ilike(f"%{query.replace('%', '\\%').replace('_', '\\_')}%", escape='\\'))
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


# ─── Message Search ───

async def search_messages(
    db: AsyncSession,
    user_id: str,
    query: str,
    channel_id: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Search messages the user has access to."""
    # Get user's channel IDs
    user_channels_q = select(ChannelMember.channel_id).where(
        ChannelMember.user_id == user_id
    )

    q = (
        select(Message, User, Channel)
        .outerjoin(User, Message.sender_id == User.id)
        .join(Channel, Message.channel_id == Channel.id)
        .where(
            Message.channel_id.in_(user_channels_q),
            Message.is_deleted == False,  # noqa: E712
            Message.content.ilike(f"%{query.replace('%', '\\%').replace('_', '\\_')}%", escape='\\'),
        )
    )

    if channel_id:
        q = q.where(Message.channel_id == channel_id)

    q = q.order_by(Message.created_at.desc()).limit(limit)
    rows = (await db.execute(q)).all()

    return [
        {
            **_message_to_dict(msg, user),
            "channel_name": ch.name,
            "channel_type": ch.type,
        }
        for msg, user, ch in rows
    ]


# ─── Mentions & Notifications ───

MENTION_RE = re.compile(r'(?:^|(?<=\s))@(\w+)')


def parse_mentions(content: str) -> list[str]:
    """Extract unique usernames from @mentions in message content."""
    return list(dict.fromkeys(MENTION_RE.findall(content)))


async def create_notifications_for_mentions(
    db: AsyncSession,
    msg_dict: dict,
    channel_id: str,
    sender_id: str,
    usernames: list[str],
) -> list[dict]:
    """Create Notification rows for valid mentions. Returns list of notification dicts."""
    if not usernames:
        return []

    # Get channel member user IDs
    member_rows = (
        await db.execute(
            select(ChannelMember.user_id).where(ChannelMember.channel_id == channel_id)
        )
    ).scalars().all()
    member_ids = set(member_rows)

    # Look up mentioned users by username
    mentioned_users = (
        await db.execute(
            select(User).where(
                User.username.in_(usernames),
                User.is_active == True,  # noqa: E712
            )
        )
    ).scalars().all()

    sender = await db.get(User, sender_id)
    sender_name = (sender.display_name or sender.username) if sender else "알 수 없음"

    notifications = []
    for u in mentioned_users:
        # Skip sender, skip non-members
        if u.id == sender_id or u.id not in member_ids:
            continue

        notif = Notification(
            id=str(uuid.uuid4()),
            user_id=u.id,
            type="mention",
            title=f"{sender_name}님이 회원님을 멘션했습니다",
            body=msg_dict.get("content", "")[:200],
            link=f"/chat?channel={channel_id}",
        )
        db.add(notif)
        notifications.append({
            "id": notif.id,
            "user_id": notif.user_id,
            "type": notif.type,
            "title": notif.title,
            "body": notif.body,
            "link": notif.link,
            "is_read": False,
            "created_at": notif.created_at.isoformat() if notif.created_at else datetime.now(timezone.utc).isoformat(),
        })

    if notifications:
        await db.commit()

    return notifications


async def get_notifications(
    db: AsyncSession,
    user_id: str,
    limit: int = 50,
    unread_only: bool = False,
) -> list[dict]:
    q = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        q = q.where(Notification.is_read == False)  # noqa: E712
    q = q.order_by(Notification.created_at.desc()).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": n.id,
            "user_id": n.user_id,
            "type": n.type,
            "title": n.title,
            "body": n.body,
            "link": n.link,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat(),
        }
        for n in rows
    ]


async def get_unread_notification_count(db: AsyncSession, user_id: str) -> int:
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read == False,  # noqa: E712
        )
    )
    return result.scalar() or 0


async def mark_notifications_read(
    db: AsyncSession,
    user_id: str,
    notification_ids: list[str] | None = None,
) -> int:
    q = (
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.is_read == False,  # noqa: E712
        )
        .values(is_read=True)
    )
    if notification_ids:
        q = q.where(Notification.id.in_(notification_ids))
    result = await db.execute(q)
    await db.commit()
    return result.rowcount


# ─── Threads ───

async def get_thread_reply_count(
    db: AsyncSession, message_ids: list[str]
) -> dict[str, int]:
    """Return {parent_id: reply_count} for the given message IDs."""
    if not message_ids:
        return {}
    rows = (
        await db.execute(
            select(Message.parent_id, func.count(Message.id))
            .where(
                Message.parent_id.in_(message_ids),
                Message.is_deleted == False,  # noqa: E712
            )
            .group_by(Message.parent_id)
        )
    ).all()
    return {pid: cnt for pid, cnt in rows}


async def get_thread_messages(
    db: AsyncSession, parent_id: str, limit: int = 100
) -> list[dict]:
    """Get replies to a parent message, oldest first."""
    rows = (
        await db.execute(
            select(Message, User)
            .outerjoin(User, Message.sender_id == User.id)
            .where(
                Message.parent_id == parent_id,
                Message.is_deleted == False,  # noqa: E712
            )
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
    ).all()

    msg_ids = [msg.id for msg, _ in rows]
    reactions_map = await get_reactions_for_messages(db, msg_ids)

    result = []
    for msg, user in rows:
        d = _message_to_dict(msg, user)
        d["reply_count"] = 0
        d["reactions"] = reactions_map.get(msg.id, [])
        result.append(d)
    return result


# ─── Reactions ───

async def toggle_reaction(
    db: AsyncSession, message_id: str, user_id: str, emoji: str
) -> dict:
    """Toggle a reaction: add if not exists, remove if exists. Returns action and reaction state."""
    existing = (
        await db.execute(
            select(Reaction).where(
                Reaction.message_id == message_id,
                Reaction.user_id == user_id,
                Reaction.emoji == emoji,
            )
        )
    ).scalar_one_or_none()

    if existing:
        await db.delete(existing)
        await db.commit()
        action = "removed"
    else:
        db.add(Reaction(
            id=str(uuid.uuid4()),
            message_id=message_id,
            user_id=user_id,
            emoji=emoji,
        ))
        await db.commit()
        action = "added"

    # Return current reaction state for this message
    reactions = await get_reactions_for_messages(db, [message_id])
    return {
        "action": action,
        "message_id": message_id,
        "reactions": reactions.get(message_id, []),
    }


async def get_reactions_for_messages(
    db: AsyncSession, message_ids: list[str]
) -> dict[str, list[dict]]:
    """Return {message_id: [{emoji, count, user_ids}]} for the given message IDs."""
    if not message_ids:
        return {}
    rows = (
        await db.execute(
            select(Reaction.message_id, Reaction.emoji, Reaction.user_id)
            .where(Reaction.message_id.in_(message_ids))
            .order_by(Reaction.emoji)
        )
    ).all()

    # Group by message_id → emoji → user_ids
    from collections import defaultdict
    msg_emoji_map: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for mid, emoji, uid in rows:
        msg_emoji_map[mid][emoji].append(uid)

    result: dict[str, list[dict]] = {}
    for mid, emojis in msg_emoji_map.items():
        result[mid] = [
            {"emoji": emoji, "count": len(uids), "user_ids": uids}
            for emoji, uids in emojis.items()
        ]
    return result


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
        "parent_id": msg.parent_id,
        "is_edited": msg.is_edited,
        "is_deleted": msg.is_deleted,
        "created_at": msg.created_at.isoformat(),
        "updated_at": msg.updated_at.isoformat(),
    }
