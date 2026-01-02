"""WebSocket support for real-time communication.

Provides ConnectionManager for handling multiple WebSocket connections,
WebSocketProgressBroadcaster for adapting FolderEventHandler callbacks,
and WebSocketLogHandler for streaming logs to connected clients.

Usage:
    manager = ConnectionManager()
    await manager.connect(websocket)
    await manager.broadcast({"type": "progress", "data": {...}})
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = logging.getLogger(__name__)


# =============================================================================
# Message Types
# =============================================================================


@dataclass
class WebSocketMessage:
    """Structured WebSocket message with automatic timestamp.

    Attributes:
        type: Message type (progress, status, chat, log, command).
        data: Message payload.
        timestamp: ISO 8601 timestamp (auto-generated if not provided).
    """

    type: str
    data: dict[str, Any]
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert message to JSON-serializable dictionary.

        Returns:
            Dictionary with type, data, and timestamp.
        """
        return {
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp,
        }


# =============================================================================
# Connection Manager
# =============================================================================


class ConnectionManager:
    """Manage active WebSocket connections.

    Handles connection lifecycle (connect, disconnect, close_all) and
    message distribution (send_personal_message, broadcast).

    Thread-safe through asyncio.Lock for concurrent access protection.

    Attributes:
        active_connections: List of currently connected WebSockets.
    """

    def __init__(self) -> None:
        """Initialize connection manager with empty connection list."""
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    @property
    def active_connections(self) -> list[WebSocket]:
        """Get list of active WebSocket connections.

        Returns:
            Copy of the connections list.
        """
        return list(self._connections)

    @property
    def connection_count(self) -> int:
        """Get number of active connections.

        Returns:
            Count of connected clients.
        """
        return len(self._connections)

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection.

        Args:
            websocket: FastAPI WebSocket instance to connect.
        """
        await websocket.accept()
        async with self._lock:
            self._connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {self.connection_count}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection from active connections.

        Safe to call even if the WebSocket was never connected.

        Args:
            websocket: WebSocket instance to remove.
        """
        try:
            self._connections.remove(websocket)
            count = self.connection_count
            logger.info(f"WebSocket disconnected. Remaining: {count}")
        except ValueError:
            pass  # WebSocket was not in the list

    async def send_personal_message(
        self, message: dict[str, Any], websocket: WebSocket
    ) -> None:
        """Send a message to a specific WebSocket client.

        Args:
            message: Dictionary to send as JSON.
            websocket: Target WebSocket connection.
        """
        await websocket.send_json(message)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all connected clients.

        Handles disconnected clients gracefully by removing them from
        the active connections list.

        Args:
            message: Dictionary to broadcast as JSON.
        """
        if not self._connections:
            return

        disconnected: list[WebSocket] = []

        for connection in self._connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                disconnected.append(connection)

        # Remove failed connections
        for ws in disconnected:
            self.disconnect(ws)

    async def close_all(self) -> None:
        """Close all active WebSocket connections.

        Used during server shutdown to cleanly terminate all connections.
        """
        async with self._lock:
            for connection in self._connections:
                try:
                    await connection.close()
                except Exception as e:
                    logger.warning(f"Error closing WebSocket: {e}")
            self._connections.clear()

        logger.info("All WebSocket connections closed")


# =============================================================================
# Progress Broadcaster (Adapter for FolderEventHandler callbacks)
# =============================================================================


class WebSocketProgressBroadcaster:
    """Adapter between FolderEventHandler callbacks and WebSocket broadcasting.

    Converts progress and event callbacks from the file processing system
    into structured WebSocket messages and broadcasts them to all connected
    clients.

    Provides both async methods (on_progress, on_event) and synchronous
    wrappers (get_progress_callback, get_event_callback) for integration
    with synchronous code.

    Attributes:
        manager: ConnectionManager for broadcasting messages.
    """

    def __init__(self, manager: ConnectionManager) -> None:
        """Initialize broadcaster with connection manager.

        Args:
            manager: ConnectionManager instance for broadcasting.
        """
        self.manager = manager
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def on_progress(
        self,
        current: int,
        total: int,
        filename: str,
        error: Optional[str] = None,
    ) -> None:
        """Broadcast a progress update message.

        Args:
            current: Current progress count.
            total: Total items to process.
            filename: Name of file being processed.
            error: Optional error message.
        """
        message = WebSocketMessage(
            type="progress",
            data={
                "current": current,
                "total": total,
                "filename": filename,
                "error": error,
            },
        )
        await self.manager.broadcast(message.to_dict())

    async def on_event(
        self,
        status: str,
        filename: str,
        error: Optional[str] = None,
    ) -> None:
        """Broadcast a status event message.

        Args:
            status: Event status (incoming, waiting, analyzing, sorted, error).
            filename: Name of file being processed.
            error: Optional error message.
        """
        message = WebSocketMessage(
            type="status",
            data={
                "status": status,
                "filename": filename,
                "error": error,
            },
        )
        await self.manager.broadcast(message.to_dict())

    def get_progress_callback(
        self,
    ) -> Callable[[int, int, str, Optional[str]], None]:
        """Get synchronous callback wrapper for progress updates.

        The returned callback can be passed to FolderEventHandler as
        progress_callback. It schedules async broadcasting on the event loop.

        Returns:
            Synchronous callback function with signature:
            (current: int, total: int, filename: str, error: Optional[str]) -> None
        """

        def sync_progress(
            current: int, total: int, filename: str, error: Optional[str] = None
        ) -> None:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(
                        self.on_progress(current, total, filename, error)
                    )
                else:
                    loop.run_until_complete(
                        self.on_progress(current, total, filename, error)
                    )
            except RuntimeError:
                # No event loop available, create a new one
                asyncio.run(self.on_progress(current, total, filename, error))

        return sync_progress

    def get_event_callback(
        self,
    ) -> Callable[[str, str, Optional[str]], None]:
        """Get synchronous callback wrapper for event updates.

        The returned callback can be passed to FolderEventHandler as
        on_event_callback. It schedules async broadcasting on the event loop.

        Returns:
            Synchronous callback function with signature:
            (status: str, filename: str, error: Optional[str]) -> None
        """

        def sync_event(status: str, filename: str, error: Optional[str] = None) -> None:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.on_event(status, filename, error))
                else:
                    loop.run_until_complete(self.on_event(status, filename, error))
            except RuntimeError:
                # No event loop available, create a new one
                asyncio.run(self.on_event(status, filename, error))

        return sync_event


# =============================================================================
# Log Handler for WebSocket Streaming
# =============================================================================


class WebSocketLogHandler(logging.Handler):
    """Logging handler that streams logs to WebSocket clients.

    Converts Python logging records into WebSocket messages and broadcasts
    them to all connected clients. Can filter by logger name prefix.

    Integrates with Python's logging system as a standard Handler.

    Attributes:
        manager: ConnectionManager for broadcasting messages.
        logger_prefix: Optional prefix to filter logger names.
    """

    def __init__(
        self,
        manager: ConnectionManager,
        logger_prefix: Optional[str] = None,
        level: int = logging.DEBUG,
    ) -> None:
        """Initialize log handler.

        Args:
            manager: ConnectionManager for broadcasting.
            logger_prefix: Only emit logs from loggers starting with this prefix.
            level: Minimum log level to emit.
        """
        super().__init__(level=level)
        self.manager = manager
        self.logger_prefix = logger_prefix

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log records by logger name prefix.

        Args:
            record: Log record to filter.

        Returns:
            True if record should be emitted, False otherwise.
        """
        if self.logger_prefix is None:
            return True
        return record.name.startswith(self.logger_prefix)

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record as a WebSocket message.

        Converts the log record to a structured message and broadcasts it.
        Exceptions during emission are caught to prevent logging system crashes.

        Args:
            record: Log record to emit.
        """
        try:
            message = WebSocketMessage(
                type="log",
                data={
                    "level": record.levelname,
                    "message": self.format(record),
                    "logger": record.name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            # Schedule broadcast asynchronously
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.manager.broadcast(message.to_dict()))
                else:
                    # Fallback for sync context
                    loop.run_until_complete(self.manager.broadcast(message.to_dict()))
            except RuntimeError:
                # No event loop, try creating one
                asyncio.run(self.manager.broadcast(message.to_dict()))

        except Exception:
            # Never let logging errors propagate
            self.handleError(record)
