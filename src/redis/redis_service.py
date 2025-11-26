from typing import Any, Optional
from .redis_client import redis_client as redis

async def redis_ping():
    return await redis.ping()

async def redis_set(key: str, value: Any, expire: Optional[int] = None):
    return await redis.set(key, value, ex=expire)

async def redis_get(key: str):
    return await redis.get(key)

async def redis_delete(key: str):
    return await redis.delete(key)

async def redis_exists(key: str) -> bool:
    return await redis.exists(key) == 1

async def redis_incr(key: str) -> int:
    return await redis.incr(key)

async def redis_expire(key: str, ttl: int):
    return await redis.expire(key, ttl)