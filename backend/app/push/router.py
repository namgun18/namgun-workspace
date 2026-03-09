"""Push notification API — VAPID key distribution + subscription management."""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth.deps import get_current_user
from app.db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/push", tags=["push"])


class PushSubscription(BaseModel):
    endpoint: str
    keys: dict
    expirationTime: float | None = None


# ─── In-memory subscription store (production: use DB) ───
_subscriptions: dict[str, list[dict]] = {}  # user_id -> [subscription_json]


def _get_vapid_keys() -> tuple[str, str]:
    """Get or generate VAPID keys."""
    from app.config import get_settings
    settings = get_settings()

    pub = getattr(settings, "vapid_public_key", None) or ""
    priv = getattr(settings, "vapid_private_key", None) or ""

    if not pub or not priv:
        # Auto-generate if not configured
        try:
            from py_vapid import Vapid
            vapid = Vapid()
            vapid.generate_keys()
            pub = vapid.public_key_urlsafe_base64()
            priv = vapid.private_key_urlsafe_base64()
            logger.info("VAPID keys auto-generated (set VAPID_PUBLIC_KEY/VAPID_PRIVATE_KEY in .env for persistence)")
        except ImportError:
            logger.warning("py_vapid not installed — push notifications disabled")
            return "", ""

    return pub, priv


@router.get("/vapid-key")
async def get_vapid_key():
    """Return VAPID public key for client subscription."""
    pub, _ = _get_vapid_keys()
    if not pub:
        raise HTTPException(status_code=503, detail="Push notifications not configured")
    return {"vapid_public_key": pub}


@router.post("/subscribe")
async def subscribe(
    sub: PushSubscription,
    user: User = Depends(get_current_user),
):
    """Store push subscription for the current user."""
    user_id = str(user.id)
    sub_data = sub.model_dump()

    if user_id not in _subscriptions:
        _subscriptions[user_id] = []

    # Avoid duplicates
    existing_endpoints = {s["endpoint"] for s in _subscriptions[user_id]}
    if sub_data["endpoint"] not in existing_endpoints:
        _subscriptions[user_id].append(sub_data)

    logger.info("Push subscription added for user %s", user_id)
    return {"ok": True}


@router.post("/unsubscribe")
async def unsubscribe(
    sub: PushSubscription,
    user: User = Depends(get_current_user),
):
    """Remove push subscription for the current user."""
    user_id = str(user.id)
    if user_id in _subscriptions:
        _subscriptions[user_id] = [
            s for s in _subscriptions[user_id]
            if s["endpoint"] != sub.endpoint
        ]
    return {"ok": True}


async def send_push(user_id: str, title: str, body: str, url: str | None = None):
    """Send push notification to all subscriptions of a user."""
    subs = _subscriptions.get(user_id, [])
    if not subs:
        return

    _, priv = _get_vapid_keys()
    if not priv:
        return

    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        logger.warning("pywebpush not installed — cannot send push")
        return

    from app.config import get_settings
    settings = get_settings()
    claims = {"sub": f"mailto:{settings.smtp_from or 'noreply@localhost'}"}

    payload = json.dumps({
        "title": title,
        "body": body,
        "url": url or "/",
    })

    dead_subs = []
    for sub in subs:
        try:
            webpush(
                subscription_info=sub,
                data=payload,
                vapid_private_key=priv,
                vapid_claims=claims,
            )
        except Exception as e:
            logger.debug("Push send failed for %s: %s", sub.get("endpoint", "?")[:50], e)
            dead_subs.append(sub["endpoint"])

    # Clean up expired subscriptions
    if dead_subs:
        _subscriptions[user_id] = [
            s for s in _subscriptions[user_id]
            if s["endpoint"] not in dead_subs
        ]
