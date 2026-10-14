import asyncio
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[int, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(
        self,
        request_id: int,
        websocket: WebSocket,
    ) -> None:
        await websocket.accept()

        async with self._lock:
            self.active_connections.setdefault(request_id, set()).add(
                websocket
            )

        logger.debug("WebSocket connected for request %s", request_id)

    async def disconnect(
        self,
        request_id: int,
        websocket: WebSocket,
    ) -> None:
        async with self._lock:
            connections = self.active_connections.get(request_id)

            if connections is None:
                return

            connections.discard(websocket)

            if not connections:
                self.active_connections.pop(request_id, None)

        logger.debug("WebSocket disconnected for request %s", request_id)

    async def broadcast(
        self,
        request_id: int,
        message: dict,
    ) -> None:
        async with self._lock:
            connections = list(
                self.active_connections.get(request_id, set())
            )

        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception:
                logger.warning(
                    "Failed to send WebSocket event for request %s",
                    request_id,
                    exc_info=True,
                )
                await self.disconnect(request_id, websocket)


manager = ConnectionManager()
