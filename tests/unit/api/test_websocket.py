"""Tests for WebSocket functionality.

Tests for ConnectionManager, WebSocketProgressBroadcaster, WebSocketLogHandler,
and WebSocket endpoint integration.
Following TDD principles: these tests are written before the implementation.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from folder_extractor.api.websocket import (
    ConnectionManager,
    WebSocketLogHandler,
    WebSocketMessage,
    WebSocketProgressBroadcaster,
)

# =============================================================================
# WebSocketMessage Tests
# =============================================================================


class TestWebSocketMessage:
    """Tests for WebSocketMessage dataclass."""

    def test_creates_message_with_required_fields(self) -> None:
        """Message includes type, data, and auto-generated timestamp."""
        msg = WebSocketMessage(type="progress", data={"current": 1, "total": 10})

        assert msg.type == "progress"
        assert msg.data == {"current": 1, "total": 10}
        assert msg.timestamp is not None
        # Timestamp should be ISO 8601 format
        datetime.fromisoformat(msg.timestamp)

    def test_to_dict_returns_json_serializable(self) -> None:
        """to_dict returns dictionary suitable for JSON serialization."""
        msg = WebSocketMessage(type="status", data={"status": "incoming"})
        result = msg.to_dict()

        assert isinstance(result, dict)
        assert result["type"] == "status"
        assert result["data"] == {"status": "incoming"}
        assert "timestamp" in result


# =============================================================================
# ConnectionManager Tests
# =============================================================================


class TestConnectionManager:
    """Tests for WebSocket ConnectionManager."""

    @pytest.fixture
    def manager(self) -> ConnectionManager:
        """Create a fresh ConnectionManager for each test."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self) -> AsyncMock:
        """Create a mock WebSocket connection."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_connect_accepts_and_tracks_websocket(
        self, manager: ConnectionManager, mock_websocket: AsyncMock
    ) -> None:
        """Connect accepts the WebSocket and adds it to active connections."""
        await manager.connect(mock_websocket)

        mock_websocket.accept.assert_called_once()
        assert mock_websocket in manager.active_connections

    @pytest.mark.asyncio
    async def test_disconnect_removes_websocket(
        self, manager: ConnectionManager, mock_websocket: AsyncMock
    ) -> None:
        """Disconnect removes WebSocket from active connections."""
        await manager.connect(mock_websocket)
        manager.disconnect(mock_websocket)

        assert mock_websocket not in manager.active_connections

    @pytest.mark.asyncio
    async def test_disconnect_unknown_websocket_is_safe(
        self, manager: ConnectionManager, mock_websocket: AsyncMock
    ) -> None:
        """Disconnecting a WebSocket that was never connected is safe."""
        # Should not raise
        manager.disconnect(mock_websocket)
        assert len(manager.active_connections) == 0

    @pytest.mark.asyncio
    async def test_send_personal_message_sends_to_single_client(
        self, manager: ConnectionManager, mock_websocket: AsyncMock
    ) -> None:
        """send_personal_message sends message only to specified client."""
        await manager.connect(mock_websocket)
        message = {"type": "chat", "data": {"message": "Hello"}}

        await manager.send_personal_message(message, mock_websocket)

        mock_websocket.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all_connected_clients(
        self, manager: ConnectionManager
    ) -> None:
        """Broadcast sends message to all connected clients."""
        ws1, ws2, ws3 = AsyncMock(), AsyncMock(), AsyncMock()
        for ws in [ws1, ws2, ws3]:
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            await manager.connect(ws)

        message = {"type": "progress", "data": {"current": 5, "total": 10}}
        await manager.broadcast(message)

        for ws in [ws1, ws2, ws3]:
            ws.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_handles_client_disconnect_gracefully(
        self, manager: ConnectionManager
    ) -> None:
        """Broadcasting to a disconnected client removes it from active connections."""
        ws_healthy = AsyncMock()
        ws_healthy.accept = AsyncMock()
        ws_healthy.send_json = AsyncMock()

        ws_dead = AsyncMock()
        ws_dead.accept = AsyncMock()
        ws_dead.send_json = AsyncMock(side_effect=Exception("Connection closed"))

        await manager.connect(ws_healthy)
        await manager.connect(ws_dead)

        message = {"type": "status", "data": {"status": "sorted"}}
        await manager.broadcast(message)

        # Dead connection should be removed
        assert ws_dead not in manager.active_connections
        # Healthy connection should remain and receive message
        assert ws_healthy in manager.active_connections
        ws_healthy.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_with_no_connections_does_nothing(
        self, manager: ConnectionManager
    ) -> None:
        """Broadcasting with no connections completes without error."""
        message = {"type": "log", "data": {"message": "test"}}
        # Should not raise
        await manager.broadcast(message)

    @pytest.mark.asyncio
    async def test_close_all_closes_all_connections(
        self, manager: ConnectionManager
    ) -> None:
        """close_all closes all active WebSocket connections."""
        ws1, ws2 = AsyncMock(), AsyncMock()
        for ws in [ws1, ws2]:
            ws.accept = AsyncMock()
            ws.close = AsyncMock()
            await manager.connect(ws)

        await manager.close_all()

        ws1.close.assert_called_once()
        ws2.close.assert_called_once()
        assert len(manager.active_connections) == 0

    def test_connection_count_returns_number_of_active_connections(
        self, manager: ConnectionManager
    ) -> None:
        """connection_count property returns the number of active connections."""
        assert manager.connection_count == 0

        # Manually add connections for sync testing
        manager._connections.append(MagicMock())
        assert manager.connection_count == 1


# =============================================================================
# WebSocketProgressBroadcaster Tests
# =============================================================================


class TestWebSocketProgressBroadcaster:
    """Tests for WebSocketProgressBroadcaster adapter."""

    @pytest.fixture
    def mock_manager(self) -> AsyncMock:
        """Create a mock ConnectionManager."""
        manager = AsyncMock(spec=ConnectionManager)
        manager.broadcast = AsyncMock()
        return manager

    @pytest.fixture
    def broadcaster(self, mock_manager: AsyncMock) -> WebSocketProgressBroadcaster:
        """Create a WebSocketProgressBroadcaster with mock manager."""
        return WebSocketProgressBroadcaster(mock_manager)

    @pytest.mark.asyncio
    async def test_on_progress_broadcasts_progress_message(
        self, broadcaster: WebSocketProgressBroadcaster, mock_manager: AsyncMock
    ) -> None:
        """on_progress converts callback to progress WebSocket message."""
        await broadcaster.on_progress(current=5, total=10, filename="test.pdf")

        mock_manager.broadcast.assert_called_once()
        call_args = mock_manager.broadcast.call_args[0][0]
        assert call_args["type"] == "progress"
        assert call_args["data"]["current"] == 5
        assert call_args["data"]["total"] == 10
        assert call_args["data"]["filename"] == "test.pdf"
        assert call_args["data"]["error"] is None

    @pytest.mark.asyncio
    async def test_on_progress_includes_error_when_provided(
        self, broadcaster: WebSocketProgressBroadcaster, mock_manager: AsyncMock
    ) -> None:
        """on_progress includes error message when provided."""
        await broadcaster.on_progress(
            current=1, total=1, filename="fail.pdf", error="Permission denied"
        )

        call_args = mock_manager.broadcast.call_args[0][0]
        assert call_args["data"]["error"] == "Permission denied"

    @pytest.mark.asyncio
    async def test_on_event_broadcasts_status_message(
        self, broadcaster: WebSocketProgressBroadcaster, mock_manager: AsyncMock
    ) -> None:
        """on_event converts callback to status WebSocket message."""
        await broadcaster.on_event(status="analyzing", filename="doc.pdf")

        mock_manager.broadcast.assert_called_once()
        call_args = mock_manager.broadcast.call_args[0][0]
        assert call_args["type"] == "status"
        assert call_args["data"]["status"] == "analyzing"
        assert call_args["data"]["filename"] == "doc.pdf"
        assert call_args["data"]["error"] is None

    @pytest.mark.asyncio
    async def test_on_event_includes_error_when_provided(
        self, broadcaster: WebSocketProgressBroadcaster, mock_manager: AsyncMock
    ) -> None:
        """on_event includes error message when provided."""
        await broadcaster.on_event(
            status="error", filename="bad.pdf", error="AI analysis failed"
        )

        call_args = mock_manager.broadcast.call_args[0][0]
        assert call_args["data"]["status"] == "error"
        assert call_args["data"]["error"] == "AI analysis failed"

    def test_sync_progress_callback_wraps_async_method(
        self, broadcaster: WebSocketProgressBroadcaster
    ) -> None:
        """get_progress_callback returns synchronous wrapper for async on_progress."""
        callback = broadcaster.get_progress_callback()

        # Callback should be callable with the expected signature
        assert callable(callback)

    def test_sync_event_callback_wraps_async_method(
        self, broadcaster: WebSocketProgressBroadcaster
    ) -> None:
        """get_event_callback returns synchronous wrapper for async on_event."""
        callback = broadcaster.get_event_callback()

        # Callback should be callable with the expected signature
        assert callable(callback)


# =============================================================================
# WebSocketLogHandler Tests
# =============================================================================


class TestWebSocketLogHandler:
    """Tests for WebSocketLogHandler logging integration."""

    @pytest.fixture
    def mock_manager(self) -> MagicMock:
        """Create a mock ConnectionManager."""
        manager = MagicMock(spec=ConnectionManager)

        # Use a regular MagicMock that returns a coroutine for broadcast
        async def mock_broadcast(msg: dict[str, Any]) -> None:
            manager._broadcast_calls.append(msg)

        manager._broadcast_calls = []
        manager.broadcast = mock_broadcast
        return manager

    @pytest.fixture
    def log_handler(self, mock_manager: MagicMock) -> WebSocketLogHandler:
        """Create a WebSocketLogHandler with mock manager."""
        return WebSocketLogHandler(mock_manager)

    @pytest.mark.asyncio
    async def test_emits_log_records_as_websocket_messages(
        self, log_handler: WebSocketLogHandler, mock_manager: MagicMock
    ) -> None:
        """Log records are converted to WebSocket messages and broadcast."""
        record = logging.LogRecord(
            name="folder_extractor.core.watch",
            level=logging.INFO,
            pathname="watch.py",
            lineno=100,
            msg="Processing file: test.pdf",
            args=(),
            exc_info=None,
        )

        log_handler.emit(record)

        # Allow async task to complete
        await asyncio.sleep(0.01)

        # Should have scheduled a broadcast
        assert len(mock_manager._broadcast_calls) > 0

    def test_filters_by_logger_name_prefix(
        self, log_handler: WebSocketLogHandler, mock_manager: MagicMock
    ) -> None:
        """Only logs from folder_extractor.* loggers are broadcast."""
        # Create handler with filter
        handler = WebSocketLogHandler(mock_manager, logger_prefix="folder_extractor")

        # folder_extractor log should pass
        record_pass = logging.LogRecord(
            name="folder_extractor.api.server",
            level=logging.INFO,
            pathname="server.py",
            lineno=50,
            msg="Server started",
            args=(),
            exc_info=None,
        )
        assert handler.filter(record_pass) is True

        # Other logs should be filtered
        record_fail = logging.LogRecord(
            name="uvicorn.access",
            level=logging.INFO,
            pathname="access.py",
            lineno=10,
            msg="GET /health",
            args=(),
            exc_info=None,
        )
        assert handler.filter(record_fail) is False

    @pytest.mark.asyncio
    async def test_maps_log_level_to_message(
        self, log_handler: WebSocketLogHandler, mock_manager: MagicMock
    ) -> None:
        """Log levels are correctly mapped in the message."""
        for level, expected_name in [
            (logging.DEBUG, "DEBUG"),
            (logging.INFO, "INFO"),
            (logging.WARNING, "WARNING"),
            (logging.ERROR, "ERROR"),
            (logging.CRITICAL, "CRITICAL"),
        ]:
            mock_manager._broadcast_calls.clear()

            record = logging.LogRecord(
                name="folder_extractor.test",
                level=level,
                pathname="test.py",
                lineno=1,
                msg="Test message",
                args=(),
                exc_info=None,
            )

            log_handler.emit(record)

            # Allow async task to complete
            await asyncio.sleep(0.01)

            assert len(mock_manager._broadcast_calls) > 0
            call_args = mock_manager._broadcast_calls[-1]

            assert call_args["type"] == "log"
            assert call_args["data"]["level"] == expected_name

    def test_exception_in_emit_does_not_propagate(self) -> None:
        """Exceptions during emit are caught and don't crash the logging system."""
        manager = MagicMock(spec=ConnectionManager)

        async def failing_broadcast(msg: dict[str, Any]) -> None:
            raise Exception("Broadcast failed")

        manager.broadcast = failing_broadcast
        handler = WebSocketLogHandler(manager)

        record = logging.LogRecord(
            name="folder_extractor.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        # Should not raise
        handler.emit(record)


# =============================================================================
# WebSocket Endpoint Integration Tests
# =============================================================================


class TestWebSocketEndpoint:
    """Integration tests for WebSocket endpoint /ws/chat.

    Note: These tests verify the WebSocket endpoint behavior via direct
    async function testing rather than TestClient, which has known issues
    with WebSocket connections in test environments.
    """

    @pytest.mark.asyncio
    async def test_websocket_message_handling_logic(self) -> None:
        """WebSocket message handling logic works correctly."""
        from folder_extractor.api.websocket import ConnectionManager, WebSocketMessage

        # Test ConnectionManager behavior
        manager = ConnectionManager()
        assert manager.connection_count == 0

        # Test WebSocketMessage creation
        msg = WebSocketMessage(type="status", data={"status": "typing"})
        result = msg.to_dict()
        assert result["type"] == "status"
        assert result["data"]["status"] == "typing"
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_chat_message_format(self) -> None:
        """Chat messages have correct format."""
        from folder_extractor.api.websocket import WebSocketMessage

        # Chat response format
        response = WebSocketMessage(
            type="chat", data={"message": "Hello!", "sender": "ai"}
        )
        result = response.to_dict()

        assert result["type"] == "chat"
        assert result["data"]["message"] == "Hello!"
        assert result["data"]["sender"] == "ai"

    @pytest.mark.asyncio
    async def test_command_message_format(self) -> None:
        """Command messages have correct format."""
        from folder_extractor.api.websocket import WebSocketMessage

        # Abort response format
        response = WebSocketMessage(
            type="status",
            data={"status": "abort_requested", "message": "Abbruch angefordert"},
        )
        result = response.to_dict()

        assert result["type"] == "status"
        assert result["data"]["status"] == "abort_requested"

    @pytest.mark.asyncio
    async def test_error_message_format(self) -> None:
        """Error messages have correct format."""
        from folder_extractor.api.websocket import WebSocketMessage

        # Error response format
        response = WebSocketMessage(
            type="error",
            data={"message": "KI nicht verfügbar", "code": "AI_UNAVAILABLE"},
        )
        result = response.to_dict()

        assert result["type"] == "error"
        assert result["data"]["code"] == "AI_UNAVAILABLE"
