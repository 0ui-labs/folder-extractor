"""File system event handler for watch mode.

Provides smart debouncing and robust error handling for filesystem monitoring.
The FolderEventHandler class handles file system events from watchdog. It filters
temporary files, waits for file stability, and triggers extraction via the
orchestrator. Errors are caught and logged to prevent the watcher from crashing.

SmartFolderEventHandler extends this with AI-powered categorization via SmartSorter,
supporting template-based path building with placeholders.
"""

from __future__ import annotations

import asyncio
import fnmatch
import logging
import mimetypes
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional

from watchdog.events import FileSystemEvent, FileSystemEventHandler

from folder_extractor.config.constants import TEMP_EXTENSIONS
from folder_extractor.core.extractor import EnhancedExtractionOrchestrator
from folder_extractor.core.file_operations import FileOperations
from folder_extractor.core.monitor import StabilityMonitor
from folder_extractor.core.state_manager import IStateManager
from folder_extractor.utils.path_validators import is_safe_path

if TYPE_CHECKING:
    from folder_extractor.core.smart_sorter import SmartSorter

logger = logging.getLogger(__name__)

# Type alias for progress callback: (current, total, filename, error) -> None
ProgressCallback = Optional[Callable[[int, int, str, Optional[str]], None]]

# Type alias for event callback: (status, filename, error) -> None
# status: "incoming", "waiting", "analyzing", "sorted", "error"
EventCallback = Optional[Callable[[str, str, Optional[str]], None]]

# Type alias for WebSocket callback: receives structured updates for real-time streaming
# Can be sync or async - handler checks and schedules appropriately
WebSocketCallback = Optional[Callable[..., Any]]


