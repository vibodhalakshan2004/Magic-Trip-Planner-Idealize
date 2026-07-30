from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from collections import defaultdict, deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger("magictrip.http")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - started) * 1_000, 1)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = str(duration_ms)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                }
            )
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    _lock = threading.Lock()
    _requests: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/health"):
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        auth_path = request.url.path in {"/auth/login", "/auth/register"}
        limit = settings.AUTH_RATE_LIMIT_PER_MINUTE if auth_path else settings.API_RATE_LIMIT_PER_MINUTE
        bucket = f"{client}:{'auth' if auth_path else 'api'}"
        now = time.monotonic()

        with self._lock:
            requests = self._requests[bucket]
            while requests and requests[0] <= now - 60:
                requests.popleft()
            if len(requests) >= limit:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please wait a moment before trying again."},
                    headers={"Retry-After": "60"},
                )
            requests.append(now)

        return await call_next(request)
