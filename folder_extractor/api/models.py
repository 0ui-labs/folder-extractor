"""
Pydantic models for API request/response validation.

This module defines all data models used by the REST API and WebSocket
endpoints. All models use Pydantic v2 for validation and serialization.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

# =============================================================================
# Request Models
# =============================================================================


class ProcessRequest(BaseModel):
    """Request model for file processing endpoint.

    Attributes:
        filepath: Absolute path to the file to process.
        sort_by_type: Whether to sort files by type into subfolders.
        deduplicate: Enable content-based deduplication (same name + content).
        global_dedup: Check against entire target directory for duplicates.
    """

    filepath: str = Field(..., min_length=1, description="Absolute path to file")
    sort_by_type: bool = Field(default=False, description="Sort by file type")
    deduplicate: bool = Field(default=False, description="Content-based deduplication")
    global_dedup: bool = Field(default=False, description="Global deduplication check")


class ZoneConfig(BaseModel):
    """Configuration for a dropzone (request model).

    Attributes:
        name: Human-readable name for the zone.
        path: Absolute path to the watched directory.
        enabled: Whether the zone is active.
        auto_sort: Automatically sort files by type.
        categories: List of allowed file extensions (e.g., ["pdf", "jpg"]).
    """

    name: str = Field(..., min_length=1, max_length=100, description="Zone name")
    path: str = Field(..., min_length=1, description="Absolute path to directory")
    enabled: bool = Field(default=True, description="Zone is active")
    auto_sort: bool = Field(default=False, description="Auto-sort by type")
    categories: list[str] = Field(
        default_factory=list, description="Allowed file types"
    )


class ZoneUpdateRequest(BaseModel):
    """Request for updating a zone (partial update).

    All fields are optional - only specified fields will be updated.

    Attributes:
        name: New zone name.
        path: New absolute path to directory.
        enabled: New enabled status.
        auto_sort: New auto-sort setting.
        categories: New list of allowed file types.
    """

    name: Optional[str] = Field(
        default=None, min_length=1, max_length=100, description="Zone name"
    )
    path: Optional[str] = Field(default=None, min_length=1, description="Absolute path")
    enabled: Optional[bool] = Field(default=None, description="Zone is active")
    auto_sort: Optional[bool] = Field(default=None, description="Auto-sort")
    categories: Optional[list[str]] = Field(
        default=None, description="Allowed file types"
    )


class WatcherStartRequest(BaseModel):
    """Request to start watching a zone.

    Attributes:
        zone_id: ID of the zone to watch.
        auto_process: Whether to automatically process new files.
    """

    zone_id: str = Field(..., description="Zone ID to watch")
    auto_process: bool = Field(default=True, description="Auto-process new files")


class WatcherStopRequest(BaseModel):
    """Request to stop watching a zone.

    Attributes:
        zone_id: ID of the zone to stop watching.
    """

    zone_id: str = Field(..., description="Zone ID to stop")


# =============================================================================
# Response Models
# =============================================================================


class ProcessResponse(BaseModel):
    """Response for file processing operations.

    Attributes:
        task_id: Unique identifier for the background task.
        status: Current status (started, processing, completed, failed).
        message: Human-readable status message.
    """

    task_id: str = Field(..., description="Background task ID")
    status: str = Field(..., description="Task status")
    message: str = Field(..., description="Status message")


class ZoneResponse(BaseModel):
    """Response containing full zone information.

    Attributes:
        id: Unique zone identifier (UUID).
        name: Human-readable zone name.
        path: Absolute path to directory.
        enabled: Whether zone is active.
        auto_sort: Whether auto-sorting is enabled.
        categories: List of allowed file types.
        created_at: Zone creation timestamp (optional, not stored by ZoneManager).
    """

    id: str = Field(..., description="Zone UUID")
    name: str = Field(..., description="Zone name")
    path: str = Field(..., description="Directory path")
    enabled: bool = Field(..., description="Zone is active")
    auto_sort: bool = Field(..., description="Auto-sort enabled")
    categories: list[str] = Field(..., description="Allowed file types")
    created_at: Optional[datetime] = Field(
        default=None, description="Creation timestamp"
    )


class ZoneListResponse(BaseModel):
    """Response for listing all zones.

    Attributes:
        zones: List of zone configurations.
        total: Total number of zones.
    """

    zones: list[ZoneResponse] = Field(..., description="List of zones")
    total: int = Field(..., description="Total number of zones")


class SingleWatcherStatus(BaseModel):
    """Status information for a single active watcher.

    Attributes:
        zone_id: ID of the watched zone.
        zone_path: Absolute path being watched.
        status: Current status ("running", "stopping").
        started_at: Timestamp when watcher was started.
        files_processed: Number of files processed since start.
    """

    zone_id: str = Field(..., description="Zone UUID")
    zone_path: str = Field(..., description="Watched directory path")
    status: str = Field(..., description="Watcher status: running, stopping")
    started_at: datetime = Field(..., description="Start timestamp")
    files_processed: int = Field(default=0, description="Files processed count")


class WatcherStatusResponse(BaseModel):
    """Response containing watcher status information.

    Attributes:
        running: Whether the watcher is currently running.
        zones: List of currently watched zone IDs.
        active_since: Timestamp when watcher was started (None if stopped).
    """

    running: bool = Field(..., description="Watcher is running")
    zones: list[str] = Field(..., description="Watched zone IDs")
    active_since: Optional[datetime] = Field(
        default=None, description="Start timestamp"
    )


class WatcherListResponse(BaseModel):
    """Response for listing all active watchers.

    Attributes:
        overall_status: "running" if any watcher active, "stopped" if none.
        active_watchers: List of active watcher status objects.
        total_count: Total number of active watchers.
    """

    overall_status: str = Field(..., description="Overall status: running or stopped")
    active_watchers: list[SingleWatcherStatus] = Field(
        ..., description="Active watchers"
    )
    total_count: int = Field(..., description="Total active watcher count")


class HealthResponse(BaseModel):
    """Response for health check endpoint.

    Attributes:
        status: Overall health status ("healthy" or "unhealthy").
        version: Application version string.
        database: Database connection status.
        smart_sorter: AI sorter availability status.
    """

    status: str = Field(..., description="Health status")
    version: str = Field(..., description="App version")
    database: str = Field(..., description="Database status")
    smart_sorter: str = Field(..., description="SmartSorter status")


# =============================================================================
# WebSocket Models
# =============================================================================


class WebSocketMessage(BaseModel):
    """Message format for WebSocket communication.

    Supports different message types for real-time updates:
    - "progress": File processing progress updates
    - "status": General status messages
    - "chat": AI-to-user communication (e.g., clarification requests)
    - "error": Error notifications

    Attributes:
        type: Message type identifier.
        data: Flexible payload containing message-specific data.
        timestamp: When the message was created.

    Example payloads:
        Progress: {"current": 5, "total": 10, "file": "document.pdf"}
        Status: {"message": "Analyzing...", "level": "info"}
        Chat: {"message": "Category unclear. Please choose:", "file": "X.pdf"}
        Error: {"message": "Processing failed", "details": "IO Error"}
    """

    type: str = Field(..., description="Message type: progress, status, chat, error")
    data: dict[str, Any] = Field(..., description="Message payload")
    timestamp: datetime = Field(..., description="Message timestamp")
