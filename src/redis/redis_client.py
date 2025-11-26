from redis import Redis
from src.redis.config import RedisConfig

redis_config = RedisConfig()

redis_client = Redis.from_url(
    redis_config.url,
    decode_responses=True
)
