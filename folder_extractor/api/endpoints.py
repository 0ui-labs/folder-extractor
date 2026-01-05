"""
REST API endpoints for file processing and zone management.

This module defines the core REST endpoints for the Folder Extractor API:
- POST /process: Process a single file (background task)
- GET /zones: List all dropzones
- POST /zones: Create a new dropzone
- DELETE /zones/{zone_id}: Delete a dropzone
- PUT /zones/{zone_id}: Update a dropzone

All endpoints use dependency injection for testability and are
registered under the /api/v1 prefix.
"""

from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
)
from fastapi import Path as PathParam
from watchdog.observers import Observer

from folder_extractor.config.settings import Settings

from folder_extractor.api.dependencies import get_orchestrator, get_zone_manager
from folder_extractor.api.models import (
    ProcessRequest,
    ProcessResponse,
    SingleWatcherStatus,
    WatcherListResponse,
    WatcherStartRequest,
    WatcherStopRequest,
    ZoneConfig,
    ZoneListResponse,
    ZoneResponse,
    ZoneUpdateRequest,
)
from folder_extractor.api.websocket import (
    ConnectionManager,
    WebSocketProgressBroadcaster,
)
from folder_extractor.core.extractor import (
    EnhancedExtractionOrchestrator,
    EnhancedFileExtractor,
)
from folder_extractor.core.monitor import StabilityMonitor
from folder_extractor.core.state_manager import StateManager
from folder_extractor.core.watch import FolderEventHandler
from folder_extractor.core.zone_manager import ZoneManager, ZoneManagerError

# =============================================================================
# Router and Logger Setup
# =============================================================================

router = APIRouter()
logger = logging.getLogger(__name__)


# =============================================================================
# Global Watcher State Management
# =============================================================================

# Thread-safe storage for active filesystem watchers.
# Each entry stores observer, handler, monitor, state_manager, and metadata.
active_watchers: dict[str, dict[str, Any]] = {}
watchers_lock = threading.Lock()


