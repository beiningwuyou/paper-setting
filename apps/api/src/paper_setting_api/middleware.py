from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from re import compile as compile_pattern

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import Response
from paper_setting_runtime.config import Settings
from paper_setting_runtime.logging import get_logger

from paper_setting_api.errors import problem_response

REQUEST_ID_PATTERN = compile_pattern(r"^[A-Za-z0-9._-]{1,128}$")


def _request_id(request: Request) -> str:
    supplied = request.headers.get("X-Request-Id", "")
    return supplied if REQUEST_ID_PATTERN.fullmatch(supplied) else str(uuid.uuid4())


def _apply_response_headers(
    response: Response,
    *,
    request_id: str,
    limit: int,
    remaining: int,
) -> None:
    response.headers["X-Request-Id"] = request_id
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; connect-src 'self' http://127.0.0.1:8765 http://localhost:8765 http://127.0.0.1:8766 http://localhost:8766"
    )


def install_middleware(app: FastAPI, settings: Settings) -> None:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Last-Event-ID", "X-Request-Id"],
        expose_headers=["X-Request-Id", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
    )
    requests: dict[str, deque[float]] = defaultdict(deque)
    limit = settings.api_rate_limit_per_minute

    @app.middleware("http")
    async def local_security_and_observability(request: Request, call_next):
        request_id = _request_id(request)
        request.state.request_id = request_id
        structlog.contextvars.bind_contextvars(request_id=request_id)
        started = time.perf_counter()
        response: Response | None = None
        remaining = limit
        try:
            origin = request.headers.get("origin")
            same_origin = f"{request.url.scheme}://{request.headers.get('host', '')}"
            if origin and origin != same_origin and origin not in settings.allowed_origins:
                response = problem_response(
                    request,
                    title="Forbidden",
                    status=403,
                    detail="请求来源不在本地服务允许范围内",
                    code="ORIGIN_NOT_ALLOWED",
                )
            else:
                client = request.client.host if request.client else "local"
                now = time.monotonic()
                window = requests[client]
                while window and window[0] < now - 60:
                    window.popleft()
                remaining = limit - len(window)
                if len(window) >= limit:
                    response = problem_response(
                        request,
                        title="Too Many Requests",
                        status=429,
                        detail="本地服务请求过于频繁，请稍后重试",
                        code="RATE_LIMITED",
                    )
                    response.headers["Retry-After"] = "60"
                else:
                    window.append(now)
                    remaining = limit - len(window)
                    response = await call_next(request)

            _apply_response_headers(
                response,
                request_id=request_id,
                limit=limit,
                remaining=remaining,
            )
            if request.url.path.startswith("/api/"):
                response.headers.setdefault("Cache-Control", "no-store")
            get_logger().info(
                "http_request",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
            )
            return response
        finally:
            structlog.contextvars.clear_contextvars()
