"""Chat WebSocket endpoint + ConnectionManager + Redis Pub/Sub."""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from itsdangerous import URLSafeTimedSerializer, BadSignature

from app.config import get_settings
from app.db.session import async_session
from app.db.models import User
from app.chat import service
from app.chat.presence import set_online, set_offline, refresh_heartbeat, get_online_users
from app.chat.redis_client import get_redis

logger = logging.getLogger(__name__)
router = APIRouter()

PUBSUB_MSG = "chat:channel:{}"
PUBSUB_PRESENCE = "chat:presence"
PUBSUB_TYPING = "chat:typing:{}"
PUBSUB_NOTIFICATION = "chat:notification:{}"


class ConnectionManager:
    def __init__(self):
        self.active: dict[str, WebSocket] = {}  # user_id → ws
        self.user_channels: dict[str, set[str]] = {}  # user_id → channel_ids
        self._subscriber_task: asyncio.Task | None = None

    async def connect(self, user_id: str, ws: WebSocket, channel_ids: list[str]):
        self.active[user_id] = ws
        self.user_channels[user_id] = set(channel_ids)

        if self._subscriber_task is None or self._subscriber_task.done():
            self._subscriber_task = asyncio.create_task(self._subscribe_loop())

    def disconnect(self, user_id: str):
        self.active.pop(user_id, None)
        self.user_channels.pop(user_id, None)

    def update_channels(self, user_id: str, channel_ids: set[str]):
        self.user_channels[user_id] = channel_ids

    async def publish_to_channel(self, channel_id: str, data: dict):
        r = await get_redis()
        await r.publish(PUBSUB_MSG.format(channel_id), json.dumps(data))

    async def publish_presence(self, data: dict):
        r = await get_redis()
        await r.publish(PUBSUB_PRESENCE, json.dumps(data))

    async def publish_typing(self, channel_id: str, data: dict):
        r = await get_redis()
        await r.publish(PUBSUB_TYPING.format(channel_id), json.dumps(data))

    async def publish_notification(self, user_id: str, data: dict):
        r = await get_redis()
        await r.publish(PUBSUB_NOTIFICATION.format(user_id), json.dumps(data))

    async def _subscribe_loop(self):
        """Background subscriber that routes Pub/Sub messages to local WS connections."""
        r = await get_redis()
        pubsub = r.pubsub()
        subscribed_channels: set[str] = set()

        try:
            # Subscribe to presence channel
            await pubsub.subscribe(PUBSUB_PRESENCE)

            while True:
                # Update channel subscriptions based on active users
                needed = set()
                for uid, chs in self.user_channels.items():
                    for ch in chs:
                        needed.add(PUBSUB_MSG.format(ch))
                        needed.add(PUBSUB_TYPING.format(ch))
                    needed.add(PUBSUB_NOTIFICATION.format(uid))

                to_sub = needed - subscribed_channels
                to_unsub = subscribed_channels - needed

                if to_sub:
                    await pubsub.subscribe(*to_sub)
                    subscribed_channels.update(to_sub)
                if to_unsub:
                    await pubsub.unsubscribe(*to_unsub)
                    subscribed_channels -= to_unsub

                if not self.active:
                    await asyncio.sleep(1)
                    continue

                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
                if msg is None:
                    continue

                if msg["type"] != "message":
                    continue

                channel_name = msg["channel"]
                try:
                    data = json.loads(msg["data"])
                except (json.JSONDecodeError, TypeError):
                    continue

                if channel_name == PUBSUB_PRESENCE:
                    # Broadcast to all connected users
                    for uid, ws in list(self.active.items()):
                        try:
                            await ws.send_json(data)
                        except Exception:
                            pass
                elif channel_name.startswith("chat:channel:"):
                    ch_id = channel_name.split(":", 2)[2]
                    for uid, ws in list(self.active.items()):
                        if ch_id in self.user_channels.get(uid, set()):
                            try:
                                await ws.send_json(data)
                            except Exception:
                                pass
                elif channel_name.startswith("chat:typing:"):
                    ch_id = channel_name.split(":", 2)[2]
                    sender_id = data.get("user_id")
                    for uid, ws in list(self.active.items()):
                        if uid != sender_id and ch_id in self.user_channels.get(uid, set()):
                            try:
                                await ws.send_json(data)
                            except Exception:
                                pass
                elif channel_name.startswith("chat:notification:"):
                    target_uid = channel_name.split(":", 2)[2]
                    ws = self.active.get(target_uid)
                    if ws:
                        try:
                            await ws.send_json(data)
                        except Exception:
                            pass

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Pub/Sub subscriber error: %s", e)
        finally:
            try:
                await pubsub.unsubscribe()
                await pubsub.aclose()
            except Exception:
                pass


