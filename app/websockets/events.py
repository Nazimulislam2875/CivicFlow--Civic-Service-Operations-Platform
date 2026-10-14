
from typing import Any

from app.websockets.manager import manager


async def publish_request_event(
    request_id: int,
    event: str,
    data: dict[str, Any],
) -> None:
    await manager.broadcast(
        request_id,
        {
            "event": event,
            "request_id": request_id,
            "data": data,
        },
    )
