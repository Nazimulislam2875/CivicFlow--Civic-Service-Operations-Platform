
import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from app.api.v1.attachments import router as attachments_router
from app.api.v1.auth import router as auth_router
from app.api.v1.categories import router as categories_router
from app.api.v1.departments import router as departments_router
from app.api.v1.health import router as health_router
from app.api.v1.service_requests import router as service_requests_router
from app.middleware.observability import ObservabilityMiddleware
from app.websockets.redis_subscriber import run_redis_subscriber


@asynccontextmanager
async def lifespan(app: FastAPI):
    subscriber_task = asyncio.create_task(run_redis_subscriber())

    try:
        yield
    finally:
        subscriber_task.cancel()
        with suppress(asyncio.CancelledError):
            await subscriber_task


app = FastAPI(
    title="CivicFlow — Civic Service Operations Platform",
    description=(
        "Backend API for citizen service requests, staff operations, "
        "assignments, and status tracking."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(
    health_router,
    prefix="/api/v1",
    tags=["Health"],
)

app.include_router(
    auth_router,
    prefix="/api/v1/auth",
    tags=["Authentication"],
)

app.include_router(
    departments_router,
    prefix="/api/v1/departments",
    tags=["Departments"],
)

app.include_router(
    categories_router,
    prefix="/api/v1/categories",
    tags=["Categories"],
)

app.include_router(
    service_requests_router,
    prefix="/api/v1/service-requests",
    tags=["Service Requests"],
)

app.include_router(
    attachments_router,
    prefix="/api/v1",
)

app.add_middleware(ObservabilityMiddleware)
