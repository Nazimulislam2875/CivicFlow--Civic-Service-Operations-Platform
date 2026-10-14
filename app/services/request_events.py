
import logging
from typing import Any

from app.websockets.events import publish_request_event

logger = logging.getLogger(__name__)


async def publish_request_status_changed(
    *,
    request_id: int,
    status_value: str,
    actor_id: int,
    extra: dict[str, Any] | None = None,
) -> None:
    """
    Publish a status-change event after the database transaction commits.

    This function must be called only after a successful DB commit.
    """
    data: dict[str, Any] = {
        "status": status_value,
        "actor_id": actor_id,
    }

    if extra:
        data.update(extra)

    try:
        await publish_request_event(
            request_id=request_id,
            event="request.status_changed",
            data=data,
        )
    except Exception:
        # The status change has already committed. A WebSocket failure
        # must not turn a successful database update into an API failure.
        logger.exception(
            "Failed to broadcast request status change",
            extra={"request_id": request_id},
        )
