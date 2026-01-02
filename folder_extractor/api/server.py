"""
FastAPI server with lifecycle management.

This module provides the main FastAPI application for native macOS integration.
It manages initialization and cleanup of core components (KnowledgeGraph,
AsyncGeminiClient, SmartSorter) through the lifespan context manager.

Usage:
    uvicorn folder_extractor.api.server:app --host 127.0.0.1 --port 23456
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from folder_extractor.api.endpoints import router as api_router
from folder_extractor.api.models import HealthResponse
from folder_extractor.config.constants import VERSION
from folder_extractor.core.ai_async import AIClientError, AsyncGeminiClient
from folder_extractor.core.memory.graph import (
    KnowledgeGraph,
    get_knowledge_graph,
    reset_knowledge_graph,
)
from folder_extractor.core.security import APIKeyError
from folder_extractor.core.smart_sorter import SmartSorter
from folder_extractor.api.websocket import (
    ConnectionManager,
    WebSocketLogHandler,
    WebSocketMessage,
    WebSocketProgressBroadcaster,
)

if TYPE_CHECKING:
    from folder_extractor.config.settings import Settings

# Load environment variables
load_dotenv()

# API Configuration
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "23456"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


# =============================================================================
# Lifespan Context Manager
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage FastAPI application lifecycle.

    Initializes core components on startup:
    - KnowledgeGraph: Kùzu database for document metadata
    - AsyncGeminiClient: AI client for file analysis
    - SmartSorter: Document categorization engine

    Cleans up resources on shutdown.

    Args:
        app: FastAPI application instance

    Yields:
        Control to FastAPI for request handling
    """
    # -------------------------------------------------------------------------
    # Startup
    # -------------------------------------------------------------------------
    logger.info(f"Starting Folder Extractor API v{VERSION}...")

    # Initialize ConnectionManager for WebSocket support
    connection_manager = ConnectionManager()
    app.state.connection_manager = connection_manager
    logger.info("WebSocket ConnectionManager initialized")

    # Initialize WebSocketLogHandler for log streaming
    ws_log_handler = WebSocketLogHandler(
        connection_manager,
        logger_prefix="folder_extractor",
        level=logging.INFO,
    )
    ws_log_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logging.getLogger("folder_extractor").addHandler(ws_log_handler)
    app.state.ws_log_handler = ws_log_handler
    logger.info("WebSocket log streaming enabled")

    # Initialize KnowledgeGraph (required)
    try:
        kg = get_knowledge_graph()
        app.state.knowledge_graph = kg
        logger.info("Knowledge graph initialized")
    except Exception as e:
        logger.error(f"Failed to initialize knowledge graph: {e}")
        raise

    # Initialize AsyncGeminiClient (optional - API key may be missing)
    try:
        client = AsyncGeminiClient()
        app.state.ai_client = client
        logger.info(f"AI client initialized (model: {client.model_name})")
    except APIKeyError as e:
        logger.warning(f"AI client not available: {e}")
        app.state.ai_client = None

    # Initialize SmartSorter (depends on AI client)
    if app.state.ai_client is not None:
        try:
            from folder_extractor.config.settings import settings

            sorter = SmartSorter(client=app.state.ai_client, settings=settings)
            app.state.smart_sorter = sorter
            logger.info("SmartSorter initialized")
        except Exception as e:
            logger.warning(f"SmartSorter not available: {e}")
            app.state.smart_sorter = None
    else:
        app.state.smart_sorter = None
        logger.info("SmartSorter skipped (AI client unavailable)")

    logger.info(f"API server ready on port {API_PORT}")

    yield

    # -------------------------------------------------------------------------
    # Shutdown
    # -------------------------------------------------------------------------
    logger.info("Shutting down Folder Extractor API...")

    # Stop all active filesystem watchers
    from folder_extractor.api.endpoints import active_watchers, watchers_lock

    with watchers_lock:
        for zone_id, watcher_data in list(active_watchers.items()):
            try:
                state_manager = watcher_data["state_manager"]
                observer = watcher_data["observer"]

                state_manager.request_abort()
                observer.stop()
                observer.join(timeout=5.0)

                logger.info(f"Stopped watcher for zone: {zone_id}")
            except Exception as e:
                logger.warning(f"Error stopping watcher {zone_id}: {e}")

        active_watchers.clear()

    if active_watchers:
        logger.info("All filesystem watchers stopped")

    # Cleanup KnowledgeGraph - reset singleton so next startup creates fresh instance
    reset_knowledge_graph()
    app.state.knowledge_graph = None
    logger.info("Knowledge graph closed and singleton reset")

    # Cleanup AI client (no explicit cleanup needed)
    if hasattr(app.state, "ai_client") and app.state.ai_client is not None:
        logger.info("AI client resources released")

    # Cleanup WebSocket connections
    if hasattr(app.state, "connection_manager") and app.state.connection_manager:
        await app.state.connection_manager.close_all()
        logger.info("All WebSocket connections closed")

    # Remove WebSocket log handler
    if hasattr(app.state, "ws_log_handler") and app.state.ws_log_handler:
        logging.getLogger("folder_extractor").removeHandler(app.state.ws_log_handler)
        logger.info("WebSocket log handler removed")

    logger.info("Shutdown complete")


