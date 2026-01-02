"""
Tests for REST API endpoints.

Tests the /process and /zones endpoints for file processing
and dropzone management.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Generator
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

    # Sample zone data with created_at timestamp
    sample_zone = {
        "id": "test-zone-id-123",
        "name": "Downloads",
        "path": "/Users/test/Downloads",
        "enabled": True,
        "auto_sort": True,
        "categories": ["pdf", "jpg"],
        "created_at": "2025-01-15T10:30:00+00:00",
    }

    manager.list_zones.return_value = [sample_zone]
    manager.get_zone.return_value = sample_zone
    manager.add_zone.return_value = "new-zone-id-456"
    manager.zone_exists.return_value = True
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
def app_with_endpoints(
    mock_knowledge_graph: MagicMock,
    mock_ai_client: MagicMock,
    mock_smart_sorter: MagicMock,
    mock_zone_manager: MagicMock,
    mock_orchestrator: MagicMock,
) -> Generator[TestClient, None, None]:
    """Create a test client with endpoints and all dependencies mocked."""
    # Reset the zone_manager singleton before each test
    import folder_extractor.api.dependencies as deps

    deps._zone_manager = None

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
    ):
        from folder_extractor.api.server import app

        with TestClient(app) as client:
            yield client

    # Reset singleton after test
    deps._zone_manager = None


@pytest.fixture
def temp_file(tmp_path: Path) -> Path:
    """Create a temporary file for testing."""
    test_file = tmp_path / "test_document.pdf"
    test_file.write_text("PDF content")
    return test_file


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for zone testing."""
    test_dir = tmp_path / "test_zone"
    test_dir.mkdir()
    return test_dir


# =============================================================================
# Process Endpoint Tests
# =============================================================================


