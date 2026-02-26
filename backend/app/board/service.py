"""Board business logic — board/post/comment/reaction/bookmark/must-read CRUD."""

import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Board,
    Post,
    PostBookmark,
    PostComment,
    PostReaction,
    PostReadLog,
    User,
)


# ─── Board ───

async def get_boards(db: AsyncSession) -> list[dict]:
    rows = (
        await db.execute(
            select(Board).order_by(Board.sort_order, Board.created_at)
        )
    ).scalars().all()
    return [_board_to_dict(b) for b in rows]


async def get_board(db: AsyncSession, board_id: str) -> Board | None:
    return await db.get(Board, board_id)


async def get_board_by_slug(db: AsyncSession, slug: str) -> Board | None:
    row = (
        await db.execute(select(Board).where(Board.slug == slug))
    ).scalar_one_or_none()
    return row


async def create_board(db: AsyncSession, **kwargs) -> dict:
    if "categories" in kwargs and kwargs["categories"] is not None:
        kwargs["categories"] = json.dumps(kwargs["categories"], ensure_ascii=False)
    board = Board(id=str(uuid.uuid4()), **kwargs)
    db.add(board)
    await db.commit()
    await db.refresh(board)
    return _board_to_dict(board)


async def update_board(db: AsyncSession, board_id: str, **kwargs) -> dict | None:
    board = await db.get(Board, board_id)
    if not board:
        return None
    if "categories" in kwargs and kwargs["categories"] is not None:
        kwargs["categories"] = json.dumps(kwargs["categories"], ensure_ascii=False)
    for k, v in kwargs.items():
        if v is not None:
            setattr(board, k, v)
    board.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(board)
    return _board_to_dict(board)


async def delete_board(db: AsyncSession, board_id: str) -> bool:
    board = await db.get(Board, board_id)
    if not board:
        return False
    await db.delete(board)
    await db.commit()
    return True


# ─── Post ───

