"""Stalwart Admin API client — principal (mail account) management."""

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


def _auth() -> tuple[str, str]:
    s = get_settings()
    return (s.stalwart_admin_user, s.stalwart_admin_password)


def _base() -> str:
    return get_settings().stalwart_url


async def create_principal(
    username: str,
    password: str,
    email: str,
    display_name: str | None = None,
) -> bool:
    """Create a new mail principal in Stalwart. Returns True on success."""
    payload = {
        "type": "individual",
        "name": username,
        "secrets": [password],
        "emails": [email],
        "roles": ["user"],
    }
    if display_name:
        payload["description"] = display_name

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{_base()}/api/principal",
            json=payload,
            auth=_auth(),
        )
    if resp.status_code in (200, 201):
        logger.info("Stalwart principal created: %s <%s>", username, email)
        return True
    if resp.status_code == 409:
        logger.info("Stalwart principal already exists: %s", username)
        return True
    logger.error(
        "Failed to create Stalwart principal %s: %s %s",
        username, resp.status_code, resp.text,
    )
    return False


async def delete_principal(username: str) -> bool:
    """Delete a mail principal from Stalwart. Returns True on success."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.delete(
            f"{_base()}/api/principal/{username}",
            auth=_auth(),
        )
    if resp.status_code == 200:
        logger.info("Stalwart principal deleted: %s", username)
        return True
    if resp.status_code == 404:
        logger.info("Stalwart principal not found (already deleted): %s", username)
        return True
    logger.error(
        "Failed to delete Stalwart principal %s: %s %s",
        username, resp.status_code, resp.text,
    )
    return False


async def update_password(username: str, new_password: str) -> bool:
    """Update a principal's password in Stalwart. Returns True on success."""
    import json

    payload = json.dumps([{"action": "set", "field": "secrets", "value": [new_password]}])
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.patch(
            f"{_base()}/api/principal/{username}",
            content=payload,
            headers={"Content-Type": "application/json"},
            auth=_auth(),
        )
    if resp.status_code == 200:
        logger.info("Stalwart password updated: %s", username)
        return True
    logger.error(
        "Failed to update Stalwart password for %s: %s %s",
        username, resp.status_code, resp.text,
    )
    return False


async def principal_exists(username: str) -> bool:
    """Check if a principal exists in Stalwart."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{_base()}/api/principal/{username}",
            auth=_auth(),
        )
    return resp.status_code == 200
