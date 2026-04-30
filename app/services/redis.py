from __future__ import annotations

from redis.asyncio import Redis

from app.core.config import get_settings

redis_client: Redis | None = None


def create_redis_client() -> Redis:
    settings = get_settings()
    return Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)


async def init_redis() -> Redis:
    global redis_client

    if redis_client is None:
        redis_client = create_redis_client()

    return redis_client


def get_redis() -> Redis:
    if redis_client is None:
        raise RuntimeError("Redis client is not initialized")

    return redis_client


async def check_redis_connection() -> bool:
    try:
        client = redis_client or await init_redis()
        return bool(await client.ping())
    except Exception:
        return False


async def close_redis() -> None:
    global redis_client

    if redis_client is not None:
        await redis_client.aclose()
        redis_client = None
