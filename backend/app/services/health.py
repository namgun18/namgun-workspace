"""Background service health checker with in-memory cache."""

import asyncio
import time

import httpx

from app.config import get_settings
from app.services.schemas import ServiceStatus


def _build_service_defs() -> list[dict]:
    """Build SERVICE_DEFS from settings — allows .env to override URLs."""
    s = get_settings()
    return [
        {
            "name": "Gitea",
            "health_url": f"{s.gitea_url}/api/v1/version",
            "external_url": "/git/",
            "internal_only": False,
        },
        {
            "name": "Stalwart Mail",
            "health_url": f"{s.stalwart_url}/.well-known/jmap",
            "external_url": "/mail/",
            "internal_only": True,
        },
        {
            "name": "LiveKit",
            "health_url": s.livekit_url.replace("ws://", "http://").replace("wss://", "https://") + "/",
            "external_url": None,
            "internal_only": True,
        },
    ]

# In-memory cache
_cache: list[ServiceStatus] = []
_check_interval = 60  # seconds


async def check_service(svc: dict) -> ServiceStatus:
    """Check a single service health endpoint (HTTP or TCP)."""
    elapsed_ms = None
    status = "down"

    try:
        start = time.monotonic()
        if "health_tcp" in svc:
            host, port = svc["health_tcp"].rsplit(":", 1)
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, int(port)), timeout=5.0
            )
            writer.close()
            await writer.wait_closed()
            elapsed_ms = int((time.monotonic() - start) * 1000)
            status = "ok"
        else:
            headers = svc.get("health_headers", {})
            async with httpx.AsyncClient(timeout=10.0, verify=False, follow_redirects=True) as client:
                resp = await client.get(svc["health_url"], headers=headers)
                elapsed_ms = int((time.monotonic() - start) * 1000)
                status = "ok" if resp.status_code < 400 else "down"
    except Exception:
        elapsed_ms = None
        status = "down"

    return ServiceStatus(
        name=svc["name"],
        url=svc["external_url"],
        status=status,
        response_ms=elapsed_ms,
        internal_only=svc["internal_only"],
    )


async def run_health_checker():
    """Background task: check all services every 60s."""
    global _cache
    while True:
        defs = _build_service_defs()
        results = await asyncio.gather(
            *(check_service(svc) for svc in defs),
            return_exceptions=True,
        )
        _cache = [
            r if isinstance(r, ServiceStatus)
            else ServiceStatus(
                name="unknown", url=None, status="down",
                response_ms=None, internal_only=False,
            )
            for r in results
        ]
        await asyncio.sleep(_check_interval)


def get_cached_status() -> list[ServiceStatus]:
    """Return cached service statuses."""
    if not _cache:
        return [
            ServiceStatus(
                name=svc["name"],
                url=svc["external_url"],
                status="checking",
                response_ms=None,
                internal_only=svc["internal_only"],
            )
            for svc in _build_service_defs()
        ]
    return _cache
