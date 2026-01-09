"""Unit tests for folder event handler with temp file filtering and error recovery.

Tests verify the behavior of FolderEventHandler which handles file system events
for watch mode. The handler filters temp files, waits for file stability, and
triggers extraction via the orchestrator.
"""

import logging
from pathlib import Path
from unittest.mock import Mock

import pytest
from watchdog.events import DirCreatedEvent, FileCreatedEvent, FileMovedEvent

from folder_extractor.core.extractor import EnhancedExtractionOrchestrator
from folder_extractor.core.monitor import StabilityMonitor
from folder_extractor.core.state_manager import StateManager
from folder_extractor.core.watch import FolderEventHandler


class TestFolderEventHandler:
    """Tests for FolderEventHandler class."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.state_manager = StateManager()
        self.monitor = Mock(spec=StabilityMonitor)
        self.orchestrator = Mock(spec=EnhancedExtractionOrchestrator)
        self.progress_callback = Mock()
        self.handler = FolderEventHandler(
            self.orchestrator,
            self.monitor,
            self.state_manager,
            progress_callback=self.progress_callback,
        )

    def test_initialization_stores_dependencies(self) -> None:
        """Handler stores all dependencies for later use."""
        assert self.handler.orchestrator is self.orchestrator
        assert self.handler.monitor is self.monitor
        assert self.handler.state_manager is self.state_manager
        assert self.handler.progress_callback is self.progress_callback

    def test_initialization_creates_empty_processing_set(self) -> None:
        """Handler initializes with empty set to track files being processed."""
        # Access via public interface by checking no duplicates are blocked
        # when processing for the first time
        assert hasattr(self.handler, "_processing_files")
        assert len(self.handler._processing_files) == 0

    def test_on_created_processes_file_successfully(self, tmp_path: Path) -> None:
        """File creation event triggers stability check and extraction."""
        # Arrange
        test_file = tmp_path / "document.pdf"
        test_file.write_text("test content")
        event = FileCreatedEvent(str(test_file))

        self.monitor.wait_for_file_ready.return_value = True
        self.orchestrator.process_single_file.return_value = {"status": "success"}

        # Act
        self.handler.on_created(event)

        # Assert
        self.monitor.wait_for_file_ready.assert_called_once()
        self.orchestrator.process_single_file.assert_called_once()
        # Progress callback called for: waiting, analyzing, success
        assert self.progress_callback.call_count == 3

    def test_on_created_ignores_directories(self, tmp_path: Path) -> None:
        """Directory creation events are silently ignored."""
        # Arrange
        test_dir = tmp_path / "subdir"
        test_dir.mkdir()
        event = DirCreatedEvent(str(test_dir))

        # Act
        self.handler.on_created(event)

        # Assert
        self.monitor.wait_for_file_ready.assert_not_called()
        self.orchestrator.process_single_file.assert_not_called()

    def test_on_moved_processes_destination_file(self, tmp_path: Path) -> None:
        """File move event processes the destination file (browser download complete)."""
        # Arrange
        src_file = tmp_path / "document.crdownload"
        dest_file = tmp_path / "document.pdf"
        dest_file.write_text("completed download")
        event = FileMovedEvent(str(src_file), str(dest_file))

        self.monitor.wait_for_file_ready.return_value = True
        self.orchestrator.process_single_file.return_value = {"status": "success"}

        # Act
        self.handler.on_moved(event)

        # Assert
        # Verify destination path is used, not source
        call_args = self.monitor.wait_for_file_ready.call_args
        assert Path(call_args[0][0]) == dest_file
        self.orchestrator.process_single_file.assert_called_once()

    def test_temp_file_with_tmp_extension_is_ignored(self, tmp_path: Path) -> None:
        """Files with .tmp extension are filtered out."""
        # Arrange
        test_file = tmp_path / "download.tmp"
        test_file.write_text("temporary")
        event = FileCreatedEvent(str(test_file))

        # Act
        self.handler.on_created(event)

        # Assert
        self.monitor.wait_for_file_ready.assert_not_called()

    def test_temp_file_with_crdownload_extension_is_ignored(
        self, tmp_path: Path
    ) -> None:
        """Chrome download files (.crdownload) are filtered out."""
        # Arrange
        test_file = tmp_path / "file.pdf.crdownload"
        test_file.write_text("incomplete")
        event = FileCreatedEvent(str(test_file))

        # Act
        self.handler.on_created(event)

        # Assert
        self.monitor.wait_for_file_ready.assert_not_called()

    def test_temp_file_with_part_extension_is_ignored(self, tmp_path: Path) -> None:
        """Firefox partial download files (.part) are filtered out."""
        # Arrange
        test_file = tmp_path / "document.pdf.part"
        test_file.write_text("partial")
        event = FileCreatedEvent(str(test_file))

        # Act
        self.handler.on_created(event)

        # Assert
        self.monitor.wait_for_file_ready.assert_not_called()

    def test_temp_file_with_lock_extension_is_ignored(self, tmp_path: Path) -> None:
        """Lock files (.lock) are filtered out."""
        # Arrange
        test_file = tmp_path / "resource.lock"
        test_file.write_text("locked")
        event = FileCreatedEvent(str(test_file))

        # Act
        self.handler.on_created(event)

        # Assert
        self.monitor.wait_for_file_ready.assert_not_called()

    def test_file_not_ready_after_timeout_is_skipped(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Files that don't become ready within timeout are skipped with warning."""
        # Arrange
        test_file = tmp_path / "large_file.pdf"
        test_file.write_text("content")
        event = FileCreatedEvent(str(test_file))

        self.monitor.wait_for_file_ready.return_value = False  # Timeout

        # Act
        with caplog.at_level(logging.WARNING):
            self.handler.on_created(event)

        # Assert
        self.orchestrator.process_single_file.assert_not_called()
        assert "not ready" in caplog.text.lower() or "File not ready" in caplog.text

    def test_abort_signal_stops_processing(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Abort signal prevents extraction from running."""
        # Arrange
        test_file = tmp_path / "document.pdf"
        test_file.write_text("content")
        event = FileCreatedEvent(str(test_file))

        self.monitor.wait_for_file_ready.return_value = True
        self.state_manager.request_abort()

        # Act
        with caplog.at_level(logging.INFO):
            self.handler.on_created(event)

        # Assert
        self.orchestrator.process_single_file.assert_not_called()
        assert "abort" in caplog.text.lower()

    def test_processing_error_does_not_crash_handler(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Errors during processing are caught and logged, handler continues."""
        # Arrange
        test_file = tmp_path / "document.pdf"
        test_file.write_text("content")
        event = FileCreatedEvent(str(test_file))

        self.monitor.wait_for_file_ready.return_value = True
        self.orchestrator.process_single_file.side_effect = RuntimeError("Test error")

        # Act - should not raise
        with caplog.at_level(logging.ERROR):
            self.handler.on_created(event)

        # Assert
        assert "error" in caplog.text.lower()
        # Progress callback notified of error
        error_calls = [
            call for call in self.progress_callback.call_args_list if call[0][3]
        ]
        assert len(error_calls) >= 1

    def test_duplicate_file_processing_is_prevented(self, tmp_path: Path) -> None:
        """Same file is not processed multiple times simultaneously."""
        # Arrange
        test_file = tmp_path / "document.pdf"
        test_file.write_text("content")
        event = FileCreatedEvent(str(test_file))

        # Simulate file being in processing
        self.handler._processing_files.add(str(test_file))

        # Act
        self.handler.on_created(event)

        # Assert - nothing should happen because file is already being processed
        self.monitor.wait_for_file_ready.assert_not_called()

    def test_processing_set_cleanup_after_success(self, tmp_path: Path) -> None:
        """Processing set is cleaned up after successful processing."""
        # Arrange
        test_file = tmp_path / "document.pdf"
        test_file.write_text("content")
        event = FileCreatedEvent(str(test_file))

        self.monitor.wait_for_file_ready.return_value = True
        self.orchestrator.process_single_file.return_value = {"status": "success"}

        # Act
        self.handler.on_created(event)

        # Assert
        assert str(test_file) not in self.handler._processing_files

    def test_processing_set_cleanup_after_error(self, tmp_path: Path) -> None:
        """Processing set is cleaned up even after processing error."""
        # Arrange
        test_file = tmp_path / "document.pdf"
        test_file.write_text("content")
        event = FileCreatedEvent(str(test_file))

        self.monitor.wait_for_file_ready.side_effect = RuntimeError("Monitor error")

        # Act
        self.handler.on_created(event)

        # Assert - file should be removed from processing set despite error
        assert str(test_file) not in self.handler._processing_files

    def test_extraction_failure_is_logged(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Extraction failure status is logged as error."""
        # Arrange
        test_file = tmp_path / "document.pdf"
        test_file.write_text("content")
        event = FileCreatedEvent(str(test_file))

        self.monitor.wait_for_file_ready.return_value = True
        self.orchestrator.process_single_file.return_value = {
            "status": "error",
            "message": "Test error",
        }

        # Act
        with caplog.at_level(logging.ERROR):
            self.handler.on_created(event)

        # Assert
        assert "failed" in caplog.text.lower()

    def test_multiple_files_processed_sequentially(self, tmp_path: Path) -> None:
        """Multiple file events are processed independently."""
        # Arrange
        files = [tmp_path / f"doc{i}.pdf" for i in range(3)]
        for f in files:
            f.write_text(f"content of {f.name}")

        self.monitor.wait_for_file_ready.return_value = True
        self.orchestrator.process_single_file.return_value = {"status": "success"}

        # Act
        for f in files:
            event = FileCreatedEvent(str(f))
            self.handler.on_created(event)

        # Assert
        assert self.orchestrator.process_single_file.call_count == 3

    def test_handler_without_progress_callback(self, tmp_path: Path) -> None:
        """Handler works correctly when no progress callback is provided."""
        # Arrange
        handler = FolderEventHandler(
            self.orchestrator,
            self.monitor,
            self.state_manager,
            progress_callback=None,
        )
        test_file = tmp_path / "document.pdf"
        test_file.write_text("content")
        event = FileCreatedEvent(str(test_file))

        self.monitor.wait_for_file_ready.return_value = True
        self.orchestrator.process_single_file.return_value = {"status": "success"}

        # Act - should not raise
        handler.on_created(event)

        # Assert
        self.orchestrator.process_single_file.assert_called_once()

    def test_faulty_progress_callback_does_not_crash_handler(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Progress callback exceptions are caught and logged, handler continues."""
        # Arrange
        faulty_callback = Mock(side_effect=RuntimeError("Callback exploded"))
        handler = FolderEventHandler(
            self.orchestrator,
            self.monitor,
            self.state_manager,
            progress_callback=faulty_callback,
        )
        test_file = tmp_path / "document.pdf"
        test_file.write_text("content")
        event = FileCreatedEvent(str(test_file))

        self.monitor.wait_for_file_ready.return_value = True
        self.orchestrator.process_single_file.return_value = {"status": "success"}

        # Act - should not raise despite faulty callback
        with caplog.at_level(logging.WARNING):
            handler.on_created(event)

        # Assert - extraction still completed
        self.orchestrator.process_single_file.assert_called_once()
        # Callback exception was logged as warning
        assert "callback" in caplog.text.lower()
        assert "exception" in caplog.text.lower()

    def test_watch_mode_uses_base_path_as_destination(self, tmp_path: Path) -> None:
        """File in watch root should use base_path as destination, not filepath.parent.

        REGRESSION TEST for bug: watch-mode-no-move
        This test verifies that watch mode uses self.base_path instead of computing
        filepath.parent, which is critical when filepath is in a subdirectory.
        """
        # Arrange - create a scenario where base_path != filepath.parent
        watch_root = tmp_path / "watch_root"
        watch_root.mkdir()

        # File is in a subdirectory, so filepath.parent != watch_root
        subdir = watch_root / "incoming"
        subdir.mkdir()
        test_file = subdir / "document.pdf"
        test_file.write_text("test content")

        # Create handler with base_path set to watch_root
        handler = FolderEventHandler(
            orchestrator=self.orchestrator,
            monitor=self.monitor,
            state_manager=self.state_manager,
            base_path=watch_root,  # ✅ Key: base_path is watch_root
            progress_callback=self.progress_callback,
        )

        event = FileCreatedEvent(str(test_file))

        self.monitor.wait_for_file_ready.return_value = True
        self.orchestrator.process_single_file.return_value = {"status": "success"}

        # Act
        handler.on_created(event)

        # Assert
        # CRITICAL: Verify destination is base_path, NOT filepath.parent
        call_args = self.orchestrator.process_single_file.call_args
        assert call_args is not None

        # Get the destination argument (can be positional or keyword)
        if "destination" in call_args.kwargs:
            destination = call_args.kwargs["destination"]
        else:
            destination = call_args[0][1]  # Second positional argument

        # ✅ PASS after fix: destination should be watch_root (base_path)
        # ❌ FAIL before fix: destination is subdir (filepath.parent)
        assert destination == watch_root, (
            f"Expected destination to be base_path ({watch_root}), "
            f"but got {destination}. filepath.parent would be {test_file.parent}"
        )

        # Verify process_single_file was called (file not skipped)
        self.orchestrator.process_single_file.assert_called_once()

    def test_watch_mode_fallback_when_base_path_none(self, tmp_path: Path) -> None:
        """Handler should fall back to filepath.parent if base_path is None.

        This test ensures backward compatibility when base_path is not configured.
        """
        # Arrange
        test_file = tmp_path / "document.pdf"
        test_file.write_text("test content")

        # Create handler WITHOUT base_path
        handler = FolderEventHandler(
            orchestrator=self.orchestrator,
            monitor=self.monitor,
            state_manager=self.state_manager,
            base_path=None,  # ✅ Key: base_path is None
            progress_callback=self.progress_callback,
        )

        event = FileCreatedEvent(str(test_file))

        self.monitor.wait_for_file_ready.return_value = True
        self.orchestrator.process_single_file.return_value = {"status": "success"}

        # Act
        handler.on_created(event)

        # Assert
        call_args = self.orchestrator.process_single_file.call_args
        assert call_args is not None

        # Get destination argument
        if "destination" in call_args.kwargs:
            destination = call_args.kwargs["destination"]
        else:
            destination = call_args[0][1]

        # ✅ Fallback to filepath.parent for backward compatibility
        assert destination == test_file.parent, (
            f"Expected fallback to filepath.parent ({test_file.parent}), "
            f"but got {destination}"
        )

        # Verify process_single_file was still called
        self.orchestrator.process_single_file.assert_called_once()


class TestTempFileFiltering:
    """Dedicated tests for temp file filtering logic."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.handler = FolderEventHandler(
            orchestrator=Mock(spec=EnhancedExtractionOrchestrator),
            monitor=Mock(spec=StabilityMonitor),
            state_manager=StateManager(),
            progress_callback=None,
        )

    @pytest.mark.parametrize(
        "filename,expected",
        [
            # Temp extensions from TEMP_EXTENSIONS
            ("file.tmp", True),
            ("file.temp", True),
            ("file.part", True),
            ("file.partial", True),
            ("file.crdownload", True),
            ("file.download", True),
            ("file.downloading", True),
            ("file.lock", True),
            ("file.lck", True),
            # Normal files
            ("document.pdf", False),
            ("image.jpg", False),
            ("archive.zip", False),
            ("readme.txt", False),
            # Case insensitivity
            ("file.TMP", True),
            ("file.CRDOWNLOAD", True),
            # Compound extensions (browser downloads)
            ("document.pdf.crdownload", True),
            ("image.jpg.part", True),
            ("file.tar.gz.tmp", True),
        ],
    )
    def test_is_temp_file(self, filename: str, expected: bool) -> None:
        """Verify temp file detection for various file patterns."""
        filepath = Path(f"/test/{filename}")
        result = self.handler._is_temp_file(filepath)
        assert result == expected, f"Expected {expected} for {filename}"


class TestOnEventCallback:
    """Tests for on_event_callback parameter in FolderEventHandler."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.state_manager = StateManager()
        self.monitor = Mock(spec=StabilityMonitor)
        self.orchestrator = Mock(spec=EnhancedExtractionOrchestrator)
        self.event_callback = Mock()

    def test_on_event_callback_parameter_accepted(self) -> None:
        """Handler accepts optional on_event_callback parameter."""
        handler = FolderEventHandler(
            self.orchestrator,
            self.monitor,
            self.state_manager,
            progress_callback=None,
            on_event_callback=self.event_callback,
        )
        assert handler.on_event_callback is self.event_callback

    def test_on_event_callback_defaults_to_none(self) -> None:
        """Handler works without on_event_callback (backward compatibility)."""
        handler = FolderEventHandler(
            self.orchestrator,
            self.monitor,
            self.state_manager,
            progress_callback=None,
        )
        assert handler.on_event_callback is None

    def test_callback_called_with_incoming_status(self, tmp_path: Path) -> None:
        """Callback is invoked with 'incoming' status when file event detected."""
        handler = FolderEventHandler(
            self.orchestrator,
            self.monitor,
            self.state_manager,
            progress_callback=None,
            on_event_callback=self.event_callback,
        )
        test_file = tmp_path / "document.pdf"
        test_file.write_text("content")
        event = FileCreatedEvent(str(test_file))

        self.monitor.wait_for_file_ready.return_value = True
        self.orchestrator.process_single_file.return_value = {"status": "success"}

        handler.on_created(event)

        # Find the 'incoming' call
        incoming_calls = [
            call
            for call in self.event_callback.call_args_list
            if call[0][0] == "incoming"
        ]
        assert len(incoming_calls) == 1
        assert incoming_calls[0][0][1] == "document.pdf"

    def test_callback_called_with_waiting_status(self, tmp_path: Path) -> None:
        """Callback is invoked with 'waiting' status during stability check."""
        handler = FolderEventHandler(
            self.orchestrator,
            self.monitor,
            self.state_manager,
            progress_callback=None,
            on_event_callback=self.event_callback,
        )
        test_file = tmp_path / "document.pdf"
        test_file.write_text("content")
        event = FileCreatedEvent(str(test_file))

        self.monitor.wait_for_file_ready.return_value = True
        self.orchestrator.process_single_file.return_value = {"status": "success"}

        handler.on_created(event)

        waiting_calls = [
            call
            for call in self.event_callback.call_args_list
            if call[0][0] == "waiting"
        ]
        assert len(waiting_calls) == 1
        assert waiting_calls[0][0][1] == "document.pdf"

    def test_callback_called_with_analyzing_status(self, tmp_path: Path) -> None:
        """Callback is invoked with 'analyzing' status before extraction."""
        handler = FolderEventHandler(
            self.orchestrator,
            self.monitor,
            self.state_manager,
            progress_callback=None,
            on_event_callback=self.event_callback,
        )
        test_file = tmp_path / "document.pdf"
        test_file.write_text("content")
        event = FileCreatedEvent(str(test_file))

        self.monitor.wait_for_file_ready.return_value = True
        self.orchestrator.process_single_file.return_value = {"status": "success"}

        handler.on_created(event)

        analyzing_calls = [
            call
            for call in self.event_callback.call_args_list
            if call[0][0] == "analyzing"
        ]
        assert len(analyzing_calls) == 1
        assert analyzing_calls[0][0][1] == "document.pdf"

    def test_callback_called_with_sorted_status_on_success(
        self, tmp_path: Path
    ) -> None:
        """Callback is invoked with 'sorted' status after successful extraction."""
        handler = FolderEventHandler(
            self.orchestrator,
            self.monitor,
            self.state_manager,
            progress_callback=None,
            on_event_callback=self.event_callback,
        )
        test_file = tmp_path / "document.pdf"
        test_file.write_text("content")
        event = FileCreatedEvent(str(test_file))

        self.monitor.wait_for_file_ready.return_value = True
        self.orchestrator.process_single_file.return_value = {"status": "success"}

        handler.on_created(event)

        sorted_calls = [
            call
            for call in self.event_callback.call_args_list
            if call[0][0] == "sorted"
        ]
        assert len(sorted_calls) == 1
        assert sorted_calls[0][0][1] == "document.pdf"

    def test_callback_called_with_error_status_on_failure(self, tmp_path: Path) -> None:
        """Callback is invoked with 'error' status and error message on failure."""
        handler = FolderEventHandler(
            self.orchestrator,
            self.monitor,
            self.state_manager,
            progress_callback=None,
            on_event_callback=self.event_callback,
        )
        test_file = tmp_path / "document.pdf"
        test_file.write_text("content")
        event = FileCreatedEvent(str(test_file))

        self.monitor.wait_for_file_ready.return_value = True
        self.orchestrator.process_single_file.side_effect = RuntimeError("Test error")

        handler.on_created(event)

        error_calls = [
            call for call in self.event_callback.call_args_list if call[0][0] == "error"
        ]
        assert len(error_calls) == 1
        assert error_calls[0][0][1] == "document.pdf"
        assert "Test error" in error_calls[0][0][2]

    def test_callback_order_is_correct(self, tmp_path: Path) -> None:
        """Callback events follow expected order: incoming → waiting → analyzing → sorted."""
        handler = FolderEventHandler(
            self.orchestrator,
            self.monitor,
            self.state_manager,
            progress_callback=None,
            on_event_callback=self.event_callback,
        )
        test_file = tmp_path / "document.pdf"
        test_file.write_text("content")
        event = FileCreatedEvent(str(test_file))

        self.monitor.wait_for_file_ready.return_value = True
        self.orchestrator.process_single_file.return_value = {"status": "success"}

        handler.on_created(event)

        # Extract status sequence
        statuses = [call[0][0] for call in self.event_callback.call_args_list]
        assert statuses == ["incoming", "waiting", "analyzing", "sorted"]

    def test_faulty_event_callback_does_not_crash_handler(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Event callback exceptions are caught and logged, handler continues."""
        faulty_callback = Mock(side_effect=RuntimeError("Callback exploded"))
        handler = FolderEventHandler(
            self.orchestrator,
            self.monitor,
            self.state_manager,
            progress_callback=None,
            on_event_callback=faulty_callback,
        )
        test_file = tmp_path / "document.pdf"
        test_file.write_text("content")
        event = FileCreatedEvent(str(test_file))

        self.monitor.wait_for_file_ready.return_value = True
        self.orchestrator.process_single_file.return_value = {"status": "success"}

        # Should not raise despite faulty callback
        with caplog.at_level(logging.WARNING):
            handler.on_created(event)

        # Extraction still completed
        self.orchestrator.process_single_file.assert_called_once()

    def test_callback_not_called_for_temp_files(self, tmp_path: Path) -> None:
        """Event callback is not invoked for ignored temp files."""
        handler = FolderEventHandler(
            self.orchestrator,
            self.monitor,
            self.state_manager,
            progress_callback=None,
            on_event_callback=self.event_callback,
        )
        test_file = tmp_path / "document.pdf.crdownload"
        test_file.write_text("incomplete")
        event = FileCreatedEvent(str(test_file))

        handler.on_created(event)

        self.event_callback.assert_not_called()


class TestWebSocketCallback:
    """Tests for websocket_callback parameter in FolderEventHandler.

    The websocket_callback provides an additional notification channel
    for real-time updates to WebSocket clients, alongside the existing
    progress_callback and on_event_callback.
    """

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.state_manager = StateManager()
        self.monitor = Mock(spec=StabilityMonitor)
        self.orchestrator = Mock(spec=EnhancedExtractionOrchestrator)
        self.websocket_callback = Mock()

    def test_websocket_callback_parameter_accepted(self) -> None:
        """Handler accepts optional websocket_callback parameter."""
        handler = FolderEventHandler(
            self.orchestrator,
            self.monitor,
            self.state_manager,
            progress_callback=None,
            on_event_callback=None,
            websocket_callback=self.websocket_callback,
        )
        assert handler.websocket_callback is self.websocket_callback

    def test_websocket_callback_defaults_to_none(self) -> None:
        """Handler works without websocket_callback (backward compatibility)."""
        handler = FolderEventHandler(
            self.orchestrator,
            self.monitor,
            self.state_manager,
            progress_callback=None,
        )
        assert handler.websocket_callback is None

    def test_websocket_callback_called_for_progress_updates(
        self, tmp_path: Path
    ) -> None:
        """Websocket callback receives progress updates."""
        handler = FolderEventHandler(
            self.orchestrator,
            self.monitor,
            self.state_manager,
            progress_callback=None,
            on_event_callback=None,
            websocket_callback=self.websocket_callback,
        )
        test_file = tmp_path / "document.pdf"
        test_file.write_text("content")
        event = FileCreatedEvent(str(test_file))

        self.monitor.wait_for_file_ready.return_value = True
        self.orchestrator.process_single_file.return_value = {"status": "success"}

        handler.on_created(event)

        # Websocket callback should have been called multiple times
        assert self.websocket_callback.call_count >= 1

    def test_websocket_callback_called_for_event_updates(self, tmp_path: Path) -> None:
        """Websocket callback receives event status updates."""
        handler = FolderEventHandler(
            self.orchestrator,
            self.monitor,
            self.state_manager,
            progress_callback=None,
            on_event_callback=None,
            websocket_callback=self.websocket_callback,
        )
        test_file = tmp_path / "document.pdf"
        test_file.write_text("content")
        event = FileCreatedEvent(str(test_file))

        self.monitor.wait_for_file_ready.return_value = True
        self.orchestrator.process_single_file.return_value = {"status": "success"}

        handler.on_created(event)

        # Check that callback was called with expected event types
        call_args_list = self.websocket_callback.call_args_list
        call_types = [call[1].get("type") or call[0][0] for call in call_args_list]

        # Should have progress and event updates
        assert len(call_types) >= 1

    def test_websocket_callback_independent_of_progress_callback(
        self, tmp_path: Path
    ) -> None:
        """Websocket callback works independently of progress_callback."""
        progress_callback = Mock()
        handler = FolderEventHandler(
            self.orchestrator,
            self.monitor,
            self.state_manager,
            progress_callback=progress_callback,
            on_event_callback=None,
            websocket_callback=self.websocket_callback,
        )
        test_file = tmp_path / "document.pdf"
        test_file.write_text("content")
        event = FileCreatedEvent(str(test_file))

        self.monitor.wait_for_file_ready.return_value = True
        self.orchestrator.process_single_file.return_value = {"status": "success"}

        handler.on_created(event)

        # Both callbacks should have been called
        assert progress_callback.call_count >= 1
        assert self.websocket_callback.call_count >= 1

    def test_faulty_websocket_callback_does_not_crash_handler(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Websocket callback exceptions are caught and logged, handler continues."""
        faulty_callback = Mock(side_effect=RuntimeError("WebSocket error"))
        handler = FolderEventHandler(
            self.orchestrator,
            self.monitor,
            self.state_manager,
            progress_callback=None,
            on_event_callback=None,
            websocket_callback=faulty_callback,
        )
        test_file = tmp_path / "document.pdf"
        test_file.write_text("content")
        event = FileCreatedEvent(str(test_file))

        self.monitor.wait_for_file_ready.return_value = True
        self.orchestrator.process_single_file.return_value = {"status": "success"}

        # Should not raise despite faulty callback
        with caplog.at_level(logging.WARNING):
            handler.on_created(event)

        # Extraction still completed
        self.orchestrator.process_single_file.assert_called_once()

    def test_websocket_callback_not_called_for_temp_files(self, tmp_path: Path) -> None:
        """Websocket callback is not invoked for ignored temp files."""
        handler = FolderEventHandler(
            self.orchestrator,
            self.monitor,
            self.state_manager,
            progress_callback=None,
            on_event_callback=None,
            websocket_callback=self.websocket_callback,
        )
        test_file = tmp_path / "document.pdf.crdownload"
        test_file.write_text("incomplete")
        event = FileCreatedEvent(str(test_file))

        handler.on_created(event)

        self.websocket_callback.assert_not_called()


class TestSmartWatchSecurity:
    """Security tests for SmartFolderEventHandler path validation.

    Verifies that Smart-Watch mode enforces safe folder policy and prevents
    files from being moved to unsafe locations via path traversal or AI-generated
    paths that escape the safe folders.
    """

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        pytest.importorskip(
            "folder_extractor.core.smart_sorter",
            reason="SmartSorter requires Python 3.9+"
        )
        from folder_extractor.core.smart_sorter import SmartSorter
        from folder_extractor.core.watch import SmartFolderEventHandler

        self.SmartFolderEventHandler = SmartFolderEventHandler
        self.state_manager = StateManager()
        self.monitor = Mock(spec=StabilityMonitor)
        self.smart_sorter = Mock(spec=SmartSorter)

    def test_smart_watch_rejects_unsafe_base_path(self, tmp_path: Path) -> None:
        """SmartFolderEventHandler must reject base_path outside safe folders.

        SECURITY TEST: Prevents Smart-Watch from operating in unsafe locations
        like /tmp, /etc, or arbitrary directories outside Desktop/Downloads/Documents.
        """
        # Arrange - create unsafe base_path (not in safe folders)
        unsafe_base = tmp_path / "unsafe_location"
        unsafe_base.mkdir()

        # Act & Assert - initialization or first file processing should fail
        with pytest.raises((ValueError, PermissionError)) as exc_info:
            handler = self.SmartFolderEventHandler(
                smart_sorter=self.smart_sorter,
                monitor=self.monitor,
                state_manager=self.state_manager,
                base_path=unsafe_base,
            )

        # Verify error message mentions safe folders
        error_msg = str(exc_info.value).lower()
        assert any(
            keyword in error_msg
            for keyword in ["safe", "allowed", "desktop", "downloads", "documents"]
        )

    def test_smart_watch_validates_resolved_target_path(self, tmp_path: Path) -> None:
        """SmartFolderEventHandler must validate target_dir escapes safe folders.

        SECURITY TEST: Defense-in-depth - even if sanitization is bypassed somehow,
        is_safe_path validation must catch unsafe target directories before file moves.
        """
        # Arrange - create a safe base_path in Downloads
        home = Path.home()
        safe_base = home / "Downloads" / "test_watch_security"
        safe_base.mkdir(parents=True, exist_ok=True)

        try:
            # Create test file in safe location
            test_file = safe_base / "document.pdf"
            test_file.write_text("test content")

            # Create handler with SAFE base_path
            handler = self.SmartFolderEventHandler(
                smart_sorter=self.smart_sorter,
                monitor=self.monitor,
                state_manager=self.state_manager,
                base_path=safe_base,
                folder_structure="{category}",
            )

            # Mock AI to return safe-looking data
            async def mock_process_file(filepath, mime_type):
                return {"category": "Invoices"}

            self.smart_sorter.process_file = mock_process_file
            self.monitor.wait_for_file_ready.return_value = True

            # Mock _build_target_path to return an UNSAFE path
            # This simulates a bypass in sanitization or other vulnerability
            unsafe_path = tmp_path / "evil"  # Outside safe folders!
            original_build = handler._build_target_path
            handler._build_target_path = Mock(return_value=unsafe_path)

            # Act - process file should detect unsafe target_dir and raise ValueError
            import asyncio
            with pytest.raises(ValueError) as exc_info:
                asyncio.run(handler._process_file_smart(test_file, timeout=30))

            # Assert - error mentions security violation
            error_msg = str(exc_info.value).lower()
            assert "security" in error_msg or "safe" in error_msg

            # Verify file was NOT moved to unsafe location
            assert not (unsafe_path / "document.pdf").exists()

        finally:
            # Cleanup
            if safe_base.exists():
                import shutil
                shutil.rmtree(safe_base, ignore_errors=True)
