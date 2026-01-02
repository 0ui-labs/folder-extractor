"""
Tests for API Pydantic models.

These tests define the expected behavior of our request/response models
before implementation (TDD approach).
"""

from datetime import datetime, timezone
from typing import Any

import pytest
from pydantic import ValidationError


class TestProcessRequest:
    """Tests for file processing request model."""

    def test_minimal_valid_request(self) -> None:
        """ProcessRequest requires only a filepath."""
        from folder_extractor.api.models import ProcessRequest

        request = ProcessRequest(filepath="/Users/test/Desktop/document.pdf")

        assert request.filepath == "/Users/test/Desktop/document.pdf"
        assert request.sort_by_type is False
        assert request.deduplicate is False
        assert request.global_dedup is False

    def test_full_request_with_all_options(self) -> None:
        """ProcessRequest accepts all optional flags."""
        from folder_extractor.api.models import ProcessRequest

        request = ProcessRequest(
            filepath="/Users/test/Downloads/file.txt",
            sort_by_type=True,
            deduplicate=True,
            global_dedup=True,
        )

        assert request.sort_by_type is True
        assert request.deduplicate is True
        assert request.global_dedup is True

    def test_filepath_is_required(self) -> None:
        """ProcessRequest must have a filepath."""
        from folder_extractor.api.models import ProcessRequest

        with pytest.raises(ValidationError) as exc_info:
            ProcessRequest()  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("filepath",) for e in errors)

    def test_filepath_must_be_non_empty(self) -> None:
        """ProcessRequest filepath cannot be empty string."""
        from folder_extractor.api.models import ProcessRequest

        with pytest.raises(ValidationError) as exc_info:
            ProcessRequest(filepath="")

        errors = exc_info.value.errors()
        assert len(errors) > 0


class TestZoneConfig:
    """Tests for dropzone configuration model."""

    def test_minimal_zone_config(self) -> None:
        """ZoneConfig requires name and path."""
        from folder_extractor.api.models import ZoneConfig

        config = ZoneConfig(name="Downloads", path="/Users/test/Downloads")

        assert config.name == "Downloads"
        assert config.path == "/Users/test/Downloads"
        assert config.enabled is True
        assert config.auto_sort is False
        assert config.categories == []

    def test_full_zone_config(self) -> None:
        """ZoneConfig accepts all optional settings."""
        from folder_extractor.api.models import ZoneConfig

        config = ZoneConfig(
            name="Documents",
            path="/Users/test/Documents",
            enabled=False,
            auto_sort=True,
            categories=["pdf", "docx", "txt"],
        )

        assert config.enabled is False
        assert config.auto_sort is True
        assert config.categories == ["pdf", "docx", "txt"]

    def test_name_is_required(self) -> None:
        """ZoneConfig must have a name."""
        from folder_extractor.api.models import ZoneConfig

        with pytest.raises(ValidationError) as exc_info:
            ZoneConfig(path="/some/path")  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_path_is_required(self) -> None:
        """ZoneConfig must have a path."""
        from folder_extractor.api.models import ZoneConfig

        with pytest.raises(ValidationError) as exc_info:
            ZoneConfig(name="Test")  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("path",) for e in errors)


class TestWatcherRequests:
    """Tests for watcher control request models."""

    def test_watcher_start_request(self) -> None:
        """WatcherStartRequest requires zone_id."""
        from folder_extractor.api.models import WatcherStartRequest

        request = WatcherStartRequest(zone_id="zone-123")

        assert request.zone_id == "zone-123"
        assert request.auto_process is True  # default

    def test_watcher_start_with_auto_process_disabled(self) -> None:
        """WatcherStartRequest can disable auto_process."""
        from folder_extractor.api.models import WatcherStartRequest

        request = WatcherStartRequest(zone_id="zone-456", auto_process=False)

        assert request.auto_process is False

    def test_watcher_stop_request(self) -> None:
        """WatcherStopRequest requires zone_id."""
        from folder_extractor.api.models import WatcherStopRequest

        request = WatcherStopRequest(zone_id="zone-789")

        assert request.zone_id == "zone-789"


class TestProcessResponse:
    """Tests for file processing response model."""

    def test_process_response_fields(self) -> None:
        """ProcessResponse contains task tracking info."""
        from folder_extractor.api.models import ProcessResponse

        response = ProcessResponse(
            task_id="task-abc-123",
            status="started",
            message="Verarbeitung gestartet",
        )

        assert response.task_id == "task-abc-123"
        assert response.status == "started"
        assert response.message == "Verarbeitung gestartet"

    def test_status_values(self) -> None:
        """ProcessResponse accepts valid status values."""
        from folder_extractor.api.models import ProcessResponse

        valid_statuses = ["started", "processing", "completed", "failed"]

        for status in valid_statuses:
            response = ProcessResponse(
                task_id="test", status=status, message="Test"
            )
            assert response.status == status


