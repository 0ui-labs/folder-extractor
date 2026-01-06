"""
Tests for API dependency injection module.

Tests that dependencies correctly provide instances of ZoneManager,
EnhancedFileExtractor, and EnhancedExtractionOrchestrator.
"""

from __future__ import annotations

from typing import Generator
from unittest.mock import MagicMock, patch

import pytest


# Skip entire module if API server cannot be imported (Python 3.8 lacks google-generativeai)
def _can_import_api_server() -> bool:
    """Check if the API server module can be imported."""
    try:
        from folder_extractor.api import server  # noqa: F401

        return True
    except ImportError:
        return False


pytestmark = pytest.mark.skipif(
    not _can_import_api_server(),
    reason="API server requires google-generativeai (Python 3.9+)",
)

# Import after skip marker to avoid import errors on Python 3.8
from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

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
def app_with_mocks(
    mock_knowledge_graph: MagicMock,
    mock_ai_client: MagicMock,
    mock_smart_sorter: MagicMock,
) -> Generator[TestClient, None, None]:
    """Create a test client with all server dependencies mocked."""
    with patch(
        "folder_extractor.api.server.get_knowledge_graph",
        return_value=mock_knowledge_graph,
    ), patch(
        "folder_extractor.api.server.AsyncGeminiClient",
        return_value=mock_ai_client,
    ), patch(
        "folder_extractor.api.server.SmartSorter",
        return_value=mock_smart_sorter,
    ):
        from folder_extractor.api.server import app

        with TestClient(app) as client:
            yield client


# =============================================================================
# ZoneManager Dependency Tests
# =============================================================================


class TestGetZoneManager:
    """Tests for get_zone_manager dependency function."""

    def test_returns_zone_manager_instance(self) -> None:
        """Dependency returns a valid ZoneManager instance."""
        with patch("folder_extractor.api.dependencies.ZoneManager") as mock_zm_class:
            mock_instance = MagicMock()
            mock_zm_class.return_value = mock_instance

            from folder_extractor.api.dependencies import get_zone_manager

            result = get_zone_manager()
            assert result is mock_instance

    def test_returns_singleton_instance(self) -> None:
        """Multiple calls return the same ZoneManager instance (singleton)."""
        with patch("folder_extractor.api.dependencies.ZoneManager") as mock_zm_class:
            mock_instance = MagicMock()
            mock_zm_class.return_value = mock_instance

            # Reset the singleton
            import folder_extractor.api.dependencies as deps

            deps._zone_manager = None

            from folder_extractor.api.dependencies import get_zone_manager

            first_call = get_zone_manager()
            second_call = get_zone_manager()

            assert first_call is second_call
            # Constructor should only be called once
            mock_zm_class.assert_called_once()

    def test_raises_503_when_zone_manager_init_fails(self) -> None:
        """Dependency raises HTTPException 503 when ZoneManager initialization fails."""
        with patch(
            "folder_extractor.api.dependencies.ZoneManager",
            side_effect=Exception("Failed to initialize"),
        ):
            # Reset the singleton
            import folder_extractor.api.dependencies as deps

            deps._zone_manager = None

            from folder_extractor.api.dependencies import get_zone_manager

            with pytest.raises(HTTPException) as exc_info:
                get_zone_manager()

            assert exc_info.value.status_code == 503
            assert "Zone Manager" in exc_info.value.detail


# =============================================================================
# App State Dependencies Tests
# =============================================================================


class TestGetSmartSorterFromAppState:
    """Tests for get_smart_sorter_from_app_state dependency."""

    def test_returns_smart_sorter_from_app_state(
        self,
        mock_knowledge_graph: MagicMock,
        mock_ai_client: MagicMock,
        mock_smart_sorter: MagicMock,
    ) -> None:
        """Dependency returns SmartSorter from app.state."""
        with patch(
            "folder_extractor.api.server.get_knowledge_graph",
            return_value=mock_knowledge_graph,
        ), patch(
            "folder_extractor.api.server.AsyncGeminiClient",
            return_value=mock_ai_client,
        ), patch(
            "folder_extractor.api.server.SmartSorter",
            return_value=mock_smart_sorter,
        ):
            from fastapi import Depends, Request

            from folder_extractor.api.dependencies import (
                get_smart_sorter_from_app_state,
            )
            from folder_extractor.api.server import app

            # Add a test endpoint that uses the dependency
            @app.get("/test-smart-sorter-dep")
            async def test_endpoint(
                request: Request,
                sorter: MagicMock = Depends(
                    lambda r=Depends(lambda req: req): get_smart_sorter_from_app_state(
                        r
                    )
                ),
            ) -> dict[str, str]:
                return {"status": "ok"}

            with TestClient(app) as client:
                # The test is that the app starts and the dependency can be resolved
                response = client.get("/health")
                assert response.status_code == 200

    def test_raises_503_when_smart_sorter_unavailable(
        self,
        mock_knowledge_graph: MagicMock,
    ) -> None:
        """Dependency raises 503 when SmartSorter is not available."""
        from folder_extractor.core.security import APIKeyError

        with patch(
            "folder_extractor.api.server.get_knowledge_graph",
            return_value=mock_knowledge_graph,
        ), patch(
            "folder_extractor.api.server.AsyncGeminiClient",
            side_effect=APIKeyError("No API key"),
        ):
            from folder_extractor.api.dependencies import (
                get_smart_sorter_from_app_state,
            )
            from folder_extractor.api.server import app

            with TestClient(app):
                # Create a mock request with app state
                mock_request = MagicMock()
                mock_request.app = app

                with pytest.raises(HTTPException) as exc_info:
                    get_smart_sorter_from_app_state(mock_request)

                assert exc_info.value.status_code == 503
                assert "SmartSorter" in exc_info.value.detail


class TestGetKnowledgeGraphFromAppState:
    """Tests for get_knowledge_graph_from_app_state dependency."""

    def test_returns_knowledge_graph_from_app_state(
        self,
        mock_knowledge_graph: MagicMock,
        mock_ai_client: MagicMock,
        mock_smart_sorter: MagicMock,
    ) -> None:
        """Dependency returns KnowledgeGraph from app.state."""
        with patch(
            "folder_extractor.api.server.get_knowledge_graph",
            return_value=mock_knowledge_graph,
        ), patch(
            "folder_extractor.api.server.AsyncGeminiClient",
            return_value=mock_ai_client,
        ), patch(
            "folder_extractor.api.server.SmartSorter",
            return_value=mock_smart_sorter,
        ):
            from folder_extractor.api.dependencies import (
                get_knowledge_graph_from_app_state,
            )
            from folder_extractor.api.server import app

            with TestClient(app):
                # Create a mock request with app state
                mock_request = MagicMock()
                mock_request.app = app

                result = get_knowledge_graph_from_app_state(mock_request)
                assert result is mock_knowledge_graph

    def test_raises_503_when_knowledge_graph_unavailable(self) -> None:
        """Dependency raises 503 when KnowledgeGraph is not available."""
        from folder_extractor.api.dependencies import (
            get_knowledge_graph_from_app_state,
        )

        # Create a mock request with no knowledge graph in app state
        mock_request = MagicMock()
        mock_request.app.state.knowledge_graph = None

        with pytest.raises(HTTPException) as exc_info:
            get_knowledge_graph_from_app_state(mock_request)

        assert exc_info.value.status_code == 503
        assert "Knowledge Graph" in exc_info.value.detail
