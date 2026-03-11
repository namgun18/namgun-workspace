"""Push notification API — VAPID key distribution + subscription management."""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db.models import PushSubscription as PushSubModel, User
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/push", tags=["push"])


class PushSubscription(BaseModel):
    endpoint: str
    keys: dict
    expirationTime: float | None = None


def _get_vapid_keys() -> tuple[str, str]:
    """Get or generate VAPID keys."""
    from app.config import get_settings
    settings = get_settings()

    pub = getattr(settings, "vapid_public_key", None) or ""
    priv = getattr(settings, "vapid_private_key", None) or ""

    if not pub or not priv:
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
    db: AsyncSession = Depends(get_db),
):
    """Store push subscription for the current user."""
    user_id = str(user.id)

    # Avoid duplicates
    existing = await db.execute(
        select(PushSubModel).where(
            PushSubModel.user_id == user_id,
            PushSubModel.endpoint == sub.endpoint,
        )
    )
    if existing.scalar_one_or_none():
        return {"ok": True}

    row = PushSubModel(
        user_id=user_id,
        endpoint=sub.endpoint,
        keys_json=json.dumps(sub.keys),
        expiration_time=sub.expirationTime,
    )
    db.add(row)
    await db.commit()
    logger.info("Push subscription added for user %s", user_id)
    return {"ok": True}


@router.post("/unsubscribe")
async def unsubscribe(
    sub: PushSubscription,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove push subscription for the current user."""
    await db.execute(
        delete(PushSubModel).where(
            PushSubModel.user_id == str(user.id),
            PushSubModel.endpoint == sub.endpoint,
        )
    )
    await db.commit()
    return {"ok": True}


async def send_push(user_id: str, title: str, body: str, url: str | None = None):
    """Send push notification to all subscriptions of a user."""
    from app.db.session import async_session

    async with async_session() as db:
        result = await db.execute(
            select(PushSubModel).where(PushSubModel.user_id == user_id)
        )
        subs = result.scalars().all()

    if not subs:
        return

    _, priv = _get_vapid_keys()
    if not priv:
        return

    try:
        from pywebpush import webpush
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

    dead_ids = []
    for sub in subs:
        sub_info = {"endpoint": sub.endpoint, "keys": json.loads(sub.keys_json)}
        try:
            webpush(
                subscription_info=sub_info,
                data=payload,
                vapid_private_key=priv,
                vapid_claims=claims,
            )
        except Exception as e:
            logger.debug("Push send failed for %s: %s", sub.endpoint[:50], e)
            dead_ids.append(sub.id)

    # Clean up expired/dead subscriptions
    if dead_ids:
        async with async_session() as db:
            await db.execute(
                delete(PushSubModel).where(PushSubModel.id.in_(dead_ids))
            )
            await db.commit()
