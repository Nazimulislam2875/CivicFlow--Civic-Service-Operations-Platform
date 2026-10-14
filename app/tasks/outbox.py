
import json
import logging
from datetime import UTC, datetime

import redis
from celery import shared_task
from redis.exceptions import RedisError
from sqlalchemy import select

from app.core.config import settings
from app.db.database import SessionLocal
from app.models.outbox_event import OutboxEvent

logger = logging.getLogger(__name__)

OUTBOX_CHANNEL = "city-service-events"
BATCH_SIZE = 100
MAX_ATTEMPTS = 10


@shared_task(
    name="outbox.publish_pending_events",
    bind=True,
    max_retries=5,
    default_retry_delay=10,
)
def publish_pending_events(self) -> dict[str, int]:
    published = 0
    failed = 0

    client = redis.Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=3,
    )

    try:
        with SessionLocal() as db:
            events = db.scalars(
                select(OutboxEvent)
                .where(
                    OutboxEvent.published_at.is_(None),
                    OutboxEvent.attempts < MAX_ATTEMPTS,
                )
                .order_by(OutboxEvent.id)
                .limit(BATCH_SIZE)
                .with_for_update(skip_locked=True)
            ).all()

            for event in events:
                try:
                    message = {
                        "id": event.id,
                        "event_type": event.event_type,
                        "aggregate_type": event.aggregate_type,
                        "aggregate_id": event.aggregate_id,
                        "payload": event.payload,
                        "created_at": (
                            event.created_at.isoformat()
                            if event.created_at
                            else None
                        ),
                    }

                    # PUBLISH returns the number of current subscribers.
                    subscriber_count = client.publish(
                        OUTBOX_CHANNEL,
                        json.dumps(message),
                    )

                    if subscriber_count == 0:
                        event.attempts += 1
                        event.last_error = "No active Redis subscribers"
                        failed += 1
                        continue

                    event.published_at = datetime.now(UTC)
                    event.last_error = None
                    published += 1

                except RedisError as exc:
                    event.attempts += 1
                    event.last_error = str(exc)[:500]
                    failed += 1

                    logger.exception(
                        "Outbox event publish failed",
                        extra={"outbox_event_id": event.id},
                    )

            db.commit()

    except Exception as exc:
        logger.exception("Outbox dispatcher failed")
        raise self.retry(exc=exc) from exc

    finally:
        client.close()

    return {"published": published, "failed": failed}
