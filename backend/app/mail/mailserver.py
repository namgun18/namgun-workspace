"""docker-mailserver account management.

Manages accounts by executing `setup email` commands inside the ws-mailserver container.
Requires the backend to have access to the Docker socket or use docker exec via subprocess.
"""

import asyncio
import logging
import subprocess

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

CONTAINER_NAME = "ws-mailserver"


def _docker_exec(args: list[str]) -> tuple[int, str]:
    """Run a command inside the mailserver container (blocking)."""
    full_cmd = ["docker", "exec", CONTAINER_NAME] + args
    try:
        result = subprocess.run(
            full_cmd, capture_output=True, text=True, timeout=15,
        )
        return result.returncode, result.stdout.strip() + result.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, "timeout"
    except Exception as e:
        return 1, str(e)


async def create_account(email: str, password: str) -> bool:
    """Create a mail account in docker-mailserver. Returns True on success."""
    rc, out = await asyncio.to_thread(
        _docker_exec,
        ["setup", "email", "add", email, password],
    )
    if rc == 0:
        logger.info("Mail account created: %s", email)
        return True
    # Already exists is OK
    if "already exists" in out.lower():
        logger.info("Mail account already exists: %s", email)
        return True
    logger.error("Failed to create mail account %s: %s", email, out)
    return False


async def delete_account(email: str) -> bool:
    """Delete a mail account from docker-mailserver."""
    rc, out = await asyncio.to_thread(
        _docker_exec,
        ["setup", "email", "del", "-y", email],
    )
    if rc == 0:
        logger.info("Mail account deleted: %s", email)
        return True
    if "not found" in out.lower():
        logger.info("Mail account not found (already deleted): %s", email)
        return True
    logger.error("Failed to delete mail account %s: %s", email, out)
    return False


async def update_password(email: str, new_password: str) -> bool:
    """Update a mail account password in docker-mailserver."""
    rc, out = await asyncio.to_thread(
        _docker_exec,
        ["setup", "email", "update", email, new_password],
    )
    if rc == 0:
        logger.info("Mail password updated: %s", email)
        return True
    logger.error("Failed to update mail password %s: %s", email, out)
    return False


async def account_exists(email: str) -> bool:
    """Check if a mail account exists."""
    rc, out = await asyncio.to_thread(
        _docker_exec,
        ["setup", "email", "list"],
    )
    if rc != 0:
        return False
    return email in out
