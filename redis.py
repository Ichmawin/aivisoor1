import json
from typing import Any, Optional
import redis.asyncio as aioredis
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


async def cache_get(key: str) -> Optional[Any]:
    try:
        r = await get_redis()
        value = await r.get(key)
        return json.loads(value) if value else None
    except Exception as e:
        logger.warning(f"Cache GET error for {key}: {e}")
        return None


async def cache_set(key: str, value: Any, ttl: int = settings.CACHE_TTL) -> None:
    try:
        r = await get_redis()
        await r.setex(key, ttl, json.dumps(value, default=str))
    except Exception as e:
        logger.warning(f"Cache SET error for {key}: {e}")


async def cache_delete(key: str) -> None:
    try:
        r = await get_redis()
        await r.delete(key)
    except Exception as e:
        logger.warning(f"Cache DELETE error for {key}: {e}")


async def cache_delete_pattern(pattern: str) -> None:
    try:
        r = await get_redis()
        keys = await r.keys(pattern)
        if keys:
            await r.delete(*keys)
    except Exception as e:
        logger.warning(f"Cache DELETE pattern error for {pattern}: {e}")


async def rate_limit_check(key: str, limit: int, window: int = 60) -> bool:
    """Returns True if within limit, False if exceeded."""
    try:
        r = await get_redis()
        pipe = r.pipeline()
        await pipe.incr(key)
        await pipe.expire(key, window)
        results = await pipe.execute()
        return results[0] <= limit
    except Exception:
        return True  # Fail open on Redis error
