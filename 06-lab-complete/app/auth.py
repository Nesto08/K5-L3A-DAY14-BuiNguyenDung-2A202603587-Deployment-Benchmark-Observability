"""
API Key authentication (tiêu chí 6).

Yêu cầu:
  • Client gửi header X-API-Key: <key>
  • Key phải trùng biến môi trường AGENT_API_KEY
  • Thiếu hoặc sai key → HTTP 401
"""

import secrets

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader

from app.config import settings


api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
)


def verify_api_key(
    api_key: str | None = Depends(api_key_header),
) -> str:
    """Dependency xác thực API Key cho FastAPI."""

    if (
        not api_key
        or not settings.agent_api_key
        or not secrets.compare_digest(
            api_key.encode(),
            settings.agent_api_key.encode(),
        )
    ):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid API key",
        )

    return api_key