# =============================================================================
# FastAPI Application
# =============================================================================

# OpenAPI tag metadata for endpoint grouping
tags_metadata = [
    {
        "name": "System",
        "description": "System-Endpunkte (Health, Info)",
    },
    {
        "name": "Processing",
        "description": "Dateiverarbeitung und Extraktion",
    },
    {
        "name": "Zones",
        "description": "Dropzone-Verwaltung (CRUD)",
    },
]

app = FastAPI(
    title="Folder Extractor API",
    description="REST API für native macOS Integration mit KI-gestützter Dokumentenanalyse",
    version=VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=tags_metadata,
)

# =============================================================================
# API Router Registration
# =============================================================================

# Register API endpoints under /api/v1 prefix for versioning
app.include_router(api_router, prefix="/api/v1")


# =============================================================================
# CORS Middleware
# =============================================================================

# Allow localhost origins for Swift macOS app integration
# Note: CORSMiddleware doesn't support wildcards in port, so we specify common ports
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:8080",
        "http://localhost:3000",
        "http://localhost:23456",
        "http://127.0.0.1",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:23456",
    ],
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Exception Handlers
# =============================================================================


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled exceptions with structured error response."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )


@app.exception_handler(AIClientError)
async def ai_client_error_handler(
    request: Request, exc: AIClientError
) -> JSONResponse:
    """Handle AI client errors with 503 Service Unavailable."""
    logger.warning(f"AI client error: {exc}")
    return JSONResponse(
        status_code=503,
        content={"detail": str(exc), "type": "AIClientError"},
    )


# =============================================================================
# Endpoints
# =============================================================================


@app.get("/", tags=["System"])
async def root() -> dict[str, str]:
    """
    API root endpoint with basic information.

    Returns:
        Dictionary with API name, version, and documentation links.
    """
    return {
        "name": "Folder Extractor API",
        "version": VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    responses={503: {"model": HealthResponse, "description": "Service Unavailable"}},
)
async def health_check() -> HealthResponse | JSONResponse:
    """
    Health check endpoint for monitoring.

    Checks availability of all core components:
    - Kùzu database (KnowledgeGraph)
    - SmartSorter (AI integration)
    - API server itself

    Returns:
        HealthResponse with status and component details.
        HTTP 200 for "healthy" or "degraded" status.
        HTTP 503 for "unhealthy" status.
    """
    # Check KnowledgeGraph status
    if hasattr(app.state, "knowledge_graph") and app.state.knowledge_graph is not None:
        kg = app.state.knowledge_graph
        if hasattr(kg, "_conn") and kg._conn is not None:
            database_status = "healthy"
        else:
            database_status = "unhealthy (no connection)"
    else:
        database_status = "unavailable"

    # Check SmartSorter status
    if hasattr(app.state, "smart_sorter") and app.state.smart_sorter is not None:
        smart_sorter_status = "healthy"
    else:
        smart_sorter_status = "unavailable (API key missing)"

    # Determine overall status
    if database_status == "unavailable" or "unhealthy" in database_status:
        overall_status = "unhealthy"
    elif smart_sorter_status != "healthy":
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    response_data = HealthResponse(
        status=overall_status,
        version=VERSION,
        database=database_status,
        smart_sorter=smart_sorter_status,
    )

    # Return 503 for unhealthy status
    if overall_status == "unhealthy":
        return JSONResponse(
            status_code=503,
            content=response_data.model_dump(),
        )

    return response_data


# =============================================================================
# WebSocket Endpoint
# =============================================================================