class TestProcessEndpoint:
    """Tests for POST /api/v1/process endpoint."""

    def test_process_file_starts_background_task(
        self,
        app_with_endpoints: TestClient,
        temp_file: Path,
    ) -> None:
        """Processing a valid file starts a background task and returns immediately."""
        response = app_with_endpoints.post(
            "/api/v1/process",
            json={"filepath": str(temp_file)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert "task_id" in data
        assert temp_file.name in data["message"]

    def test_process_file_with_destination(
        self,
        app_with_endpoints: TestClient,
        temp_file: Path,
        temp_dir: Path,
    ) -> None:
        """Processing with explicit destination passes it to the orchestrator."""
        response = app_with_endpoints.post(
            "/api/v1/process",
            json={
                "filepath": str(temp_file),
                "destination": str(temp_dir),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"

    def test_process_nonexistent_file_returns_404(
        self,
        app_with_endpoints: TestClient,
    ) -> None:
        """Processing a non-existent file returns 404 Not Found."""
        response = app_with_endpoints.post(
            "/api/v1/process",
            json={"filepath": "/nonexistent/path/file.pdf"},
        )

        assert response.status_code == 404
        data = response.json()
        assert (
            "nicht gefunden" in data["detail"].lower()
            or "not found" in data["detail"].lower()
        )

    def test_process_empty_filepath_returns_422(
        self,
        app_with_endpoints: TestClient,
    ) -> None:
        """Processing with empty filepath returns 422 Validation Error."""
        response = app_with_endpoints.post(
            "/api/v1/process",
            json={"filepath": ""},
        )

        assert response.status_code == 422

    def test_process_invalid_json_returns_422(
        self,
        app_with_endpoints: TestClient,
    ) -> None:
        """Processing with invalid JSON returns 422 Validation Error."""
        response = app_with_endpoints.post(
            "/api/v1/process",
            content="not json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422


# =============================================================================
# Zone List Endpoint Tests
# =============================================================================


class TestZoneListEndpoint:
    """Tests for GET /api/v1/zones endpoint."""

    def test_list_zones_returns_all_zones(
        self,
        app_with_endpoints: TestClient,
        mock_zone_manager: MagicMock,
    ) -> None:
        """Listing zones returns all configured zones."""
        response = app_with_endpoints.get("/api/v1/zones")

        assert response.status_code == 200
        data = response.json()
        assert "zones" in data
        assert "total" in data
        assert data["total"] == 1
        assert len(data["zones"]) == 1

        zone = data["zones"][0]
        assert zone["id"] == "test-zone-id-123"
        assert zone["name"] == "Downloads"
        assert zone["enabled"] is True

    def test_list_zones_includes_created_at_timestamp(
        self,
        app_with_endpoints: TestClient,
        mock_zone_manager: MagicMock,
    ) -> None:
        """Listing zones includes the created_at timestamp for each zone."""
        response = app_with_endpoints.get("/api/v1/zones")

        assert response.status_code == 200
        data = response.json()
        zone = data["zones"][0]
        assert "created_at" in zone
        # Pydantic may serialize as 'Z' or '+00:00' - both are valid ISO 8601
        assert zone["created_at"] is not None
        assert "2025-01-15T10:30:00" in zone["created_at"]

    def test_list_zones_returns_empty_list_when_no_zones(
        self,
        mock_knowledge_graph: MagicMock,
        mock_ai_client: MagicMock,
        mock_smart_sorter: MagicMock,
    ) -> None:
        """Listing zones returns empty list when no zones configured."""
        import folder_extractor.api.dependencies as deps

        deps._zone_manager = None

        mock_empty_manager = MagicMock()
        mock_empty_manager.list_zones.return_value = []

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
            return_value=mock_empty_manager,
        ):
            from folder_extractor.api.server import app

            with TestClient(app) as client:
                response = client.get("/api/v1/zones")

                assert response.status_code == 200
                data = response.json()
                assert data["zones"] == []
                assert data["total"] == 0


# =============================================================================
# Zone Create Endpoint Tests
# =============================================================================


class TestZoneCreateEndpoint:
    """Tests for POST /api/v1/zones endpoint."""

    def test_create_zone_returns_201_with_zone_data(
        self,
        app_with_endpoints: TestClient,
        mock_zone_manager: MagicMock,
        temp_dir: Path,
    ) -> None:
        """Creating a zone returns 201 Created with the new zone data."""
        # Configure mock to return the created zone
        new_zone_id = str(uuid.uuid4())
        mock_zone_manager.add_zone.return_value = new_zone_id
        mock_zone_manager.get_zone.return_value = {
            "id": new_zone_id,
            "name": "New Zone",
            "path": str(temp_dir),
            "enabled": True,
            "auto_sort": False,
            "categories": [],
            "created_at": "2025-01-15T12:00:00+00:00",
        }
        # Make sure path doesn't already exist
        mock_zone_manager.list_zones.return_value = []

        response = app_with_endpoints.post(
            "/api/v1/zones",
            json={
                "name": "New Zone",
                "path": str(temp_dir),
                "enabled": True,
                "auto_sort": False,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == new_zone_id
        assert data["name"] == "New Zone"
        assert data["path"] == str(temp_dir)

    def test_create_zone_with_duplicate_path_returns_409(
        self,
        app_with_endpoints: TestClient,
        mock_zone_manager: MagicMock,
    ) -> None:
        """Creating a zone with an existing path returns 409 Conflict."""
        # The mock already returns a zone with /Users/test/Downloads
        response = app_with_endpoints.post(
            "/api/v1/zones",
            json={
                "name": "Duplicate Zone",
                "path": "/Users/test/Downloads",  # Same as existing zone
            },
        )

        assert response.status_code == 409
        data = response.json()
        assert (
            "existiert bereits" in data["detail"].lower()
            or "exists" in data["detail"].lower()
        )

    def test_create_zone_with_empty_name_returns_422(
        self,
        app_with_endpoints: TestClient,
        temp_dir: Path,
    ) -> None:
        """Creating a zone with empty name returns 422 Validation Error."""
        response = app_with_endpoints.post(
            "/api/v1/zones",
            json={
                "name": "",
                "path": str(temp_dir),
            },
        )

        assert response.status_code == 422

    def test_create_zone_with_categories(
        self,
        app_with_endpoints: TestClient,
        mock_zone_manager: MagicMock,
        temp_dir: Path,
    ) -> None:
        """Creating a zone with categories includes them in the response."""
        new_zone_id = str(uuid.uuid4())
        mock_zone_manager.add_zone.return_value = new_zone_id
        mock_zone_manager.get_zone.return_value = {
            "id": new_zone_id,
            "name": "Filtered Zone",
            "path": str(temp_dir),
            "enabled": True,
            "auto_sort": True,
            "categories": ["pdf", "docx"],
            "created_at": "2025-01-15T12:30:00+00:00",
        }
        mock_zone_manager.list_zones.return_value = []

        response = app_with_endpoints.post(
            "/api/v1/zones",
            json={
                "name": "Filtered Zone",
                "path": str(temp_dir),
                "auto_sort": True,
                "categories": ["pdf", "docx"],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["categories"] == ["pdf", "docx"]
        assert data["auto_sort"] is True


# =============================================================================
# Zone Delete Endpoint Tests
# =============================================================================


class TestZoneDeleteEndpoint:
    """Tests for DELETE /api/v1/zones/{zone_id} endpoint."""

    def test_delete_zone_returns_204(
        self,
        app_with_endpoints: TestClient,
        mock_zone_manager: MagicMock,
    ) -> None:
        """Deleting an existing zone returns 204 No Content."""
        response = app_with_endpoints.delete("/api/v1/zones/test-zone-id-123")

        assert response.status_code == 204
        mock_zone_manager.remove_zone.assert_called_once_with("test-zone-id-123")

    def test_delete_nonexistent_zone_returns_404(
        self,
        app_with_endpoints: TestClient,
        mock_zone_manager: MagicMock,
    ) -> None:
        """Deleting a non-existent zone returns 404 Not Found."""
        mock_zone_manager.zone_exists.return_value = False

        response = app_with_endpoints.delete("/api/v1/zones/nonexistent-id")

        assert response.status_code == 404
        data = response.json()
        assert (
            "nicht gefunden" in data["detail"].lower()
            or "not found" in data["detail"].lower()
        )


# =============================================================================
# Zone Update Endpoint Tests
# =============================================================================


class TestZoneUpdateEndpoint:
    """Tests for PUT /api/v1/zones/{zone_id} endpoint."""

    def test_update_zone_returns_updated_zone(
        self,
        app_with_endpoints: TestClient,
        mock_zone_manager: MagicMock,
    ) -> None:
        """Updating a zone returns the updated zone data."""
        updated_zone = {
            "id": "test-zone-id-123",
            "name": "Updated Name",
            "path": "/Users/test/Downloads",
            "enabled": False,
            "auto_sort": True,
            "categories": ["pdf"],
            "created_at": "2025-01-15T10:30:00+00:00",
        }
        mock_zone_manager.get_zone.return_value = updated_zone

        response = app_with_endpoints.put(
            "/api/v1/zones/test-zone-id-123",
            json={"name": "Updated Name", "enabled": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["enabled"] is False

    def test_update_nonexistent_zone_returns_404(
        self,
        app_with_endpoints: TestClient,
        mock_zone_manager: MagicMock,
    ) -> None:
        """Updating a non-existent zone returns 404 Not Found."""
        mock_zone_manager.zone_exists.return_value = False

        response = app_with_endpoints.put(
            "/api/v1/zones/nonexistent-id",
            json={"name": "New Name"},
        )

        assert response.status_code == 404

    def test_partial_update_only_changes_specified_fields(
        self,
        app_with_endpoints: TestClient,
        mock_zone_manager: MagicMock,
    ) -> None:
        """Partial update only modifies the specified fields."""
        # Original zone data
        original = {
            "id": "test-zone-id-123",
            "name": "Downloads",
            "path": "/Users/test/Downloads",
            "enabled": True,
            "auto_sort": True,
            "categories": ["pdf", "jpg"],
            "created_at": "2025-01-15T10:30:00+00:00",
        }
        # After update, only enabled changed
        updated = {**original, "enabled": False}
        mock_zone_manager.get_zone.return_value = updated

        response = app_with_endpoints.put(
            "/api/v1/zones/test-zone-id-123",
            json={"enabled": False},
        )

        assert response.status_code == 200
        data = response.json()
        # Unchanged fields should remain the same
        assert data["name"] == "Downloads"
        assert data["auto_sort"] is True
        # Changed field
        assert data["enabled"] is False


# =============================================================================
# API Versioning Tests
# =============================================================================


class TestAPIVersioning:
    """Tests for API versioning and routing."""

    def test_endpoints_use_v1_prefix(
        self,
        app_with_endpoints: TestClient,
    ) -> None:
        """All endpoints are accessible under /api/v1/ prefix."""
        # These should work
        response = app_with_endpoints.get("/api/v1/zones")
        assert response.status_code == 200

        # Root endpoints should still work without prefix
        response = app_with_endpoints.get("/health")
        assert response.status_code == 200

    def test_endpoints_without_prefix_return_404(
        self,
        app_with_endpoints: TestClient,
    ) -> None:
        """Endpoints without /api/v1/ prefix return 404."""
        response = app_with_endpoints.get("/zones")
        assert response.status_code == 404

        response = app_with_endpoints.post("/process", json={"filepath": "/test"})
        assert response.status_code == 404
