"""LiveKit API client wrapper."""

from livekit import api

from app.config import get_settings

settings = get_settings()


def is_configured() -> bool:
    return bool(settings.livekit_api_key and settings.livekit_api_secret)


def get_ws_url() -> str:
    """브라우저가 접속할 공개 WebSocket URL."""
    if settings.livekit_ws_url:
        return settings.livekit_ws_url
    url = settings.app_url.rstrip("/")
    if url.startswith("https://"):
        return url.replace("https://", "wss://", 1) + "/livekit/"
    return url.replace("http://", "ws://", 1) + "/livekit/"


def generate_token(room: str, identity: str, name: str = "") -> str:
    token = (
        api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(identity)
        .with_name(name or identity)
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            )
        )
        .to_jwt()
    )
    return token


def _get_api() -> api.LiveKitAPI:
    return api.LiveKitAPI(
        settings.livekit_url,
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
    )


async def create_room(
    name: str,
    empty_timeout: int = 300,
    max_participants: int = 10,
) -> dict:
    lk = _get_api()
    try:
        room = await lk.room.create_room(
            api.CreateRoomRequest(
                name=name,
                empty_timeout=empty_timeout,
                max_participants=max_participants,
            )
        )
        return {
            "name": room.name,
            "num_participants": room.num_participants,
            "max_participants": room.max_participants,
            "creation_time": room.creation_time,
        }
    finally:
        await lk.aclose()


async def list_rooms() -> list[dict]:
    lk = _get_api()
    try:
        resp = await lk.room.list_rooms(api.ListRoomsRequest())
        return [
            {
                "name": r.name,
                "num_participants": r.num_participants,
                "max_participants": r.max_participants,
                "creation_time": r.creation_time,
            }
            for r in resp.rooms
        ]
    finally:
        await lk.aclose()


async def delete_room(name: str) -> None:
    lk = _get_api()
    try:
        await lk.room.delete_room(api.DeleteRoomRequest(room=name))
    finally:
        await lk.aclose()


async def list_participants(room: str) -> list[dict]:
    lk = _get_api()
    try:
        resp = await lk.room.list_participants(
            api.ListParticipantsRequest(room=room)
        )
        return [
            {
                "identity": p.identity,
                "name": p.name,
                "joined_at": p.joined_at,
            }
            for p in resp.participants
        ]
    finally:
        await lk.aclose()
