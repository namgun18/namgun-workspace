"""Wiki business logic — space/page CRUD, versioning, access control."""

import re
from datetime import datetime, timezone

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    User, WikiPage, WikiPageVersion, WikiSpace, WikiSpaceMember,
)


def _slugify(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text.lower().strip())
    return re.sub(r"[-\s]+", "-", s) or "untitled"


# ─── Space ───


async def get_spaces(db: AsyncSession, user_id: str) -> list[dict]:
    """Return all spaces the user can see (public + member of)."""
    result = await db.execute(
        select(WikiSpace, User.username, User.display_name, User.avatar_url)
        .outerjoin(User, WikiSpace.owner_id == User.id)
        .where(
            (WikiSpace.visibility == "public")
            | (WikiSpace.owner_id == user_id)
            | (WikiSpace.id.in_(
                select(WikiSpaceMember.space_id)
                .where(WikiSpaceMember.user_id == user_id)
            ))
        )
        .order_by(WikiSpace.name)
    )
    rows = result.all()
    spaces = []
    for space, username, display, avatar in rows:
        page_count = await db.scalar(
            select(func.count(WikiPage.id)).where(WikiPage.space_id == space.id)
        )
        spaces.append({
            "id": space.id,
            "name": space.name,
            "slug": space.slug,
            "description": space.description,
            "visibility": space.visibility,
            "icon": space.icon,
            "owner": {"id": space.owner_id, "username": username, "display_name": display, "avatar_url": avatar},
            "page_count": page_count or 0,
            "created_at": space.created_at.isoformat(),
            "updated_at": space.updated_at.isoformat(),
        })
    return spaces


async def get_space(db: AsyncSession, space_id: str) -> WikiSpace | None:
    return (await db.execute(
        select(WikiSpace).where(WikiSpace.id == space_id)
    )).scalar_one_or_none()


async def get_space_by_slug(db: AsyncSession, slug: str) -> WikiSpace | None:
    return (await db.execute(
        select(WikiSpace).where(WikiSpace.slug == slug)
    )).scalar_one_or_none()


async def create_space(db: AsyncSession, owner_id: str, **kwargs) -> dict:
    space = WikiSpace(owner_id=owner_id, **kwargs)
    db.add(space)
    await db.commit()
    await db.refresh(space)
    return {"id": space.id, "name": space.name, "slug": space.slug}


async def update_space(db: AsyncSession, space_id: str, **kwargs) -> bool:
    data = {k: v for k, v in kwargs.items() if v is not None}
    if not data:
        return True
    await db.execute(update(WikiSpace).where(WikiSpace.id == space_id).values(**data))
    await db.commit()
    return True


async def delete_space(db: AsyncSession, space_id: str) -> bool:
    await db.execute(delete(WikiSpace).where(WikiSpace.id == space_id))
    await db.commit()
    return True


# ─── Access control ───


async def get_user_role(db: AsyncSession, space_id: str, user_id: str) -> str | None:
    """Return user's role in a space. Owner gets 'admin'. None if no access."""
    space = await get_space(db, space_id)
    if not space:
        return None
    if space.owner_id == user_id:
        return "admin"
    member = (await db.execute(
        select(WikiSpaceMember).where(
            WikiSpaceMember.space_id == space_id,
            WikiSpaceMember.user_id == user_id,
        )
    )).scalar_one_or_none()
    if member:
        return member.role
    if space.visibility == "public":
        return "reader"
    return None


async def add_member(db: AsyncSession, space_id: str, user_id: str, role: str = "reader"):
    member = WikiSpaceMember(space_id=space_id, user_id=user_id, role=role)
    db.add(member)
    await db.commit()


async def update_member(db: AsyncSession, space_id: str, user_id: str, role: str):
    await db.execute(
        update(WikiSpaceMember)
        .where(WikiSpaceMember.space_id == space_id, WikiSpaceMember.user_id == user_id)
        .values(role=role)
    )
    await db.commit()


async def remove_member(db: AsyncSession, space_id: str, user_id: str):
    await db.execute(
        delete(WikiSpaceMember)
        .where(WikiSpaceMember.space_id == space_id, WikiSpaceMember.user_id == user_id)
    )
    await db.commit()


async def get_members(db: AsyncSession, space_id: str) -> list[dict]:
    result = await db.execute(
        select(WikiSpaceMember, User.username, User.display_name, User.avatar_url)
        .outerjoin(User, WikiSpaceMember.user_id == User.id)
        .where(WikiSpaceMember.space_id == space_id)
    )
    return [
        {
            "user_id": m.user_id,
            "role": m.role,
            "username": username,
            "display_name": display,
            "avatar_url": avatar,
        }
        for m, username, display, avatar in result.all()
    ]


# ─── Pages ───