@app.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time bidirectional communication.

    Handles:
    - Chat messages: Forwards to SmartSorter AI for analysis/response
    - Command messages: Process control commands (abort, pause, resume)
    - Broadcasts: Progress updates, status changes, and logs

    Message types (incoming):
    - chat: {"type": "chat", "data": {"message": "..."}}
    - command: {"type": "command", "data": {"action": "abort|pause|resume"}}
    - ping: {"type": "ping"} - Keepalive

    Message types (outgoing):
    - chat: AI responses
    - status: Event updates (incoming, waiting, analyzing, sorted, error)
    - progress: File processing progress
    - log: Application logs
    """
    manager: ConnectionManager = app.state.connection_manager

    await manager.connect(websocket)
    logger.info(f"WebSocket client connected. Active connections: {manager.connection_count}")

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            msg_type = data.get("type", "unknown")
            msg_data = data.get("data", {})

            if msg_type == "ping":
                # Keepalive - no response needed
                continue

            elif msg_type == "chat":
                # Chat message - forward to AI if available
                user_message = msg_data.get("message", "")
                await _handle_chat_message(websocket, manager, user_message)

            elif msg_type == "command":
                # Control command
                action = msg_data.get("action", "")
                await _handle_command(websocket, manager, action, msg_data)

            else:
                # Unknown message type - log but don't crash
                logger.warning(f"Unknown WebSocket message type: {msg_type}")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"WebSocket client disconnected. Active connections: {manager.connection_count}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        manager.disconnect(websocket)


async def _handle_chat_message(
    websocket: WebSocket,
    manager: ConnectionManager,
    message: str,
) -> None:
    """Process a chat message from the client.

    If SmartSorter is available, forwards the message for AI analysis.
    Otherwise, sends an error response.

    Args:
        websocket: The client's WebSocket connection.
        manager: ConnectionManager for sending responses.
        message: The chat message from the user.
    """
    # Send typing indicator
    typing_msg = WebSocketMessage(
        type="status",
        data={"status": "typing", "filename": ""},
    )
    await manager.send_personal_message(typing_msg.to_dict(), websocket)

    # Check if AI is available
    if not hasattr(app.state, "smart_sorter") or app.state.smart_sorter is None:
        error_msg = WebSocketMessage(
            type="error",
            data={
                "message": "KI nicht verfügbar. Bitte API-Key konfigurieren.",
                "code": "AI_UNAVAILABLE",
            },
        )
        await manager.send_personal_message(error_msg.to_dict(), websocket)
        return

    try:
        # Use AI client for chat response
        ai_client = app.state.ai_client
        if ai_client:
            response_text = await ai_client.generate_response(
                prompt=f"Benutzer fragt: {message}\n\nAntworte kurz und hilfreich auf Deutsch.",
            )
        else:
            response_text = "KI-Client nicht initialisiert."

        response_msg = WebSocketMessage(
            type="chat",
            data={
                "message": response_text,
                "sender": "ai",
            },
        )
        await manager.send_personal_message(response_msg.to_dict(), websocket)

    except Exception as e:
        logger.error(f"AI chat error: {e}")
        error_msg = WebSocketMessage(
            type="error",
            data={
                "message": f"Fehler bei KI-Antwort: {e}",
                "code": "AI_ERROR",
            },
        )
        await manager.send_personal_message(error_msg.to_dict(), websocket)


async def _handle_command(
    websocket: WebSocket,
    manager: ConnectionManager,
    action: str,
    data: dict[str, Any],
) -> None:
    """Process a control command from the client.

    Supported actions:
    - abort: Request abort of current operation
    - pause: Pause current operation (not yet implemented)
    - resume: Resume paused operation (not yet implemented)

    Args:
        websocket: The client's WebSocket connection.
        manager: ConnectionManager for sending responses.
        action: The command action to perform.
        data: Additional command parameters.
    """
    from folder_extractor.api.endpoints import active_watchers, watchers_lock

    if action == "abort":
        # Request abort on all active watchers
        with watchers_lock:
            for zone_id, watcher_data in active_watchers.items():
                state_manager = watcher_data.get("state_manager")
                if state_manager:
                    state_manager.request_abort()
                    logger.info(f"Abort requested for zone: {zone_id}")

        response = WebSocketMessage(
            type="status",
            data={
                "status": "abort_requested",
                "message": "Abbruch angefordert",
            },
        )
        await manager.send_personal_message(response.to_dict(), websocket)

    elif action in ("pause", "resume"):
        # Not yet implemented
        response = WebSocketMessage(
            type="status",
            data={
                "status": "not_implemented",
                "message": f"Aktion '{action}' noch nicht implementiert",
            },
        )
        await manager.send_personal_message(response.to_dict(), websocket)

    else:
        logger.warning(f"Unknown command action: {action}")
        response = WebSocketMessage(
            type="status",
            data={
                "status": "unknown_command",
                "message": f"Unbekannte Aktion: {action}",
            },
        )
        await manager.send_personal_message(response.to_dict(), websocket)


# =============================================================================
# Dependency Injection Functions
# =============================================================================


def get_knowledge_graph_dependency() -> KnowledgeGraph:
    """
    Dependency for KnowledgeGraph access in endpoints.

    Returns:
        The initialized KnowledgeGraph instance.

    Raises:
        HTTPException: 503 if KnowledgeGraph is not available.
    """
    if not hasattr(app.state, "knowledge_graph") or app.state.knowledge_graph is None:
        raise HTTPException(status_code=503, detail="Knowledge graph not available")
    return app.state.knowledge_graph


def get_smart_sorter_dependency() -> SmartSorter:
    """
    Dependency for SmartSorter access in endpoints.

    Returns:
        The initialized SmartSorter instance.

    Raises:
        HTTPException: 503 if SmartSorter is not available.
    """
    if not hasattr(app.state, "smart_sorter") or app.state.smart_sorter is None:
        raise HTTPException(
            status_code=503, detail="SmartSorter not available (API key missing)"
        )
    return app.state.smart_sorter


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "folder_extractor.api.server:app",
        host=API_HOST,
        port=API_PORT,
        reload=os.getenv("API_RELOAD", "false").lower() == "true",
    )
