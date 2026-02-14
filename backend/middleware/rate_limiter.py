"""
Rate limiting middleware using Redis.

Limits requests per user (by tg_userid from initData) or IP address.
"""

import hashlib
import logging
import re
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from backend.config import RATE_LIMIT_REQUESTS
from backend.redis_client import redis_client

logger = logging.getLogger(__name__)

# Endpoints to skip rate limiting
SKIP_ENDPOINTS = {
    "/health",
    "/docs",
    "/openapi.json",
    "/favicon.ico",
}

# Endpoints with custom limits (endpoint: max_requests_per_minute)
CUSTOM_LIMITS = {
    "/api/external-auth/register": 10,  # Stricter limit for token registration
    "/api/create_user": 20,  # Stricter limit for user creation
}


def extract_tg_userid_from_init_data(init_data: str) -> str | None:
    """
    Extract tg_userid from Telegram initData string.

    Args:
        init_data: URL-encoded initData from Telegram Mini App

    Returns:
        tg_userid as string or None if not found
    """
    try:
        # initData contains user={"id":123,...}
        # URL decoded format: user=%7B%22id%22%3A123...
        from urllib.parse import parse_qs, unquote

        decoded = unquote(init_data)
        params = parse_qs(decoded)

        if "user" in params:
            import json

            user_data = json.loads(params["user"][0])
            if "id" in user_data:
                return str(user_data["id"])

        # Try direct regex as fallback
        match = re.search(r'"id"\s*:\s*(\d+)', decoded)
        if match:
            return match.group(1)

    except Exception as e:
        logger.debug(f"Failed to extract tg_userid: {e}")

    return None


def get_client_ip(request: Request) -> str:
    """Get client IP from request headers or connection."""
    # Check common proxy headers
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take first IP in chain
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fallback to direct connection
    if request.client:
        return request.client.host

    return "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware.

    Limits requests based on tg_userid (from initData) or IP address.
    Uses Redis for distributed rate limiting.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and apply rate limiting."""
        path = request.url.path

        # Skip rate limiting for certain endpoints
        if path in SKIP_ENDPOINTS or path.startswith("/assets"):
            return await call_next(request)

        # Determine rate limit
        max_requests = CUSTOM_LIMITS.get(path, RATE_LIMIT_REQUESTS)

        # Try to get identifier (prefer tg_userid over IP)
        identifier = None

        # Check query params for initData
        init_data = request.query_params.get("initData")
        if init_data:
            identifier = extract_tg_userid_from_init_data(init_data)

        # Check Authorization header
        if not identifier:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                # Use token hash as identifier
                token = auth_header[7:]
                identifier = f"token:{hashlib.sha256(token.encode()).hexdigest()[:16]}"

        # Fallback to IP
        if not identifier:
            identifier = f"ip:{get_client_ip(request)}"

        # Check rate limit using Redis
        is_allowed, remaining = await redis_client.check_rate_limit(
            identifier=identifier,
            max_requests=max_requests,
            window_seconds=60,
        )

        if not is_allowed:
            logger.warning(f"Rate limit exceeded for {identifier}")
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Слишком много запросов. Попробуйте позже.",
                    "error_code": "RATE_LIMIT_EXCEEDED",
                },
                headers={
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": "60",
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response
