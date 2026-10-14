import logging
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


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", "").strip()

        if not request_id or len(request_id) > 128:
            request_id = str(uuid.uuid4())

        started_at = time.perf_counter()
        response = None

        # Avoid using query parameters in logs because they can contain secrets.
        try:
            response = await call_next(request)
            return response
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
        finally:
            duration = time.perf_counter() - started_at
            status_code = response.status_code if response else 500

            # Do not use raw path parameters as labels; that can create
            # unbounded Prometheus time series.
            route = request.scope.get("route")
            metric_path = getattr(route, "path", request.url.path)

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

            if response is not None:
                response.headers["X-Request-ID"] = request_id