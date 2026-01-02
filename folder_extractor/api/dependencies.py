"""
Dependency injection functions for FastAPI endpoints.

This module provides reusable dependencies for accessing core components
like ZoneManager, EnhancedFileExtractor, and EnhancedExtractionOrchestrator.
Uses FastAPI's Depends() mechanism for automatic injection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from fastapi import HTTPException, Request

from folder_extractor.core.extractor import (
    EnhancedExtractionOrchestrator,
    EnhancedFileExtractor,
)
from folder_extractor.core.zone_manager import ZoneManager

if TYPE_CHECKING:
    from folder_extractor.core.memory.graph import KnowledgeGraph
    from folder_extractor.core.smart_sorter import SmartSorter


# =============================================================================
# Module-level Singletons
# =============================================================================

_zone_manager: Optional[ZoneManager] = None


# =============================================================================
# ZoneManager Dependency
# =============================================================================


def get_zone_manager() -> ZoneManager:
    """
    Provide a singleton ZoneManager instance.

    Creates the ZoneManager on first call and returns the same instance
    on subsequent calls. Thread-safe through ZoneManager's internal locking.

    Returns:
        The shared ZoneManager instance.

    Raises:
        HTTPException: 503 if ZoneManager initialization fails.
    """
    global _zone_manager

    if _zone_manager is None:
        try:
            _zone_manager = ZoneManager()
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Zone Manager nicht verfügbar: {e}",
            ) from e

    return _zone_manager


def reset_zone_manager() -> None:
    """
    Reset the ZoneManager singleton.

    Useful for testing to ensure clean state between tests.
    """
    global _zone_manager
    _zone_manager = None


# =============================================================================
# Extractor Dependencies
# =============================================================================


def get_extractor() -> EnhancedFileExtractor:
    """
    Create a new EnhancedFileExtractor instance.

    Creates a new instance on each call (not a singleton) because
    each extraction operation may have different state requirements.

    Returns:
        A new EnhancedFileExtractor instance with default dependencies.
    """
    return EnhancedFileExtractor()


def get_orchestrator() -> EnhancedExtractionOrchestrator:
    """
    Create an EnhancedExtractionOrchestrator with a new extractor.

    Creates both the extractor and orchestrator for each request,
    ensuring clean state for each file processing operation.

    Returns:
        A new EnhancedExtractionOrchestrator instance.
    """
    extractor = EnhancedFileExtractor()
    return EnhancedExtractionOrchestrator(extractor)


# =============================================================================
# App State Dependencies
# =============================================================================


def get_smart_sorter_from_app_state(request: Request) -> "SmartSorter":
    """
    Get SmartSorter from FastAPI app state.

    The SmartSorter is initialized during app startup (lifespan) and
    stored in app.state. This dependency retrieves it for endpoint use.

    Args:
        request: FastAPI request object containing app reference.

    Returns:
        The initialized SmartSorter instance.

    Raises:
        HTTPException: 503 if SmartSorter is not available (e.g., no API key).
    """
    if (
        not hasattr(request.app.state, "smart_sorter")
        or request.app.state.smart_sorter is None
    ):
        raise HTTPException(
            status_code=503,
            detail="SmartSorter nicht verfügbar (API-Key fehlt)",
        )

    return request.app.state.smart_sorter


def get_knowledge_graph_from_app_state(request: Request) -> "KnowledgeGraph":
    """
    Get KnowledgeGraph from FastAPI app state.

    The KnowledgeGraph is initialized during app startup (lifespan) and
    stored in app.state. This dependency retrieves it for endpoint use.

    Args:
        request: FastAPI request object containing app reference.

    Returns:
        The initialized KnowledgeGraph instance.

    Raises:
        HTTPException: 503 if KnowledgeGraph is not available.
    """
    if (
        not hasattr(request.app.state, "knowledge_graph")
        or request.app.state.knowledge_graph is None
    ):
        raise HTTPException(
            status_code=503,
            detail="Knowledge Graph nicht verfügbar",
        )

    return request.app.state.knowledge_graph
