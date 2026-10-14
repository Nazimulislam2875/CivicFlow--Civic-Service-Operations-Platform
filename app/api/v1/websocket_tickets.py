
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.services.websocket_tickets import (
    WebSocketTicketError,
    create_websocket_ticket,
)

router = APIRouter(tags=["WebSockets"])


class WebSocketTicketResponse(BaseModel):
    ticket: str
    expires_in: int = 60


@router.post(
    "/websocket-tickets",
    response_model=WebSocketTicketResponse,
)
def issue_websocket_ticket(
    current_user: Annotated[object, Depends(get_current_user)],
) -> WebSocketTicketResponse:
    try:
        ticket = create_websocket_ticket(current_user.id)
    except WebSocketTicketError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WebSocket authentication is temporarily unavailable",
        ) from exc

    return WebSocketTicketResponse(ticket=ticket)
