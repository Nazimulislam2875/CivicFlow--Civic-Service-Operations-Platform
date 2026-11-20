import logging

import redis
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)

redis_client = redis.Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)


def check_redis_connection() -> bool:
    try:
        return bool(redis_client.ping())
    except (RedisError, OSError):
        logger.warning("Redis connection check failed", exc_info=True)
        return False
