
import asyncio
import json
import logging
from contextlib import suppress
from typing import Any

import redis.asyncio as redis
from app.websockets.manager import manager
from redis.exceptions import RedisError

from app.core.config import settings
from app.tasks.outbox import OUTBOX_CHANNEL

logger = logging.getLogger(__name__)


async def run_redis_subscriber() -> None:
    client = redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=None,
    )

    pubsub = client.pubsub()

    try:
        await pubsub.subscribe(OUTBOX_CHANNEL)
        logger.info("Subscribed to Redis channel %s", OUTBOX_CHANNEL)

        while True:
            try:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )

                if message is None:
                    await asyncio.sleep(0.05)
                    continue

                try:
                    event: dict[str, Any] = json.loads(message["data"])
                    payload = event.get("payload", {})
                    event_type = event.get("event_type")
                    request_id = event.get("aggregate_id")

                    if (
                        event.get("aggregate_type") != "service_request"
                        or not isinstance(request_id, int)
                        or not isinstance(payload, dict)
                        or not isinstance(event_type, str)
                    ):
                        logger.warning("Ignoring malformed outbox event")
                        continue

                    await manager.broadcast(
                        request_id,
                        {
                            "event": event_type,
                            "request_id": request_id,
                            "data": payload,
                            "event_id": event.get("id"),
                        },
                    )

                except (ValueError, TypeError, KeyError):
                    logger.exception("Invalid Redis event payload")

            except RedisError:
                logger.exception("Redis subscriber error; reconnecting")
                await asyncio.sleep(2)
                with suppress(RedisError):
                    await pubsub.unsubscribe(OUTBOX_CHANNEL)
                await pubsub.close()
                pubsub = client.pubsub()
                await pubsub.subscribe(OUTBOX_CHANNEL)

    finally:
        await pubsub.aclose()
        await client.aclose()
