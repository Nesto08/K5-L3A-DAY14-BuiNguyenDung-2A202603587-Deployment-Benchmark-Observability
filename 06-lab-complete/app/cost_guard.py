"""
Cost guard — Redis-backed daily budget.
"""

import math
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from redis.exceptions import RedisError

from app.config import settings
from app.redis_client import get_redis


# Estimated pricing for mock usage.
INPUT_PRICE_PER_1K = 0.00015
OUTPUT_PRICE_PER_1K = 0.00060


def budget_key() -> str:
    """Return the Redis key for today's budget."""

    today = datetime.now(timezone.utc).date()

    return f"cost_guard:daily:{today.isoformat()}"


def seconds_until_midnight() -> int:
    now = datetime.now(timezone.utc)

    tomorrow = (now + timedelta(days=1)).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    return max(
        1,
        int((tomorrow - now).total_seconds()),
    )


def get_total_cost() -> float:
    try:
        value = get_redis().get(budget_key())

        return int(value or 0) / 1_000_000

    except RedisError:
        raise HTTPException(
            status_code=503,
            detail="Cost guard service unavailable",
        )


def check_budget() -> None:
    """Reject requests when the daily budget is exhausted."""

    total_cost = get_total_cost()

    if total_cost >= settings.daily_budget_usd:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "Daily budget exceeded",
                "used_usd": total_cost,
                "budget_usd": settings.daily_budget_usd,
            },
        )


def record_cost(
    input_tokens: int,
    output_tokens: int,
) -> float:
    """Estimate and record mock LLM usage."""

    cost = (
        input_tokens / 1000 * INPUT_PRICE_PER_1K
        + output_tokens / 1000 * OUTPUT_PRICE_PER_1K
    )

    # Store integer micro-dollars to avoid float accumulation.
    cost_micros = max(
        1,
        math.ceil(cost * 1_000_000),
    )

    try:
        key = budget_key()

        with get_redis().pipeline(transaction=True) as pipe:
            pipe.incrby(key, cost_micros)
            pipe.expire(key, seconds_until_midnight())

            total_micros, _ = pipe.execute()

        return total_micros / 1_000_000

    except RedisError:
        raise HTTPException(
            status_code=503,
            detail="Cost recording unavailable",
        )