def _parse_iso_timestamp(timestamp_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO 8601 timestamp string to datetime object.

    Args:
        timestamp_str: ISO 8601 formatted string or None.

    Returns:
        Parsed datetime object or None if input is None/invalid.
    """
    if not timestamp_str:
        return None
    try:
        return datetime.fromisoformat(timestamp_str)
    except (ValueError, TypeError):
        return None


# =============================================================================
# File Processing Endpoints
# =============================================================================


@router.post("/process", response_model=ProcessResponse, tags=["Processing"])
async def process_file(
    request: ProcessRequest,
    http_request: Request,
    background_tasks: BackgroundTasks,
) -> ProcessResponse:
    """
    Process a single file in the background.

    Takes a file path and starts processing with the EnhancedExtractionOrchestrator.
    Processing runs asynchronously in the background, so the response is
    returned immediately.

    Args:
        request: ProcessRequest with filepath and optional settings.
        background_tasks: FastAPI BackgroundTasks for async processing.
        orchestrator: Injected EnhancedExtractionOrchestrator.

    Returns:
        ProcessResponse with task ID and initial status.

    Raises:
        HTTPException 404: File not found.
        HTTPException 422: Invalid request data.

    Example Request:
        POST /api/v1/process
        {
            "filepath": "/Users/user/Downloads/invoice.pdf"
        }

    Example Response:
        {
            "task_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "processing",
            "message": "Verarbeitung gestartet für: invoice.pdf"
        }
    """
    file_path = Path(request.filepath)

    # Validate file exists
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Datei nicht gefunden: {request.filepath}",
        )

    # Generate task ID for tracking
    task_id = str(uuid.uuid4())

    # Determine destination (file's directory if not specified)
    destination = file_path.parent

    # Create orchestrator with dependencies from app state
    settings = http_request.app.state.settings
    state_manager = StateManager()
    extractor = EnhancedFileExtractor(settings=settings, state_manager=state_manager)
    orchestrator = EnhancedExtractionOrchestrator(extractor, state_manager=state_manager)

    # Define background processing function
    def process_in_background() -> None:
        try:
            result = orchestrator.process_single_file(
                filepath=file_path,
                destination=destination,
                progress_callback=None,  # WebSocket integration in future phase
            )
            logger.info(
                f"File processed: {file_path.name}, "
                f"Status: {result.get('status', 'unknown')}, "
                f"Task ID: {task_id}"
            )
        except Exception as e:
            logger.error(
                f"Background processing failed for {file_path.name}: {e}",
                exc_info=True,
            )

    # Add task to background queue
    background_tasks.add_task(process_in_background)

    logger.info(f"Processing started for: {file_path.name}, Task ID: {task_id}")

    return ProcessResponse(
        task_id=task_id,
        status="processing",
        message=f"Verarbeitung gestartet für: {file_path.name}",
    )


# =============================================================================
# Zone Management Endpoints
# =============================================================================


@router.get("/zones", response_model=ZoneListResponse, tags=["Zones"])
async def list_zones(
    zone_manager: ZoneManager = Depends(get_zone_manager),
) -> ZoneListResponse:
    """
    List all configured dropzones.

    Returns:
        ZoneListResponse with list of all zones and total count.

    Raises:
        HTTPException 503: Zone Manager not available.

    Example Response:
        {
            "zones": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "name": "Downloads",
                    "path": "/Users/user/Downloads",
                    "enabled": true,
                    "auto_sort": true,
                    "categories": ["pdf", "jpg"]
                }
            ],
            "total": 1
        }
    """
    zones = zone_manager.list_zones()

    zone_responses = [
        ZoneResponse(
            id=zone["id"],
            name=zone["name"],
            path=zone["path"],
            enabled=zone["enabled"],
            auto_sort=zone["auto_sort"],
            categories=zone.get("categories", []),
            created_at=_parse_iso_timestamp(zone.get("created_at")),
        )
        for zone in zones
    ]

    return ZoneListResponse(
        zones=zone_responses,
        total=len(zone_responses),
    )


@router.post("/zones", response_model=ZoneResponse, status_code=201, tags=["Zones"])
async def create_zone(
    request: ZoneConfig,
    zone_manager: ZoneManager = Depends(get_zone_manager),
) -> ZoneResponse:
    """
    Create a new dropzone.

    Args:
        request: ZoneConfig with zone configuration.
        zone_manager: Injected ZoneManager.

    Returns:
        ZoneResponse with created zone data (including generated ID).

    Raises:
        HTTPException 400: Invalid zone configuration.
        HTTPException 409: Zone with same path already exists.
        HTTPException 503: Zone Manager not available.

    Example Request:
        POST /api/v1/zones
        {
            "name": "Downloads",
            "path": "/Users/user/Downloads",
            "enabled": true,
            "auto_sort": true,
            "categories": ["pdf", "jpg"]
        }

    Example Response:
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "Downloads",
            "path": "/Users/user/Downloads",
            "enabled": true,
            "auto_sort": true,
            "categories": ["pdf", "jpg"]
        }
    """
    # Check for duplicate path
    existing_zones = zone_manager.list_zones()
    if any(zone["path"] == request.path for zone in existing_zones):
        raise HTTPException(
            status_code=409,
            detail=f"Zone mit Pfad '{request.path}' existiert bereits",
        )

    # Create the zone
    try:
        zone_id = zone_manager.add_zone(
            name=request.name,
            path=request.path,
            enabled=request.enabled,
            auto_sort=request.auto_sort,
            categories=request.categories or [],
        )
    except ZoneManagerError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Retrieve created zone
    zone = zone_manager.get_zone(zone_id)
    if not zone:
        raise HTTPException(
            status_code=500,
            detail="Zone erstellt, aber nicht abrufbar",
        )

    logger.info(f"Zone created: {zone_id} ({request.name})")

    return ZoneResponse(
        id=zone["id"],
        name=zone["name"],
        path=zone["path"],
        enabled=zone["enabled"],
        auto_sort=zone["auto_sort"],
        categories=zone.get("categories", []),
        created_at=_parse_iso_timestamp(zone.get("created_at")),
    )


@router.delete("/zones/{zone_id}", status_code=204, tags=["Zones"])
async def delete_zone(
    zone_id: str = PathParam(..., description="Zone-ID (UUID)"),
    zone_manager: ZoneManager = Depends(get_zone_manager),
) -> Response:
    """
    Delete a dropzone.

    Args:
        zone_id: UUID of the zone to delete.
        zone_manager: Injected ZoneManager.

    Returns:
        None (204 No Content on success).

    Raises:
        HTTPException 404: Zone not found.
        HTTPException 503: Zone Manager not available.

    Example:
        DELETE /api/v1/zones/550e8400-e29b-41d4-a716-446655440000
    """
    # Check if zone exists
    if not zone_manager.zone_exists(zone_id):
        raise HTTPException(
            status_code=404,
            detail=f"Zone nicht gefunden: {zone_id}",
        )

    # Delete the zone
    success = zone_manager.remove_zone(zone_id)
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Zone konnte nicht gelöscht werden",
        )

    logger.info(f"Zone deleted: {zone_id}")

    # Return empty Response for 204 No Content
    return Response(status_code=204)


@router.put("/zones/{zone_id}", response_model=ZoneResponse, tags=["Zones"])
async def update_zone(
    request: ZoneUpdateRequest,
    zone_id: str = PathParam(..., description="Zone-ID (UUID)"),
    zone_manager: ZoneManager = Depends(get_zone_manager),
) -> ZoneResponse:
    """
    Update a dropzone configuration.

    Supports partial updates - only specified fields will be changed.

    Args:
        zone_id: UUID of the zone to update.
        request: ZoneUpdateRequest with fields to update.
        zone_manager: Injected ZoneManager.

    Returns:
        ZoneResponse with updated zone data.

    Raises:
        HTTPException 400: Invalid zone configuration.
        HTTPException 404: Zone not found.
        HTTPException 503: Zone Manager not available.

    Example Request:
        PUT /api/v1/zones/550e8400-e29b-41d4-a716-446655440000
        {
            "name": "Updated Name",
            "enabled": false
        }
    """
    # Check if zone exists
    if not zone_manager.zone_exists(zone_id):
        raise HTTPException(
            status_code=404,
            detail=f"Zone nicht gefunden: {zone_id}",
        )

    # Build update dict from request (only set fields)
    update_data: dict[str, Any] = {}
    if request.name is not None:
        update_data["name"] = request.name
    if request.path is not None:
        update_data["path"] = request.path
    if request.enabled is not None:
        update_data["enabled"] = request.enabled
    if request.auto_sort is not None:
        update_data["auto_sort"] = request.auto_sort
    if request.categories is not None:
        update_data["categories"] = request.categories

    # Update the zone
    try:
        success = zone_manager.update_zone(zone_id, **update_data)
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Zone konnte nicht aktualisiert werden",
            )
    except ZoneManagerError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Retrieve updated zone
    zone = zone_manager.get_zone(zone_id)
    if not zone:
        raise HTTPException(
            status_code=500,
            detail="Zone aktualisiert, aber nicht abrufbar",
        )

    logger.info(f"Zone updated: {zone_id}")

    return ZoneResponse(
        id=zone["id"],
        name=zone["name"],
        path=zone["path"],
        enabled=zone["enabled"],
        auto_sort=zone["auto_sort"],
        categories=zone.get("categories", []),
        created_at=_parse_iso_timestamp(zone.get("created_at")),
    )


# =============================================================================
# Watcher Endpoints
# =============================================================================


@router.post("/watcher/start", response_model=SingleWatcherStatus, tags=["Watcher"])
async def start_watcher(
    request: WatcherStartRequest,
    http_request: Request,
    zone_manager: ZoneManager = Depends(get_zone_manager),
) -> SingleWatcherStatus:
    """
    Start filesystem watching for a zone.

    Creates a new Observer that monitors the zone's directory for file
    creation and move events. Each zone can only have one active watcher.

    Args:
        request: WatcherStartRequest with zone_id.
        zone_manager: Injected ZoneManager.

    Returns:
        SingleWatcherStatus with watcher details.

    Raises:
        HTTPException 404: Zone not found.
        HTTPException 409: Zone already being watched.
        HTTPException 500: Observer start failed.

    Example Request:
        POST /api/v1/watcher/start
        {"zone_id": "550e8400-e29b-41d4-a716-446655440000"}

    Example Response:
        {
            "zone_id": "550e8400-e29b-41d4-a716-446655440000",
            "zone_path": "/Users/user/Downloads",
            "status": "running",
            "started_at": "2025-01-15T12:30:00Z",
            "files_processed": 0
        }
    """
    zone_id = request.zone_id

    # Check if zone exists
    zone = zone_manager.get_zone(zone_id)
    if not zone:
        raise HTTPException(
            status_code=404,
            detail=f"Zone nicht gefunden: {zone_id}",
        )

    zone_path = zone["path"]

    # Get Settings from app state
    if not hasattr(http_request.app.state, "settings") or http_request.app.state.settings is None:
        raise HTTPException(
            status_code=503,
            detail="Settings nicht verfügbar",
        )
    settings = http_request.app.state.settings

    # Check if already watching
    with watchers_lock:
        if zone_id in active_watchers:
            raise HTTPException(
                status_code=409,
                detail=f"Zone wird bereits überwacht: {zone_id}",
            )

        # Create components for watching
        state_manager = StateManager()
        monitor = StabilityMonitor(state_manager)
        extractor = EnhancedFileExtractor(settings=settings, state_manager=state_manager)
        orchestrator = EnhancedExtractionOrchestrator(extractor, state_manager=state_manager)

        # Get ConnectionManager from app state for WebSocket broadcasting
        connection_manager: Optional[ConnectionManager] = getattr(
            http_request.app.state, "connection_manager", None
        )

        # Create WebSocket broadcaster if ConnectionManager is available
        progress_callback = None
        event_callback = None
        websocket_callback = None

        if connection_manager is not None:
            broadcaster = WebSocketProgressBroadcaster(connection_manager)
            progress_callback = broadcaster.get_progress_callback()
            event_callback = broadcaster.get_event_callback()
            logger.info(f"WebSocket broadcasting enabled for zone {zone_id}")

        # Create event handler with WebSocket callbacks
        handler = FolderEventHandler(
            orchestrator=orchestrator,
            monitor=monitor,
            state_manager=state_manager,
            progress_callback=progress_callback,
            on_event_callback=event_callback,
            websocket_callback=websocket_callback,
        )

        # Create and configure observer
        observer = Observer()
        observer.schedule(handler, zone_path, recursive=False)

        # Start observer
        try:
            observer.start()
        except Exception as e:
            logger.error(f"Failed to start observer for zone {zone_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Observer konnte nicht gestartet werden: {e}",
            ) from e

        # Record start time
        started_at = datetime.now(timezone.utc)

        # Store watcher data
        active_watchers[zone_id] = {
            "observer": observer,
            "handler": handler,
            "monitor": monitor,
            "state_manager": state_manager,
            "zone_path": zone_path,
            "started_at": started_at,
        }

    logger.info(f"Started watcher for zone: {zone_id} ({zone_path})")

    return SingleWatcherStatus(
        zone_id=zone_id,
        zone_path=zone_path,
        status="running",
        started_at=started_at,
        files_processed=0,
    )


@router.post("/watcher/stop", tags=["Watcher"])
async def stop_watcher(
    request: WatcherStopRequest,
) -> Dict[str, str]:
    """
    Stop filesystem watching for a zone.

    Gracefully stops the observer, waits for it to finish, and cleans up
    resources. Signals abort via StateManager to stop any in-progress processing.

    Args:
        request: WatcherStopRequest with zone_id.

    Returns:
        Dictionary with zone_id and status "stopped".

    Raises:
        HTTPException 404: Zone not being watched.
        HTTPException 500: Stop operation failed.

    Example Request:
        POST /api/v1/watcher/stop
        {"zone_id": "550e8400-e29b-41d4-a716-446655440000"}

    Example Response:
        {
            "zone_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "stopped"
        }
    """
    zone_id = request.zone_id

    # Get watcher data without removing yet
    with watchers_lock:
        if zone_id not in active_watchers:
            raise HTTPException(
                status_code=404,
                detail=f"Zone wird nicht aktiv überwacht: {zone_id}",
            )

        watcher_data = active_watchers[zone_id]

    # Stop operations outside lock to avoid blocking
    state_manager: StateManager = watcher_data["state_manager"]
    observer: Observer = watcher_data["observer"]

    try:
        # Signal abort to stop any in-progress processing
        state_manager.request_abort()

        # Stop and wait for observer
        observer.stop()
        observer.join(timeout=5.0)

    except Exception as e:
        logger.error(f"Error stopping watcher for zone {zone_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Fehler beim Stoppen des Watchers: {e}",
        ) from e

    # Only remove from registry after successful stop
    with watchers_lock:
        active_watchers.pop(zone_id, None)

    logger.info(f"Stopped watcher for zone: {zone_id}")

    return {"zone_id": zone_id, "status": "stopped"}


@router.get("/watcher/status", response_model=WatcherListResponse, tags=["Watcher"])
async def get_watcher_status(
    zone_id: Optional[str] = Query(default=None, description="Filter by zone ID"),
) -> WatcherListResponse:
    """
    Get status of all active watchers.

    Returns a list of all currently active filesystem watchers with their
    status, zone paths, and processing statistics. The overall_status field
    indicates whether any watchers are running or none are active.

    Args:
        zone_id: Optional zone ID to filter results.

    Returns:
        WatcherListResponse with overall status and list of active watchers.

    Example Response (with active watchers):
        {
            "overall_status": "running",
            "active_watchers": [
                {
                    "zone_id": "550e8400-e29b-41d4-a716-446655440000",
                    "zone_path": "/Users/user/Downloads",
                    "status": "running",
                    "started_at": "2025-01-15T12:30:00Z",
                    "files_processed": 5
                }
            ],
            "total_count": 1
        }

    Example Response (no active watchers):
        {
            "overall_status": "stopped",
            "active_watchers": [],
            "total_count": 0
        }
    """
    watchers_list: list[SingleWatcherStatus] = []

    with watchers_lock:
        # Determine overall status based on ALL watchers (before filtering)
        has_any_watchers = len(active_watchers) > 0

        for watcher_zone_id, watcher_data in active_watchers.items():
            # Apply filter if specified
            if zone_id is not None and watcher_zone_id != zone_id:
                continue

            # Get files processed from state manager if available
            state_manager: StateManager = watcher_data["state_manager"]
            files_processed = 0

            operation_id = state_manager.get_current_operation_id()
            if operation_id:
                stats = state_manager.get_operation_stats(operation_id)
                if stats:
                    files_processed = stats.files_processed

            watchers_list.append(
                SingleWatcherStatus(
                    zone_id=watcher_zone_id,
                    zone_path=watcher_data["zone_path"],
                    status="running",
                    started_at=watcher_data["started_at"],
                    files_processed=files_processed,
                )
            )

    # overall_status reflects whether ANY watchers are running (not affected by filter)
    overall_status = "running" if has_any_watchers else "stopped"

    return WatcherListResponse(
        overall_status=overall_status,
        active_watchers=watchers_list,
        total_count=len(watchers_list),
    )
