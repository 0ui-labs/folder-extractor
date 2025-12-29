"""File stability monitoring for watch mode with smart debouncing.

This module provides the StabilityMonitor class which determines when files
are fully written and ready for processing. It checks file size stability
and lock status to avoid processing incomplete downloads or files still
being written by other applications.
"""

import logging
import time
from pathlib import Path
from typing import Union

from folder_extractor.core.state_manager import IStateManager

logger = logging.getLogger(__name__)


class StabilityMonitor:
    """Monitor files to determine when they are ready for processing.

    Uses file size stability and lock detection to ensure files are
    fully written before processing. Integrates with StateManager
    for graceful abort handling.

    Attributes:
        state_manager: State manager for abort signal checking.
    """

    def __init__(self, state_manager: IStateManager) -> None:
        """Initialize the stability monitor.

        Args:
            state_manager: State manager instance for abort signal handling.
        """
        self.state_manager = state_manager

    def wait_for_file_ready(
        self, filepath: Union[str, Path], timeout: int = 60
    ) -> bool:
        """Wait until file is fully written and ready for processing.

        Monitors file size stability and lock status. Returns True when
        the file size has been stable for at least one check interval
        and the file is not locked by another process.

        Args:
            filepath: Path to the file to monitor.
            timeout: Maximum time to wait in seconds. Defaults to 60.

        Returns:
            True if file is ready for processing.
            False if timeout reached, abort requested, or file doesn't exist.
        """
        filepath = Path(filepath)
        start_time = time.time()
        last_size = -1

        while time.time() - start_time < timeout:
            # Check for abort signal
            if self.state_manager.is_abort_requested():
                logger.debug(f"Abort requested while waiting for {filepath}")
                return False

            # Check if file exists
            if not filepath.exists():
                time.sleep(1)
                continue

            # Get current file size
            try:
                current_size = filepath.stat().st_size
            except OSError as e:
                logger.warning(f"Could not stat file {filepath}: {e}")
                time.sleep(1)
                continue

            # Check if size is stable and file is not locked
            if current_size == last_size and not self._is_file_locked(filepath):
                logger.debug(f"File ready: {filepath}")
                return True

            last_size = current_size
            time.sleep(1)

        logger.warning(f"Timeout waiting for {filepath} to be ready")
        return False

    def _is_file_locked(self, filepath: Path) -> bool:
        """Check if file is locked by another process.

        Attempts to open the file in append-binary mode. If successful,
        the file is not locked. Permission or OS errors indicate the
        file may be locked or in use.

        Args:
            filepath: Path to the file to check.

        Returns:
            True if file appears to be locked.
            False if file is accessible.
        """
        try:
            with open(filepath, "ab"):
                pass
            return False
        except (PermissionError, OSError):
            return True
        except Exception as e:
            logger.warning(f"Unexpected error checking lock for {filepath}: {e}")
            return False  # Fail-safe: assume not locked to avoid blocking
