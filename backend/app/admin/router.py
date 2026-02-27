"""Admin API routes: user approval, management, analytics, settings."""

import asyncio
import logging
import os
import time as _time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func, select, and_, case, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db.models import AccessLog, User
from app.db.session import get_db
from app.config import get_settings
from app.admin.settings import (
    get_setting,
    set_setting,
    delete_setting,
    get_settings_by_prefix,
    get_smtp_config,
    send_system_email,
)
from app.admin.schemas import (
    AccessLogEntry,
    AccessLogPage,
    ActiveUser,
    AnalyticsOverview,
    DailyVisit,
    GitActivityItem,
    GitStats,
    RecentLogin,
    ServiceUsage,
    TopIP,
    TopPage,
)

logger = logging.getLogger(__name__)

settings = get_settings()

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ── Dependency: admin-only ───────────────────────────────────


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")
    return user


# ── GET /api/admin/users — 전체 사용자 목록 ──────────────────


@router.get("/users")
async def list_users(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all users."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "display_name": u.display_name,
            "email": u.email,
            "recovery_email": u.recovery_email,
            "is_admin": u.is_admin,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


# ── GET /api/admin/users/pending — 승인 대기 목록 ────────────


@router.get("/users/pending")
async def list_pending_users(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List users pending approval."""
    result = await db.execute(
        select(User).where(User.is_active == False).order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "display_name": u.display_name,
            "email": u.email,
            "recovery_email": u.recovery_email,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


# ── POST /api/admin/users/{user_id}/approve — 승인 ──────────


@router.post("/users/{user_id}/approve")
async def approve_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Approve a pending user registration."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    if user.is_active:
        raise HTTPException(status_code=400, detail="이미 활성화된 사용자입니다")

    # Ensure mail account exists in docker-mailserver (only if built-in mailserver is enabled)
    mail_created = True
    if getattr(settings, 'feature_builtin_mailserver', False):
        try:
            from app.mail.mailserver import account_exists, create_account
            exists = await account_exists(user.email)
            if not exists:
                mail_created = await create_account(user.email, "")
        except Exception as e:
            logger.warning("Failed to ensure mail account for %s: %s", user.email, e)
            mail_created = False

    # Activate in DB
    user.is_active = True
    await db.commit()

    # Create default calendar + address book for the new user
    try:
        from app.calendar.service import get_calendars, create_calendar
        from app.contacts.service import get_address_books, create_address_book
        cals = await get_calendars(db, user.id)
        if not cals:
            await create_calendar(db, user.id, "내 캘린더", "#3b82f6")
        books = await get_address_books(db, user.id)
        if not books:
            await create_address_book(db, user.id, "내 연락처")
    except Exception as e:
        logger.warning("Failed to create default calendar/address book for %s: %s", user.username, e)

    try:
        await _send_welcome_email(user.email, user.username)
        logger.info("Welcome email sent to %s", user.email)
    except Exception as e:
        logger.warning("Failed to send welcome email to %s: %s", user.email, e)

    msg = f"{user.username} 사용자가 승인되었습니다"
    if not mail_created:
        msg += " (메일 계정 생성에 실패했습니다. 수동 확인 필요)"

    return {"message": msg}


# ── POST /api/admin/users/{user_id}/reject — 거절 ───────────


@router.post("/users/{user_id}/reject")
async def reject_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Reject a pending user registration (deletes from workspace)."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")

    # Clean up mail principal if built-in mailserver is enabled
    if getattr(settings, 'feature_builtin_mailserver', False):
        try:
            from app.mail.mailserver import delete_account
            await delete_account(user.email)
        except Exception as e:
            logger.warning("Failed to delete mail account for rejected user %s: %s", user.email, e)

    # Delete from DB
    await db.delete(user)
    await db.commit()

    return {"message": "가입 신청이 거절되었습니다"}


# ── POST /api/admin/users/{user_id}/deactivate — 비활성화 ───


@router.post("/users/{user_id}/deactivate")
async def deactivate_user_endpoint(
    user_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate an active user."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="이미 비활성화된 사용자입니다")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="자기 자신은 비활성화할 수 없습니다")

    # Deactivate in DB
    user.is_active = False
    await db.commit()

    return {"message": f"{user.username} 사용자가 비활성화되었습니다"}


# ── POST /api/admin/users/{user_id}/set-role — 권한 변경 ──


class SetRoleRequest(BaseModel):
    is_admin: bool


@router.post("/users/{user_id}/set-role")
async def set_user_role(
    user_id: str,
    body: SetRoleRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Grant or revoke admin role for a user."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="자기 자신의 권한은 변경할 수 없습니다")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="비활성 사용자의 권한은 변경할 수 없습니다")
    if user.is_admin == body.is_admin:
        role = "관리자" if body.is_admin else "일반 사용자"
        raise HTTPException(status_code=400, detail=f"이미 {role}입니다")

    # Update DB
    user.is_admin = body.is_admin
    await db.commit()

    role = "관리자" if body.is_admin else "일반 사용자"
    return {"message": f"{user.username} 사용자가 {role}(으)로 변경되었습니다"}


# ── Analytics helpers ──────────────────────────────────────


def _period_start(period: str) -> datetime:
    now = datetime.now(timezone.utc)
    if period == "7d":
        return now - timedelta(days=7)
    if period == "30d":
        return now - timedelta(days=30)
    # today
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


# ── In-memory TTL cache ──────────────────────────────────

_cache: dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 30  # seconds


def _cached(key: str) -> Any | None:
    entry = _cache.get(key)
    if entry and _time.monotonic() - entry[0] < _CACHE_TTL:
        return entry[1]
    return None


def _set_cache(key: str, value: Any) -> None:
    _cache[key] = (_time.monotonic(), value)


# ── Private IP exclusion for existing DB data ────────────

_PRIVATE_PREFIXES = (
    "10.", "172.16.", "172.17.", "172.18.", "172.19.",
    "172.20.", "172.21.", "172.22.", "172.23.", "172.24.",
    "172.25.", "172.26.", "172.27.", "172.28.", "172.29.",
    "172.30.", "172.31.", "192.168.", "127.", "::1", "fe80:", "fc00:", "fd",
)


def _exclude_private_ip():
    """SQLAlchemy filter: exclude rows with private IP addresses."""
    return and_(*(~AccessLog.ip_address.startswith(p) for p in _PRIVATE_PREFIXES))


# ── GET /api/admin/analytics/overview ─────────────────────


@router.get("/analytics/overview", response_model=AnalyticsOverview)
async def analytics_overview(
    period: str = Query("today", pattern="^(today|7d|30d)$"),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"overview:{period}"
    if (hit := _cached(cache_key)) is not None:
        return hit

    since = _period_start(period)
    result = await db.execute(
        select(
            func.count(AccessLog.id),
            func.count(distinct(AccessLog.ip_address)),
            func.count(case((AccessLog.user_id.isnot(None), 1))),
            func.count(case((AccessLog.user_id.is_(None), 1))),
            func.coalesce(func.avg(AccessLog.response_time_ms), 0),
        ).where(and_(AccessLog.created_at >= since, _exclude_private_ip()))
    )
    row = result.one()
    data = AnalyticsOverview(
        total_visits=row[0],
        unique_ips=row[1],
        authenticated_visits=row[2],
        unauthenticated_visits=row[3],
        avg_response_time_ms=int(row[4]),
    )
    _set_cache(cache_key, data)
    return data


# ── GET /api/admin/analytics/daily-visits ─────────────────


@router.get("/analytics/daily-visits", response_model=list[DailyVisit])
async def analytics_daily_visits(
    days: int = Query(30, ge=1, le=90),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"daily:{days}"
    if (hit := _cached(cache_key)) is not None:
        return hit

    since = datetime.now(timezone.utc) - timedelta(days=days)
    date_col = func.date(AccessLog.created_at)
    result = await db.execute(
        select(
            date_col.label("date"),
            func.count(AccessLog.id),
            func.count(case((AccessLog.user_id.isnot(None), 1))),
            func.count(case((AccessLog.user_id.is_(None), 1))),
        )
        .where(and_(AccessLog.created_at >= since, _exclude_private_ip()))
        .group_by(date_col)
        .order_by(date_col)
    )
    data = [
        DailyVisit(date=str(row[0]), total=row[1], authenticated=row[2], unauthenticated=row[3])
        for row in result.all()
    ]
    _set_cache(cache_key, data)
    return data


# ── GET /api/admin/analytics/top-pages ────────────────────


@router.get("/analytics/top-pages", response_model=list[TopPage])
async def analytics_top_pages(
    period: str = Query("today", pattern="^(today|7d|30d)$"),
    limit: int = Query(10, ge=1, le=50),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"pages:{period}"
    if (hit := _cached(cache_key)) is not None:
        return hit

    since = _period_start(period)
    result = await db.execute(
        select(AccessLog.path, func.count(AccessLog.id).label("cnt"))
        .where(and_(AccessLog.created_at >= since, _exclude_private_ip()))
        .group_by(AccessLog.path)
        .order_by(func.count(AccessLog.id).desc())
        .limit(limit)
    )
    data = [TopPage(path=row[0], count=row[1]) for row in result.all()]
    _set_cache(cache_key, data)
    return data


# ── GET /api/admin/analytics/top-ips ──────────────────────


@router.get("/analytics/top-ips", response_model=list[TopIP])
async def analytics_top_ips(
    period: str = Query("today", pattern="^(today|7d|30d)$"),
    limit: int = Query(15, ge=1, le=50),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"top-ips:{period}"
    if (hit := _cached(cache_key)) is not None:
        return hit

    since = _period_start(period)
    result = await db.execute(
        select(
            AccessLog.ip_address,
            func.count(AccessLog.id).label("cnt"),
            func.count(distinct(AccessLog.path)).label("paths"),
        )
        .where(and_(AccessLog.created_at >= since, _exclude_private_ip()))
        .group_by(AccessLog.ip_address)
        .order_by(func.count(AccessLog.id).desc())
        .limit(limit)
    )
    data = [
        TopIP(ip_address=row[0], count=row[1], paths=row[2])
        for row in result.all()
    ]
    _set_cache(cache_key, data)
    return data


# ── GET /api/admin/analytics/service-usage ────────────────


@router.get("/analytics/service-usage", response_model=list[ServiceUsage])
async def analytics_service_usage(
    period: str = Query("today", pattern="^(today|7d|30d)$"),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"services:{period}"
    if (hit := _cached(cache_key)) is not None:
        return hit

    since = _period_start(period)
    result = await db.execute(
        select(AccessLog.service, func.count(AccessLog.id).label("cnt"))
        .where(and_(AccessLog.created_at >= since, AccessLog.service.isnot(None), _exclude_private_ip()))
        .group_by(AccessLog.service)
        .order_by(func.count(AccessLog.id).desc())
    )
    data = [ServiceUsage(service=row[0], count=row[1]) for row in result.all()]
    _set_cache(cache_key, data)
    return data


# ── GET /api/admin/analytics/active-users ─────────────────


@router.get("/analytics/active-users", response_model=list[ActiveUser])
async def analytics_active_users(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(minutes=5)
    # Subquery: latest log per user in last 5 min
    subq = (
        select(
            AccessLog.user_id,
            func.max(AccessLog.created_at).label("last_seen"),
        )
        .where(and_(AccessLog.created_at >= since, AccessLog.user_id.isnot(None)))
        .group_by(AccessLog.user_id)
        .subquery()
    )
    result = await db.execute(
        select(
            subq.c.user_id,
            User.username,
            User.display_name,
            AccessLog.path,
            AccessLog.ip_address,
            subq.c.last_seen,
        )
        .join(AccessLog, and_(
            AccessLog.user_id == subq.c.user_id,
            AccessLog.created_at == subq.c.last_seen,
        ))
        .join(User, User.id == subq.c.user_id)
        .order_by(subq.c.last_seen.desc())
    )
    return [
        ActiveUser(
            user_id=row[0], username=row[1], display_name=row[2],
            path=row[3], ip_address=row[4],
            last_seen=row[5].isoformat() if row[5] else "",
        )
        for row in result.all()
    ]


# ── GET /api/admin/analytics/recent-logins ────────────────


@router.get("/analytics/recent-logins", response_model=list[RecentLogin])
async def analytics_recent_logins(
    limit: int = Query(20, ge=1, le=100),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(
            AccessLog.user_id,
            User.username,
            User.display_name,
            AccessLog.ip_address,
            AccessLog.created_at,
        )
        .join(User, User.id == AccessLog.user_id)
        .where(and_(
            AccessLog.path.in_(["/api/auth/login", "/api/auth/callback"]),
            AccessLog.status_code < 400,
            _exclude_private_ip(),
        ))
        .order_by(AccessLog.created_at.desc())
        .limit(limit)
    )
    return [
        RecentLogin(
            user_id=row[0], username=row[1], display_name=row[2],
            ip_address=row[3],
            login_at=row[4].isoformat() if row[4] else "",
        )
        for row in result.all()
    ]


# ── GET /api/admin/analytics/access-logs ──────────────────


@router.get("/analytics/access-logs", response_model=AccessLogPage)
async def analytics_access_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    service: str | None = Query(None),
    user_id: str | None = Query(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    conditions = [_exclude_private_ip()]
    if service:
        conditions.append(AccessLog.service == service)
    if user_id:
        conditions.append(AccessLog.user_id == user_id)

    where = and_(*conditions)

    # Count
    count_result = await db.execute(
        select(func.count(AccessLog.id)).where(where)
    )
    total = count_result.scalar() or 0

    # Fetch with LEFT JOIN to get username
    offset = (page - 1) * limit
    result = await db.execute(
        select(
            AccessLog.id,
            AccessLog.ip_address,
            AccessLog.method,
            AccessLog.path,
            AccessLog.status_code,
            AccessLog.response_time_ms,
            AccessLog.browser,
            AccessLog.os,
            AccessLog.device,
            AccessLog.user_id,
            User.username,
            AccessLog.service,
            AccessLog.created_at,
        )
        .outerjoin(User, User.id == AccessLog.user_id)
        .where(where)
        .order_by(AccessLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    logs = [
        AccessLogEntry(
            id=row[0], ip_address=row[1], method=row[2], path=row[3],
            status_code=row[4], response_time_ms=row[5],
            browser=row[6], os=row[7], device=row[8],
            user_id=row[9], username=row[10],
            service=row[11],
            created_at=row[12].isoformat() if row[12] else "",
        )
        for row in result.all()
    ]
    return AccessLogPage(logs=logs, total=total, page=page, limit=limit)


# ── GET /api/admin/analytics/git-activity ─────────────────


@router.get("/analytics/git-activity", response_model=list[GitActivityItem])
async def analytics_git_activity(
    admin: User = Depends(require_admin),
):
    if (hit := _cached("git-activity")) is not None:
        return hit

    from app.git import gitea
    try:
        repos, _ = await gitea.search_repos(limit=10, sort="updated")
    except Exception:
        return []

    items: list[GitActivityItem] = []
    for repo in repos[:5]:
        owner = repo.get("owner", {}).get("login", "")
        name = repo.get("name", "")
        full = repo.get("full_name", f"{owner}/{name}")

        # Recent commits (as push events)
        try:
            commits = await gitea.get_commits(owner, name, page=1)
            for c in commits[:3]:
                commit_info = c.get("commit", {})
                items.append(GitActivityItem(
                    repo_name=name, repo_full_name=full,
                    event_type="push",
                    title=commit_info.get("message", "").split("\n")[0][:100],
                    user=commit_info.get("author", {}).get("name", ""),
                    created_at=commit_info.get("author", {}).get("date", ""),
                ))
        except Exception:
            pass

        # Recent issues
        try:
            issues = await gitea.get_issues(owner, name, state="all", page=1)
            for iss in issues[:2]:
                items.append(GitActivityItem(
                    repo_name=name, repo_full_name=full,
                    event_type="issue",
                    title=iss.get("title", "")[:100],
                    user=iss.get("user", {}).get("login", ""),
                    created_at=iss.get("created_at", ""),
                ))
        except Exception:
            pass

        # Recent PRs
        try:
            pulls = await gitea.get_pulls(owner, name, state="all", page=1)
            for pr in pulls[:2]:
                items.append(GitActivityItem(
                    repo_name=name, repo_full_name=full,
                    event_type="pull_request",
                    title=pr.get("title", "")[:100],
                    user=pr.get("user", {}).get("login", ""),
                    created_at=pr.get("created_at", ""),
                ))
        except Exception:
            pass

    items.sort(key=lambda x: x.created_at, reverse=True)
    data = items[:20]
    _set_cache("git-activity", data)
    return data


# ── GET /api/admin/analytics/git-stats ────────────────────


@router.get("/analytics/git-stats", response_model=GitStats)
async def analytics_git_stats(
    admin: User = Depends(require_admin),
):
    if (hit := _cached("git-stats")) is not None:
        return hit

    from app.git import gitea
    try:
        repos, total_repos = await gitea.search_repos(limit=50, sort="updated")
        total_issues = sum(r.get("open_issues_count", 0) for r in repos)
        total_pulls = sum(r.get("open_pr_counter", 0) for r in repos)
        # Unique owners as proxy for users
        users = {r.get("owner", {}).get("login") for r in repos}
        data = GitStats(
            total_repos=total_repos,
            total_users=len(users),
            total_issues=total_issues,
            total_pulls=total_pulls,
        )
        _set_cache("git-stats", data)
        return data
    except Exception:
        return GitStats(total_repos=0, total_users=0, total_issues=0, total_pulls=0)


# ── Email helper ──────────────────────────────────────────


async def _send_welcome_email(to_email: str, username: str, db: AsyncSession | None = None) -> None:
    """Send welcome email via system SMTP."""
    from email.mime.text import MIMEText
    from app.db.session import async_session as _async_session

    async def _inner(session: AsyncSession):
        smtp_cfg = await get_smtp_config(session)
        msg = MIMEText(
            f"{username}님, {settings.app_name} 가입이 승인되었습니다.\n\n"
            f"이제 {settings.app_url} 에 로그인하여 메일, 파일, "
            f"회의 등 모든 서비스를 이용하실 수 있습니다.\n\n"
            f"— {settings.app_name} 관리팀",
            "plain",
            "utf-8",
        )
        msg["Subject"] = f"[{settings.domain}] 가입이 승인되었습니다"
        msg["From"] = smtp_cfg.from_addr
        msg["To"] = to_email
        await asyncio.to_thread(send_system_email, smtp_cfg, msg)

    if db:
        await _inner(db)
    else:
        async with _async_session() as session:
            await _inner(session)


# ── Settings API ─────────────────────────────────────────


LOGO_DIR = Path(settings.storage_root) / "branding"
LOGO_MAX_BYTES = 2 * 1024 * 1024
LOGO_ALLOWED_TYPES = {"image/png", "image/jpeg", "image/svg+xml", "image/webp"}
SSL_DIR = Path("/etc/nginx/ssl")


class BrandingUpdate(BaseModel):
    site_name: str | None = None
    primary_color: str | None = None
    default_theme: str | None = None  # light | dark | system


class GeneralUpdate(BaseModel):
    registration_mode: str | None = None  # open | approval | closed
    upload_max_size_mb: int | None = None
    session_hours: int | None = None
    session_remember_days: int | None = None
    announcement: str | None = None
    announcement_type: str | None = None  # info | warning | error
    git_visibility: str | None = None  # public | private


class SmtpUpdate(BaseModel):
    host: str | None = None
    port: int | None = None
    security: str | None = None  # starttls | ssl | none
    user: str | None = None
    password: str | None = None
    from_addr: str | None = None


class SmtpTestRequest(BaseModel):
    to_email: str


# ── Branding ─────────────────────────────────────────────


@router.get("/settings/branding")
async def get_branding(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get current branding settings (DB values with .env fallback)."""
    db_vals = await get_settings_by_prefix(db, "branding.")
    return {
        "site_name": db_vals.get("branding.site_name") or settings.app_name,
        "primary_color": db_vals.get("branding.primary_color") or settings.brand_color,
        "logo_url": db_vals.get("branding.logo_url") or settings.brand_logo or "",
        "default_theme": db_vals.get("branding.default_theme") or "system",
        "favicon_url": db_vals.get("branding.favicon_url") or "",
    }


@router.patch("/settings/branding")
async def update_branding(
    body: BrandingUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update branding settings in DB."""
    if body.site_name is not None:
        await set_setting(db, "branding.site_name", body.site_name)
    if body.primary_color is not None:
        await set_setting(db, "branding.primary_color", body.primary_color)
    if body.default_theme is not None:
        if body.default_theme not in ("light", "dark", "system"):
            raise HTTPException(status_code=400, detail="유효하지 않은 테마 값입니다")
        await set_setting(db, "branding.default_theme", body.default_theme)
    return {"message": "브랜딩 설정이 저장되었습니다"}


@router.post("/settings/branding/logo")
async def upload_logo(
    file: UploadFile,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Upload site logo (max 2MB, png/jpeg/svg/webp)."""
    if file.content_type not in LOGO_ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="png/jpeg/svg/webp 이미지만 허용됩니다")

    data = await file.read()
    if len(data) > LOGO_MAX_BYTES:
        raise HTTPException(status_code=413, detail="로고 이미지는 2MB 이하여야 합니다")

    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "png"
    filename = f"logo.{ext}"
    (LOGO_DIR / filename).write_bytes(data)

    logo_url = "/api/branding/logo"
    await set_setting(db, "branding.logo_url", logo_url)
    return {"logo_url": logo_url}


@router.delete("/settings/branding/logo")
async def delete_logo(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete uploaded logo."""
    await delete_setting(db, "branding.logo_url")
    # Remove logo files
    if LOGO_DIR.exists():
        for f in LOGO_DIR.iterdir():
            if f.name.startswith("logo."):
                f.unlink(missing_ok=True)
    return {"message": "로고가 삭제되었습니다"}


# ── Favicon ──────────────────────────────────────────────

FAVICON_ALLOWED_TYPES = {"image/x-icon", "image/vnd.microsoft.icon", "image/png", "image/svg+xml"}
FAVICON_MAX_BYTES = 1 * 1024 * 1024


@router.post("/settings/branding/favicon")
async def upload_favicon(
    file: UploadFile,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Upload site favicon (max 1MB, ico/png/svg)."""
    ct = file.content_type or ""
    if ct not in FAVICON_ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="ico/png/svg 파일만 허용됩니다")

    data = await file.read()
    if len(data) > FAVICON_MAX_BYTES:
        raise HTTPException(status_code=413, detail="파비콘은 1MB 이하여야 합니다")

    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    # Remove old favicons
    for f in LOGO_DIR.iterdir():
        if f.name.startswith("favicon."):
            f.unlink(missing_ok=True)

    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "ico"
    filename = f"favicon.{ext}"
    (LOGO_DIR / filename).write_bytes(data)

    favicon_url = "/api/branding/favicon"
    await set_setting(db, "branding.favicon_url", favicon_url)
    return {"favicon_url": favicon_url}


@router.delete("/settings/branding/favicon")
async def delete_favicon(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete uploaded favicon."""
    await delete_setting(db, "branding.favicon_url")
    if LOGO_DIR.exists():
        for f in LOGO_DIR.iterdir():
            if f.name.startswith("favicon."):
                f.unlink(missing_ok=True)
    return {"message": "파비콘이 삭제되었습니다"}


# ── General settings ─────────────────────────────────────


@router.get("/settings/general")
async def get_general_settings(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get general settings."""
    gen_vals = await get_settings_by_prefix(db, "general.")
    auth_vals = await get_settings_by_prefix(db, "auth.")
    return {
        "registration_mode": auth_vals.get("auth.registration_mode") or "approval",
        "upload_max_size_mb": int(gen_vals.get("general.upload_max_size_mb") or str(settings.upload_max_size_mb)),
        "session_hours": int(auth_vals.get("auth.session_hours") or "8"),
        "session_remember_days": int(auth_vals.get("auth.session_remember_days") or "30"),
        "announcement": gen_vals.get("general.announcement") or "",
        "announcement_type": gen_vals.get("general.announcement_type") or "info",
        "git_visibility": gen_vals.get("general.git_visibility") or "private",
    }


@router.patch("/settings/general")
async def update_general_settings(
    body: GeneralUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update general settings."""
    if body.registration_mode is not None:
        if body.registration_mode not in ("open", "approval", "closed"):
            raise HTTPException(status_code=400, detail="유효하지 않은 가입 모드입니다")
        await set_setting(db, "auth.registration_mode", body.registration_mode)
    if body.upload_max_size_mb is not None:
        if body.upload_max_size_mb < 1 or body.upload_max_size_mb > 10240:
            raise HTTPException(status_code=400, detail="업로드 크기는 1~10240 MB 범위여야 합니다")
        await set_setting(db, "general.upload_max_size_mb", str(body.upload_max_size_mb))
    if body.session_hours is not None:
        if body.session_hours < 1 or body.session_hours > 720:
            raise HTTPException(status_code=400, detail="세션 시간은 1~720시간 범위여야 합니다")
        await set_setting(db, "auth.session_hours", str(body.session_hours))
    if body.session_remember_days is not None:
        if body.session_remember_days < 1 or body.session_remember_days > 365:
            raise HTTPException(status_code=400, detail="기억 기간은 1~365일 범위여야 합니다")
        await set_setting(db, "auth.session_remember_days", str(body.session_remember_days))
    if body.announcement is not None:
        await set_setting(db, "general.announcement", body.announcement)
    if body.announcement_type is not None:
        if body.announcement_type not in ("info", "warning", "error"):
            raise HTTPException(status_code=400, detail="유효하지 않은 공지 유형입니다")
        await set_setting(db, "general.announcement_type", body.announcement_type)
    if body.git_visibility is not None:
        if body.git_visibility not in ("public", "private"):
            raise HTTPException(status_code=400, detail="유효하지 않은 Git 공개 설정입니다")
        await set_setting(db, "general.git_visibility", body.git_visibility)
    return {"message": "일반 설정이 저장되었습니다"}


# ── SMTP ─────────────────────────────────────────────────


@router.get("/settings/smtp")
async def get_smtp(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get SMTP settings (password masked)."""
    cfg = await get_smtp_config(db)
    return {
        "host": cfg.host,
        "port": cfg.port,
        "security": cfg.security,
        "user": cfg.user,
        "password": "••••••••" if cfg.password else "",
        "from_addr": cfg.from_addr,
    }


@router.patch("/settings/smtp")
async def update_smtp(
    body: SmtpUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update SMTP settings in DB."""
    if body.host is not None:
        await set_setting(db, "smtp.host", body.host)
    if body.port is not None:
        await set_setting(db, "smtp.port", str(body.port))
    if body.security is not None:
        await set_setting(db, "smtp.security", body.security)
    if body.user is not None:
        await set_setting(db, "smtp.user", body.user)
    if body.password is not None:
        await set_setting(db, "smtp.password", body.password)
    if body.from_addr is not None:
        await set_setting(db, "smtp.from", body.from_addr)
    return {"message": "SMTP 설정이 저장되었습니다"}


@router.post("/settings/smtp/test")
async def test_smtp(
    body: SmtpTestRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Send a test email using current SMTP settings."""
    from email.mime.text import MIMEText

    cfg = await get_smtp_config(db)
    msg = MIMEText(
        f"이 메일은 {settings.domain} 포털의 SMTP 테스트 메일입니다.\n\n"
        f"이 메일이 정상 수신되었다면 SMTP 설정이 올바르게 구성된 것입니다.",
        "plain",
        "utf-8",
    )
    msg["Subject"] = f"[{settings.domain}] SMTP 테스트"
    msg["From"] = cfg.from_addr
    msg["To"] = body.to_email

    try:
        await asyncio.to_thread(send_system_email, cfg, msg)
        return {"message": f"{body.to_email}으로 테스트 메일이 전송되었습니다"}
    except Exception as e:
        logger.error("SMTP test failed: %s", e)
        raise HTTPException(status_code=500, detail=f"SMTP 테스트 실패: {e}")


# ── SSL ──────────────────────────────────────────────────


@router.get("/settings/ssl")
async def get_ssl_status(
    admin: User = Depends(require_admin),
):
    """Get current SSL certificate status."""
    import subprocess

    cert_path = SSL_DIR / "cert.pem"
    key_path = SSL_DIR / "key.pem"

    if not cert_path.is_file():
        return {"installed": False, "message": "SSL 인증서가 설치되지 않았습니다"}

    try:
        result = subprocess.run(
            ["openssl", "x509", "-in", str(cert_path), "-noout",
             "-subject", "-issuer", "-dates"],
            capture_output=True, text=True, timeout=5,
        )
        lines = result.stdout.strip().split("\n")
        info = {}
        for line in lines:
            if "=" in line:
                k, v = line.split("=", 1)
                info[k.strip()] = v.strip()
        return {
            "installed": True,
            "subject": info.get("subject", ""),
            "issuer": info.get("issuer", ""),
            "not_before": info.get("notBefore", ""),
            "not_after": info.get("notAfter", ""),
            "has_key": key_path.is_file(),
        }
    except Exception as e:
        return {"installed": True, "error": str(e)}


@router.post("/settings/ssl")
async def upload_ssl(
    cert: UploadFile,
    key: UploadFile,
    admin: User = Depends(require_admin),
):
    """Upload SSL certificate and private key."""
    cert_data = await cert.read()
    key_data = await key.read()

    if len(cert_data) > 1024 * 1024 or len(key_data) > 1024 * 1024:
        raise HTTPException(status_code=413, detail="인증서/키 파일은 1MB 이하여야 합니다")

    SSL_DIR.mkdir(parents=True, exist_ok=True)
    (SSL_DIR / "cert.pem").write_bytes(cert_data)
    (SSL_DIR / "key.pem").write_bytes(key_data)

    return {
        "message": "SSL 인증서가 업로드되었습니다. nginx 재시작이 필요할 수 있습니다.",
    }


@router.delete("/settings/ssl")
async def delete_ssl(
    admin: User = Depends(require_admin),
):
    """Delete uploaded SSL certificate."""
    for name in ("cert.pem", "key.pem"):
        path = SSL_DIR / name
        if path.is_file():
            path.unlink()
    return {"message": "SSL 인증서가 삭제되었습니다"}


# ── Audit Logs ────────────────────────────────────────────


@router.get("/audit-logs")
async def list_audit_logs(
    page: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    actor_id: str | None = Query(None),
    action: str | None = Query(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List audit log entries with optional filters (admin only)."""
    from app.admin.audit import get_audit_logs

    logs, total = await get_audit_logs(
        db, page=page, limit=limit, actor_id=actor_id, action=action
    )
    return {"logs": logs, "total": total, "page": page, "limit": limit}
