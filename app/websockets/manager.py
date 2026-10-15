
import asyncio
from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    """Manage WebSocket connections grouped by service request."""

    def __init__(self) -> None:
        self._rooms: dict[int, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, request_id: int, websocket: WebSocket) -> None:
        await websocket.accept()

        async with self._lock:
            self._rooms[request_id].add(websocket)

    async def disconnect(
        self,
        request_id: int,
        websocket: WebSocket,
    ) -> None:
        async with self._lock:
            connections = self._rooms.get(request_id)

            if connections is None:
                return

            connections.discard(websocket)

            if not connections:
                self._rooms.pop(request_id, None)

    async def broadcast(
        self,
        request_id: int,
        message: dict[str, Any],
    ) -> None:
        async with self._lock:
            connections = list(self._rooms.get(request_id, set()))

        if not connections:
            return

        results = await asyncio.gather(
            *(
                self._send_safely(websocket, message)
                for websocket in connections
            ),
            return_exceptions=True,
        )

        failed = [
            websocket
            for websocket, result in zip(connections, results)
            if isinstance(result, Exception) or result is False
        ]

        for websocket in failed:
            await self.disconnect(request_id, websocket)

    async def _send_safely(
        self,
        websocket: WebSocket,
        message: dict[str, Any],
    ) -> bool:
        try:
            await websocket.send_json(message)
            return True
        except Exception:
            return False


manager = ConnectionManager()
