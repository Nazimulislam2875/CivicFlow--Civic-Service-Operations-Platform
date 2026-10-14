
from typing import Any

from sqlalchemy.orm import Session

from app.models.outbox_event import OutboxEvent


def enqueue_event(
    db: Session,
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: int,
    payload: dict[str, Any],
) -> OutboxEvent:
    """
    Add an event to the current transaction.
    The caller is responsible for committing or rolling back.
    """
    event = OutboxEvent(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload=payload,
    )
    db.add(event)
    db.flush()
    return event
