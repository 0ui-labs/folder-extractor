"""Unit tests for folder event handler with temp file filtering and error recovery.

Tests verify the behavior of FolderEventHandler which handles file system events
for watch mode. The handler filters temp files, waits for file stability, and
triggers extraction via the orchestrator.
"""

import logging
from pathlib import Path
from unittest.mock import Mock, MagicMock

import pytest
from watchdog.events import FileCreatedEvent, FileMovedEvent, DirCreatedEvent

from folder_extractor.core.watch import FolderEventHandler
from folder_extractor.core.monitor import StabilityMonitor
from folder_extractor.core.extractor import EnhancedExtractionOrchestrator
from folder_extractor.core.state_manager import StateManager


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
            self.progress_callback,
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
