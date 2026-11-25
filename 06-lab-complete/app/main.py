"""
Production AI Agent — Part 6 Final Project.
"""

import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_budget, record_cost
from app.rate_limiter import check_rate_limit
from app.redis_client import get_redis, redis_healthy
from utils.mock_llm import ask as llm_ask


# Structured logging
class JsonFormatter(logging.Formatter):
    def format(self, record):
        data = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "lvl": record.levelname,
            "event": record.getMessage(),
        }

        for key in (
            "path",
            "method",
            "status",
            "ms",
        ):
            if hasattr(record, key):
                data[key] = getattr(record, key)

        return json.dumps(data, ensure_ascii=False)


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.handlers.clear()
logger.addHandler(handler)
logger.propagate = False

START_TIME = time.monotonic()


# Graceful shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("agent_startup")

    try:
        yield

    finally:
        logger.info("graceful_shutdown")

        get_redis().close()

        logger.info("agent_shutdown_complete")


app = FastAPI(
    title="Production AI Agent",
    lifespan=lifespan,
)


# Request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()

    response = await call_next(request)

    duration_ms = (
        time.perf_counter() - start
    ) * 1000

    logger.info(
        "request",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status": response.status_code,
            "ms": round(duration_ms, 2),
        },
    )

    return response


class AskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
    )

    user_id: str | None = None


# Criterion 4 — Liveness
@app.get("/health")
def health():
    return {
        "status": "ok",
        "uptime_seconds": round(
            time.monotonic() - START_TIME,
            1,
        ),
        "environment": settings.environment,
    }


# Criterion 5 — Readiness
@app.get("/ready")
def ready():
    if not redis_healthy():
        raise HTTPException(
            status_code=503,
            detail="Redis unavailable",
        )

    return {
        "ready": True,
        "redis": "connected",
    }


# Criteria 6, 7, 8 — Protected AI endpoint
@app.post("/ask")
def ask(
    body: AskRequest,
    api_key: str = Depends(verify_api_key),
):
    # Check daily budget.
    check_budget()

    # Check rate limit.
    remaining = check_rate_limit(api_key)

    # Call mock LLM.
    answer = llm_ask(body.question)

    # Estimate token usage.
    input_tokens = max(
        1,
        len(body.question.split()) * 2,
    )

    output_tokens = max(
        1,
        len(answer.split()) * 2,
    )

    # Record estimated cost.
    total_cost = record_cost(
        input_tokens,
        output_tokens,
    )

    return {
        "question": body.question,
        "answer": answer,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "requests_remaining": remaining,
            "total_cost_usd": total_cost,
        },
    }