import re
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.metrics import http_request_duration_seconds, http_requests_total


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        # Skip metrics and health endpoints
        if request.url.path in ("/metrics", "/health"):
            return await call_next(request)

        start_time = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start_time

        # Normalize path (replace UUIDs with {id})
        path = request.url.path
        # Simple UUID pattern replacement
        path = re.sub(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "{id}", path
        )

        http_requests_total.labels(
            method=request.method,
            endpoint=path,
            status=response.status_code,
        ).inc()

        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=path,
        ).observe(duration)

        return response
