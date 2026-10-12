import json
import logging
from typing import Any

from redis.exceptions import RedisError

from app.core.redis_client import redis_client

logger = logging.getLogger(__name__)

SERVICE_REQUEST_LIST_PREFIX = "service-requests:list:"
SERVICE_REQUEST_LIST_TTL = 60


def get_cached_json(key: str) -> Any | None:
    try:
        value = redis_client.get(key)
        return json.loads(value) if value is not None else None
    except (RedisError, OSError, ValueError):
        logger.warning("Redis cache read failed", exc_info=True)
        return None


def set_cached_json(
    key: str,
    value: Any,
    ttl: int = SERVICE_REQUEST_LIST_TTL,
) -> None:
    try:
        redis_client.set(
            key,
            json.dumps(value, separators=(",", ":")),
            ex=ttl,
        )
    except (RedisError, OSError, TypeError, ValueError):
        logger.warning("Redis cache write failed", exc_info=True)


def invalidate_service_request_lists() -> None:
    pattern = f"{SERVICE_REQUEST_LIST_PREFIX}*"

    try:
        keys = redis_client.scan_iter(match=pattern, count=100)
        batch: list[str] = []

        for key in keys:
            batch.append(key)

            if len(batch) >= 100:
                redis_client.delete(*batch)
                batch.clear()

        if batch:
            redis_client.delete(*batch)
    except (RedisError, OSError):
        logger.warning(
            "Service request cache invalidation failed",
            exc_info=True,
        )
