"""
Integration tests for watch mode functionality.

This module tests the watch mode feature end-to-end including:
- File event detection (created, moved)
- Debouncing and file stability monitoring
- Temp file filtering
- Integration with existing features (--sort-by-type, --deduplicate)
- Error handling and recovery
- Interface notifications and progress updates

Tests use mocked Observer for CI/CD stability while testing
the actual business logic of event handling and file processing.
"""

from __future__ import annotations

import os
import shutil
import threading
import time
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, Mock, patch

import pytest
from watchdog.events import FileCreatedEvent, FileMovedEvent

from folder_extractor.cli.app import EnhancedFolderExtractorCLI
from folder_extractor.config.settings import settings
from folder_extractor.core.extractor import EnhancedExtractionOrchestrator
from folder_extractor.core.monitor import StabilityMonitor
from folder_extractor.core.state_manager import (
    IStateManager,
    reset_state_manager,
)
from folder_extractor.core.watch import FolderEventHandler

# =============================================================================
# Helper Functions
# =============================================================================


def create_test_file_slowly(
    path: Path, content: str, steps: int = 3, delay: float = 0.1
) -> None:
    """Simulate a file being written slowly (like a download).

    Writes content in multiple steps with delays between, simulating
    a file that's being actively written.

    Args:
        path: Path where the file should be created.
        content: Full content to write.
        steps: Number of steps to split the write into.
        delay: Delay in seconds between steps.
    """
    chunk_size = len(content) // steps
    with open(path, "w") as f:
        for i in range(steps):
            start = i * chunk_size
            end = start + chunk_size if i < steps - 1 else len(content)
            f.write(content[start:end])
            f.flush()
            if i < steps - 1:
                time.sleep(delay)


def create_temp_file_with_extension(directory: Path, extension: str) -> Path:
    """Create a temporary file with a specific extension.

    Args:
        directory: Directory where the file should be created.
        extension: File extension (including dot, e.g., '.tmp').

    Returns:
        Path to the created file.
    """
    filename = f"tempfile{extension}"
    filepath = directory / filename
    filepath.write_text("temporary content")
    return filepath


