"""
Tests for FastAPI server with lifecycle management.

Tests the server startup/shutdown lifecycle, health endpoints,
and exception handling. Uses pytest-asyncio and httpx for async testing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    pass


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_knowledge_graph() -> MagicMock:
    """Create a mock KnowledgeGraph that behaves like the real one."""
    kg = MagicMock()
    kg._conn = MagicMock()  # Simulate active connection
    kg.close = MagicMock()
    return kg


@pytest.fixture
def mock_ai_client() -> MagicMock:
    """Create a mock AsyncGeminiClient."""
    client = MagicMock()
    client.model_name = "gemini-3-flash-preview"
    client.analyze_file = AsyncMock(return_value={"category": "Test"})
    return client


@pytest.fixture
def mock_smart_sorter(mock_ai_client: MagicMock) -> MagicMock:
    """Create a mock SmartSorter."""
    sorter = MagicMock()
    sorter.process_file = AsyncMock(return_value={"category": "Test"})
    return sorter


@pytest.fixture
def app_with_mocks(
    mock_knowledge_graph: MagicMock,
    mock_ai_client: MagicMock,
    mock_smart_sorter: MagicMock,
) -> Generator[TestClient, None, None]:
    """Create a test client with all dependencies mocked."""
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


@pytest.fixture
def app_without_ai_client(
    mock_knowledge_graph: MagicMock,
) -> Generator[TestClient, None, None]:
    """Create a test client where AI client initialization fails."""
    from folder_extractor.core.security import APIKeyError

    with patch(
        "folder_extractor.api.server.get_knowledge_graph",
        return_value=mock_knowledge_graph,
    ), patch(
        "folder_extractor.api.server.AsyncGeminiClient",
        side_effect=APIKeyError("No API key found"),
    ):
        from folder_extractor.api.server import app

        with TestClient(app) as client:
            yield client


# =============================================================================
# Lifespan Tests
# =============================================================================


class TestLifespanManagement:
    """Tests for FastAPI lifespan context manager."""

    def test_startup_initializes_all_components(
        self,
        mock_knowledge_graph: MagicMock,
        mock_ai_client: MagicMock,
        mock_smart_sorter: MagicMock,
    ) -> None:
        """Server startup initializes KnowledgeGraph, AI client, and SmartSorter."""
        with patch(
            "folder_extractor.api.server.get_knowledge_graph",
            return_value=mock_knowledge_graph,
        ) as kg_mock, patch(
            "folder_extractor.api.server.AsyncGeminiClient",
            return_value=mock_ai_client,
        ) as ai_mock, patch(
            "folder_extractor.api.server.SmartSorter",
            return_value=mock_smart_sorter,
        ) as sorter_mock:
            from folder_extractor.api.server import app

            with TestClient(app):
                # Verify all components were initialized
                kg_mock.assert_called_once()
                ai_mock.assert_called_once()
                sorter_mock.assert_called_once()

    def test_shutdown_resets_knowledge_graph_singleton(
        self,
        mock_knowledge_graph: MagicMock,
        mock_ai_client: MagicMock,
        mock_smart_sorter: MagicMock,
    ) -> None:
        """Server shutdown resets the KnowledgeGraph singleton for clean restart."""
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
            "folder_extractor.api.server.reset_knowledge_graph",
        ) as mock_reset:
            from folder_extractor.api.server import app

            with TestClient(app):
                pass  # Context manager triggers startup and shutdown

            # Verify reset_knowledge_graph was called (closes and clears singleton)
            mock_reset.assert_called_once()

    def test_restart_creates_fresh_knowledge_graph(
        self,
        mock_ai_client: MagicMock,
        mock_smart_sorter: MagicMock,
    ) -> None:
        """After shutdown, next startup creates a fresh KnowledgeGraph instance."""
        first_kg = MagicMock()
        first_kg._conn = MagicMock()
        first_kg.close = MagicMock()

        second_kg = MagicMock()
        second_kg._conn = MagicMock()
        second_kg.close = MagicMock()

        # Track which KnowledgeGraph is returned
        kg_instances = [first_kg, second_kg]
        call_count = [0]

        def get_kg_side_effect() -> MagicMock:
            instance = kg_instances[call_count[0]]
            call_count[0] += 1
            return instance

        with patch(
            "folder_extractor.api.server.get_knowledge_graph",
            side_effect=get_kg_side_effect,
        ), patch(
            "folder_extractor.api.server.AsyncGeminiClient",
            return_value=mock_ai_client,
        ), patch(
            "folder_extractor.api.server.SmartSorter",
            return_value=mock_smart_sorter,
        ), patch(
            "folder_extractor.api.server.reset_knowledge_graph",
        ):
            from folder_extractor.api.server import app

            # First startup/shutdown cycle
            with TestClient(app) as client:
                response = client.get("/health")
                assert response.status_code == 200

            # Second startup/shutdown cycle - should get fresh KnowledgeGraph
            with TestClient(app) as client:
                response = client.get("/health")
                assert response.status_code == 200

            # Verify get_knowledge_graph was called twice (once per startup)
            assert call_count[0] == 2

    def test_startup_continues_without_ai_client(
        self,
        mock_knowledge_graph: MagicMock,
    ) -> None:
        """Server starts even if AI client initialization fails (degraded mode)."""
        from folder_extractor.core.security import APIKeyError

        with patch(
            "folder_extractor.api.server.get_knowledge_graph",
            return_value=mock_knowledge_graph,
        ), patch(
            "folder_extractor.api.server.AsyncGeminiClient",
            side_effect=APIKeyError("No API key"),
        ):
            from folder_extractor.api.server import app

            # Should not raise - server starts in degraded mode
            with TestClient(app) as client:
                response = client.get("/health")
                assert response.status_code == 200


# =============================================================================
# Health Check Tests
# =============================================================================


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_healthy_when_all_components_available(
        self,
        app_with_mocks: TestClient,
    ) -> None:
        """Health check returns 'healthy' when all components are initialized."""
        response = app_with_mocks.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "healthy"
        assert data["smart_sorter"] == "healthy"
        assert "version" in data

    def test_health_returns_degraded_without_smart_sorter(
        self,
        app_without_ai_client: TestClient,
    ) -> None:
        """Health check returns 'degraded' when SmartSorter is unavailable."""
        response = app_without_ai_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["database"] == "healthy"
        assert "unavailable" in data["smart_sorter"].lower()

    def test_health_returns_503_when_database_unavailable(
        self,
    ) -> None:
        """Health check returns 503 when KnowledgeGraph is unavailable."""
        # Create a mock KnowledgeGraph with no connection
        mock_kg = MagicMock()
        mock_kg._conn = None  # Simulate no connection
        mock_kg.close = MagicMock()

        with patch(
            "folder_extractor.api.server.get_knowledge_graph",
            return_value=mock_kg,
        ), patch(
            "folder_extractor.api.server.AsyncGeminiClient",
            return_value=MagicMock(model_name="test-model"),
        ), patch(
            "folder_extractor.api.server.SmartSorter",
            return_value=MagicMock(),
        ):
            from folder_extractor.api.server import app

            with TestClient(app) as client:
                response = client.get("/health")

                assert response.status_code == 503
                data = response.json()
                assert data["status"] == "unhealthy"
                assert "unhealthy" in data["database"].lower()

    def test_health_includes_version(
        self,
        app_with_mocks: TestClient,
    ) -> None:
        """Health check response includes application version."""
        response = app_with_mocks.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        # Version should be a non-empty string like "1.3.3"
        assert len(data["version"]) > 0
        assert "." in data["version"]


# =============================================================================
# Root Endpoint Tests
# =============================================================================


class TestRootEndpoint:
    """Tests for / root endpoint."""

    def test_root_returns_api_info(
        self,
        app_with_mocks: TestClient,
    ) -> None:
        """Root endpoint returns API name, version, and documentation links."""
        response = app_with_mocks.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Folder Extractor API"
        assert "version" in data
        assert data["docs"] == "/docs"
        assert data["redoc"] == "/redoc"
        assert data["health"] == "/health"


# =============================================================================
# CORS Tests
# =============================================================================


class TestCORSMiddleware:
    """Tests for CORS middleware configuration."""

    def test_cors_allows_localhost_origin(
        self,
        app_with_mocks: TestClient,
    ) -> None:
        """CORS middleware allows requests from localhost."""
        response = app_with_mocks.options(
            "/health",
            headers={
                "Origin": "http://localhost:8080",
                "Access-Control-Request-Method": "GET",
            },
        )

        # CORS preflight should succeed
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_cors_allows_127_origin(
        self,
        app_with_mocks: TestClient,
    ) -> None:
        """CORS middleware allows requests from 127.0.0.1."""
        response = app_with_mocks.options(
            "/health",
            headers={
                "Origin": "http://127.0.0.1:23456",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.status_code == 200


# =============================================================================
# Exception Handler Tests
# =============================================================================


class TestExceptionHandlers:
    """Tests for global exception handlers."""

    def test_unhandled_exception_returns_500(
        self,
        mock_knowledge_graph: MagicMock,
        mock_ai_client: MagicMock,
        mock_smart_sorter: MagicMock,
    ) -> None:
        """Unhandled exceptions return 500 with error details."""
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

            # Add a test endpoint that raises an exception
            @app.get("/test-error")
            async def raise_error() -> None:
                raise RuntimeError("Test error")

            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/test-error")

                assert response.status_code == 500
                data = response.json()
                assert "detail" in data
                assert data["type"] == "RuntimeError"


# =============================================================================
# Dependency Injection Tests
# =============================================================================


class TestDependencyInjection:
    """Tests for dependency injection functions."""

    def test_get_knowledge_graph_dependency_returns_instance(
        self,
        mock_knowledge_graph: MagicMock,
        mock_ai_client: MagicMock,
        mock_smart_sorter: MagicMock,
    ) -> None:
        """Dependency function returns the initialized KnowledgeGraph."""
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
            from folder_extractor.api.server import (
                app,
                get_knowledge_graph_dependency,
            )

            with TestClient(app):
                # Access app.state through the dependency
                kg = get_knowledge_graph_dependency()
                assert kg is mock_knowledge_graph

    def test_get_smart_sorter_dependency_raises_when_unavailable(
        self,
        mock_knowledge_graph: MagicMock,
    ) -> None:
        """Dependency function raises 503 when SmartSorter is unavailable."""
        from fastapi import HTTPException

        from folder_extractor.core.security import APIKeyError

        with patch(
            "folder_extractor.api.server.get_knowledge_graph",
            return_value=mock_knowledge_graph,
        ), patch(
            "folder_extractor.api.server.AsyncGeminiClient",
            side_effect=APIKeyError("No API key"),
        ):
            from folder_extractor.api.server import (
                app,
                get_smart_sorter_dependency,
            )

            with TestClient(app):
                with pytest.raises(HTTPException) as exc_info:
                    get_smart_sorter_dependency()
                assert exc_info.value.status_code == 503
                assert "SmartSorter" in exc_info.value.detail
