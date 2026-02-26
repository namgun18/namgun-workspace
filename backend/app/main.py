import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.rate_limit import limiter
from app.db.session import init_db
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
    version="3.2.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url=None,
)

app.add_middleware(AccessLogMiddleware)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please try again later."},
    )

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


@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": "3.2.0",
        "domain": settings.domain,
        "app_url": settings.app_url,
        "gitea_url": settings.gitea_url,
    }
