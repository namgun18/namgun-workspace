"""Wiki real-time collaboration — Yjs WebSocket relay.

Each wiki page gets a "room" identified by page_id.
Connected clients exchange Yjs sync/update messages through this relay.
"""

import asyncio
import logging
from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from starlette.websockets import WebSocketState

from app.auth.deps import unsign_value
from app.db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["wiki-collab"])

# Room state: page_id -> set of connected websockets
_rooms: dict[str, set[WebSocket]] = defaultdict(set)


async def _auth_ws(ws: WebSocket) -> User | None:
    """Authenticate WebSocket via session cookie."""
    from app.db.session import async_session

    cookie_header = ws.headers.get("cookie", "")
    session_val = None
    for part in cookie_header.split(";"):
        part = part.strip()
        if part.startswith("ws_session="):
            session_val = part[len("ws_session="):]
            break

    if not session_val:
        return None

    data = unsign_value(session_val)
    if not data or "user_id" not in data:
        return None

    async with async_session() as db:
        user = await db.get(User, data["user_id"])
        if user and user.is_active:
            return user
    return None


@router.websocket("/ws/wiki/collab")
async def wiki_collab_ws(
    ws: WebSocket,
    page_id: str = Query(...),
):
    """Yjs WebSocket relay for real-time collaborative editing."""
    user = await _auth_ws(ws)
    if not user:
        await ws.close(code=4001, reason="Unauthorized")
        return

    await ws.accept()

    room = _rooms[page_id]
    room.add(ws)
    logger.info("Wiki collab: user=%s joined page=%s (clients=%d)", user.username, page_id, len(room))

    try:
        while True:
            data = await ws.receive_bytes()
            if not data:
                continue

            # Broadcast to all other clients in the same room
            peers = [p for p in room if p is not ws and p.client_state == WebSocketState.CONNECTED]
            if peers:
                await asyncio.gather(*[_safe_send(p, data) for p in peers])

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug("Wiki collab error: %s", e)
    finally:
        room.discard(ws)
        logger.info("Wiki collab: user=%s left page=%s (clients=%d)", user.username, page_id, len(room))

        if not room:
            _rooms.pop(page_id, None)


async def _safe_send(ws: WebSocket, data: bytes):
    try:
        await ws.send_bytes(data)
    except Exception:
        pass


def get_room_clients(page_id: str) -> int:
    """Return number of clients in a room."""
    return len(_rooms.get(page_id, set()))
