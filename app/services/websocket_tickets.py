
import secrets

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings


class WebSocketTicketError(RuntimeError):
    pass


def _get_redis() -> Redis:
    return Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )


def create_websocket_ticket(user_id: int) -> str:
    """Create a short-lived, single-use WebSocket ticket."""
    ticket = secrets.token_urlsafe(32)
    key = f"ws-ticket:{ticket}"

    try:
        with _get_redis() as redis:
            redis.set(
                key,
                str(user_id),
                ex=60,
                nx=True,
            )
    except RedisError as exc:
        raise WebSocketTicketError(
            "WebSocket ticket service is unavailable"
        ) from exc

    return ticket


def consume_websocket_ticket(ticket: str) -> int | None:
    """Atomically consume a ticket so it cannot be reused."""
    if not ticket or len(ticket) > 128:
        return None

    try:
        with _get_redis() as redis:
            # GETDEL requires Redis 6.2 or newer.
            value = redis.execute_command(
                "GETDEL",
                f"ws-ticket:{ticket}",
            )
    except RedisError as exc:
        raise WebSocketTicketError(
            "WebSocket ticket service is unavailable"
        ) from exc

    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None