class TestZoneResponse:
    """Tests for zone response model."""

    def test_zone_response_fields(self) -> None:
        """ZoneResponse contains full zone information."""
        from folder_extractor.api.models import ZoneResponse

        now = datetime.now(timezone.utc)
        response = ZoneResponse(
            id="zone-uuid-123",
            name="Downloads",
            path="/Users/test/Downloads",
            enabled=True,
            auto_sort=False,
            categories=["pdf"],
            created_at=now,
        )

        assert response.id == "zone-uuid-123"
        assert response.name == "Downloads"
        assert response.path == "/Users/test/Downloads"
        assert response.enabled is True
        assert response.auto_sort is False
        assert response.categories == ["pdf"]
        assert response.created_at == now


class TestWatcherStatusResponse:
    """Tests for watcher status response model."""

    def test_watcher_running(self) -> None:
        """WatcherStatusResponse shows active watcher state."""
        from folder_extractor.api.models import WatcherStatusResponse

        now = datetime.now(timezone.utc)
        response = WatcherStatusResponse(
            running=True,
            zones=["zone-1", "zone-2"],
            active_since=now,
        )

        assert response.running is True
        assert response.zones == ["zone-1", "zone-2"]
        assert response.active_since == now

    def test_watcher_stopped(self) -> None:
        """WatcherStatusResponse shows inactive watcher state."""
        from folder_extractor.api.models import WatcherStatusResponse

        response = WatcherStatusResponse(
            running=False,
            zones=[],
            active_since=None,
        )

        assert response.running is False
        assert response.zones == []
        assert response.active_since is None


class TestHealthResponse:
    """Tests for health check response model."""

    def test_healthy_response(self) -> None:
        """HealthResponse shows system health status."""
        from folder_extractor.api.models import HealthResponse

        response = HealthResponse(
            status="healthy",
            version="1.4.0",
            database="connected",
            smart_sorter="available",
        )

        assert response.status == "healthy"
        assert response.version == "1.4.0"
        assert response.database == "connected"
        assert response.smart_sorter == "available"


class TestWebSocketMessage:
    """Tests for WebSocket message model."""

    def test_progress_message(self) -> None:
        """WebSocketMessage can represent progress updates."""
        from folder_extractor.api.models import WebSocketMessage

        now = datetime.now(timezone.utc)
        message = WebSocketMessage(
            type="progress",
            data={"current": 5, "total": 10, "file": "document.pdf"},
            timestamp=now,
        )

        assert message.type == "progress"
        assert message.data["current"] == 5
        assert message.data["total"] == 10
        assert message.data["file"] == "document.pdf"
        assert message.timestamp == now

    def test_status_message(self) -> None:
        """WebSocketMessage can represent status updates."""
        from folder_extractor.api.models import WebSocketMessage

        message = WebSocketMessage(
            type="status",
            data={"message": "Analysiere Datei...", "level": "info"},
            timestamp=datetime.now(timezone.utc),
        )

        assert message.type == "status"
        assert message.data["level"] == "info"

    def test_chat_message(self) -> None:
        """WebSocketMessage can represent AI chat messages."""
        from folder_extractor.api.models import WebSocketMessage

        message = WebSocketMessage(
            type="chat",
            data={"message": "Kategorie unklar. Bitte wählen:", "file": "X.pdf"},
            timestamp=datetime.now(timezone.utc),
        )

        assert message.type == "chat"

    def test_error_message(self) -> None:
        """WebSocketMessage can represent errors."""
        from folder_extractor.api.models import WebSocketMessage

        message = WebSocketMessage(
            type="error",
            data={"message": "Fehler beim Verarbeiten", "details": "IO Error"},
            timestamp=datetime.now(timezone.utc),
        )

        assert message.type == "error"
        assert "Fehler" in message.data["message"]

    def test_serialization_to_json(self) -> None:
        """WebSocketMessage can be serialized to JSON for WebSocket transmission."""
        from folder_extractor.api.models import WebSocketMessage

        message = WebSocketMessage(
            type="progress",
            data={"current": 1, "total": 5},
            timestamp=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        )

        json_str = message.model_dump_json()

        assert '"type":"progress"' in json_str
        assert '"current":1' in json_str
