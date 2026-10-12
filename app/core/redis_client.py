import redis

from app.core.config import settings

redis_client = redis.Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)


def check_redis_connection() -> bool:
    return bool(redis_client.ping())