manager = ConnectionManager()


def _authenticate_ws(ws: WebSocket) -> str | None:
    """Extract user_id from portal_session cookie."""
    cookie = ws.cookies.get("portal_session")
    if not cookie:
        return None
    try:
        settings = get_settings()
        s = URLSafeTimedSerializer(settings.secret_key)
        data = s.loads(cookie, max_age=86400 * 30)
        return data.get("user_id") if isinstance(data, dict) else None
    except (BadSignature, Exception):
        return None


@router.websocket("/ws/chat")
async def chat_ws(ws: WebSocket):
    user_id = _authenticate_ws(ws)
    if not user_id:
        await ws.close(code=4001, reason="Unauthorized")
        return

    await ws.accept()

    # Fetch user info & channels
    async with async_session() as db:
        user = await db.get(User, user_id)
        if not user or not user.is_active:
            await ws.close(code=4001, reason="Unauthorized")
            return
        username = user.username
        display_name = user.display_name

        channels = await service.get_user_channels(db, user_id)
        channel_ids = [ch["id"] for ch in channels]

    await set_online(user_id)
    await manager.connect(user_id, ws, channel_ids)

    # Notify presence
    await manager.publish_presence({
        "type": "presence",
        "user_id": user_id,
        "username": username,
        "status": "online",
    })

    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "detail": "Invalid JSON"})
                continue

            msg_type = data.get("type")

            if msg_type == "ping":
                await refresh_heartbeat(user_id)
                await ws.send_json({"type": "pong"})

            elif msg_type == "send_message":
                channel_id = data.get("channel_id")
                content = data.get("content", "").strip()
                message_type = data.get("message_type", "text")
                file_meta = data.get("file_meta")

                if not channel_id or not content:
                    await ws.send_json({"type": "error", "detail": "Missing channel_id or content"})
                    continue

                async with async_session() as db:
                    if not await service.is_channel_member(db, channel_id, user_id):
                        await ws.send_json({"type": "error", "detail": "Not a member"})
                        continue
                    msg = await service.create_message(
                        db, channel_id, user_id, content,
                        message_type=message_type, file_meta=file_meta,
                    )

                    # Process @mentions
                    mentioned = service.parse_mentions(content)
                    if mentioned:
                        notifs = await service.create_notifications_for_mentions(
                            db, msg, channel_id, user_id, mentioned,
                        )
                        for notif in notifs:
                            await manager.publish_notification(notif["user_id"], {
                                "type": "notification",
                                "notification": notif,
                            })

                await manager.publish_to_channel(channel_id, {
                    "type": "new_message",
                    "message": msg,
                })

            elif msg_type == "typing":
                channel_id = data.get("channel_id")
                if channel_id:
                    await manager.publish_typing(channel_id, {
                        "type": "typing",
                        "channel_id": channel_id,
                        "user_id": user_id,
                        "username": display_name or username,
                    })

            elif msg_type == "mark_read":
                channel_id = data.get("channel_id")
                message_id = data.get("message_id")
                if channel_id and message_id:
                    async with async_session() as db:
                        await service.mark_read(db, channel_id, user_id, message_id)
                        u = await db.get(User, user_id)
                        avatar = u.avatar_url if u else None
                    await manager.publish_to_channel(channel_id, {
                        "type": "message_read",
                        "channel_id": channel_id,
                        "user_id": user_id,
                        "username": display_name or username,
                        "avatar_url": avatar,
                        "message_id": message_id,
                    })

            else:
                await ws.send_json({"type": "error", "detail": f"Unknown type: {msg_type}"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("WebSocket error for user %s: %s", user_id, e)
    finally:
        manager.disconnect(user_id)
        await set_offline(user_id)
        await manager.publish_presence({
            "type": "presence",
            "user_id": user_id,
            "username": username,
            "status": "offline",
        })
