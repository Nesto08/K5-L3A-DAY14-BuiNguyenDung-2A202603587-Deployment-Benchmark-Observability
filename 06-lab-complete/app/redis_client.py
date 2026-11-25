"""
Redis connection — shared state for production agent.
"""

import redis
from redis.exceptions import RedisError

from app.config import settings


redis_client = redis.Redis.from_url(
    settings.redis_url,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)


def get_redis():
    """Return the shared Redis client."""
    return redis_client


def redis_healthy() -> bool:
    """Check whether Redis is available."""
    try:
        return bool(redis_client.ping())
    except RedisError:
        return False