class FolderEventHandler(FileSystemEventHandler):
    """Handle file system events for watch mode.

    Processes file creation and move events, filtering temporary files and
    waiting for file stability before triggering extraction. Integrates with
    StabilityMonitor for debouncing and StateManager for abort handling.

    Attributes:
        orchestrator: Extraction orchestrator for processing files.
        monitor: Stability monitor for file readiness detection.
        state_manager: State manager for abort signal handling.
        base_path: Base directory for the watch zone.
        file_types: Optional list of allowed file extensions.
        ignore_patterns: Patterns for files to ignore.
        exclude_subfolders: Subfolders to exclude when recursive=True.
        recursive: Whether subdirectories are watched.
        progress_callback: Optional callback for progress updates.
    """

    def __init__(
        self,
        orchestrator: EnhancedExtractionOrchestrator,
        monitor: StabilityMonitor,
        state_manager: IStateManager,
        base_path: Optional[Path] = None,
        file_types: Optional[list[str]] = None,
        ignore_patterns: Optional[list[str]] = None,
        exclude_subfolders: Optional[list[str]] = None,
        recursive: bool = False,
        progress_callback: ProgressCallback = None,
        on_event_callback: EventCallback = None,
        websocket_callback: WebSocketCallback = None,
    ) -> None:
        """Initialize folder event handler for watch mode.

        Args:
            orchestrator: Extraction orchestrator instance.
            monitor: Stability monitor instance.
            state_manager: State manager instance.
            base_path: Base directory for the watch zone (required for
                subfolder filtering).
            file_types: Optional list of allowed file extensions.
            ignore_patterns: Glob patterns for files to ignore.
            exclude_subfolders: Subfolder names to exclude when recursive=True.
            recursive: Whether subdirectories are watched.
            progress_callback: Optional callback for progress updates.
                Signature: (current, total, filename, error) -> None
            on_event_callback: Optional callback for UI event updates.
                Signature: (status, filename, error) -> None
                Status values: "incoming", "waiting", "analyzing", "sorted", "error"
            websocket_callback: Optional callback for WebSocket real-time updates.
                Receives structured dict with type, data, and filename.
                Can be sync or async - handler schedules appropriately.
        """
        super().__init__()
        self.orchestrator = orchestrator
        self.monitor = monitor
        self.state_manager = state_manager
        self.base_path = Path(base_path).resolve() if base_path else None
        self.file_types = [ft.lower().lstrip(".") for ft in (file_types or [])]
        self.ignore_patterns = ignore_patterns or []
        self.exclude_subfolders = exclude_subfolders or []
        self.recursive = recursive
        self.progress_callback = progress_callback
        self.on_event_callback = on_event_callback
        self.websocket_callback = websocket_callback
        self._processing_files: set[str] = set()

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events.

        Args:
            event: File system event from watchdog.

        Note:
            Errors are logged but do not stop the watcher.
        """
        if event.is_directory:
            return

        filepath = Path(event.src_path)
        self._process_file(filepath)

    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file move events (e.g., browser downloads completing).

        Args:
            event: File system event from watchdog.

        Note:
            Processes destination file after move completes.
        """
        if event.is_directory:
            return

        filepath = Path(event.dest_path)
        self._process_file(filepath)

    def _safe_progress(
        self,
        current: int,
        total: int,
        filename: str,
        error: Optional[str] = None,
    ) -> None:
        """Safely invoke progress callback, suppressing any exceptions.

        Args:
            current: Current progress count.
            total: Total items to process.
            filename: Name of file being processed.
            error: Optional error message.

        Note:
            Exceptions from the callback are logged but suppressed
            to prevent faulty callbacks from crashing the watcher.
        """
        # Also notify WebSocket callback with progress data
        self._safe_websocket(
            type="progress",
            data={"current": current, "total": total, "error": error},
            filename=filename,
        )

        if not self.progress_callback:
            return

        try:
            self.progress_callback(current, total, filename, error)
        except Exception as e:
            logger.warning(
                f"Progress callback raised exception: {e}",
                exc_info=True,
            )

    def _safe_event(
        self,
        status: str,
        filename: str,
        error: Optional[str] = None,
    ) -> None:
        """Safely invoke event callback, suppressing any exceptions.

        Args:
            status: Event status. One of: incoming, waiting, analyzing,
                sorted, or error.
            filename: Name of file being processed.
            error: Optional error message.

        Note:
            Exceptions from the callback are logged but suppressed
            to prevent faulty callbacks from crashing the watcher.
        """
        # Also notify WebSocket callback with event data
        self._safe_websocket(
            type="status",
            data={"status": status, "error": error},
            filename=filename,
        )

        if not self.on_event_callback:
            return

        try:
            self.on_event_callback(status, filename, error)
        except Exception as e:
            logger.warning(
                f"Event callback raised exception: {e}",
                exc_info=True,
            )

    def _safe_websocket(
        self,
        type: str,
        data: dict[str, Any],
        filename: str,
    ) -> None:
        """Safely invoke WebSocket callback, suppressing any exceptions.

        The callback receives a structured dict suitable for WebSocket broadcast.
        Supports both sync and async callbacks - async callbacks are scheduled
        via asyncio.create_task when an event loop is running.

        Args:
            type: Message type (progress, status, etc.).
            data: Message payload data.
            filename: Name of file being processed.

        Note:
            Exceptions from the callback are logged but suppressed
            to prevent faulty callbacks from crashing the watcher.
        """
        if not self.websocket_callback:
            return

        message = {
            "type": type,
            "data": {**data, "filename": filename},
        }

        try:
            result = self.websocket_callback(message)
            # Handle async callbacks
            if asyncio.iscoroutine(result):
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(result)
                    else:
                        loop.run_until_complete(result)
                except RuntimeError:
                    asyncio.run(result)
        except Exception as e:
            logger.warning(
                f"WebSocket callback raised exception: {e}",
                exc_info=True,
            )

    def _is_temp_file(self, filepath: Path) -> bool:
        """Check if file is a temporary file that should be ignored.

        Checks both the file extension against TEMP_EXTENSIONS and
        common browser download patterns.

        Args:
            filepath: Path to the file to check.

        Returns:
            True if the file is a temporary file, False otherwise.
        """
        filename = filepath.name.lower()
        extension = filepath.suffix.lower()

        # Check extension against known temp extensions
        if extension in TEMP_EXTENSIONS:
            return True

        # Check filename patterns for browser downloads
        # These patterns catch compound extensions like .pdf.crdownload
        return any(filename.endswith(ext) for ext in (".crdownload", ".part", ".tmp"))

    def _should_skip_file(self, filepath: Path) -> bool:
        """Check if file should be skipped based on filters.

        Checks:
        - Temp files (extensions and patterns)
        - File type filter (if configured)
        - Ignore patterns
        - Excluded subfolders (when recursive)

        Args:
            filepath: Path to check.

        Returns:
            True if file should be skipped.
        """
        filename = filepath.name
        extension = filepath.suffix.lower().lstrip(".")

        # Skip temp files
        if self._is_temp_file(filepath):
            return True

        # Check file type filter
        if self.file_types and extension not in self.file_types:
            return True

        # Check ignore patterns
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(filename, pattern):
                return True

        # Check excluded subfolders (when recursive)
        if self.recursive and self.exclude_subfolders and self.base_path:
            try:
                relative = filepath.relative_to(self.base_path)
                for part in relative.parts[:-1]:  # Exclude filename
                    if part in self.exclude_subfolders:
                        return True
            except ValueError:
                pass  # Not relative to base_path

        return False

    def _process_file(self, filepath: Path) -> None:
        """Process a new file: wait for stability, then extract.

        Args:
            filepath: Path to the file to process.

        Note:
            All errors are caught and logged to prevent watcher crash.
        """
        try:
            # Check if file should be skipped based on filters
            if self._should_skip_file(filepath):
                logger.debug(f"Skipping file based on filters: {filepath}")
                return

            # Prevent duplicate processing
            if str(filepath) in self._processing_files:
                logger.debug(f"Already processing: {filepath}")
                return

            # Track this file as being processed
            self._processing_files.add(str(filepath))

            try:
                logger.info(f"Detected new file: {filepath.name}")

                # Notify UI: incoming
                self._safe_event("incoming", filepath.name)

                # Notify UI: waiting
                self._safe_event("waiting", filepath.name)

                # Notify progress: waiting
                self._safe_progress(0, 1, f"\u23f3 Warte auf {filepath.name}...")

                # Wait for file to be ready
                ready = self.monitor.wait_for_file_ready(filepath, timeout=60)
                if not ready:
                    logger.warning(f"File not ready after timeout: {filepath}")
                    return

                # Check for abort signal
                if self.state_manager.is_abort_requested():
                    logger.info("Abort requested, skipping file processing")
                    return

                # Notify UI: analyzing
                self._safe_event("analyzing", filepath.name)

                # Notify progress: analyzing
                self._safe_progress(0, 1, f"\U0001f916 Analysiere {filepath.name}...")

                # Process single file directly - avoid full directory scan
                results = self.orchestrator.process_single_file(
                    filepath=filepath,
                    destination=self.base_path or filepath.parent,
                    progress_callback=self.progress_callback,
                )

                # Check results
                if results.get("status") == "success":
                    logger.info(f"Successfully processed: {filepath.name}")
                    # Notify UI: sorted
                    self._safe_event("sorted", filepath.name)
                    self._safe_progress(1, 1, f"\u2705 {filepath.name} sortiert")
                else:
                    logger.error(f"Failed to process: {filepath.name}")

            finally:
                # Always clean up processing set
                self._processing_files.discard(str(filepath))

        except Exception as e:
            logger.error(f"Error processing {filepath}: {e}", exc_info=True)
            # Notify UI: error
            self._safe_event("error", filepath.name, str(e))
            self._safe_progress(1, 1, filepath.name, str(e))


