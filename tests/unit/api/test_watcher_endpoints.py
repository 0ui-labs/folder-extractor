"""
Tests for Watcher API endpoints.

Tests the /watcher/start, /watcher/stop, and /watcher/status endpoints
for filesystem monitoring via API.

Following TDD approach: tests define expected behavior before implementation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_knowledge_graph() -> MagicMock:
    """Create a mock KnowledgeGraph."""
    kg = MagicMock()
    kg._conn = MagicMock()
    return kg


@pytest.fixture
def mock_ai_client() -> MagicMock:
    """Create a mock AI client."""
    client = MagicMock()
    client.model_name = "gemini-test"
    return client


@pytest.fixture
def mock_smart_sorter() -> MagicMock:
    """Create a mock SmartSorter."""
    return MagicMock()


@pytest.fixture
def mock_zone_manager() -> MagicMock:
    """Create a mock ZoneManager with predefined zones."""
    manager = MagicMock()

    sample_zone = {
        "id": "zone-123",
        "name": "Downloads",
        "path": "/Users/test/Downloads",
        "enabled": True,
        "auto_sort": True,
        "categories": ["pdf", "jpg"],
        "created_at": "2025-01-15T10:30:00+00:00",
    }

    def get_zone_side_effect(zone_id: str) -> dict[str, Any] | None:
        if zone_id == "zone-123":
            return sample_zone
        return None

    manager.list_zones.return_value = [sample_zone]
    manager.get_zone.side_effect = get_zone_side_effect
    manager.zone_exists.side_effect = lambda zid: zid == "zone-123"
    manager.add_zone.return_value = "new-zone-id"
    manager.remove_zone.return_value = True
    manager.update_zone.return_value = True

    return manager


@pytest.fixture
def mock_orchestrator() -> MagicMock:
    """Create a mock EnhancedExtractionOrchestrator."""
    orchestrator = MagicMock()
    orchestrator.process_single_file.return_value = {
        "status": "success",
        "moved": 1,
        "errors": 0,
        "duplicates": 0,
    }
    return orchestrator


@pytest.fixture
def mock_observer() -> MagicMock:
    """Create a mock watchdog Observer."""
    observer = MagicMock()
    observer.is_alive.return_value = True
    return observer


@pytest.fixture
def mock_state_manager() -> MagicMock:
    """Create a mock StateManager."""
    state_manager = MagicMock()
    state_manager.is_abort_requested.return_value = False
    state_manager.get_current_operation_id.return_value = "op-123"
    state_manager.get_operation_stats.return_value = MagicMock(
        files_processed=5,
        files_moved=4,
        files_skipped=1,
    )
    return state_manager


@pytest.fixture
def app_with_watcher_endpoints(
    mock_knowledge_graph: MagicMock,
    mock_ai_client: MagicMock,
    mock_smart_sorter: MagicMock,
    mock_zone_manager: MagicMock,
    mock_orchestrator: MagicMock,
    mock_observer: MagicMock,
    mock_state_manager: MagicMock,
) -> Generator[TestClient, None, None]:
    """Create a test client with watcher endpoints and all dependencies mocked."""
    import folder_extractor.api.dependencies as deps
    import folder_extractor.api.endpoints as endpoints

    # Reset singletons
    deps._zone_manager = None
    # Clear active watchers between tests
    with endpoints.watchers_lock:
        endpoints.active_watchers.clear()

    with patch(
        "folder_extractor.api.server.get_knowledge_graph",
        return_value=mock_knowledge_graph,
    ), patch(
        "folder_extractor.api.server.AsyncGeminiClient",
        return_value=mock_ai_client,
    ), patch(
        "folder_extractor.api.server.SmartSorter",
        return_value=mock_smart_sorter,
    ), patch(
        "folder_extractor.api.dependencies.ZoneManager",
        return_value=mock_zone_manager,
    ), patch(
        "folder_extractor.api.dependencies.EnhancedExtractionOrchestrator",
        return_value=mock_orchestrator,
    ), patch(
        "folder_extractor.api.endpoints.Observer",
        return_value=mock_observer,
    ), patch(
        "folder_extractor.api.endpoints.StateManager",
        return_value=mock_state_manager,
    ), patch(
        "folder_extractor.api.endpoints.StabilityMonitor",
        return_value=MagicMock(),
    ), patch(
        "folder_extractor.api.endpoints.FolderEventHandler",
        return_value=MagicMock(),
    ):
        from folder_extractor.api.server import app

        with TestClient(app) as client:
            yield client

    # Cleanup
    deps._zone_manager = None
    with endpoints.watchers_lock:
        endpoints.active_watchers.clear()


# =============================================================================
# Watcher Start Endpoint Tests
# =============================================================================


class TestWatcherStartEndpoint:
    """Tests for POST /api/v1/watcher/start endpoint."""

    def test_start_watcher_for_valid_zone_returns_success(
        self,
        app_with_watcher_endpoints: TestClient,
    ) -> None:
        """Starting a watcher for a valid zone returns 200 with status info."""
        response = app_with_watcher_endpoints.post(
            "/api/v1/watcher/start",
            json={"zone_id": "zone-123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["zone_id"] == "zone-123"
        assert data["status"] == "running"
        assert "started_at" in data
        assert data["zone_path"] == "/Users/test/Downloads"

    def test_start_watcher_for_nonexistent_zone_returns_404(
        self,
        app_with_watcher_endpoints: TestClient,
    ) -> None:
        """Starting a watcher for a non-existent zone returns 404."""
        response = app_with_watcher_endpoints.post(
            "/api/v1/watcher/start",
            json={"zone_id": "nonexistent-zone"},
        )

        assert response.status_code == 404
        data = response.json()
        assert "nicht gefunden" in data["detail"].lower() or "not found" in data["detail"].lower()

    def test_start_watcher_for_already_watched_zone_returns_409(
        self,
        app_with_watcher_endpoints: TestClient,
    ) -> None:
        """Starting a watcher for an already watched zone returns 409 Conflict."""
        # Start first watcher
        response = app_with_watcher_endpoints.post(
            "/api/v1/watcher/start",
            json={"zone_id": "zone-123"},
        )
        assert response.status_code == 200

        # Try to start again
        response = app_with_watcher_endpoints.post(
            "/api/v1/watcher/start",
            json={"zone_id": "zone-123"},
        )

        assert response.status_code == 409
        data = response.json()
        assert "bereits" in data["detail"].lower() or "already" in data["detail"].lower()

    def test_start_watcher_creates_observer_with_zone_path(
        self,
        app_with_watcher_endpoints: TestClient,
        mock_observer: MagicMock,
    ) -> None:
        """Starting a watcher schedules the observer with the correct zone path."""
        response = app_with_watcher_endpoints.post(
            "/api/v1/watcher/start",
            json={"zone_id": "zone-123"},
        )

        assert response.status_code == 200
        # Verify observer was scheduled with the zone path
        mock_observer.schedule.assert_called_once()
        call_args = mock_observer.schedule.call_args
        # Second argument should be the path
        assert call_args[0][1] == "/Users/test/Downloads"

    def test_start_watcher_starts_observer(
        self,
        app_with_watcher_endpoints: TestClient,
        mock_observer: MagicMock,
    ) -> None:
        """Starting a watcher calls observer.start()."""
        response = app_with_watcher_endpoints.post(
            "/api/v1/watcher/start",
            json={"zone_id": "zone-123"},
        )

        assert response.status_code == 200
        mock_observer.start.assert_called_once()


# =============================================================================
# Watcher Stop Endpoint Tests
# =============================================================================


class TestWatcherStopEndpoint:
    """Tests for POST /api/v1/watcher/stop endpoint."""

    def test_stop_watcher_for_active_zone_returns_success(
        self,
        app_with_watcher_endpoints: TestClient,
    ) -> None:
        """Stopping an active watcher returns 200 with confirmation."""
        # Start the watcher first
        app_with_watcher_endpoints.post(
            "/api/v1/watcher/start",
            json={"zone_id": "zone-123"},
        )

        # Stop it
        response = app_with_watcher_endpoints.post(
            "/api/v1/watcher/stop",
            json={"zone_id": "zone-123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["zone_id"] == "zone-123"
        assert data["status"] == "stopped"

    def test_stop_watcher_for_inactive_zone_returns_404(
        self,
        app_with_watcher_endpoints: TestClient,
    ) -> None:
        """Stopping a watcher that isn't running returns 404."""
        response = app_with_watcher_endpoints.post(
            "/api/v1/watcher/stop",
            json={"zone_id": "zone-123"},
        )

        assert response.status_code == 404
        data = response.json()
        assert "nicht aktiv" in data["detail"].lower() or "not active" in data["detail"].lower()

    def test_stop_watcher_calls_request_abort(
        self,
        app_with_watcher_endpoints: TestClient,
        mock_state_manager: MagicMock,
    ) -> None:
        """Stopping a watcher signals abort via StateManager."""
        # Start first
        app_with_watcher_endpoints.post(
            "/api/v1/watcher/start",
            json={"zone_id": "zone-123"},
        )

        # Stop
        response = app_with_watcher_endpoints.post(
            "/api/v1/watcher/stop",
            json={"zone_id": "zone-123"},
        )

        assert response.status_code == 200
        mock_state_manager.request_abort.assert_called_once()

    def test_stop_watcher_stops_and_joins_observer(
        self,
        app_with_watcher_endpoints: TestClient,
        mock_observer: MagicMock,
    ) -> None:
        """Stopping a watcher calls observer.stop() and observer.join()."""
        # Start first
        app_with_watcher_endpoints.post(
            "/api/v1/watcher/start",
            json={"zone_id": "zone-123"},
        )

        # Stop
        response = app_with_watcher_endpoints.post(
            "/api/v1/watcher/stop",
            json={"zone_id": "zone-123"},
        )

        assert response.status_code == 200
        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once()

    def test_stop_watcher_removes_from_active_watchers(
        self,
        app_with_watcher_endpoints: TestClient,
    ) -> None:
        """After stopping, the zone is no longer in active watchers."""
        # Start
        app_with_watcher_endpoints.post(
            "/api/v1/watcher/start",
            json={"zone_id": "zone-123"},
        )

        # Verify it's active via status endpoint
        status_response = app_with_watcher_endpoints.get("/api/v1/watcher/status")
        assert status_response.json()["overall_status"] == "running"
        assert status_response.json()["total_count"] == 1

        # Stop
        app_with_watcher_endpoints.post(
            "/api/v1/watcher/stop",
            json={"zone_id": "zone-123"},
        )

        # Verify it's no longer active
        status_response = app_with_watcher_endpoints.get("/api/v1/watcher/status")
        assert status_response.json()["overall_status"] == "stopped"
        assert status_response.json()["total_count"] == 0


