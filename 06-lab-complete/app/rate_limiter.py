"""
Rate limiting — Redis-backed fixed window.
"""

import hashlib

from fastapi import HTTPException
from redis.exceptions import RedisError

from app.config import settings
from app.redis_client import get_redis


RATE_LIMIT_SCRIPT = """
local count = redis.call('INCR', KEYS[1])

if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end

local ttl = redis.call('TTL', KEYS[1])

return {count, ttl}
"""


def check_rate_limit(api_key: str) -> int:
    """Check request limit and return remaining requests."""

    key_hash = hashlib.sha256(
        api_key.encode()
    ).hexdigest()

    redis_key = f"rate_limit:{key_hash}"

    try:
        count, ttl = get_redis().eval(
            RATE_LIMIT_SCRIPT,
            1,
            redis_key,
            60,
        )

    except RedisError:
        raise HTTPException(
            status_code=503,
            detail="Rate limiting service unavailable",
        )

    limit = settings.rate_limit_per_minute

    if count > limit:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={
                "Retry-After": str(max(1, ttl)),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
            },
        )

    return max(0, limit - count)