class SmartFolderEventHandler(FileSystemEventHandler):
    """Handle file system events with AI-powered smart sorting.

    Processes file creation and move events using SmartSorter for AI-based
    categorization. Supports template-based path building with placeholders
    like {category}, {sender}, {year}, {month}, {filename}.

    Attributes:
        smart_sorter: SmartSorter instance for AI categorization.
        monitor: Stability monitor for file readiness detection.
        state_manager: State manager for abort signal handling.
        base_path: Base directory for the watch zone.
        folder_structure: Template for target path (e.g., "{category}/{sender}/{year}").
        file_types: Optional list of allowed file extensions.
        ignore_patterns: Patterns for files to ignore.
        exclude_subfolders: Subfolders to exclude when recursive=True.
        recursive: Whether to watch subdirectories.
    """

    # Timeout constants
    CREATED_TIMEOUT = 30  # 30 seconds for newly created files
    MOVED_TIMEOUT = 2  # 2 seconds for moved files (already complete)

    def __init__(
        self,
        smart_sorter: SmartSorter,
        monitor: StabilityMonitor,
        state_manager: IStateManager,
        base_path: Path,
        folder_structure: str = "{category}/{sender}/{year}",
        file_types: Optional[list[str]] = None,
        ignore_patterns: Optional[list[str]] = None,
        exclude_subfolders: Optional[list[str]] = None,
        recursive: bool = False,
        progress_callback: ProgressCallback = None,
        on_event_callback: EventCallback = None,
        websocket_callback: WebSocketCallback = None,
    ) -> None:
        """Initialize smart folder event handler.

        Args:
            smart_sorter: SmartSorter instance for AI categorization.
            monitor: Stability monitor instance.
            state_manager: State manager instance.
            base_path: Base directory for the watch zone.
            folder_structure: Template for target path with placeholders.
                Supported: {category}, {sender}, {year}, {month}, {filename}
            file_types: Optional list of allowed file extensions.
            ignore_patterns: Glob patterns for files to ignore.
            exclude_subfolders: Subfolder names to exclude when recursive=True.
            recursive: Whether to watch subdirectories.
            progress_callback: Optional callback for progress updates.
            on_event_callback: Optional callback for UI event updates.
            websocket_callback: Optional callback for WebSocket real-time updates.
        """
        super().__init__()
        self.smart_sorter = smart_sorter
        self.monitor = monitor
        self.state_manager = state_manager

        # Validate base_path is in a safe location
        resolved_base = Path(base_path).resolve()
        if not is_safe_path(resolved_base):
            raise ValueError(
                f"base_path must be in an allowed folder (Desktop, Downloads, or Documents). "
                f"Got: {resolved_base}"
            )

        self.base_path = resolved_base
        self.folder_structure = folder_structure
        self.file_types = [ft.lower().lstrip(".") for ft in (file_types or [])]
        self.ignore_patterns = ignore_patterns or []
        self.exclude_subfolders = exclude_subfolders or []
        self.recursive = recursive
        self.progress_callback = progress_callback
        self.on_event_callback = on_event_callback
        self.websocket_callback = websocket_callback
        self._processing_files: set[str] = set()
        self._file_ops = FileOperations()

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events with 30s stability timeout.

        Args:
            event: File system event from watchdog.
        """
        if event.is_directory:
            return

        filepath = Path(event.src_path)
        self._schedule_processing(filepath, timeout=self.CREATED_TIMEOUT)

    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file move events with 2s stability timeout.

        Args:
            event: File system event from watchdog.
        """
        if event.is_directory:
            return

        filepath = Path(event.dest_path)
        self._schedule_processing(filepath, timeout=self.MOVED_TIMEOUT)

    def _schedule_processing(self, filepath: Path, timeout: int) -> None:
        """Schedule file processing with the given stability timeout.

        Args:
            filepath: Path to the file to process.
            timeout: Stability timeout in seconds.
        """
        if self._should_skip_file(filepath):
            logger.debug(f"Skipping file: {filepath}")
            return

        # Prevent duplicate processing
        if str(filepath) in self._processing_files:
            logger.debug(f"Already processing: {filepath}")
            return

        self._processing_files.add(str(filepath))

        try:
            # Run async processing
            asyncio.run(self._process_file_smart(filepath, timeout))
        except Exception as e:
            logger.error(f"Error processing {filepath}: {e}", exc_info=True)
            self._safe_event("error", filepath.name, str(e))
        finally:
            self._processing_files.discard(str(filepath))

    def _should_skip_file(self, filepath: Path) -> bool:
        """Check if file should be skipped based on filters.

        Checks:
        - Temp files (extensions and patterns)
        - File type filter (if configured)
        - Ignore patterns
        - Excluded subfolders (when recursive)

        Args:
            filepath: Path to check.

        Returns:
            True if file should be skipped.
        """
        filename = filepath.name
        extension = filepath.suffix.lower().lstrip(".")

        # Skip temp files
        if filepath.suffix.lower() in TEMP_EXTENSIONS:
            return True

        # Skip browser download temp patterns
        if any(
            filename.lower().endswith(ext) for ext in (".crdownload", ".part", ".tmp")
        ):
            return True

        # Check file type filter
        if self.file_types and extension not in self.file_types:
            return True

        # Check ignore patterns
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(filename, pattern):
                return True

        # Check excluded subfolders (when recursive)
        if self.recursive and self.exclude_subfolders:
            try:
                relative = filepath.relative_to(self.base_path)
                for part in relative.parts[:-1]:  # Exclude filename
                    if part in self.exclude_subfolders:
                        return True
            except ValueError:
                pass  # Not relative to base_path

        return False

    async def _process_file_smart(self, filepath: Path, timeout: int) -> None:
        """Process file with SmartSorter for AI categorization.

        Waits for file stability, detects MIME type, calls SmartSorter,
        builds target path from template, and moves file with duplicate-safe naming.

        Args:
            filepath: Path to the file to process.
            timeout: Stability timeout in seconds.
        """
        logger.info(f"Detected new file: {filepath.name}")
        self._safe_event("incoming", filepath.name)

        # Wait for file stability
        self._safe_event("waiting", filepath.name)
        self._safe_progress(0, 1, f"⏳ Warte auf {filepath.name}...")

        ready = self.monitor.wait_for_file_ready(filepath, timeout=timeout)
        if not ready:
            logger.warning(f"File not ready after {timeout}s timeout: {filepath}")
            self._safe_event("error", filepath.name, "Timeout: Datei nicht bereit")
            return

        # Check abort signal
        if self.state_manager.is_abort_requested():
            logger.info("Abort requested, skipping file processing")
            return

        # Verify file still exists
        if not filepath.exists():
            logger.warning(f"File no longer exists: {filepath}")
            return

        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(str(filepath))
        if mime_type is None:
            mime_type = "application/octet-stream"

        # Analyze with SmartSorter
        self._safe_event("analyzing", filepath.name)
        self._safe_progress(0, 1, f"🤖 Analysiere {filepath.name}...")

        try:
            result = await self.smart_sorter.process_file(filepath, mime_type)
        except Exception as e:
            logger.error(f"SmartSorter error for {filepath.name}: {e}")
            self._safe_event("error", filepath.name, str(e))
            return

        # Build target path
        target_dir = self._build_target_path(result, filepath)

        # Validate target_dir is in a safe location (prevent path traversal)
        if not is_safe_path(target_dir):
            error_msg = (
                f"Security violation: target directory escapes safe folders. "
                f"Target: {target_dir}. Allowed folders: Desktop, Downloads, Documents."
            )
            logger.error(error_msg)
            self._safe_event("error", filepath.name, error_msg)
            raise ValueError(error_msg)

        target_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        unique_name = self._file_ops.generate_unique_name(target_dir, filepath.name)
        target_path = target_dir / unique_name

        # Move file
        try:
            shutil.move(str(filepath), str(target_path))
            logger.info(f"Moved {filepath.name} -> {target_path}")
            self._safe_event("sorted", filepath.name)
            self._safe_progress(
                1, 1, f"✅ {filepath.name} → {result.get('category', 'Sortiert')}"
            )
        except Exception as e:
            logger.error(f"Failed to move {filepath.name}: {e}")
            self._safe_event("error", filepath.name, str(e))

    def _build_target_path(self, result: dict[str, Any], filepath: Path) -> Path:
        """Build target directory path from template and AI result.

        Supported placeholders:
        - {category}: Category from AI analysis (default: "Sonstiges")
        - {sender}: Sender from AI analysis (default: "Unbekannt")
        - {year}: Year from AI analysis or current year
        - {month}: Current month (01-12)
        - {filename}: Original filename (without extension)

        Args:
            result: SmartSorter result with category, sender, year.
            filepath: Original file path.

        Returns:
            Resolved target directory path.
        """
        now = datetime.now()

        # Extract values with defaults
        category = result.get("category") or "Sonstiges"
        sender = result.get("sender") or "Unbekannt"
        year = result.get("year") or str(now.year)
        month = f"{now.month:02d}"
        filename = filepath.stem

        # Sanitize values for filesystem
        category = self._sanitize_path_component(category)
        sender = self._sanitize_path_component(sender)
        year = self._sanitize_path_component(str(year))
        filename = self._sanitize_path_component(filename)

        # Build path from template
        path_str = self.folder_structure.format(
            category=category,
            sender=sender,
            year=year,
            month=month,
            filename=filename,
        )

        return self.base_path / path_str

    def _sanitize_path_component(self, value: str) -> str:
        """Sanitize a value for use in filesystem paths.

        Removes or replaces characters that are invalid in paths.

        Args:
            value: String to sanitize.

        Returns:
            Sanitized string safe for filesystem use.
        """
        # Replace path separators and other problematic chars
        sanitized = re.sub(r'[<>:"/\\|?*]', "_", value)
        # Remove leading/trailing whitespace and dots
        sanitized = sanitized.strip(". ")
        # Collapse multiple underscores
        sanitized = re.sub(r"_+", "_", sanitized)
        return sanitized or "Unbekannt"

    def _safe_progress(
        self,
        current: int,
        total: int,
        filename: str,
        error: Optional[str] = None,
    ) -> None:
        """Safely invoke progress callback."""
        # Also notify WebSocket callback with progress data
        self._safe_websocket(
            type="progress",
            data={"current": current, "total": total, "error": error},
            filename=filename,
        )

        if not self.progress_callback:
            return
        try:
            self.progress_callback(current, total, filename, error)
        except Exception as e:
            logger.warning(f"Progress callback raised exception: {e}")

    def _safe_event(
        self,
        status: str,
        filename: str,
        error: Optional[str] = None,
    ) -> None:
        """Safely invoke event callback."""
        # Also notify WebSocket callback with event data
        self._safe_websocket(
            type="status",
            data={"status": status, "error": error},
            filename=filename,
        )

        if not self.on_event_callback:
            return
        try:
            self.on_event_callback(status, filename, error)
        except Exception as e:
            logger.warning(f"Event callback raised exception: {e}")

    def _safe_websocket(
        self,
        type: str,
        data: dict[str, Any],
        filename: str,
    ) -> None:
        """Safely invoke WebSocket callback, suppressing any exceptions.

        Args:
            type: Message type (progress, status, etc.).
            data: Message payload data.
            filename: Name of file being processed.
        """
        if not self.websocket_callback:
            return

        message = {
            "type": type,
            "data": {**data, "filename": filename},
        }

        try:
            result = self.websocket_callback(message)
            # Handle async callbacks
            if asyncio.iscoroutine(result):
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(result)
                    else:
                        loop.run_until_complete(result)
                except RuntimeError:
                    asyncio.run(result)
        except Exception as e:
            logger.warning(f"WebSocket callback raised exception: {e}")