# =============================================================================
# Watcher Status Endpoint Tests
# =============================================================================


class TestWatcherStatusEndpoint:
    """Tests for GET /api/v1/watcher/status endpoint."""

    def test_status_with_no_watchers_returns_empty_list_and_stopped_status(
        self,
        app_with_watcher_endpoints: TestClient,
    ) -> None:
        """Status endpoint returns empty list with overall_status 'stopped' when no watchers active."""
        response = app_with_watcher_endpoints.get("/api/v1/watcher/status")

        assert response.status_code == 200
        data = response.json()
        assert data["overall_status"] == "stopped"
        assert data["active_watchers"] == []
        assert data["total_count"] == 0

    def test_status_with_active_watcher_returns_watcher_info_and_running_status(
        self,
        app_with_watcher_endpoints: TestClient,
    ) -> None:
        """Status endpoint includes active watcher details with overall_status 'running'."""
        # Start a watcher
        app_with_watcher_endpoints.post(
            "/api/v1/watcher/start",
            json={"zone_id": "zone-123"},
        )

        response = app_with_watcher_endpoints.get("/api/v1/watcher/status")

        assert response.status_code == 200
        data = response.json()
        assert data["overall_status"] == "running"
        assert data["total_count"] == 1
        assert len(data["active_watchers"]) == 1

        watcher = data["active_watchers"][0]
        assert watcher["zone_id"] == "zone-123"
        assert watcher["zone_path"] == "/Users/test/Downloads"
        assert watcher["status"] == "running"
        assert "started_at" in watcher

    def test_status_includes_files_processed_count(
        self,
        app_with_watcher_endpoints: TestClient,
    ) -> None:
        """Status endpoint includes the number of files processed."""
        # Start a watcher
        app_with_watcher_endpoints.post(
            "/api/v1/watcher/start",
            json={"zone_id": "zone-123"},
        )

        response = app_with_watcher_endpoints.get("/api/v1/watcher/status")

        assert response.status_code == 200
        data = response.json()
        watcher = data["active_watchers"][0]
        # files_processed should be present (default 0)
        assert "files_processed" in watcher

    def test_status_with_zone_id_filter(
        self,
        app_with_watcher_endpoints: TestClient,
    ) -> None:
        """Status endpoint supports filtering by zone_id query parameter."""
        # Start a watcher
        app_with_watcher_endpoints.post(
            "/api/v1/watcher/start",
            json={"zone_id": "zone-123"},
        )

        # Query with matching zone_id
        response = app_with_watcher_endpoints.get(
            "/api/v1/watcher/status",
            params={"zone_id": "zone-123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["overall_status"] == "running"  # Watcher is active
        assert data["total_count"] == 1

        # Query with non-matching zone_id - overall_status still "running"
        # because OTHER watchers exist (just not matching the filter)
        response = app_with_watcher_endpoints.get(
            "/api/v1/watcher/status",
            params={"zone_id": "other-zone"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["overall_status"] == "running"  # Still running - filter doesn't affect this
        assert data["total_count"] == 0  # But filtered list is empty


# =============================================================================
# Watcher Lifecycle Integration Tests
# =============================================================================


class TestWatcherLifecycle:
    """Integration tests for watcher lifecycle: start → status → stop."""

    def test_full_watcher_lifecycle(
        self,
        app_with_watcher_endpoints: TestClient,
    ) -> None:
        """Complete lifecycle: start, check status, stop."""
        # Initial status: no watchers, overall_status "stopped"
        status = app_with_watcher_endpoints.get("/api/v1/watcher/status")
        assert status.json()["overall_status"] == "stopped"
        assert status.json()["total_count"] == 0

        # Start watcher
        start = app_with_watcher_endpoints.post(
            "/api/v1/watcher/start",
            json={"zone_id": "zone-123"},
        )
        assert start.status_code == 200
        assert start.json()["status"] == "running"

        # Check status: 1 active watcher, overall_status "running"
        status = app_with_watcher_endpoints.get("/api/v1/watcher/status")
        assert status.json()["overall_status"] == "running"
        assert status.json()["total_count"] == 1

        # Stop watcher
        stop = app_with_watcher_endpoints.post(
            "/api/v1/watcher/stop",
            json={"zone_id": "zone-123"},
        )
        assert stop.status_code == 200
        assert stop.json()["status"] == "stopped"

        # Final status: no watchers, overall_status "stopped"
        status = app_with_watcher_endpoints.get("/api/v1/watcher/status")
        assert status.json()["overall_status"] == "stopped"
        assert status.json()["total_count"] == 0


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestWatcherErrorHandling:
    """Tests for error handling in watcher endpoints."""

    def test_start_watcher_with_empty_zone_id_returns_422(
        self,
        app_with_watcher_endpoints: TestClient,
    ) -> None:
        """Starting a watcher with empty zone_id returns validation error."""
        response = app_with_watcher_endpoints.post(
            "/api/v1/watcher/start",
            json={"zone_id": ""},
        )

        # Empty string might fail validation or return 404
        assert response.status_code in [404, 422]

    def test_start_watcher_without_zone_id_returns_422(
        self,
        app_with_watcher_endpoints: TestClient,
    ) -> None:
        """Starting a watcher without zone_id returns validation error."""
        response = app_with_watcher_endpoints.post(
            "/api/v1/watcher/start",
            json={},
        )

        assert response.status_code == 422

    def test_stop_watcher_with_invalid_json_returns_422(
        self,
        app_with_watcher_endpoints: TestClient,
    ) -> None:
        """Stopping a watcher with invalid JSON returns 422."""
        response = app_with_watcher_endpoints.post(
            "/api/v1/watcher/stop",
            content="not valid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422
