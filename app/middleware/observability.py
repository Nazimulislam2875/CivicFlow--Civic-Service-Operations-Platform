import logging
import re
import time
import uuid

from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("app.http")

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
)

REQUEST_ID_PATTERN = re.compile(r"^[a-zA-Z0-9._-]{1,128}$")


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", "").strip()

        if not REQUEST_ID_PATTERN.fullmatch(request_id):
            request_id = str(uuid.uuid4())

        request.state.request_id = request_id
        started_at = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "Unhandled request exception",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                },
            )
            raise
        else:
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            duration = time.perf_counter() - started_at

            route = request.scope.get("route")
            metric_path = getattr(route, "path", request.url.path)

            status_code = response.status_code if "response" in locals() else 500

            HTTP_REQUESTS_TOTAL.labels(
                method=request.method,
                path=metric_path,
                status_code=str(status_code),
            ).inc()

            HTTP_REQUEST_DURATION.labels(
                method=request.method,
                path=metric_path,
            ).observe(duration)

            logger.info(
                "HTTP request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_seconds": round(duration, 6),
                },
            )
