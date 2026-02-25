"""In-memory store for meeting room metadata and join requests."""

import time
import uuid
from dataclasses import dataclass, field


@dataclass
class JoinRequest:
    id: str
    nickname: str
    status: str = "pending"  # pending | approved | denied
    created_at: float = field(default_factory=time.time)
    livekit_token: str | None = None


@dataclass
class RoomMeta:
    name: str
    host_user_id: str
    host_username: str
    host_display_name: str
    share_token: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_at: float = field(default_factory=time.time)
    requests: dict[str, JoinRequest] = field(default_factory=dict)


# room_name → RoomMeta
_rooms: dict[str, RoomMeta] = {}
# share_token → room_name (역참조)
_tokens: dict[str, str] = {}


def create_room_meta(
    name: str,
    host_user_id: str,
    host_username: str,
    host_display_name: str,
) -> RoomMeta:
    meta = RoomMeta(
        name=name,
        host_user_id=host_user_id,
        host_username=host_username,
        host_display_name=host_display_name,
    )
    _rooms[name] = meta
    _tokens[meta.share_token] = name
    return meta


def get_room_meta(name: str) -> RoomMeta | None:
    return _rooms.get(name)


def get_room_by_token(token: str) -> RoomMeta | None:
    name = _tokens.get(token)
    if name:
        return _rooms.get(name)
    return None


def delete_room_meta(name: str) -> None:
    meta = _rooms.pop(name, None)
    if meta:
        _tokens.pop(meta.share_token, None)


def create_join_request(room_name: str, nickname: str) -> JoinRequest | None:
    meta = _rooms.get(room_name)
    if not meta:
        return None
    req = JoinRequest(id=uuid.uuid4().hex[:8], nickname=nickname)
    meta.requests[req.id] = req
    return req


def get_join_request(room_name: str, request_id: str) -> JoinRequest | None:
    meta = _rooms.get(room_name)
    if not meta:
        return None
    return meta.requests.get(request_id)


def get_pending_requests(room_name: str) -> list[JoinRequest]:
    meta = _rooms.get(room_name)
    if not meta:
        return []
    return [r for r in meta.requests.values() if r.status == "pending"]
