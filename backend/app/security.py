import time
from collections import defaultdict
from typing import Dict, List
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from .config import settings

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    In-memory sliding-window rate limiter per client IP.
    Protects synthesis and data endpoints from abuse and DoS.
    """
    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = defaultdict(list)

    def _clean_old_requests(self, client_ip: str, current_time: float):
        cutoff = current_time - self.window_seconds
        self.requests[client_ip] = [t for t in self.requests[client_ip] if t > cutoff]

    async def dispatch(self, request: Request, call_next):
        # Exclude static assets or documentation from aggressive throttling
        if request.url.path in ("/", "/docs", "/openapi.json", "/api/health"):
            return await call_next(request)

        # Determine client identifier (header or client host)
        client_ip = request.headers.get("X-Forwarded-For")
        if client_ip:
            client_ip = client_ip.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "127.0.0.1"

        now = time.time()
        self._clean_old_requests(client_ip, now)

        # Stricter limit specifically for heavy TTS generation
        limit = self.max_requests
        if request.url.path == "/api/tts" and request.method == "POST":
            limit = min(self.max_requests, 30)  # max 30 synthesis calls per minute per IP

        if len(self.requests[client_ip]) >= limit:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Please wait before generating more audio.",
                    "retry_after_seconds": int(self.window_seconds - (now - self.requests[client_ip][0]))
                },
                headers={"Retry-After": str(self.window_seconds)}
            )

        self.requests[client_ip].append(now)
        response = await call_next(request)
        return response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Enforces essential HTTP security headers across all API responses.
    """
    async def dispatch(self, request: Request, call_next):
        if request.url.path in ("/docs", "/openapi.json"):
            return await call_next(request)

        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(self), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "media-src 'self' blob: data:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-eval' 'unsafe-inline'; "
            "connect-src 'self' http://localhost:8000 http://127.0.0.1:8000 http://localhost:3000 http://127.0.0.1:3000;"
        )
        return response