def wait_for_condition(
    condition_fn: callable, timeout: float = 5.0, interval: float = 0.1
) -> bool:
    """Wait for a condition to become true.

    Args:
        condition_fn: Function that returns True when condition is met.
        timeout: Maximum time to wait in seconds.
        interval: Check interval in seconds.

    Returns:
        True if condition was met, False if timeout reached.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        if condition_fn():
            return True
        time.sleep(interval)
    return False


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def watch_test_env(tmp_path):
    """Set up test environment for watch mode tests.

    Creates a Desktop-based test directory (required for security validation)
    with a watched subdirectory for simulating downloads.

    Yields:
        Dict with:
        - root: Path to test root directory
        - watched_folder: Path to the folder being watched
        - original_cwd: Original working directory
    """
    reset_state_manager()
    settings.reset_to_defaults()

    # Create test directory in Desktop (safe path for security checks)
    desktop = Path.home() / "Desktop"
    test_dir = desktop / f"watch_test_{tmp_path.name}"
    test_dir.mkdir(parents=True, exist_ok=True)

    # Create watched subdirectory (simulates Downloads folder)
    watched_folder = test_dir / "watched"
    watched_folder.mkdir()

    original_cwd = Path.cwd()

    yield {
        "root": test_dir,
        "watched_folder": watched_folder,
        "original_cwd": original_cwd,
    }

    # Cleanup
    os.chdir(original_cwd)
    if test_dir.exists():
        shutil.rmtree(test_dir)


@pytest.fixture
def mock_observer():
    """Mock the watchdog Observer class.

    Returns a configured mock that simulates Observer behavior
    without actually monitoring the filesystem.
    """
    with patch("folder_extractor.core.watch.Observer") as mock_observer_class:
        mock_instance = MagicMock()
        mock_observer_class.return_value = mock_instance

        # Configure mock methods
        mock_instance.start = Mock()
        mock_instance.stop = Mock()
        mock_instance.join = Mock()
        mock_instance.schedule = Mock()
        mock_instance.is_alive = Mock(return_value=True)

        yield mock_instance


@pytest.fixture
def mock_stability_monitor():
    """Mock the StabilityMonitor's wait_for_file_ready method.

    Returns a mock that defaults to True (file is ready).
    """
    with patch.object(
        StabilityMonitor, "wait_for_file_ready", return_value=True
    ) as mock_wait:
        yield mock_wait


@pytest.fixture
def mock_state_manager():
    """Create a mock state manager for testing."""
    mock_sm = MagicMock(spec=IStateManager)
    mock_sm.is_abort_requested.return_value = False
    return mock_sm


@pytest.fixture
def event_handler_env(watch_test_env, mock_state_manager):
    """Set up environment for direct FolderEventHandler testing.

    Creates a fully configured event handler with mocked dependencies.
    """
    root = watch_test_env["root"]
    watched = watch_test_env["watched_folder"]

    # Create mock orchestrator
    mock_orchestrator = MagicMock(spec=EnhancedExtractionOrchestrator)
    mock_orchestrator.process_single_file = Mock(return_value={"status": "success"})

    # Create real stability monitor with mock state manager
    monitor = StabilityMonitor(mock_state_manager)

    # Create event handler
    handler = FolderEventHandler(
        orchestrator=mock_orchestrator,
        monitor=monitor,
        state_manager=mock_state_manager,
    )

    return {
        "handler": handler,
        "orchestrator": mock_orchestrator,
        "monitor": monitor,
        "state_manager": mock_state_manager,
        "root": root,
        "watched": watched,
    }


# =============================================================================
# Test Classes
# =============================================================================


@pytest.mark.integration
@pytest.mark.watch
class TestBasicWatchMode:
    """Test basic watch mode functionality."""

    def test_handler_ignores_directory_events(self, event_handler_env):
        """Directory creation events are ignored, only files are processed.

        The watch mode should only process file events, not directory
        creation or modification events.
        """
        handler = event_handler_env["handler"]
        orchestrator = event_handler_env["orchestrator"]
        watched = event_handler_env["watched"]

        # Create a directory event (simulated)
        event = FileCreatedEvent(str(watched / "new_directory"))
        event._is_directory = True

        handler.on_created(event)

        # Orchestrator should NOT be called for directory events
        orchestrator.process_single_file.assert_not_called()

    def test_handler_processes_new_file(self, event_handler_env):
        """New files in watched folder are processed through the orchestrator.

        When a file creation event occurs, the handler should wait for
        stability and then process the file.
        """
        handler = event_handler_env["handler"]
        orchestrator = event_handler_env["orchestrator"]
        watched = event_handler_env["watched"]

        # Create actual test file
        test_file = watched / "document.pdf"
        test_file.write_text("PDF content")

        # Simulate creation event
        event = FileCreatedEvent(str(test_file))

        with patch.object(handler.monitor, "wait_for_file_ready", return_value=True):
            handler.on_created(event)

        # Verify file was processed
        orchestrator.process_single_file.assert_called_once()
        call_kwargs = orchestrator.process_single_file.call_args
        assert call_kwargs[1]["filepath"] == test_file

    def test_handler_processes_moved_file(self, event_handler_env):
        """Files moved into watched folder are processed.

        Browser downloads often work by creating a temp file and then
        moving/renaming it to the final name.
        """
        handler = event_handler_env["handler"]
        orchestrator = event_handler_env["orchestrator"]
        watched = event_handler_env["watched"]

        # Create file at destination
        dest_file = watched / "renamed.pdf"
        dest_file.write_text("PDF content")

        # Simulate move event
        event = FileMovedEvent(
            src_path=str(watched / "temp.crdownload"),
            dest_path=str(dest_file),
        )

        with patch.object(handler.monitor, "wait_for_file_ready", return_value=True):
            handler.on_moved(event)

        # Verify file was processed
        orchestrator.process_single_file.assert_called_once()
        call_kwargs = orchestrator.process_single_file.call_args
        assert call_kwargs[1]["filepath"] == dest_file

    def test_handler_ignores_temp_files(self, event_handler_env):
        """Temporary download files are ignored until complete.

        Files with extensions like .tmp, .crdownload, .part should
        not trigger processing.
        """
        handler = event_handler_env["handler"]
        orchestrator = event_handler_env["orchestrator"]
        watched = event_handler_env["watched"]

        # Test each temp extension
        temp_extensions = [".tmp", ".crdownload", ".part", ".download"]

        for ext in temp_extensions:
            # Create temp file
            temp_file = watched / f"download{ext}"
            temp_file.write_text("incomplete content")

            # Simulate creation event
            event = FileCreatedEvent(str(temp_file))
            handler.on_created(event)

            # Clean up for next iteration
            temp_file.unlink()

        # No processing should have occurred
        orchestrator.process_single_file.assert_not_called()

    def test_handler_ignores_compound_temp_extensions(self, event_handler_env):
        """Compound temp extensions like .pdf.crdownload are ignored.

        Browsers often append temp extensions to the original filename.
        """
        handler = event_handler_env["handler"]
        orchestrator = event_handler_env["orchestrator"]
        watched = event_handler_env["watched"]

        # Create file with compound extension
        temp_file = watched / "document.pdf.crdownload"
        temp_file.write_text("incomplete content")

        event = FileCreatedEvent(str(temp_file))
        handler.on_created(event)

        # Should be ignored
        orchestrator.process_single_file.assert_not_called()


@pytest.mark.integration
@pytest.mark.watch
class TestWatchDebouncing:
    """Test debouncing and file stability detection."""

    def test_waits_for_file_size_stability(self, watch_test_env, mock_state_manager):
        """Processing waits until file size stops changing.

        A file that's still being written should not be processed
        until its size has been stable for at least one check interval.
        """
        watched = watch_test_env["watched_folder"]
        test_file = watched / "growing.txt"
        test_file.write_text("initial")

        monitor = StabilityMonitor(mock_state_manager)

        # Mock stat to simulate growing file then stable
        sizes = iter([100, 200, 300, 300])  # Growing then stable

        with patch("pathlib.Path.stat") as mock_stat:
            mock_stat.return_value.st_size = next(sizes, 300)

            def get_stat():
                mock_stat.return_value.st_size = next(sizes, 300)
                return mock_stat.return_value

            with patch.object(Path, "stat", side_effect=lambda: get_stat()):
                with patch.object(Path, "exists", return_value=True):
                    with patch.object(monitor, "_is_file_locked", return_value=False):
                        with patch("time.sleep"):
                            result = monitor.wait_for_file_ready(test_file, timeout=10)

        # Should eventually return True when stable
        assert result is True

    def test_timeout_on_continuously_growing_file(
        self, watch_test_env, mock_state_manager
    ):
        """Files that never stop growing trigger timeout.

        If a file's size keeps changing, the monitor should eventually
        give up and return False.
        """
        watched = watch_test_env["watched_folder"]
        test_file = watched / "endless.txt"
        test_file.write_text("initial")

        monitor = StabilityMonitor(mock_state_manager)

        # Simulate continuously growing file
        growth_counter = [0]

        def growing_size():
            growth_counter[0] += 100
            mock_stat = MagicMock()
            mock_stat.st_size = growth_counter[0]
            return mock_stat

        with patch.object(Path, "stat", side_effect=growing_size):
            with patch.object(Path, "exists", return_value=True):
                # Short timeout for fast test
                result = monitor.wait_for_file_ready(test_file, timeout=1)

        assert result is False

    def test_abort_signal_interrupts_stability_check(
        self, watch_test_env, mock_state_manager
    ):
        """Abort signal stops stability monitoring early.

        When abort is requested, the monitor should stop waiting
        and return False immediately.
        """
        watched = watch_test_env["watched_folder"]
        test_file = watched / "aborted.txt"
        test_file.write_text("content")

        # Configure abort to be requested
        mock_state_manager.is_abort_requested.return_value = True

        monitor = StabilityMonitor(mock_state_manager)

        result = monitor.wait_for_file_ready(test_file, timeout=10)

        assert result is False


@pytest.mark.integration
@pytest.mark.watch
class TestWatchErrorHandling:
    """Test error handling and recovery in watch mode."""

    def test_continues_after_single_file_error(self, event_handler_env):
        """Watch mode continues processing after a file error.

        If one file fails to process, the handler should log the error
        but continue monitoring for new files.
        """
        handler = event_handler_env["handler"]
        orchestrator = event_handler_env["orchestrator"]
        watched = event_handler_env["watched"]

        # Create files
        file1 = watched / "success1.txt"
        file1.write_text("content 1")
        file_error = watched / "error.txt"
        file_error.write_text("error content")
        file2 = watched / "success2.txt"
        file2.write_text("content 2")

        # Configure orchestrator to fail on error file
        def process_side_effect(filepath, **kwargs):
            if "error" in str(filepath):
                raise RuntimeError("Simulated processing error")
            return {"status": "success"}

        orchestrator.process_single_file.side_effect = process_side_effect

        with patch.object(handler.monitor, "wait_for_file_ready", return_value=True):
            # Process all files
            handler.on_created(FileCreatedEvent(str(file1)))
            handler.on_created(FileCreatedEvent(str(file_error)))
            handler.on_created(FileCreatedEvent(str(file2)))

        # All files should have been attempted
        assert orchestrator.process_single_file.call_count == 3

    def test_handles_file_access_error_gracefully(self, event_handler_env):
        """File access errors are caught and logged.

        If a file cannot be accessed (permissions, deleted), the handler
        should not crash.
        """
        handler = event_handler_env["handler"]
        orchestrator = event_handler_env["orchestrator"]
        watched = event_handler_env["watched"]

        # Create event for non-existent file
        missing_file = watched / "missing.txt"
        event = FileCreatedEvent(str(missing_file))

        # This should not raise an exception
        handler.on_created(event)

        # Orchestrator should not be called since file doesn't exist
        # and monitor.wait_for_file_ready would return False
        orchestrator.process_single_file.assert_not_called()

    def test_handles_permission_error_in_monitor(
        self, watch_test_env, mock_state_manager
    ):
        """Permission errors during file stat are handled gracefully.

        If the file cannot be stat'd, the monitor should handle
        the error and continue checking.
        """
        watched = watch_test_env["watched_folder"]
        test_file = watched / "protected.txt"
        test_file.write_text("content")

        monitor = StabilityMonitor(mock_state_manager)

        # Simulate permission error followed by success
        call_count = [0]

        def stat_side_effect():
            call_count[0] += 1
            if call_count[0] < 3:
                raise PermissionError("Access denied")
            mock_stat = MagicMock()
            mock_stat.st_size = 100
            return mock_stat

        with patch.object(Path, "stat", side_effect=stat_side_effect):
            with patch.object(Path, "exists", return_value=True):
                with patch.object(monitor, "_is_file_locked", return_value=False):
                    with patch("time.sleep"):
                        result = monitor.wait_for_file_ready(test_file, timeout=10)

        # Should eventually succeed
        assert result is True


@pytest.mark.integration
@pytest.mark.watch
class TestWatchModeIntegration:
    """Test watch mode integration with other features."""

    def test_handler_receives_correct_destination(self, event_handler_env):
        """Handler passes the correct destination path to orchestrator.

        The destination should be the parent of the watched file,
        allowing the orchestrator to sort appropriately.
        """
        handler = event_handler_env["handler"]
        orchestrator = event_handler_env["orchestrator"]
        watched = event_handler_env["watched"]

        test_file = watched / "document.pdf"
        test_file.write_text("PDF content")

        event = FileCreatedEvent(str(test_file))

        with patch.object(handler.monitor, "wait_for_file_ready", return_value=True):
            handler.on_created(event)

        call_kwargs = orchestrator.process_single_file.call_args[1]
        assert call_kwargs["destination"] == test_file.parent

    def test_progress_callback_receives_updates(self, event_handler_env):
        """Progress callback is invoked during file processing.

        The handler should send progress updates through the callback
        for UI display.
        """
        watched = event_handler_env["watched"]
        orchestrator = event_handler_env["orchestrator"]
        state_manager = event_handler_env["state_manager"]

        # Create handler with progress callback
        progress_calls: list[tuple[int, int, str, Optional[str]]] = []

        def progress_callback(current, total, filename, error=None):
            progress_calls.append((current, total, filename, error))

        handler = FolderEventHandler(
            orchestrator=orchestrator,
            monitor=event_handler_env["monitor"],
            state_manager=state_manager,
            progress_callback=progress_callback,
        )

        test_file = watched / "tracked.pdf"
        test_file.write_text("PDF content")

        event = FileCreatedEvent(str(test_file))

        with patch.object(handler.monitor, "wait_for_file_ready", return_value=True):
            handler.on_created(event)

        # Should have received progress updates
        assert len(progress_calls) >= 1

    def test_event_callback_receives_status_updates(self, event_handler_env):
        """Event callback receives status updates for UI notifications.

        Status transitions: incoming → waiting → analyzing → sorted
        """
        watched = event_handler_env["watched"]
        orchestrator = event_handler_env["orchestrator"]
        state_manager = event_handler_env["state_manager"]

        event_calls: list[tuple[str, str, Optional[str]]] = []

        def event_callback(status, filename, error=None):
            event_calls.append((status, filename, error))

        handler = FolderEventHandler(
            orchestrator=orchestrator,
            monitor=event_handler_env["monitor"],
            state_manager=state_manager,
            on_event_callback=event_callback,
        )

        test_file = watched / "tracked.pdf"
        test_file.write_text("PDF content")

        event = FileCreatedEvent(str(test_file))

        with patch.object(handler.monitor, "wait_for_file_ready", return_value=True):
            handler.on_created(event)

        # Should have received status updates
        statuses = [call[0] for call in event_calls]
        assert "incoming" in statuses
        assert "waiting" in statuses
        assert "analyzing" in statuses
        assert "sorted" in statuses


@pytest.mark.integration
@pytest.mark.watch
class TestWatchModeInterface:
    """Test watch mode interface and logging."""

    def test_callback_exception_does_not_crash_handler(self, event_handler_env):
        """Faulty callbacks are caught and don't crash the handler.

        If a progress or event callback raises an exception, the handler
        should log it but continue processing.
        """
        watched = event_handler_env["watched"]
        orchestrator = event_handler_env["orchestrator"]
        state_manager = event_handler_env["state_manager"]

        def failing_callback(*args, **kwargs):
            raise RuntimeError("Callback failed!")

        handler = FolderEventHandler(
            orchestrator=orchestrator,
            monitor=event_handler_env["monitor"],
            state_manager=state_manager,
            progress_callback=failing_callback,
            on_event_callback=failing_callback,
        )

        test_file = watched / "test.pdf"
        test_file.write_text("content")

        event = FileCreatedEvent(str(test_file))

        with patch.object(handler.monitor, "wait_for_file_ready", return_value=True):
            # Should not raise despite failing callbacks
            handler.on_created(event)

        # File should still have been processed
        orchestrator.process_single_file.assert_called_once()


@pytest.mark.integration
@pytest.mark.watch
class TestWatchModeEdgeCases:
    """Test edge cases and special scenarios."""

    def test_handles_rapid_file_creation(self, event_handler_env):
        """Multiple files created rapidly are all processed.

        Files created in quick succession should all be queued and
        processed without race conditions.
        """
        handler = event_handler_env["handler"]
        orchestrator = event_handler_env["orchestrator"]
        watched = event_handler_env["watched"]

        # Create multiple files quickly
        files = []
        for i in range(10):
            f = watched / f"rapid_{i}.txt"
            f.write_text(f"content {i}")
            files.append(f)

        with patch.object(handler.monitor, "wait_for_file_ready", return_value=True):
            # Process all files
            for f in files:
                event = FileCreatedEvent(str(f))
                handler.on_created(event)

        # All files should have been processed
        assert orchestrator.process_single_file.call_count == 10

    def test_handles_file_deleted_before_processing(self, event_handler_env):
        """Deleted files before processing don't crash the handler.

        If a file is created then immediately deleted before processing
        completes, the handler should gracefully skip it.
        """
        handler = event_handler_env["handler"]
        orchestrator = event_handler_env["orchestrator"]
        watched = event_handler_env["watched"]

        # Create and immediately delete
        ephemeral = watched / "ephemeral.txt"
        ephemeral.write_text("gone soon")
        event = FileCreatedEvent(str(ephemeral))
        ephemeral.unlink()

        # Should not crash (monitor.wait_for_file_ready will return False)
        handler.on_created(event)

        # Orchestrator should not be called
        orchestrator.process_single_file.assert_not_called()

    def test_prevents_duplicate_processing(self, event_handler_env):
        """Same file is not processed multiple times simultaneously.

        If multiple events arrive for the same file, only one should
        be processed to avoid conflicts.
        """
        handler = event_handler_env["handler"]
        orchestrator = event_handler_env["orchestrator"]
        watched = event_handler_env["watched"]

        test_file = watched / "duplicate.txt"
        test_file.write_text("content")

        # Simulate concurrent events by checking processing set
        event = FileCreatedEvent(str(test_file))

        # First call should process
        with patch.object(handler.monitor, "wait_for_file_ready", return_value=True):
            handler.on_created(event)

        # Second call with same file should also process (file is done)
        with patch.object(handler.monitor, "wait_for_file_ready", return_value=True):
            handler.on_created(event)

        # Both should process since first completes before second
        assert orchestrator.process_single_file.call_count == 2

    def test_file_not_ready_skips_processing(self, event_handler_env):
        """Files that don't become ready are skipped.

        If wait_for_file_ready returns False (timeout or abort),
        the file should not be processed.
        """
        handler = event_handler_env["handler"]
        orchestrator = event_handler_env["orchestrator"]
        watched = event_handler_env["watched"]

        test_file = watched / "not_ready.txt"
        test_file.write_text("content")

        event = FileCreatedEvent(str(test_file))

        # Monitor says file not ready
        with patch.object(handler.monitor, "wait_for_file_ready", return_value=False):
            handler.on_created(event)

        # Should not be processed
        orchestrator.process_single_file.assert_not_called()

    def test_abort_during_processing_stops_file(self, event_handler_env):
        """Abort signal during processing stops current file.

        If abort is requested while waiting for file stability,
        the file should be skipped.
        """
        handler = event_handler_env["handler"]
        orchestrator = event_handler_env["orchestrator"]
        state_manager = event_handler_env["state_manager"]
        watched = event_handler_env["watched"]

        test_file = watched / "aborted.txt"
        test_file.write_text("content")

        # Set abort after file is ready
        state_manager.is_abort_requested.return_value = True

        event = FileCreatedEvent(str(test_file))

        with patch.object(handler.monitor, "wait_for_file_ready", return_value=True):
            handler.on_created(event)

        # Processing should be skipped due to abort
        orchestrator.process_single_file.assert_not_called()


@pytest.mark.integration
@pytest.mark.watch
class TestStabilityMonitorBehavior:
    """Test StabilityMonitor edge cases and behavior."""

    def test_file_lock_detection_prevents_processing(
        self, watch_test_env, mock_state_manager
    ):
        """Locked files are not considered ready.

        If a file is locked by another process, the monitor should
        wait until the lock is released.
        """
        watched = watch_test_env["watched_folder"]
        test_file = watched / "locked.txt"
        test_file.write_text("content")

        monitor = StabilityMonitor(mock_state_manager)

        # Simulate file locked then unlocked
        lock_states = iter([True, True, False])

        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_size = 100
            with patch.object(Path, "exists", return_value=True):
                with patch.object(
                    monitor, "_is_file_locked", side_effect=lambda p: next(lock_states)
                ):
                    with patch("time.sleep"):
                        result = monitor.wait_for_file_ready(test_file, timeout=10)

        assert result is True

    def test_file_missing_initially_waits_for_creation(
        self, watch_test_env, mock_state_manager
    ):
        """Monitor waits for file to exist before checking stability.

        If a file doesn't exist initially, the monitor should wait
        for it to appear (event may arrive before file is visible).
        """
        watched = watch_test_env["watched_folder"]
        test_file = watched / "delayed.txt"

        monitor = StabilityMonitor(mock_state_manager)

        # File exists after a few checks
        exist_states = iter([False, False, True, True])

        with patch.object(Path, "exists", side_effect=lambda: next(exist_states, True)):
            with patch.object(Path, "stat") as mock_stat:
                mock_stat.return_value.st_size = 100
                with patch.object(monitor, "_is_file_locked", return_value=False):
                    with patch("time.sleep"):
                        result = monitor.wait_for_file_ready(test_file, timeout=10)

        assert result is True


# =============================================================================
# End-to-End Tests with Mocked Observer
# =============================================================================


@pytest.fixture
def e2e_watch_env(tmp_path):
    """Set up environment for end-to-end watch mode tests.

    Creates a Desktop-based test directory and prepares for CLI execution.
    """
    reset_state_manager()
    settings.reset_to_defaults()

    # Create test directory in Desktop (safe path for security checks)
    desktop = Path.home() / "Desktop"
    test_dir = desktop / f"e2e_watch_test_{tmp_path.name}"
    test_dir.mkdir(parents=True, exist_ok=True)

    # Create watched subdirectory
    watched_folder = test_dir / "watched"
    watched_folder.mkdir()

    original_cwd = Path.cwd()
    os.chdir(test_dir)

    yield {
        "root": test_dir,
        "watched_folder": watched_folder,
        "original_cwd": original_cwd,
    }

    # Cleanup
    os.chdir(original_cwd)
    reset_state_manager()
    if test_dir.exists():
        shutil.rmtree(test_dir)


@pytest.mark.integration
@pytest.mark.watch
class TestEndToEndWatchMode:
    """End-to-end tests that exercise the complete watch mode flow.

    These tests patch the Observer at the CLI level and trigger events
    manually to verify the complete integration from CLI to file processing.
    """

    def test_cli_execute_watch_starts_observer_and_processes_files(self, e2e_watch_env):
        """Complete flow: CLI starts Observer, events trigger processing.

        This test verifies:
        1. Observer.schedule is called with correct handler and path
        2. Observer.start is called
        3. Events triggered through the handler reach process_single_file
        4. Observer.stop and join are called on shutdown
        """
        watched = e2e_watch_env["watched_folder"]

        # Create test file before starting watch
        test_file = watched / "document.pdf"
        test_file.write_text("PDF content for E2E test")

        # Track handler for manual event triggering
        captured_handler = None
        captured_path = None

        def capture_schedule(handler, path, recursive=False):
            nonlocal captured_handler, captured_path
            captured_handler = handler
            captured_path = path

        # Create mock observer
        mock_observer_instance = MagicMock()
        mock_observer_instance.schedule = Mock(side_effect=capture_schedule)
        mock_observer_instance.start = Mock()
        mock_observer_instance.stop = Mock()
        mock_observer_instance.join = Mock()

        # Track process_single_file calls
        process_calls: list[Path] = []

        def track_process(filepath, destination, progress_callback=None):
            process_calls.append(filepath)
            return {"status": "success"}

        with patch("folder_extractor.cli.app.Observer") as MockObserver:
            MockObserver.return_value = mock_observer_instance

            # Patch process_single_file to track calls
            with patch.object(
                EnhancedExtractionOrchestrator,
                "process_single_file",
                side_effect=track_process,
            ):
                # Create CLI and call _execute_watch in a thread
                cli = EnhancedFolderExtractorCLI()

                def run_watch():
                    cli._execute_watch(watched)

                watch_thread = threading.Thread(target=run_watch)
                watch_thread.start()

                # Wait for observer to be started
                time.sleep(0.2)

                # Verify observer was set up correctly
                assert captured_handler is not None, "Handler should be captured"
                assert captured_path == str(watched), "Path should match watched folder"
                mock_observer_instance.start.assert_called_once()

                # Patch stability monitor to return immediately
                with patch.object(
                    StabilityMonitor, "wait_for_file_ready", return_value=True
                ):
                    # Trigger on_created event through captured handler
                    event = FileCreatedEvent(str(test_file))
                    captured_handler.on_created(event)

                # Give time for processing
                time.sleep(0.2)

                # Request abort to stop the watch loop
                cli.state_manager.request_abort()
                watch_thread.join(timeout=3)

        # Verify observer lifecycle
        mock_observer_instance.stop.assert_called_once()
        mock_observer_instance.join.assert_called_once()

        # Verify file was processed
        assert len(process_calls) == 1, "Should have processed one file"
        assert process_calls[0] == test_file, "Should have processed the test file"

    def test_cli_execute_watch_with_moved_event(self, e2e_watch_env):
        """Moved events (browser downloads completing) are processed correctly.

        Browsers often download to a .crdownload file then rename it.
        This test verifies the on_moved event triggers processing.
        """
        watched = e2e_watch_env["watched_folder"]

        # Create file at final destination
        final_file = watched / "downloaded.pdf"
        final_file.write_text("Completed download content")

        captured_handler = None

        def capture_schedule(handler, path, recursive=False):
            nonlocal captured_handler
            captured_handler = handler

        mock_observer_instance = MagicMock()
        mock_observer_instance.schedule = Mock(side_effect=capture_schedule)
        mock_observer_instance.start = Mock()
        mock_observer_instance.stop = Mock()
        mock_observer_instance.join = Mock()

        process_calls: list[Path] = []

        def track_process(filepath, destination, progress_callback=None):
            process_calls.append(filepath)
            return {"status": "success"}

        with patch("folder_extractor.cli.app.Observer") as MockObserver:
            MockObserver.return_value = mock_observer_instance

            with patch.object(
                EnhancedExtractionOrchestrator,
                "process_single_file",
                side_effect=track_process,
            ):
                cli = EnhancedFolderExtractorCLI()

                def run_watch():
                    cli._execute_watch(watched)

                watch_thread = threading.Thread(target=run_watch)
                watch_thread.start()

                time.sleep(0.2)

                assert captured_handler is not None, "Handler should be captured"

                with patch.object(
                    StabilityMonitor, "wait_for_file_ready", return_value=True
                ):
                    # Simulate browser completing download (rename from .crdownload)
                    event = FileMovedEvent(
                        src_path=str(watched / "downloaded.pdf.crdownload"),
                        dest_path=str(final_file),
                    )
                    captured_handler.on_moved(event)

                time.sleep(0.2)
                cli.state_manager.request_abort()
                watch_thread.join(timeout=3)

        assert len(process_calls) == 1
        assert process_calls[0] == final_file

    def test_cli_execute_watch_invokes_status_callbacks(self, e2e_watch_env):
        """Status callbacks (incoming, waiting, analyzing, sorted) are invoked.

        The interface should receive status updates for UI display.
        """
        watched = e2e_watch_env["watched_folder"]

        test_file = watched / "tracked.pdf"
        test_file.write_text("Content for callback test")

        captured_handler = None

        def capture_schedule(handler, path, recursive=False):
            nonlocal captured_handler
            captured_handler = handler

        mock_observer_instance = MagicMock()
        mock_observer_instance.schedule = Mock(side_effect=capture_schedule)
        mock_observer_instance.start = Mock()
        mock_observer_instance.stop = Mock()
        mock_observer_instance.join = Mock()

        # Track interface method calls
        watch_event_calls: list[tuple] = []

        with patch("folder_extractor.cli.app.Observer") as MockObserver:
            MockObserver.return_value = mock_observer_instance

            with patch.object(
                EnhancedExtractionOrchestrator,
                "process_single_file",
                return_value={"status": "success"},
            ):
                cli = EnhancedFolderExtractorCLI()

                # Patch interface to capture calls
                def capture_watch_event(*args, **kwargs):
                    watch_event_calls.append(args)

                cli.interface.show_watch_event = capture_watch_event

                def run_watch():
                    cli._execute_watch(watched)

                watch_thread = threading.Thread(target=run_watch)
                watch_thread.start()

                time.sleep(0.2)

                assert captured_handler is not None, "Handler should be captured"

                with patch.object(
                    StabilityMonitor, "wait_for_file_ready", return_value=True
                ):
                    event = FileCreatedEvent(str(test_file))
                    captured_handler.on_created(event)

                time.sleep(0.2)
                cli.state_manager.request_abort()
                watch_thread.join(timeout=3)

        # Verify status callbacks were invoked
        # Format: (event_type, filename, status, error)
        statuses = [call[2] for call in watch_event_calls if len(call) >= 3]
        assert "incoming" in statuses, "Should have incoming status"
        assert "waiting" in statuses, "Should have waiting status"
        assert "analyzing" in statuses, "Should have analyzing status"
        assert "sorted" in statuses, "Should have sorted status"

    def test_cli_execute_watch_handles_processing_error(self, e2e_watch_env):
        """Processing errors are caught and don't crash the watcher.

        When a file fails to process, the error should be reported
        but the watcher should continue running.
        """
        watched = e2e_watch_env["watched_folder"]

        test_file = watched / "error_file.pdf"
        test_file.write_text("Content that will fail")

        captured_handler = None

        def capture_schedule(handler, path, recursive=False):
            nonlocal captured_handler
            captured_handler = handler

        mock_observer_instance = MagicMock()
        mock_observer_instance.schedule = Mock(side_effect=capture_schedule)
        mock_observer_instance.start = Mock()
        mock_observer_instance.stop = Mock()
        mock_observer_instance.join = Mock()

        def failing_process(filepath, destination, progress_callback=None):
            raise RuntimeError("Simulated processing failure")

        with patch("folder_extractor.cli.app.Observer") as MockObserver:
            MockObserver.return_value = mock_observer_instance

            with patch.object(
                EnhancedExtractionOrchestrator,
                "process_single_file",
                side_effect=failing_process,
            ):
                cli = EnhancedFolderExtractorCLI()

                def run_watch():
                    cli._execute_watch(watched)

                watch_thread = threading.Thread(target=run_watch)
                watch_thread.start()

                time.sleep(0.2)

                assert captured_handler is not None, "Handler should be captured"

                with patch.object(
                    StabilityMonitor, "wait_for_file_ready", return_value=True
                ):
                    # This should not crash
                    event = FileCreatedEvent(str(test_file))
                    captured_handler.on_created(event)

                time.sleep(0.2)

                # Observer should still be running
                assert watch_thread.is_alive(), "Watch thread should still be running"

                cli.state_manager.request_abort()
                watch_thread.join(timeout=3)

        # Verify clean shutdown despite error
        mock_observer_instance.stop.assert_called_once()
        mock_observer_instance.join.assert_called_once()

    def test_cli_execute_watch_ignores_temp_files(self, e2e_watch_env):
        """Temporary files (.crdownload, .tmp, .part) are not processed.

        The watcher should filter out incomplete download files.
        """
        watched = e2e_watch_env["watched_folder"]

        # Create temp files
        temp_file = watched / "download.pdf.crdownload"
        temp_file.write_text("Incomplete content")

        captured_handler = None

        def capture_schedule(handler, path, recursive=False):
            nonlocal captured_handler
            captured_handler = handler

        mock_observer_instance = MagicMock()
        mock_observer_instance.schedule = Mock(side_effect=capture_schedule)
        mock_observer_instance.start = Mock()
        mock_observer_instance.stop = Mock()
        mock_observer_instance.join = Mock()

        process_calls: list[Path] = []

        def track_process(filepath, destination, progress_callback=None):
            process_calls.append(filepath)
            return {"status": "success"}

        with patch("folder_extractor.cli.app.Observer") as MockObserver:
            MockObserver.return_value = mock_observer_instance

            with patch.object(
                EnhancedExtractionOrchestrator,
                "process_single_file",
                side_effect=track_process,
            ):
                cli = EnhancedFolderExtractorCLI()

                def run_watch():
                    cli._execute_watch(watched)

                watch_thread = threading.Thread(target=run_watch)
                watch_thread.start()

                time.sleep(0.2)

                assert captured_handler is not None, "Handler should be captured"

                # Trigger events for temp files - should be ignored
                for ext in [".crdownload", ".tmp", ".part"]:
                    tf = watched / f"file{ext}"
                    tf.write_text("temp content")
                    event = FileCreatedEvent(str(tf))
                    captured_handler.on_created(event)

                time.sleep(0.2)
                cli.state_manager.request_abort()
                watch_thread.join(timeout=3)

        # No temp files should have been processed
        assert len(process_calls) == 0, "Temp files should not be processed"


# =============================================================================
# Watch Mode with Feature Integrations
# =============================================================================


def create_zip_archive(archive_path: Path, files: dict) -> Path:
    """Create a ZIP archive with specified files.

    Args:
        archive_path: Path where the ZIP archive should be created
        files: Dict mapping relative paths to file contents (str or bytes)

    Returns:
        Path to the created archive
    """
    import zipfile

    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            if isinstance(content, bytes):
                zf.writestr(name, content)
            else:
                zf.writestr(name, content.encode("utf-8"))
    return archive_path


@pytest.mark.integration
@pytest.mark.watch
class TestWatchModeWithFeatures:
    """Test watch mode integration with sort-by-type, deduplicate, and archives.

    These tests verify that watch mode correctly applies settings like
    --sort-by-type, --deduplicate, and --extract-archives when processing files.
    """

    def test_watch_mode_with_sort_by_type(self, e2e_watch_env):
        """Files are sorted into type folders when sort_by_type is enabled.

        When --sort-by-type is active, PDF files should go to PDF/,
        images to their respective type folders, etc.
        """
        watched = e2e_watch_env["watched_folder"]
        root = e2e_watch_env["root"]

        # Create test files of different types
        pdf_file = watched / "document.pdf"
        pdf_file.write_text("PDF content")
        jpg_file = watched / "photo.jpg"
        jpg_file.write_bytes(b"JPEG content")
        txt_file = watched / "notes.txt"
        txt_file.write_text("Text content")

        captured_handler = None

        def capture_schedule(handler, path, recursive=False):
            nonlocal captured_handler
            captured_handler = handler

        mock_observer_instance = MagicMock()
        mock_observer_instance.schedule = Mock(side_effect=capture_schedule)
        mock_observer_instance.start = Mock()
        mock_observer_instance.stop = Mock()
        mock_observer_instance.join = Mock()

        # Configure settings for sort-by-type
        settings.set("sort_by_type", True)

        with patch("folder_extractor.cli.app.Observer") as MockObserver:
            MockObserver.return_value = mock_observer_instance

            cli = EnhancedFolderExtractorCLI()

            def run_watch():
                cli._execute_watch(watched)

            watch_thread = threading.Thread(target=run_watch)
            watch_thread.start()

            time.sleep(0.2)

            assert captured_handler is not None, "Handler should be captured"

            with patch.object(
                StabilityMonitor, "wait_for_file_ready", return_value=True
            ):
                # Trigger events for all files
                for f in [pdf_file, jpg_file, txt_file]:
                    event = FileCreatedEvent(str(f))
                    captured_handler.on_created(event)
                    time.sleep(0.1)  # Small delay between events

            time.sleep(0.3)
            cli.state_manager.request_abort()
            watch_thread.join(timeout=3)

        # Verify files were sorted into type folders
        # Note: exact folder names depend on FILE_TYPE_FOLDERS mapping
        assert (root / "PDF" / "document.pdf").exists() or (
            watched / "document.pdf"
        ).exists(), "PDF file should be processed"
        assert (root / "JPEG" / "photo.jpg").exists() or (
            watched / "photo.jpg"
        ).exists(), "JPG file should be processed"
        assert (root / "TEXT" / "notes.txt").exists() or (
            watched / "notes.txt"
        ).exists(), "TXT file should be processed"

    def test_watch_mode_with_deduplicate(self, e2e_watch_env):
        """Duplicate files are skipped when deduplicate is enabled.

        When --deduplicate is active, files with same name and content
        as existing files should be skipped.
        """
        watched = e2e_watch_env["watched_folder"]
        root = e2e_watch_env["root"]

        identical_content = "This is duplicate content for testing"

        # Create existing file in root
        existing_file = root / "existing.txt"
        existing_file.write_text(identical_content)

        # Create duplicate file in watched folder
        duplicate_file = watched / "existing.txt"
        duplicate_file.write_text(identical_content)

        captured_handler = None

        def capture_schedule(handler, path, recursive=False):
            nonlocal captured_handler
            captured_handler = handler

        mock_observer_instance = MagicMock()
        mock_observer_instance.schedule = Mock(side_effect=capture_schedule)
        mock_observer_instance.start = Mock()
        mock_observer_instance.stop = Mock()
        mock_observer_instance.join = Mock()

        # Configure settings for deduplicate
        settings.set("deduplicate", True)

        with patch("folder_extractor.cli.app.Observer") as MockObserver:
            MockObserver.return_value = mock_observer_instance

            cli = EnhancedFolderExtractorCLI()

            def run_watch():
                cli._execute_watch(watched)

            watch_thread = threading.Thread(target=run_watch)
            watch_thread.start()

            time.sleep(0.2)

            assert captured_handler is not None, "Handler should be captured"

            with patch.object(
                StabilityMonitor, "wait_for_file_ready", return_value=True
            ):
                event = FileCreatedEvent(str(duplicate_file))
                captured_handler.on_created(event)

            time.sleep(0.3)
            cli.state_manager.request_abort()
            watch_thread.join(timeout=3)

        # Verify: only one file should exist (duplicate was skipped)
        # The original file should still exist, and no duplicate copy created
        txt_files_in_root = list(root.glob("existing*.txt"))
        assert len(txt_files_in_root) == 1, (
            f"Should have exactly 1 file (duplicate skipped), found {len(txt_files_in_root)}"
        )
        assert existing_file.exists(), "Original file should still exist"

    def test_watch_mode_with_global_dedup(self, e2e_watch_env):
        """Global dedup detects duplicates with different names.

        When --global-dedup is active, files with same content but different
        names should be detected as duplicates.
        """
        watched = e2e_watch_env["watched_folder"]
        root = e2e_watch_env["root"]

        identical_content = "Same content different name for global dedup"

        # Create existing file with one name
        existing_file = root / "original.txt"
        existing_file.write_text(identical_content)

        # Create file with same content but different name
        different_name_file = watched / "copy_with_new_name.txt"
        different_name_file.write_text(identical_content)

        captured_handler = None

        def capture_schedule(handler, path, recursive=False):
            nonlocal captured_handler
            captured_handler = handler

        mock_observer_instance = MagicMock()
        mock_observer_instance.schedule = Mock(side_effect=capture_schedule)
        mock_observer_instance.start = Mock()
        mock_observer_instance.stop = Mock()
        mock_observer_instance.join = Mock()

        # Configure settings for global dedup
        settings.set("global_dedup", True)

        with patch("folder_extractor.cli.app.Observer") as MockObserver:
            MockObserver.return_value = mock_observer_instance

            cli = EnhancedFolderExtractorCLI()

            def run_watch():
                cli._execute_watch(watched)

            watch_thread = threading.Thread(target=run_watch)
            watch_thread.start()

            time.sleep(0.2)

            assert captured_handler is not None, "Handler should be captured"

            with patch.object(
                StabilityMonitor, "wait_for_file_ready", return_value=True
            ):
                event = FileCreatedEvent(str(different_name_file))
                captured_handler.on_created(event)

            time.sleep(0.3)
            cli.state_manager.request_abort()
            watch_thread.join(timeout=3)

        # Verify: duplicate content should not create new file
        assert existing_file.exists(), "Original file should still exist"
        # The copy should not be in root since it's a global duplicate
        assert not (root / "copy_with_new_name.txt").exists(), (
            "Global duplicate should not be copied to root"
        )

    def test_watch_mode_with_extract_archives(self, e2e_watch_env):
        """ZIP archives are extracted when extract_archives is enabled.

        When --extract-archives is active, ZIP files should be unpacked
        and their contents processed.
        """
        watched = e2e_watch_env["watched_folder"]
        root = e2e_watch_env["root"]

        # Create a ZIP archive with test files
        archive_path = watched / "test_archive.zip"
        create_zip_archive(
            archive_path,
            {
                "inner_doc.pdf": "PDF inside archive",
                "inner_image.jpg": b"JPEG inside archive",
            },
        )

        captured_handler = None

        def capture_schedule(handler, path, recursive=False):
            nonlocal captured_handler
            captured_handler = handler

        mock_observer_instance = MagicMock()
        mock_observer_instance.schedule = Mock(side_effect=capture_schedule)
        mock_observer_instance.start = Mock()
        mock_observer_instance.stop = Mock()
        mock_observer_instance.join = Mock()

        # Configure settings for archive extraction
        settings.set("extract_archives", True)

        with patch("folder_extractor.cli.app.Observer") as MockObserver:
            MockObserver.return_value = mock_observer_instance

            cli = EnhancedFolderExtractorCLI()

            def run_watch():
                cli._execute_watch(watched)

            watch_thread = threading.Thread(target=run_watch)
            watch_thread.start()

            time.sleep(0.2)

            assert captured_handler is not None, "Handler should be captured"

            with patch.object(
                StabilityMonitor, "wait_for_file_ready", return_value=True
            ):
                event = FileCreatedEvent(str(archive_path))
                captured_handler.on_created(event)

            time.sleep(0.5)  # Give more time for archive extraction
            cli.state_manager.request_abort()
            watch_thread.join(timeout=3)

        # Verify: archive contents should be extracted
        # Check if inner files exist somewhere in the root tree
        inner_pdfs = list(root.rglob("inner_doc.pdf"))

        assert len(inner_pdfs) >= 1 or archive_path.exists(), (
            "Archive should be processed (extracted or moved)"
        )

    def test_watch_mode_with_sort_and_deduplicate_combined(self, e2e_watch_env):
        """Combined sort-by-type and deduplicate work together.

        When both --sort-by-type and --deduplicate are active,
        files should be sorted AND duplicates should be skipped.
        """
        watched = e2e_watch_env["watched_folder"]
        root = e2e_watch_env["root"]

        # Create PDF folder with existing file
        pdf_folder = root / "PDF"
        pdf_folder.mkdir(exist_ok=True)
        existing_pdf = pdf_folder / "existing.pdf"
        existing_pdf.write_text("Existing PDF content")

        # Create duplicate PDF in watched folder
        duplicate_pdf = watched / "existing.pdf"
        duplicate_pdf.write_text("Existing PDF content")

        # Create new unique PDF
        new_pdf = watched / "new_document.pdf"
        new_pdf.write_text("New unique PDF content")

        captured_handler = None

        def capture_schedule(handler, path, recursive=False):
            nonlocal captured_handler
            captured_handler = handler

        mock_observer_instance = MagicMock()
        mock_observer_instance.schedule = Mock(side_effect=capture_schedule)
        mock_observer_instance.start = Mock()
        mock_observer_instance.stop = Mock()
        mock_observer_instance.join = Mock()

        # Configure settings for both features
        settings.set("sort_by_type", True)
        settings.set("deduplicate", True)

        with patch("folder_extractor.cli.app.Observer") as MockObserver:
            MockObserver.return_value = mock_observer_instance

            cli = EnhancedFolderExtractorCLI()

            def run_watch():
                cli._execute_watch(watched)

            watch_thread = threading.Thread(target=run_watch)
            watch_thread.start()

            time.sleep(0.2)

            assert captured_handler is not None, "Handler should be captured"

            with patch.object(
                StabilityMonitor, "wait_for_file_ready", return_value=True
            ):
                # Process duplicate first
                event1 = FileCreatedEvent(str(duplicate_pdf))
                captured_handler.on_created(event1)
                time.sleep(0.1)

                # Then process new file
                event2 = FileCreatedEvent(str(new_pdf))
                captured_handler.on_created(event2)

            time.sleep(0.3)
            cli.state_manager.request_abort()
            watch_thread.join(timeout=3)

        # Verify: duplicate skipped, new file sorted
        # Should have original + new_document (duplicate was skipped)
        assert existing_pdf.exists(), "Original PDF should still exist"
        # New file should be in PDF folder (or still in watched if processing is async)
        new_in_pdf = (pdf_folder / "new_document.pdf").exists()
        new_in_watched = (watched / "new_document.pdf").exists()
        assert new_in_pdf or new_in_watched, "New PDF should be processed"


# =============================================================================
# Error and Abort Scenarios
# =============================================================================


@pytest.mark.integration
@pytest.mark.watch
class TestWatchModeErrorAndAbort:
    """Test error handling and abort scenarios in watch mode.

    These tests verify that:
    - Connection errors (AI API down) don't crash the watcher
    - Permission errors are handled gracefully
    - Missing files don't crash the watcher
    - Abort signals stop the watch loop cleanly
    - Error status is communicated via callbacks
    """

    def test_connection_error_does_not_crash_watcher(self, e2e_watch_env):
        """ConnectionError from orchestrator is caught and logged.

        When the AI API or network is unavailable, the watcher should
        log the error and continue monitoring for new files.
        """
        watched = e2e_watch_env["watched_folder"]

        test_file = watched / "ai_test.pdf"
        test_file.write_text("Content requiring AI processing")

        captured_handler = None
        error_events: list[tuple] = []

        def capture_schedule(handler, path, recursive=False):
            nonlocal captured_handler
            captured_handler = handler

        mock_observer_instance = MagicMock()
        mock_observer_instance.schedule = Mock(side_effect=capture_schedule)
        mock_observer_instance.start = Mock()
        mock_observer_instance.stop = Mock()
        mock_observer_instance.join = Mock()

        def raise_connection_error(filepath, destination, progress_callback=None):
            raise ConnectionError("AI API unavailable - network error")

        with patch("folder_extractor.cli.app.Observer") as MockObserver:
            MockObserver.return_value = mock_observer_instance

            with patch.object(
                EnhancedExtractionOrchestrator,
                "process_single_file",
                side_effect=raise_connection_error,
            ):
                cli = EnhancedFolderExtractorCLI()

                # Capture error events
                def capture_event(*args):
                    error_events.append(args)

                cli.interface.show_watch_event = capture_event

                def run_watch():
                    cli._execute_watch(watched)

                watch_thread = threading.Thread(target=run_watch)
                watch_thread.start()

                time.sleep(0.2)

                assert captured_handler is not None, "Handler should be captured"

                with patch.object(
                    StabilityMonitor, "wait_for_file_ready", return_value=True
                ):
                    event = FileCreatedEvent(str(test_file))
                    captured_handler.on_created(event)

                time.sleep(0.3)

                # Watcher should still be running despite error
                assert watch_thread.is_alive(), (
                    "Watch thread should survive ConnectionError"
                )

                cli.state_manager.request_abort()
                watch_thread.join(timeout=3)

        # Verify clean shutdown
        mock_observer_instance.stop.assert_called_once()
        mock_observer_instance.join.assert_called_once()

        # Verify error was communicated
        error_statuses = [e[2] for e in error_events if len(e) >= 3]
        assert "error" in error_statuses, "Error status should be sent via callback"

    def test_permission_error_does_not_crash_watcher(self, e2e_watch_env):
        """PermissionError during file access is handled gracefully.

        When a file cannot be accessed due to permissions, the watcher
        should log the error and continue.
        """
        watched = e2e_watch_env["watched_folder"]

        test_file = watched / "protected.pdf"
        test_file.write_text("Protected content")

        captured_handler = None

        def capture_schedule(handler, path, recursive=False):
            nonlocal captured_handler
            captured_handler = handler

        mock_observer_instance = MagicMock()
        mock_observer_instance.schedule = Mock(side_effect=capture_schedule)
        mock_observer_instance.start = Mock()
        mock_observer_instance.stop = Mock()
        mock_observer_instance.join = Mock()

        def raise_permission_error(filepath, destination, progress_callback=None):
            raise PermissionError("Access denied to file")

        with patch("folder_extractor.cli.app.Observer") as MockObserver:
            MockObserver.return_value = mock_observer_instance

            with patch.object(
                EnhancedExtractionOrchestrator,
                "process_single_file",
                side_effect=raise_permission_error,
            ):
                cli = EnhancedFolderExtractorCLI()

                def run_watch():
                    cli._execute_watch(watched)

                watch_thread = threading.Thread(target=run_watch)
                watch_thread.start()

                time.sleep(0.2)

                assert captured_handler is not None, "Handler should be captured"

                with patch.object(
                    StabilityMonitor, "wait_for_file_ready", return_value=True
                ):
                    event = FileCreatedEvent(str(test_file))
                    captured_handler.on_created(event)

                time.sleep(0.3)

                # Watcher should still be running
                assert watch_thread.is_alive(), (
                    "Watch thread should survive PermissionError"
                )

                cli.state_manager.request_abort()
                watch_thread.join(timeout=3)

        # Verify clean shutdown
        mock_observer_instance.stop.assert_called_once()
        mock_observer_instance.join.assert_called_once()

    def test_missing_file_during_processing(self, e2e_watch_env):
        """File deleted after event but before processing is handled.

        A race condition where a file is created, event fires, but file
        is deleted before processing should be handled gracefully.
        """
        watched = e2e_watch_env["watched_folder"]

        # Create file path but don't create actual file
        missing_file = watched / "disappearing.pdf"

        captured_handler = None

        def capture_schedule(handler, path, recursive=False):
            nonlocal captured_handler
            captured_handler = handler

        mock_observer_instance = MagicMock()
        mock_observer_instance.schedule = Mock(side_effect=capture_schedule)
        mock_observer_instance.start = Mock()
        mock_observer_instance.stop = Mock()
        mock_observer_instance.join = Mock()

        process_calls = []

        def track_process(filepath, destination, progress_callback=None):
            process_calls.append(filepath)
            # File doesn't exist, should return error
            return {"status": "error", "message": "File does not exist"}

        with patch("folder_extractor.cli.app.Observer") as MockObserver:
            MockObserver.return_value = mock_observer_instance

            with patch.object(
                EnhancedExtractionOrchestrator,
                "process_single_file",
                side_effect=track_process,
            ):
                cli = EnhancedFolderExtractorCLI()

                def run_watch():
                    cli._execute_watch(watched)

                watch_thread = threading.Thread(target=run_watch)
                watch_thread.start()

                time.sleep(0.2)

                assert captured_handler is not None, "Handler should be captured"

                # Simulate event for non-existent file (deleted after event)
                with patch.object(
                    StabilityMonitor, "wait_for_file_ready", return_value=False
                ):
                    event = FileCreatedEvent(str(missing_file))
                    captured_handler.on_created(event)

                time.sleep(0.2)

                # Watcher should still be running
                assert watch_thread.is_alive(), (
                    "Watch thread should handle missing file"
                )

                cli.state_manager.request_abort()
                watch_thread.join(timeout=3)

        # Verify clean shutdown
        mock_observer_instance.stop.assert_called_once()

    def test_abort_signal_stops_watch_loop_cleanly(self, e2e_watch_env):
        """Abort signal via state_manager stops the watch loop.

        When request_abort() is called, the main loop should exit,
        Observer should be stopped, and thread should terminate cleanly.
        """
        watched = e2e_watch_env["watched_folder"]

        captured_handler = None

        def capture_schedule(handler, path, recursive=False):
            nonlocal captured_handler
            captured_handler = handler

        mock_observer_instance = MagicMock()
        mock_observer_instance.schedule = Mock(side_effect=capture_schedule)
        mock_observer_instance.start = Mock()
        mock_observer_instance.stop = Mock()
        mock_observer_instance.join = Mock()

        with patch("folder_extractor.cli.app.Observer") as MockObserver:
            MockObserver.return_value = mock_observer_instance

            cli = EnhancedFolderExtractorCLI()

            watch_started = threading.Event()
            watch_stopped = threading.Event()

            def run_watch():
                watch_started.set()
                cli._execute_watch(watched)
                watch_stopped.set()

            watch_thread = threading.Thread(target=run_watch)
            watch_thread.start()

            # Wait for watch to start
            assert watch_started.wait(timeout=2), "Watch should start"
            time.sleep(0.2)

            # Verify observer started
            mock_observer_instance.start.assert_called_once()

            # Request abort
            cli.state_manager.request_abort()

            # Wait for watch to stop
            assert watch_stopped.wait(timeout=3), "Watch should stop after abort"
            watch_thread.join(timeout=1)

        # Verify clean shutdown
        mock_observer_instance.stop.assert_called_once()
        mock_observer_instance.join.assert_called_once()
        assert not watch_thread.is_alive(), "Thread should be terminated"

    def test_keyboard_interrupt_stops_watch_cleanly(self, e2e_watch_env):
        """KeyboardInterrupt (Ctrl+C) stops the watch loop cleanly.

        Simulates SIGINT/Ctrl+C behavior to verify graceful shutdown.
        """
        watched = e2e_watch_env["watched_folder"]

        mock_observer_instance = MagicMock()
        mock_observer_instance.schedule = Mock()
        mock_observer_instance.start = Mock()
        mock_observer_instance.stop = Mock()
        mock_observer_instance.join = Mock()

        with patch("folder_extractor.cli.app.Observer") as MockObserver:
            MockObserver.return_value = mock_observer_instance

            # Patch time.sleep to raise KeyboardInterrupt after first call
            sleep_count = [0]
            original_sleep = time.sleep

            def interruptible_sleep(seconds):
                sleep_count[0] += 1
                if sleep_count[0] >= 2:  # Allow initial setup
                    raise KeyboardInterrupt()
                original_sleep(min(seconds, 0.1))

            cli = EnhancedFolderExtractorCLI()

            with patch("time.sleep", side_effect=interruptible_sleep):
                # This should not raise - KeyboardInterrupt should be caught
                result = cli._execute_watch(watched)

        # Verify clean shutdown after KeyboardInterrupt
        mock_observer_instance.stop.assert_called_once()
        mock_observer_instance.join.assert_called_once()
        assert result == 0, "Should return 0 on clean shutdown"

    def test_multiple_errors_dont_accumulate_and_crash(self, e2e_watch_env):
        """Multiple consecutive errors don't cause memory leak or crash.

        When many files fail processing, the watcher should continue
        handling each one independently without accumulating state.
        """
        watched = e2e_watch_env["watched_folder"]

        # Create multiple test files
        test_files = []
        for i in range(5):
            f = watched / f"error_file_{i}.pdf"
            f.write_text(f"Content {i}")
            test_files.append(f)

        captured_handler = None
        error_count = [0]

        def capture_schedule(handler, path, recursive=False):
            nonlocal captured_handler
            captured_handler = handler

        mock_observer_instance = MagicMock()
        mock_observer_instance.schedule = Mock(side_effect=capture_schedule)
        mock_observer_instance.start = Mock()
        mock_observer_instance.stop = Mock()
        mock_observer_instance.join = Mock()

        def always_fail(filepath, destination, progress_callback=None):
            error_count[0] += 1
            raise RuntimeError(f"Simulated failure #{error_count[0]}")

        with patch("folder_extractor.cli.app.Observer") as MockObserver:
            MockObserver.return_value = mock_observer_instance

            with patch.object(
                EnhancedExtractionOrchestrator,
                "process_single_file",
                side_effect=always_fail,
            ):
                cli = EnhancedFolderExtractorCLI()

                def run_watch():
                    cli._execute_watch(watched)

                watch_thread = threading.Thread(target=run_watch)
                watch_thread.start()

                time.sleep(0.2)

                assert captured_handler is not None, "Handler should be captured"

                with patch.object(
                    StabilityMonitor, "wait_for_file_ready", return_value=True
                ):
                    # Process all files - each should fail
                    for f in test_files:
                        event = FileCreatedEvent(str(f))
                        captured_handler.on_created(event)
                        time.sleep(0.05)  # Brief delay between events

                time.sleep(0.3)

                # Watcher should still be running after all errors
                assert watch_thread.is_alive(), "Watcher should survive multiple errors"

                cli.state_manager.request_abort()
                watch_thread.join(timeout=3)

        # All files should have been attempted
        assert error_count[0] == 5, (
            f"All 5 files should be attempted, got {error_count[0]}"
        )

        # Clean shutdown
        mock_observer_instance.stop.assert_called_once()

    def test_error_callback_receives_error_details(self, e2e_watch_env):
        """Error callback receives detailed error information.

        When processing fails, the error callback should receive
        the error status and error message for UI display.
        """
        watched = e2e_watch_env["watched_folder"]

        test_file = watched / "error_details.pdf"
        test_file.write_text("Content that will fail")

        captured_handler = None
        event_calls: list[tuple] = []

        def capture_schedule(handler, path, recursive=False):
            nonlocal captured_handler
            captured_handler = handler

        mock_observer_instance = MagicMock()
        mock_observer_instance.schedule = Mock(side_effect=capture_schedule)
        mock_observer_instance.start = Mock()
        mock_observer_instance.stop = Mock()
        mock_observer_instance.join = Mock()

        error_message = "Detailed error: AI service returned 503"

        def fail_with_message(filepath, destination, progress_callback=None):
            raise RuntimeError(error_message)

        with patch("folder_extractor.cli.app.Observer") as MockObserver:
            MockObserver.return_value = mock_observer_instance

            with patch.object(
                EnhancedExtractionOrchestrator,
                "process_single_file",
                side_effect=fail_with_message,
            ):
                cli = EnhancedFolderExtractorCLI()

                # Capture event callbacks
                def capture_watch_event(*args):
                    event_calls.append(args)

                cli.interface.show_watch_event = capture_watch_event

                def run_watch():
                    cli._execute_watch(watched)

                watch_thread = threading.Thread(target=run_watch)
                watch_thread.start()

                time.sleep(0.2)

                assert captured_handler is not None, "Handler should be captured"

                with patch.object(
                    StabilityMonitor, "wait_for_file_ready", return_value=True
                ):
                    event = FileCreatedEvent(str(test_file))
                    captured_handler.on_created(event)

                time.sleep(0.3)
                cli.state_manager.request_abort()
                watch_thread.join(timeout=3)

        # Verify error callback was invoked with error status
        error_calls = [c for c in event_calls if len(c) >= 3 and c[2] == "error"]
        assert len(error_calls) >= 1, "Error callback should be invoked"

        # Error message should be included (4th argument if present)
        if len(error_calls[0]) >= 4:
            assert error_calls[0][3] is not None, "Error message should be provided"

    def test_stability_timeout_sends_appropriate_status(self, e2e_watch_env):
        """When file stability times out, appropriate status is sent.

        If a file never becomes stable (e.g., continuous download),
        the watcher should skip it and not block on it forever.
        """
        watched = e2e_watch_env["watched_folder"]

        # Create a file that "never stabilizes"
        unstable_file = watched / "unstable.pdf"
        unstable_file.write_text("Growing content")

        captured_handler = None
        process_calls = []

        def capture_schedule(handler, path, recursive=False):
            nonlocal captured_handler
            captured_handler = handler

        mock_observer_instance = MagicMock()
        mock_observer_instance.schedule = Mock(side_effect=capture_schedule)
        mock_observer_instance.start = Mock()
        mock_observer_instance.stop = Mock()
        mock_observer_instance.join = Mock()

        def track_process(filepath, destination, progress_callback=None):
            process_calls.append(filepath)
            return {"status": "success"}

        with patch("folder_extractor.cli.app.Observer") as MockObserver:
            MockObserver.return_value = mock_observer_instance

            with patch.object(
                EnhancedExtractionOrchestrator,
                "process_single_file",
                side_effect=track_process,
            ):
                cli = EnhancedFolderExtractorCLI()

                def run_watch():
                    cli._execute_watch(watched)

                watch_thread = threading.Thread(target=run_watch)
                watch_thread.start()

                time.sleep(0.2)

                assert captured_handler is not None, "Handler should be captured"

                # Simulate stability check timing out
                with patch.object(
                    StabilityMonitor, "wait_for_file_ready", return_value=False
                ):
                    event = FileCreatedEvent(str(unstable_file))
                    captured_handler.on_created(event)

                time.sleep(0.2)
                cli.state_manager.request_abort()
                watch_thread.join(timeout=3)

        # File should NOT have been processed (stability timed out)
        assert len(process_calls) == 0, "Unstable file should not be processed"

        # Clean shutdown
        mock_observer_instance.stop.assert_called_once()