async def get_posts(
    db: AsyncSession,
    board_id: str,
    page: int = 1,
    page_size: int = 20,
    category: str | None = None,
    sort: str = "latest",
) -> dict:
    """Return {pinned: [...], posts: [...], total, page, page_size}."""
    base = select(Post).where(
        Post.board_id == board_id,
        Post.is_deleted == False,  # noqa: E712
    )
    if category:
        base = base.where(Post.category == category)

    # Count total (non-pinned)
    count_q = select(func.count(Post.id)).where(
        Post.board_id == board_id,
        Post.is_deleted == False,  # noqa: E712
        Post.is_pinned == False,  # noqa: E712
    )
    if category:
        count_q = count_q.where(Post.category == category)
    total = (await db.execute(count_q)).scalar() or 0

    # Pinned posts (always returned, no pagination)
    pinned_q = base.where(Post.is_pinned == True).order_by(Post.created_at.desc())  # noqa: E712
    pinned_rows = (await db.execute(pinned_q)).scalars().all()

    # Normal posts with pagination
    if sort == "views":
        order = Post.view_count.desc()
    elif sort == "comments":
        order = Post.comment_count.desc()
    else:
        order = Post.created_at.desc()

    offset = (page - 1) * page_size
    posts_q = (
        base.where(Post.is_pinned == False)  # noqa: E712
        .order_by(order)
        .offset(offset)
        .limit(page_size)
    )
    post_rows = (await db.execute(posts_q)).scalars().all()

    # Gather author info
    all_posts = list(pinned_rows) + list(post_rows)
    author_ids = list({p.author_id for p in all_posts})
    authors = {}
    if author_ids:
        user_rows = (
            await db.execute(select(User).where(User.id.in_(author_ids)))
        ).scalars().all()
        authors = {u.id: u for u in user_rows}

    return {
        "pinned": [_post_to_summary(p, authors.get(p.author_id)) for p in pinned_rows],
        "posts": [_post_to_summary(p, authors.get(p.author_id)) for p in post_rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def get_post(
    db: AsyncSession,
    post_id: str,
    user_id: str | None = None,
) -> dict | None:
    """Get post detail with reactions and bookmark status. Increments view count."""
    post = await db.get(Post, post_id)
    if not post or post.is_deleted:
        return None

    # Increment view count
    post.view_count += 1
    await db.commit()
    await db.refresh(post)

    author = await db.get(User, post.author_id) if post.author_id else None

    # Get reactions
    reactions = await _get_post_reactions(db, post_id)

    # Check bookmark
    is_bookmarked = False
    if user_id:
        bm = (
            await db.execute(
                select(PostBookmark.id).where(
                    PostBookmark.post_id == post_id,
                    PostBookmark.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
        is_bookmarked = bm is not None

    # Mark must-read as read
    if user_id and post.is_must_read:
        existing_read = (
            await db.execute(
                select(PostReadLog.id).where(
                    PostReadLog.post_id == post_id,
                    PostReadLog.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
        if not existing_read:
            db.add(PostReadLog(
                id=str(uuid.uuid4()),
                post_id=post_id,
                user_id=user_id,
            ))
            await db.commit()

    return _post_to_detail(post, author, reactions, is_bookmarked)


async def create_post(db: AsyncSession, **kwargs) -> dict:
    if "attachments" in kwargs and kwargs["attachments"] is not None:
        kwargs["attachments"] = json.dumps(kwargs["attachments"], ensure_ascii=False)
    post = Post(id=str(uuid.uuid4()), **kwargs)
    db.add(post)
    await db.commit()
    await db.refresh(post)
    author = await db.get(User, post.author_id) if post.author_id else None
    return _post_to_detail(post, author, [], False)


async def update_post(db: AsyncSession, post_id: str, **kwargs) -> dict | None:
    post = await db.get(Post, post_id)
    if not post or post.is_deleted:
        return None
    if "attachments" in kwargs and kwargs["attachments"] is not None:
        kwargs["attachments"] = json.dumps(kwargs["attachments"], ensure_ascii=False)
    for k, v in kwargs.items():
        if v is not None:
            setattr(post, k, v)
    post.is_edited = True
    post.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(post)
    author = await db.get(User, post.author_id) if post.author_id else None
    return _post_to_detail(post, author, [], False)


async def soft_delete_post(db: AsyncSession, post_id: str) -> bool:
    post = await db.get(Post, post_id)
    if not post:
        return False
    post.is_deleted = True
    post.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return True


async def search_posts(
    db: AsyncSession,
    query: str,
    board_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    escaped = query.replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"

    base = select(Post).where(
        Post.is_deleted == False,  # noqa: E712
        (
            Post.title.ilike(pattern, escape="\\")
            | Post.content.ilike(pattern, escape="\\")
        ),
    )
    if board_id:
        base = base.where(Post.board_id == board_id)

    count_q = select(func.count(Post.id)).where(
        Post.is_deleted == False,  # noqa: E712
        (
            Post.title.ilike(pattern, escape="\\")
            | Post.content.ilike(pattern, escape="\\")
        ),
    )
    if board_id:
        count_q = count_q.where(Post.board_id == board_id)
    total = (await db.execute(count_q)).scalar() or 0

    offset = (page - 1) * page_size
    rows = (
        await db.execute(
            base.order_by(Post.created_at.desc()).offset(offset).limit(page_size)
        )
    ).scalars().all()

    author_ids = list({p.author_id for p in rows})
    authors = {}
    if author_ids:
        user_rows = (
            await db.execute(select(User).where(User.id.in_(author_ids)))
        ).scalars().all()
        authors = {u.id: u for u in user_rows}

    # Get board names
    board_ids = list({p.board_id for p in rows})
    boards = {}
    if board_ids:
        board_rows = (
            await db.execute(select(Board).where(Board.id.in_(board_ids)))
        ).scalars().all()
        boards = {b.id: b.name for b in board_rows}

    return {
        "posts": [
            {
                **_post_to_summary(p, authors.get(p.author_id)),
                "board_name": boards.get(p.board_id, ""),
            }
            for p in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ─── Comments ───

async def get_comments(db: AsyncSession, post_id: str) -> list[dict]:
    """Get comments with 2-level nesting. Deleted comments show as placeholder."""
    rows = (
        await db.execute(
            select(PostComment, User)
            .outerjoin(User, PostComment.author_id == User.id)
            .where(PostComment.post_id == post_id)
            .order_by(PostComment.created_at.asc())
        )
    ).all()

    # Build tree: parent_id → children
    comment_map: dict[str, dict] = {}
    children_map: dict[str, list[dict]] = defaultdict(list)

    for comment, user in rows:
        d = _comment_to_dict(comment, user)
        comment_map[comment.id] = d
        if comment.parent_id:
            children_map[comment.parent_id].append(d)

    # Build result: top-level comments with nested replies
    result = []
    for comment, user in rows:
        if comment.parent_id is None:
            d = comment_map[comment.id]
            d["replies"] = children_map.get(comment.id, [])
            result.append(d)

    return result


async def create_comment(
    db: AsyncSession,
    post_id: str,
    author_id: str,
    content: str,
    parent_id: str | None = None,
    attachments: str | None = None,
) -> dict:
    # Validate 2-level nesting
    if parent_id:
        parent = await db.get(PostComment, parent_id)
        if not parent:
            raise ValueError("부모 댓글을 찾을 수 없습니다")
        if parent.parent_id is not None:
            raise ValueError("대댓글에는 답글을 달 수 없습니다")

    comment = PostComment(
        id=str(uuid.uuid4()),
        post_id=post_id,
        author_id=author_id,
        parent_id=parent_id,
        content=content,
        attachments=attachments,
    )
    db.add(comment)

    # Increment comment_count
    await db.execute(
        update(Post)
        .where(Post.id == post_id)
        .values(comment_count=Post.comment_count + 1)
    )

    await db.commit()
    await db.refresh(comment)
    author = await db.get(User, author_id)
    return _comment_to_dict(comment, author)


async def update_comment(
    db: AsyncSession, comment_id: str, content: str
) -> dict | None:
    comment = await db.get(PostComment, comment_id)
    if not comment or comment.is_deleted:
        return None
    comment.content = content
    comment.is_edited = True
    comment.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(comment)
    author = await db.get(User, comment.author_id)
    return _comment_to_dict(comment, author)


async def soft_delete_comment(db: AsyncSession, comment_id: str) -> bool:
    comment = await db.get(PostComment, comment_id)
    if not comment:
        return False
    comment.is_deleted = True
    comment.content = ""
    comment.updated_at = datetime.now(timezone.utc)

    # Decrement comment_count
    await db.execute(
        update(Post)
        .where(Post.id == comment.post_id)
        .values(comment_count=func.greatest(Post.comment_count - 1, 0))
    )

    await db.commit()
    return True


# ─── Reactions ───

async def toggle_post_reaction(
    db: AsyncSession, post_id: str, user_id: str, emoji: str
) -> dict:
    existing = (
        await db.execute(
            select(PostReaction).where(
                PostReaction.post_id == post_id,
                PostReaction.user_id == user_id,
                PostReaction.emoji == emoji,
            )
        )
    ).scalar_one_or_none()

    if existing:
        await db.delete(existing)
        await db.commit()
        action = "removed"
    else:
        db.add(PostReaction(
            id=str(uuid.uuid4()),
            post_id=post_id,
            user_id=user_id,
            emoji=emoji,
        ))
        await db.commit()
        action = "added"

    reactions = await _get_post_reactions(db, post_id)
    return {
        "action": action,
        "post_id": post_id,
        "reactions": reactions,
    }


async def _get_post_reactions(
    db: AsyncSession, post_id: str
) -> list[dict]:
    rows = (
        await db.execute(
            select(PostReaction.emoji, PostReaction.user_id)
            .where(PostReaction.post_id == post_id)
            .order_by(PostReaction.emoji)
        )
    ).all()

    emoji_map: dict[str, list[str]] = defaultdict(list)
    for emoji, uid in rows:
        emoji_map[emoji].append(uid)

    return [
        {"emoji": emoji, "count": len(uids), "user_ids": uids}
        for emoji, uids in emoji_map.items()
    ]


# ─── Bookmarks ───

async def toggle_bookmark(
    db: AsyncSession, post_id: str, user_id: str
) -> dict:
    existing = (
        await db.execute(
            select(PostBookmark).where(
                PostBookmark.post_id == post_id,
                PostBookmark.user_id == user_id,
            )
        )
    ).scalar_one_or_none()

    if existing:
        await db.delete(existing)
        await db.commit()
        return {"action": "removed", "is_bookmarked": False}
    else:
        db.add(PostBookmark(
            id=str(uuid.uuid4()),
            post_id=post_id,
            user_id=user_id,
        ))
        await db.commit()
        return {"action": "added", "is_bookmarked": True}


async def get_user_bookmarks(
    db: AsyncSession, user_id: str, page: int = 1, page_size: int = 20
) -> dict:
    count_q = select(func.count(PostBookmark.id)).where(
        PostBookmark.user_id == user_id,
    )
    total = (await db.execute(count_q)).scalar() or 0

    offset = (page - 1) * page_size
    rows = (
        await db.execute(
            select(Post, PostBookmark.created_at.label("bookmarked_at"))
            .join(PostBookmark, Post.id == PostBookmark.post_id)
            .where(
                PostBookmark.user_id == user_id,
                Post.is_deleted == False,  # noqa: E712
            )
            .order_by(PostBookmark.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
    ).all()

    author_ids = list({p.author_id for p, _ in rows})
    authors = {}
    if author_ids:
        user_rows = (
            await db.execute(select(User).where(User.id.in_(author_ids)))
        ).scalars().all()
        authors = {u.id: u for u in user_rows}

    return {
        "posts": [_post_to_summary(p, authors.get(p.author_id)) for p, _ in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ─── Must Read ───

async def get_must_read_posts(db: AsyncSession, user_id: str) -> list[dict]:
    """Get must-read posts the user hasn't read yet."""
    now = datetime.now(timezone.utc)

    # Subquery: posts user has already read
    read_sq = select(PostReadLog.post_id).where(
        PostReadLog.user_id == user_id
    ).subquery()

    rows = (
        await db.execute(
            select(Post)
            .where(
                Post.is_must_read == True,  # noqa: E712
                Post.is_deleted == False,  # noqa: E712
                Post.id.notin_(select(read_sq.c.post_id)),
                (Post.must_read_expires_at == None) | (Post.must_read_expires_at > now),  # noqa: E711
            )
            .order_by(Post.created_at.desc())
        )
    ).scalars().all()

    author_ids = list({p.author_id for p in rows})
    authors = {}
    if author_ids:
        user_rows = (
            await db.execute(select(User).where(User.id.in_(author_ids)))
        ).scalars().all()
        authors = {u.id: u for u in user_rows}

    return [_post_to_summary(p, authors.get(p.author_id)) for p in rows]


# ─── Helpers ───

def _board_to_dict(board: Board) -> dict:
    categories = []
    if board.categories:
        try:
            categories = json.loads(board.categories)
        except (json.JSONDecodeError, TypeError):
            pass
    return {
        "id": board.id,
        "name": board.name,
        "slug": board.slug,
        "description": board.description,
        "categories": categories,
        "sort_order": board.sort_order,
        "write_permission": board.write_permission,
        "notice_permission": board.notice_permission,
        "comment_permission": board.comment_permission,
        "allow_comments": board.allow_comments,
        "allow_reactions": board.allow_reactions,
        "created_at": board.created_at.isoformat(),
        "updated_at": board.updated_at.isoformat(),
    }


def _author_info(user: User | None) -> dict | None:
    if not user:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
    }


def _post_to_summary(post: Post, author: User | None) -> dict:
    attachments = []
    if post.attachments:
        try:
            attachments = json.loads(post.attachments)
        except (json.JSONDecodeError, TypeError):
            pass
    return {
        "id": post.id,
        "board_id": post.board_id,
        "author": _author_info(author),
        "title": post.title,
        "category": post.category,
        "is_pinned": post.is_pinned,
        "is_must_read": post.is_must_read,
        "view_count": post.view_count,
        "comment_count": post.comment_count,
        "has_attachments": len(attachments) > 0,
        "is_edited": post.is_edited,
        "created_at": post.created_at.isoformat(),
        "updated_at": post.updated_at.isoformat(),
    }


def _post_to_detail(
    post: Post,
    author: User | None,
    reactions: list[dict],
    is_bookmarked: bool,
) -> dict:
    attachments = []
    if post.attachments:
        try:
            attachments = json.loads(post.attachments)
        except (json.JSONDecodeError, TypeError):
            pass
    return {
        "id": post.id,
        "board_id": post.board_id,
        "author": _author_info(author),
        "title": post.title,
        "content": post.content,
        "category": post.category,
        "is_pinned": post.is_pinned,
        "is_must_read": post.is_must_read,
        "must_read_expires_at": post.must_read_expires_at.isoformat() if post.must_read_expires_at else None,
        "view_count": post.view_count,
        "comment_count": post.comment_count,
        "attachments": attachments,
        "reactions": reactions,
        "is_bookmarked": is_bookmarked,
        "is_edited": post.is_edited,
        "created_at": post.created_at.isoformat(),
        "updated_at": post.updated_at.isoformat(),
    }


def _comment_to_dict(comment: PostComment, author: User | None) -> dict:
    if comment.is_deleted:
        return {
            "id": comment.id,
            "post_id": comment.post_id,
            "author": None,
            "parent_id": comment.parent_id,
            "content": "[삭제된 댓글입니다]",
            "attachments": [],
            "is_edited": False,
            "is_deleted": True,
            "created_at": comment.created_at.isoformat(),
            "updated_at": comment.updated_at.isoformat(),
        }

    attachments = []
    if comment.attachments:
        try:
            attachments = json.loads(comment.attachments)
        except (json.JSONDecodeError, TypeError):
            pass
    return {
        "id": comment.id,
        "post_id": comment.post_id,
        "author": _author_info(author),
        "parent_id": comment.parent_id,
        "content": comment.content,
        "attachments": attachments,
        "is_edited": comment.is_edited,
        "is_deleted": False,
        "created_at": comment.created_at.isoformat(),
        "updated_at": comment.updated_at.isoformat(),
    }
