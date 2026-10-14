
from fastapi import APIRouter

from app.api.v1.attachments import router as attachments_router
from app.api.v1.audit_logs import router as audit_logs_router
from app.api.v1.metrics import router as metrics_router
from app.api.v1.websocket_tickets import router as websocket_tickets_router
from app.api.v1.websockets import router as websockets_router

api_router = APIRouter()

api_router.include_router(audit_logs_router)


api_router.include_router(attachments_router)

api_router.include_router(websockets_router)

api_router.include_router(metrics_router)

api_router.include_router(websocket_tickets_router)
