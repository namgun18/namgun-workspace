import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_db, init_db
from app.rate_limit import limiter
from app.middleware.access_log import AccessLogMiddleware, run_log_flusher, run_log_cleanup
from app.auth.router import router as auth_router
from app.auth.oauth_provider import router as oauth_router
from app.services.router import router as services_router
from app.services.health import run_health_checker
from app.files.router import router as files_router
from app.mail.router import router as mail_router
from app.admin.router import router as admin_router
from app.git.router import router as git_router
from app.dashboard.router import router as dashboard_router
from app.calendar.router import router as calendar_router
from app.contacts.router import router as contacts_router
from app.meetings.router import router as meetings_router
from app.chat.router import router as chat_router
from app.chat.websocket import router as chat_ws_router
from app.chat.webhook import router as webhook_router
from app.modules.router import router as modules_router
from app.board.router import router as board_router
from app.tasks.router import router as tasks_router
from app.search.router import router as search_router
from app.dav.router import dav_app

settings = get_settings()
_health_task = None
_log_flusher_task = None
_log_cleanup_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _health_task, _log_flusher_task, _log_cleanup_task

    from app.chat.redis_client import get_redis, close_redis

    # Validate secret_key is not the default
    if settings.secret_key == "CHANGE_ME" and not settings.debug:
        raise RuntimeError(
            "FATAL: secret_key is set to the default 'CHANGE_ME'. "
            "Set a secure SECRET_KEY in .env before running in production."
        )

    await init_db()

    # Auto-seed admin if ADMIN_USERNAME + ADMIN_PASSWORD are set
    admin_user = os.environ.get("ADMIN_USERNAME")
    admin_pass = os.environ.get("ADMIN_PASSWORD")
    if admin_user and admin_pass:
        from app.cli import seed_admin
        await seed_admin(admin_user, admin_pass)

    # Load module states from DB
    from app.modules.registry import load_module_states
    from app.db.session import async_session
    async with async_session() as db:
        await load_module_states(db)

    await get_redis()  # init Redis connection pool
    _health_task = asyncio.create_task(run_health_checker())
    _log_flusher_task = asyncio.create_task(run_log_flusher())
    _log_cleanup_task = asyncio.create_task(run_log_cleanup())
    print(f"[STARTUP] {settings.app_name} started")

    yield

    # Flush remaining access logs before shutdown
    from app.middleware.access_log import _flush_buffer
    await _flush_buffer()

    for task in (_health_task, _log_flusher_task, _log_cleanup_task):
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    await close_redis()


app = FastAPI(
    title=settings.app_name,
    version="4.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url=None,
)

# CORS — allow same-origin + configured APP_URL
_cors_origins = [settings.app_url]
if settings.debug:
    _cors_origins += ["http://localhost:3000", "http://localhost:8000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.add_middleware(AccessLogMiddleware)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please try again later."},
    )

# Mount DAV sub-application (PROPFIND/REPORT via raw ASGI)
app.mount("/dav", dav_app)

app.include_router(modules_router)
app.include_router(auth_router)
app.include_router(oauth_router)
app.include_router(services_router)
app.include_router(files_router)
app.include_router(mail_router)
app.include_router(admin_router)
app.include_router(git_router)
app.include_router(dashboard_router)
app.include_router(calendar_router)
app.include_router(contacts_router)
app.include_router(meetings_router)
app.include_router(chat_router)
app.include_router(chat_ws_router)
app.include_router(webhook_router)
app.include_router(board_router)
app.include_router(tasks_router)
app.include_router(search_router)


# ── .well-known CalDAV/CardDAV discovery ──

@app.get("/.well-known/caldav")
async def well_known_caldav():
    return RedirectResponse(url="/dav/", status_code=301)


@app.get("/.well-known/carddav")
async def well_known_carddav():
    return RedirectResponse(url="/dav/", status_code=301)


@app.get("/api/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    from app.admin.settings import get_settings_by_prefix

    db_vals = await get_settings_by_prefix(db, "branding.")
    gen_vals = await get_settings_by_prefix(db, "general.")
    auth_vals = await get_settings_by_prefix(db, "auth.")

    return {
        "status": "ok",
        "service": db_vals.get("branding.site_name") or settings.app_name,
        "version": "3.5.0",
        "domain": settings.domain,
        "app_url": settings.app_url,
        "gitea_url": settings.gitea_external_url or f"{settings.app_url}/git/",
        "brand_logo": db_vals.get("branding.logo_url") or settings.brand_logo,
        "brand_color": db_vals.get("branding.primary_color") or settings.brand_color,
        "default_theme": db_vals.get("branding.default_theme") or "system",
        "favicon": db_vals.get("branding.favicon_url") or "",
        "registration_mode": auth_vals.get("auth.registration_mode") or "approval",
        "announcement": gen_vals.get("general.announcement") or "",
        "announcement_type": gen_vals.get("general.announcement_type") or "info",
        "git_visibility": gen_vals.get("general.git_visibility") or "private",
    }


@app.get("/api/branding/favicon")
async def serve_favicon():
    """Serve uploaded favicon (no auth required)."""
    favicon_dir = Path(settings.storage_root) / "branding"
    if favicon_dir.is_dir():
        for f in favicon_dir.iterdir():
            if f.name.startswith("favicon.") and f.is_file():
                media_map = {
                    ".ico": "image/x-icon",
                    ".png": "image/png",
                    ".svg": "image/svg+xml",
                }
                media = media_map.get(f.suffix.lower(), "image/x-icon")
                return FileResponse(str(f), media_type=media)
    raise HTTPException(status_code=404, detail="Favicon not found")


@app.get("/api/branding/logo")
async def serve_logo():
    """Serve uploaded branding logo (no auth required)."""
    logo_dir = Path(settings.storage_root) / "branding"
    if logo_dir.is_dir():
        for f in logo_dir.iterdir():
            if f.name.startswith("logo.") and f.is_file():
                media_map = {
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".svg": "image/svg+xml",
                    ".webp": "image/webp",
                }
                media = media_map.get(f.suffix.lower(), "application/octet-stream")
                return FileResponse(str(f), media_type=media)
    raise HTTPException(status_code=404, detail="Logo not found")