async def get_page_tree(db: AsyncSession, space_id: str) -> list[dict]:
    """Return flat list of pages for building a tree on the client."""
    result = await db.execute(
        select(WikiPage, User.username, User.display_name)
        .outerjoin(User, WikiPage.author_id == User.id)
        .where(WikiPage.space_id == space_id)
        .order_by(WikiPage.sort_order, WikiPage.title)
    )
    return [
        {
            "id": p.id,
            "parent_id": p.parent_id,
            "title": p.title,
            "slug": p.slug,
            "sort_order": p.sort_order,
            "is_pinned": p.is_pinned,
            "version": p.version,
            "author": {"username": username, "display_name": display},
            "updated_at": p.updated_at.isoformat(),
        }
        for p, username, display in result.all()
    ]


async def get_page(db: AsyncSession, page_id: str) -> dict | None:
    result = await db.execute(
        select(WikiPage, User.username, User.display_name, User.avatar_url)
        .outerjoin(User, WikiPage.author_id == User.id)
        .where(WikiPage.id == page_id)
    )
    row = result.first()
    if not row:
        return None
    p, username, display, avatar = row
    return {
        "id": p.id,
        "space_id": p.space_id,
        "parent_id": p.parent_id,
        "title": p.title,
        "slug": p.slug,
        "content": p.content,
        "sort_order": p.sort_order,
        "is_pinned": p.is_pinned,
        "version": p.version,
        "author": {"id": p.author_id, "username": username, "display_name": display, "avatar_url": avatar},
        "created_at": p.created_at.isoformat(),
        "updated_at": p.updated_at.isoformat(),
    }


async def create_page(db: AsyncSession, space_id: str, author_id: str, **kwargs) -> dict:
    page = WikiPage(space_id=space_id, author_id=author_id, **kwargs)
    db.add(page)
    await db.commit()
    await db.refresh(page)
    # Save initial version
    v = WikiPageVersion(
        page_id=page.id,
        title=page.title,
        content=page.content,
        author_id=author_id,
        version_number=1,
    )
    db.add(v)
    await db.commit()
    return await get_page(db, page.id)


async def update_page(db: AsyncSession, page_id: str, editor_id: str, **kwargs) -> dict | None:
    data = {k: v for k, v in kwargs.items() if v is not None}
    if not data:
        return await get_page(db, page_id)

    # Get current page for versioning
    page = (await db.execute(
        select(WikiPage).where(WikiPage.id == page_id)
    )).scalar_one_or_none()
    if not page:
        return None

    content_changed = "content" in data or "title" in data
    if content_changed:
        new_version = page.version + 1
        data["version"] = new_version
        data["author_id"] = editor_id

    await db.execute(update(WikiPage).where(WikiPage.id == page_id).values(**data))
    await db.commit()

    # Save version snapshot
    if content_changed:
        await db.refresh(page)
        v = WikiPageVersion(
            page_id=page_id,
            title=data.get("title", page.title),
            content=data.get("content", page.content),
            author_id=editor_id,
            version_number=data.get("version", page.version),
        )
        db.add(v)
        await db.commit()

    return await get_page(db, page_id)


async def delete_page(db: AsyncSession, page_id: str) -> bool:
    # Re-parent children to the deleted page's parent
    page = (await db.execute(
        select(WikiPage).where(WikiPage.id == page_id)
    )).scalar_one_or_none()
    if not page:
        return False
    await db.execute(
        update(WikiPage).where(WikiPage.parent_id == page_id).values(parent_id=page.parent_id)
    )
    await db.execute(delete(WikiPage).where(WikiPage.id == page_id))
    await db.commit()
    return True


async def get_page_versions(db: AsyncSession, page_id: str) -> list[dict]:
    result = await db.execute(
        select(WikiPageVersion, User.username, User.display_name)
        .outerjoin(User, WikiPageVersion.author_id == User.id)
        .where(WikiPageVersion.page_id == page_id)
        .order_by(WikiPageVersion.version_number.desc())
    )
    return [
        {
            "id": v.id,
            "version_number": v.version_number,
            "title": v.title,
            "content": v.content,
            "author": {"username": username, "display_name": display},
            "created_at": v.created_at.isoformat(),
        }
        for v, username, display in result.all()
    ]


async def search_pages(db: AsyncSession, space_id: str, query: str) -> list[dict]:
    """Simple ILIKE search on title and content."""
    pattern = f"%{query}%"
    result = await db.execute(
        select(WikiPage)
        .where(
            WikiPage.space_id == space_id,
            (WikiPage.title.ilike(pattern) | WikiPage.content.ilike(pattern)),
        )
        .order_by(WikiPage.updated_at.desc())
        .limit(50)
    )
    return [
        {
            "id": p.id,
            "title": p.title,
            "slug": p.slug,
            "parent_id": p.parent_id,
            "updated_at": p.updated_at.isoformat(),
        }
        for p in result.scalars().all()
    ]
