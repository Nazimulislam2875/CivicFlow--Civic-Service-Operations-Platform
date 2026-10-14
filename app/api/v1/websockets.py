
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.service_request import ServiceRequest
from app.models.user import User
from app.services.websocket_tickets import (
    WebSocketTicketError,
    consume_websocket_ticket,
)
from app.websockets.manager import manager

router = APIRouter(tags=["WebSockets"])


def _can_access_request(user: User, service_request: ServiceRequest) -> bool:
    role = getattr(user.role, "value", user.role)

    if role == "ADMIN":
        return True

    if role == "CITIZEN":
        return getattr(service_request, "citizen_id", None) == user.id

    if role == "STAFF":
        return getattr(service_request, "assigned_to_id", None) == user.id

    if role == "SUPERVISOR":
        return True

    return False


@router.websocket("/ws/service-requests/{request_id}")
async def service_request_updates(
    websocket: WebSocket,
    request_id: int,
    ticket: str,
) -> None:
    # Tickets are short-lived and single-use.
    try:
        user_id = consume_websocket_ticket(ticket)
    except WebSocketTicketError:
        await websocket.close(
            code=1013,
            reason="Authentication service unavailable",
        )
        return

    if user_id is None:
        await websocket.close(
            code=1008,
            reason="Invalid or expired ticket",
        )
        return

    db: Session = SessionLocal()

    try:
        user = db.get(User, user_id)

        if user is None:
            await websocket.close(code=1008, reason="User not found")
            return

        service_request = db.get(ServiceRequest, request_id)

        if service_request is None:
            await websocket.close(
                code=1008,
                reason="Service request not found",
            )
            return

        if not _can_access_request(user, service_request):
            await websocket.close(code=1008, reason="Access denied")
            return

        await manager.connect(request_id, websocket)

        try:
            while True:
                # The client can send a small heartbeat message.
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            await manager.disconnect(request_id, websocket)

    finally:
        db.close()
