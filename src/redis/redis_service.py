from typing import Any, Optional
from .redis_client import redis_client as redis

def redis_ping():
    return redis.ping()

def redis_set(key: str, value: Any, expire: Optional[int] = None):
    return redis.set(key, value, ex=expire)

def redis_get(key: str):
    return redis.get(key)

def redis_delete(key: str):
    return redis.delete(key)

def redis_exists(key: str) -> bool:
    return redis.exists(key) == 1

def redis_incr(key: str) -> int:
    return redis.incr(key)

def redis_expire(key: str, ttl: int):
    return redis.expire(key, ttl)
