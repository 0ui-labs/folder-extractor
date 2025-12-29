"""File system event handler for watch mode with smart debouncing and robust error handling.

This module provides the FolderEventHandler class which handles file system events
from watchdog. It filters temporary files, waits for file stability, and triggers
extraction via the orchestrator. Errors are caught and logged to prevent the
watcher from crashing.
"""

import logging
from pathlib import Path
from typing import Callable, Optional

from watchdog.events import FileSystemEvent, FileSystemEventHandler

from folder_extractor.config.constants import TEMP_EXTENSIONS
from folder_extractor.core.extractor import EnhancedExtractionOrchestrator
from folder_extractor.core.monitor import StabilityMonitor
from folder_extractor.core.state_manager import IStateManager

logger = logging.getLogger(__name__)

# Type alias for progress callback: (current, total, filename, error) -> None
ProgressCallback = Optional[Callable[[int, int, str, Optional[str]], None]]


class FolderEventHandler(FileSystemEventHandler):
    """Handle file system events for watch mode.

    Processes file creation and move events, filtering temporary files and
    waiting for file stability before triggering extraction. Integrates with
    StabilityMonitor for debouncing and StateManager for abort handling.

    Attributes:
        orchestrator: Extraction orchestrator for processing files.
        monitor: Stability monitor for file readiness detection.
        state_manager: State manager for abort signal handling.
        progress_callback: Optional callback for progress updates.
    """

    def __init__(
        self,
        orchestrator: EnhancedExtractionOrchestrator,
        monitor: StabilityMonitor,
        state_manager: IStateManager,
        progress_callback: ProgressCallback = None,
    ) -> None:
        """Initialize folder event handler for watch mode.

        Args:
            orchestrator: Extraction orchestrator instance.
            monitor: Stability monitor instance.
            state_manager: State manager instance.
            progress_callback: Optional callback for progress updates.
                Signature: (current, total, filename, error) -> None
        """
        super().__init__()
        self.orchestrator = orchestrator
        self.monitor = monitor
        self.state_manager = state_manager
        self.progress_callback = progress_callback
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
        if not self.progress_callback:
            return

        try:
            self.progress_callback(current, total, filename, error)
        except Exception as e:
            logger.warning(
                f"Progress callback raised exception: {e}",
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
        if filename.endswith(".crdownload"):
            return True
        if filename.endswith(".part"):
            return True
        if filename.endswith(".tmp"):
            return True

        return False

    def _process_file(self, filepath: Path) -> None:
        """Process a new file: wait for stability, then extract.

        Args:
            filepath: Path to the file to process.

        Note:
            All errors are caught and logged to prevent watcher crash.
        """
        try:
            # Check if this is a temp file
            if self._is_temp_file(filepath):
                logger.debug(f"Ignoring temp file: {filepath}")
                return

            # Prevent duplicate processing
            if str(filepath) in self._processing_files:
                logger.debug(f"Already processing: {filepath}")
                return

            # Track this file as being processed
            self._processing_files.add(str(filepath))

            try:
                logger.info(f"Detected new file: {filepath.name}")

                # Notify progress: waiting
                self._safe_progress(
                    0, 1, f"\u23f3 Warte auf {filepath.name}..."
                )

                # Wait for file to be ready
                ready = self.monitor.wait_for_file_ready(filepath, timeout=60)
                if not ready:
                    logger.warning(f"File not ready after timeout: {filepath}")
                    return

                # Check for abort signal
                if self.state_manager.is_abort_requested():
                    logger.info("Abort requested, skipping file processing")
                    return

                # Notify progress: analyzing
                self._safe_progress(
                    0, 1, f"\U0001f916 Analysiere {filepath.name}..."
                )

                # Execute extraction
                results = self.orchestrator.execute_extraction(
                    filepath.parent,
                    progress_callback=self.progress_callback,
                )

                # Check results
                if results.get("status") == "success":
                    logger.info(f"Successfully processed: {filepath.name}")
                    self._safe_progress(
                        1, 1, f"\u2705 {filepath.name} sortiert"
                    )
                else:
                    logger.error(f"Failed to process: {filepath.name}")

            finally:
                # Always clean up processing set
                self._processing_files.discard(str(filepath))

        except Exception as e:
            logger.error(f"Error processing {filepath}: {e}", exc_info=True)
            self._safe_progress(1, 1, filepath.name, str(e))
