"""Chat presence management via Redis SET."""

from app.chat.redis_client import get_redis

ONLINE_KEY = "chat:online"
WS_KEY_PREFIX = "chat:user:"
WS_TTL = 60  # seconds


async def set_online(user_id: str) -> None:
    r = await get_redis()
    pipe = r.pipeline()
    pipe.sadd(ONLINE_KEY, user_id)
    pipe.set(f"{WS_KEY_PREFIX}{user_id}:ws", "1", ex=WS_TTL)
    await pipe.execute()


async def set_offline(user_id: str) -> None:
    r = await get_redis()
    pipe = r.pipeline()
    pipe.srem(ONLINE_KEY, user_id)
    pipe.delete(f"{WS_KEY_PREFIX}{user_id}:ws")
    await pipe.execute()


async def refresh_heartbeat(user_id: str) -> None:
    r = await get_redis()
    await r.set(f"{WS_KEY_PREFIX}{user_id}:ws", "1", ex=WS_TTL)


async def get_online_users() -> set[str]:
    r = await get_redis()
    return await r.smembers(ONLINE_KEY)


async def is_online(user_id: str) -> bool:
    r = await get_redis()
    return await r.sismember(ONLINE_KEY, user_id)
