from fastapi import FastAPI

from app.api.v1.auth import router as auth_router
from app.api.v1.categories import router as categories_router
from app.api.v1.departments import router as departments_router
from app.api.v1.health import router as health_router
from app.api.v1.service_requests import router as service_requests_router

app = FastAPI(
    title="City Service Management Platform",
    description="Backend API for managing city service requests.",
    version="0.1.0",
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
