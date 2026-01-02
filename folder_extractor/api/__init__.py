"""
API layer for macOS native app integration.

This module provides REST API and WebSocket endpoints for the Folder Extractor,
enabling integration with native macOS applications.

Components:
- models.py: Pydantic request/response models
- server.py: FastAPI application (Phase 3)
- endpoints.py: REST endpoint implementations (Phase 4)
- websocket.py: WebSocket connection manager (Phase 6)
"""

from folder_extractor.api.models import (
    HealthResponse,
    ProcessRequest,
    ProcessResponse,
    SingleWatcherStatus,
    WatcherListResponse,
    WatcherStartRequest,
    WatcherStatusResponse,
    WatcherStopRequest,
    WebSocketMessage,
    ZoneConfig,
    ZoneResponse,
    ZoneUpdateRequest,
)

__all__ = [
    "ProcessRequest",
    "ProcessResponse",
    "ZoneConfig",
    "ZoneUpdateRequest",
    "ZoneResponse",
    "WatcherStartRequest",
    "WatcherStopRequest",
    "WatcherStatusResponse",
    "SingleWatcherStatus",
    "WatcherListResponse",
    "HealthResponse",
    "WebSocketMessage",
]
