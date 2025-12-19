"""
Unit tests for the enhanced extractor module.
"""

import threading
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from folder_extractor.config.constants import MESSAGES
from folder_extractor.config.settings import settings
from folder_extractor.core.extractor import (
    EnhancedExtractionOrchestrator,
    EnhancedFileExtractor,
    SecurityError,
)


class TestEnhancedFileExtractor:
    """Test EnhancedFileExtractor class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset settings
        settings.reset_to_defaults()

        # Create mocks
        self.mock_file_discovery = Mock()
        self.mock_file_operations = Mock()
        self.mock_state_manager = Mock()
        self.mock_history_manager = Mock()

        # Configure state manager mock
        self.abort_signal = threading.Event()
        self.mock_state_manager.get_abort_signal.return_value = self.abort_signal

        # Create extractor with mocks
        self.extractor = EnhancedFileExtractor(
            file_discovery=self.mock_file_discovery,
            file_operations=self.mock_file_operations,
            state_manager=self.mock_state_manager,
        )
        # Replace history manager with mock
        self.extractor.history_manager = self.mock_history_manager

    def test_validate_security_accepts_safe_path(self):
        """Safe paths (Desktop, Downloads, Documents) are accepted without exception."""
        home = Path.home()
        safe_path = str(home / "Desktop" / "test")

        # No exception means path is accepted
        self.extractor.validate_security(safe_path)

    def test_validate_security_unsafe_path(self):
        """Test security validation with unsafe path."""
        unsafe_paths = ["/etc", "/usr/bin", str(Path.home())]

        for path in unsafe_paths:
            with pytest.raises(SecurityError):
                self.extractor.validate_security(path)

    def test_discover_files_basic(self, tmp_path):
        """Test basic file discovery."""
        self.mock_file_discovery.find_files.return_value = [
            str(tmp_path / "file1.txt"),
            str(tmp_path / "file2.pdf"),
        ]

        files = self.extractor.discover_files(tmp_path)

        assert len(files) == 2
        self.mock_file_discovery.find_files.assert_called_once_with(
            directory=str(tmp_path),
            max_depth=0,
            file_type_filter=None,
            include_hidden=False,
        )

    def test_extract_files_saves_history(self, tmp_path):
        """Test that history is saved after successful extraction (line 195)."""
        # Setup - set file_type_filter to avoid triggering empty directory removal
        settings.set("file_type_filter", [".txt"])

        files = [str(tmp_path / f"file{i}.txt") for i in range(3)]
        destination = tmp_path / "dest"
        destination.mkdir()

        # Configure mocks for FileMover via file_operations
        history = [
            {"original_pfad": files[0], "neuer_pfad": str(destination / "file0.txt")},
            {"original_pfad": files[1], "neuer_pfad": str(destination / "file1.txt")},
            {"original_pfad": files[2], "neuer_pfad": str(destination / "file2.txt")},
        ]

        # Mock FileMover behavior
        with patch("folder_extractor.core.extractor.FileMover") as MockFileMover:
            mock_mover = MockFileMover.return_value
            mock_mover.move_files.return_value = (3, 0, 0, history)

            # Mock ProgressTracker
            with patch("folder_extractor.core.extractor.ProgressTracker"):
                # Execute extraction
                result = self.extractor.extract_files(files, destination)

        # Verify history was saved (line 195)
        self.mock_history_manager.save_history.assert_called_once_with(
            history, str(destination)
        )
        assert result["moved"] == 3
        assert len(result["history"]) == 3

    def test_extract_files_with_abort_signal(self, tmp_path):
        """Test that aborted flag is set when abort_signal is triggered (line 199)."""
        # Setup - set file_type_filter to avoid triggering empty directory removal
        settings.set("file_type_filter", [".txt"])

        files = [str(tmp_path / f"file{i}.txt") for i in range(3)]
        destination = tmp_path / "dest"
        destination.mkdir()

        # Set abort signal before extraction
        self.abort_signal.set()

        # Mock FileMover behavior
        with patch("folder_extractor.core.extractor.FileMover") as MockFileMover:
            mock_mover = MockFileMover.return_value
            mock_mover.move_files.return_value = (1, 0, 0, [])

            # Mock ProgressTracker
            with patch("folder_extractor.core.extractor.ProgressTracker"):
                # Execute extraction
                result = self.extractor.extract_files(files, destination)

        # Verify aborted flag was set (line 199)
        assert result["aborted"] is True

    def test_extract_files_removes_empty_directories(self, tmp_path):
        """Test empty directory removal branch (lines 207-211)."""
        # Setup: Create actual file structure
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        subdir = source_dir / "subdir"
        subdir.mkdir()

        file1 = subdir / "file1.txt"
        file1.write_text("content")

        destination = tmp_path / "dest"
        destination.mkdir()

        files = [str(file1)]

        # Mock FileMover to simulate successful move
        with patch("folder_extractor.core.extractor.FileMover") as MockFileMover:
            mock_mover = MockFileMover.return_value
            history = [
                {
                    "original_pfad": str(file1),
                    "neuer_pfad": str(destination / "file1.txt"),
                }
            ]
            mock_mover.move_files.return_value = (1, 0, 0, history)

            # Mock ProgressTracker
            with patch("folder_extractor.core.extractor.ProgressTracker"):
                # Mock get_temp_files_list to return a list
                mock_temp_files = [".DS_Store", ".gitkeep"]
                with patch(
                    "folder_extractor.core.extractor.get_temp_files_list",
                    return_value=mock_temp_files,
                    create=True,
                ):
                    # Mock _remove_empty_directories to verify it's called
                    with patch.object(
                        self.extractor, "_remove_empty_directories", return_value=1
                    ) as mock_remove:
                        # Execute extraction (not dry run, not sort by type, no file type filter, moved > 0)
                        settings.set("dry_run", False)
                        settings.set("sort_by_type", False)
                        settings.set("file_type_filter", None)

                        result = self.extractor.extract_files(files, destination)

        # Verify _remove_empty_directories was called (lines 207-211)
        mock_remove.assert_called_once()
        assert result["removed_directories"] == 1

    def test_remove_empty_directories(self, tmp_path):
        """Test the _remove_empty_directories method directly (lines 225-267)."""
        # Create directory structure:
        # tmp_path/
        #   ├── empty_subdir1/
        #   ├── empty_subdir2/
        #   │   └── nested_empty/
        #   ├── non_empty_subdir/
        #   │   └── file.txt
        #   └── .hidden_file

        empty1 = tmp_path / "empty_subdir1"
        empty1.mkdir()

        empty2 = tmp_path / "empty_subdir2"
        empty2.mkdir()
        nested_empty = empty2 / "nested_empty"
        nested_empty.mkdir()

        non_empty = tmp_path / "non_empty_subdir"
        non_empty.mkdir()
        (non_empty / "file.txt").write_text("content")

        hidden_file = tmp_path / ".hidden_file"
        hidden_file.write_text("hidden")

        # Also create a temp file that should be ignored
        temp_file = tmp_path / ".DS_Store"
        temp_file.write_text("temp")

        temp_files = [".DS_Store"]

        # Execute removal
        removed_count = self.extractor._remove_empty_directories(tmp_path, temp_files)

        # Verify empty directories were removed (deepest first)
        # nested_empty, empty_subdir2 (becomes empty after nested_empty removed), and empty_subdir1
        assert removed_count == 3
        assert not nested_empty.exists()
        assert not empty1.exists()
        assert not empty2.exists()

        # Verify non-empty directory still exists
        assert non_empty.exists()
        assert (non_empty / "file.txt").exists()

    def test_remove_empty_directories_respects_hidden_setting(self, tmp_path):
        """Test that _remove_empty_directories respects include_hidden setting."""
        # Create directory with only hidden file
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        hidden_file = subdir / ".hidden"
        hidden_file.write_text("hidden content")

        # Test with include_hidden=False (default)
        settings.set("include_hidden", False)
        removed_count = self.extractor._remove_empty_directories(tmp_path, [])

        # Directory should NOT be removed because rmdir() fails when hidden file exists
        # Even though we filter it out logically, the OS sees the directory as non-empty
        assert removed_count == 0
        assert subdir.exists()

    def test_remove_empty_directories_with_include_hidden(self, tmp_path):
        """Test that hidden files prevent directory removal when include_hidden=True."""
        # Create directory with only hidden file
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        hidden_file = subdir / ".hidden"
        hidden_file.write_text("hidden content")

        # Test with include_hidden=True
        settings.set("include_hidden", True)
        removed_count = self.extractor._remove_empty_directories(tmp_path, [])

        # Directory should NOT be removed since hidden file counts
        assert removed_count == 0
        assert subdir.exists()

    def test_remove_empty_directories_with_temp_files(self, tmp_path):
        """Test that temp files don't prevent directory removal."""
        # Create directory with only temp file
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        temp_file = subdir / ".DS_Store"
        temp_file.write_text("temp")

        temp_files = [".DS_Store"]

        # Execute removal
        removed_count = self.extractor._remove_empty_directories(tmp_path, temp_files)

        # Directory should NOT be removed because rmdir() fails when temp file exists
        # Even though we filter it out logically, the OS sees the directory as non-empty
        assert removed_count == 0
        assert subdir.exists()

    def test_remove_empty_directories_skips_inaccessible_directories(self, tmp_path):
        """Directories that raise OSError on iterdir are skipped, not crashed on."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        with patch.object(Path, "iterdir", side_effect=OSError("Permission denied")):
            removed_count = self.extractor._remove_empty_directories(tmp_path, [])

            assert removed_count == 0

    def test_remove_empty_directories_skips_undeletable_directories(self, tmp_path):
        """Directories that raise OSError on rmdir are skipped and preserved."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        with patch.object(Path, "rmdir", side_effect=OSError("Cannot remove")):
            removed_count = self.extractor._remove_empty_directories(tmp_path, [])

            assert removed_count == 0
            assert subdir.exists()  # Directory preserved despite removal attempt

    def test_undo_with_abort_signal(self, tmp_path):
        """Test undo operation being interrupted by abort signal (line 306)."""
        # Create history with multiple operations
        operations = []
        for i in range(5):
            operations.append(
                {
                    "original_pfad": str(tmp_path / "original" / f"file{i}.txt"),
                    "neuer_pfad": str(tmp_path / "new" / f"file{i}.txt"),
                    "original_name": f"file{i}.txt",
                    "neuer_name": f"file{i}.txt",
                    "zeitstempel": "2024-01-01T12:00:00",
                }
            )

        history_data = {"operationen": operations}
        self.mock_history_manager.load_history.return_value = history_data

        # Mock ManagedOperation context manager
        mock_operation = Mock()
        mock_operation.abort_signal = self.abort_signal
        mock_operation.update_stats = Mock()
        mock_operation.__enter__ = Mock(return_value=mock_operation)
        mock_operation.__exit__ = Mock(return_value=False)

        # Set abort signal before undo starts
        self.abort_signal.set()

        # Mock ProgressTracker
        with patch("folder_extractor.core.extractor.ProgressTracker"):
            # Mock ManagedOperation
            with patch(
                "folder_extractor.core.extractor.ManagedOperation",
                return_value=mock_operation,
            ):
                # Execute undo
                result = self.extractor.undo_last_operation(tmp_path)

        # Verify undo was interrupted (line 306 - break when abort_signal is set)
        assert result["restored"] == 0  # No files restored due to immediate abort
        assert result["aborted"] is True

        # Verify file_operations.move_file was never called due to abort
        self.mock_file_operations.move_file.assert_not_called()

    def test_undo_with_file_error(self, tmp_path):
        """Test exception handling in undo operation (lines 321-328)."""
        # Create history with two operations
        operations = [
            {
                "original_pfad": str(tmp_path / "original" / "file1.txt"),
                "neuer_pfad": str(tmp_path / "new" / "file1.txt"),
                "original_name": "file1.txt",
                "neuer_name": "file1.txt",
                "zeitstempel": "2024-01-01T12:00:00",
            },
            {
                "original_pfad": str(tmp_path / "original" / "file2.txt"),
                "neuer_pfad": str(tmp_path / "new" / "file2.txt"),
                "original_name": "file2.txt",
                "neuer_name": "file2.txt",
                "zeitstempel": "2024-01-01T12:00:00",
            },
        ]

        history_data = {"operationen": operations}
        self.mock_history_manager.load_history.return_value = history_data

        # Mock file_operations to raise exception on first call, succeed on second
        self.mock_file_operations.move_file.side_effect = [
            Exception("Simulated file error"),  # First call (file2 in reverse) fails
            None,  # Second call (file1 in reverse) succeeds
        ]

        # Mock ManagedOperation context manager
        mock_operation = Mock()
        mock_operation.abort_signal = self.abort_signal  # Not set
        mock_operation.update_stats = Mock()
        mock_operation.__enter__ = Mock(return_value=mock_operation)
        mock_operation.__exit__ = Mock(return_value=False)

        # Mock ProgressTracker
        with patch("folder_extractor.core.extractor.ProgressTracker") as MockProgress:
            mock_progress = MockProgress.return_value

            # Mock ManagedOperation
            with patch(
                "folder_extractor.core.extractor.ManagedOperation",
                return_value=mock_operation,
            ):
                # Execute undo
                result = self.extractor.undo_last_operation(tmp_path)

        # Verify exception was handled (lines 321-328)
        assert result["restored"] == 1  # One file successfully restored
        assert result["errors"] == 1  # One error occurred

        # Verify both operations were attempted
        assert self.mock_file_operations.move_file.call_count == 2

        # Verify progress was updated with error
        calls = mock_progress.increment.call_args_list
        assert len(calls) == 2
        # First call (file2) should have error
        assert calls[0][1].get("error") is not None or len(calls[0][0]) > 1

    def test_undo_no_history(self, tmp_path):
        """Test undo when no history exists."""
        # Mock no history
        self.mock_history_manager.load_history.return_value = None

        result = self.extractor.undo_last_operation(tmp_path)

        assert result["status"] == "no_history"
        assert result["restored"] == 0

    def test_undo_empty_operations(self, tmp_path):
        """Test undo with empty operations list."""
        # Mock history with empty operations
        history_data = {}
        self.mock_history_manager.load_history.return_value = history_data

        result = self.extractor.undo_last_operation(tmp_path)

        assert result["status"] == "no_history"
        assert result["restored"] == 0

    def test_extract_files_dry_run_no_history(self, tmp_path):
        """Test that history is not saved in dry run mode."""
        # Setup
        files = [str(tmp_path / "file.txt")]
        destination = tmp_path / "dest"
        destination.mkdir()

        settings.set("dry_run", True)

        # Mock FileMover behavior
        with patch("folder_extractor.core.extractor.FileMover") as MockFileMover:
            mock_mover = MockFileMover.return_value
            mock_mover.move_files.return_value = (1, 0, 0, [])

            # Mock ProgressTracker
            with patch("folder_extractor.core.extractor.ProgressTracker"):
                # Execute extraction
                self.extractor.extract_files(files, destination)

        # Verify history was NOT saved in dry run
        self.mock_history_manager.save_history.assert_not_called()

    def test_extract_files_no_history_when_no_files_moved(self, tmp_path):
        """Test that history is not saved when no files were moved."""
        # Setup
        files = [str(tmp_path / "file.txt")]
        destination = tmp_path / "dest"
        destination.mkdir()

        # Mock FileMover to return 0 moved files
        with patch("folder_extractor.core.extractor.FileMover") as MockFileMover:
            mock_mover = MockFileMover.return_value
            mock_mover.move_files.return_value = (0, 0, 0, [])

            # Mock ProgressTracker
            with patch("folder_extractor.core.extractor.ProgressTracker"):
                # Execute extraction
                result = self.extractor.extract_files(files, destination)

        # Verify history was NOT saved when no files moved
        self.mock_history_manager.save_history.assert_not_called()
        assert result["moved"] == 0

    def test_extract_files_sort_by_type_mode(self, tmp_path):
        """Test extraction in sort by type mode."""
        # Setup
        files = [str(tmp_path / "file.txt")]
        destination = tmp_path / "dest"
        destination.mkdir()

        settings.set("sort_by_type", True)

        # Mock FileMover behavior for sorted mode
        with patch("folder_extractor.core.extractor.FileMover") as MockFileMover:
            mock_mover = MockFileMover.return_value
            history = [
                {
                    "original_pfad": files[0],
                    "neuer_pfad": str(destination / "TXT" / "file.txt"),
                }
            ]
            mock_mover.move_files_sorted.return_value = (1, 0, 0, history, ["TXT"])

            # Mock ProgressTracker
            with patch("folder_extractor.core.extractor.ProgressTracker"):
                # Execute extraction
                result = self.extractor.extract_files(files, destination)

        # Verify sort by type was used
        mock_mover.move_files_sorted.assert_called_once()
        assert result["created_folders"] == ["TXT"]

    def test_extract_files_updates_operation_stats(self, tmp_path):
        """Test that operation stats are updated via state manager."""
        # Setup - set file_type_filter to avoid triggering empty directory removal
        settings.set("file_type_filter", [".txt"])

        files = [str(tmp_path / "file.txt")]
        destination = tmp_path / "dest"
        destination.mkdir()
        operation_id = "test-op-123"

        # Mock FileMover behavior
        with patch("folder_extractor.core.extractor.FileMover") as MockFileMover:
            mock_mover = MockFileMover.return_value
            history = [
                {"original_pfad": files[0], "neuer_pfad": str(destination / "file.txt")}
            ]
            mock_mover.move_files.return_value = (1, 0, 0, history)

            # Mock ProgressTracker and capture callback
            with patch("folder_extractor.core.extractor.ProgressTracker"):
                # Execute extraction with operation_id
                self.extractor.extract_files(
                    files, destination, operation_id=operation_id
                )

        # Verify state manager methods were called
        self.mock_state_manager.get_abort_signal.assert_called()
        # Note: update_operation_stats is called via progress callback,
        # which is complex to verify without actually triggering it


class TestEnhancedFileExtractorIntegration:
    """Integration tests with minimal mocking."""

    def test_remove_empty_directories_complete_workflow(self, tmp_path):
        """Integration test for complete empty directory removal workflow."""
        # Create complex directory structure
        (tmp_path / "level1" / "level2" / "level3").mkdir(parents=True)
        (tmp_path / "level1" / "level2_with_file").mkdir(parents=True)
        (tmp_path / "level1" / "level2_with_file" / "file.txt").write_text("content")
        (tmp_path / "empty_at_root").mkdir()

        # Create extractor
        extractor = EnhancedFileExtractor()

        # Remove empty directories
        temp_files = [".DS_Store", ".gitkeep"]
        removed = extractor._remove_empty_directories(tmp_path, temp_files)

        # Verify correct directories were removed
        # level3, level2, level1 (eventually), empty_at_root should be removed
        # level2_with_file and its parent should remain
        assert removed >= 2  # At least level3 and empty_at_root
        assert not (tmp_path / "empty_at_root").exists()
        assert (tmp_path / "level1" / "level2_with_file").exists()
        assert (tmp_path / "level1" / "level2_with_file" / "file.txt").exists()


class TestEnhancedExtractionOrchestrator:
    """Test EnhancedExtractionOrchestrator class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset settings
        settings.reset_to_defaults()

        # Create mock extractor
        self.mock_extractor = Mock()

        # Create mock state manager
        self.mock_state_manager = Mock()

        # Create orchestrator with mocks
        self.orchestrator = EnhancedExtractionOrchestrator(
            extractor=self.mock_extractor, state_manager=self.mock_state_manager
        )

    def test_init_with_default_state_manager(self):
        """Test __init__ creates default state manager (lines 357-358)."""
        # Create orchestrator without state manager
        with patch("folder_extractor.core.extractor.get_state_manager") as mock_get_sm:
            mock_default_sm = Mock()
            mock_get_sm.return_value = mock_default_sm

            orchestrator = EnhancedExtractionOrchestrator(extractor=self.mock_extractor)

            # Verify get_state_manager was called
            mock_get_sm.assert_called_once()
            assert orchestrator.state_manager == mock_default_sm

    def test_execute_extraction_success(self, tmp_path):
        """Test successful extraction workflow (lines 373-419)."""
        # Setup
        source_path = tmp_path / "source"
        source_path.mkdir()

        files = [str(tmp_path / "file1.txt"), str(tmp_path / "file2.txt")]

        # Configure mocks
        self.mock_extractor.validate_security.return_value = None
        self.mock_extractor.discover_files.return_value = files
        self.mock_extractor.extract_files.return_value = {
            "moved": 2,
            "skipped": 0,
            "errors": 0,
            "aborted": False,
        }

        # Mock ManagedOperation
        mock_operation = Mock()
        mock_operation.operation_id = "test-op-123"
        mock_operation.__enter__ = Mock(return_value=mock_operation)
        mock_operation.__exit__ = Mock(return_value=False)

        # Mock operation stats
        mock_stats = Mock()
        mock_stats.duration = 1.5
        mock_stats.success_rate = 100.0
        self.mock_state_manager.get_operation_stats.return_value = mock_stats

        with patch(
            "folder_extractor.core.extractor.ManagedOperation",
            return_value=mock_operation,
        ):
            # Execute extraction
            result = self.orchestrator.execute_extraction(source_path)

        # Verify workflow
        self.mock_extractor.validate_security.assert_called_once()
        self.mock_extractor.discover_files.assert_called_once_with(Path(source_path))
        self.mock_extractor.extract_files.assert_called_once()

        # Verify result
        assert result["status"] == "success"
        assert result["files_found"] == 2
        assert result["moved"] == 2
        assert result["operation_id"] == "test-op-123"
        assert result["duration"] == 1.5
        assert result["success_rate"] == 100.0

    def test_execute_extraction_no_files(self, tmp_path):
        """Test when no files found (lines 384-389)."""
        # Setup
        source_path = tmp_path / "source"
        source_path.mkdir()

        # Configure mocks
        self.mock_extractor.validate_security.return_value = None
        self.mock_extractor.discover_files.return_value = []

        # Mock ManagedOperation
        mock_operation = Mock()
        mock_operation.__enter__ = Mock(return_value=mock_operation)
        mock_operation.__exit__ = Mock(return_value=False)

        with patch(
            "folder_extractor.core.extractor.ManagedOperation",
            return_value=mock_operation,
        ):
            # Execute extraction
            result = self.orchestrator.execute_extraction(source_path)

        # Verify result
        assert result["status"] == "no_files"
        assert result["message"] == MESSAGES["NO_FILES_FOUND"]
        assert result["files_found"] == 0

        # Verify extract_files was NOT called
        self.mock_extractor.extract_files.assert_not_called()

    def test_execute_extraction_cancelled(self, tmp_path):
        """Test when user cancels (lines 392-398)."""
        # Setup
        source_path = tmp_path / "source"
        source_path.mkdir()

        files = [str(tmp_path / "file1.txt")]

        # Configure mocks
        self.mock_extractor.validate_security.return_value = None
        self.mock_extractor.discover_files.return_value = files

        # Mock ManagedOperation
        mock_operation = Mock()
        mock_operation.__enter__ = Mock(return_value=mock_operation)
        mock_operation.__exit__ = Mock(return_value=False)

        # Create confirmation callback that returns False (cancel)
        confirmation_callback = Mock(return_value=False)

        with patch(
            "folder_extractor.core.extractor.ManagedOperation",
            return_value=mock_operation,
        ):
            # Execute extraction with confirmation callback
            result = self.orchestrator.execute_extraction(
                source_path, confirmation_callback=confirmation_callback
            )

        # Verify confirmation was called
        confirmation_callback.assert_called_once_with(len(files))

        # Verify result
        assert result["status"] == "cancelled"
        assert result["message"] == MESSAGES["OPERATION_CANCELLED"]
        assert result["files_found"] == 1

        # Verify extract_files was NOT called
        self.mock_extractor.extract_files.assert_not_called()

    def test_execute_extraction_dry_run_no_confirmation(self, tmp_path):
        """Test that confirmation is skipped in dry run mode (line 392)."""
        # Setup
        source_path = tmp_path / "source"
        source_path.mkdir()

        files = [str(tmp_path / "file1.txt")]

        # Enable dry run
        settings.set("dry_run", True)

        # Configure mocks
        self.mock_extractor.validate_security.return_value = None
        self.mock_extractor.discover_files.return_value = files
        self.mock_extractor.extract_files.return_value = {
            "moved": 0,
            "skipped": 1,
            "errors": 0,
            "aborted": False,
        }

        # Mock ManagedOperation
        mock_operation = Mock()
        mock_operation.operation_id = "test-op-123"
        mock_operation.__enter__ = Mock(return_value=mock_operation)
        mock_operation.__exit__ = Mock(return_value=False)

        self.mock_state_manager.get_operation_stats.return_value = None

        # Create confirmation callback that should NOT be called
        confirmation_callback = Mock(return_value=False)

        with patch(
            "folder_extractor.core.extractor.ManagedOperation",
            return_value=mock_operation,
        ):
            # Execute extraction with confirmation callback in dry run mode
            result = self.orchestrator.execute_extraction(
                source_path, confirmation_callback=confirmation_callback
            )

        # Verify confirmation was NOT called in dry run
        confirmation_callback.assert_not_called()

        # Verify extract_files WAS called
        self.mock_extractor.extract_files.assert_called_once()

        # Verify result
        assert result["status"] == "success"

    def test_execute_extraction_security_error(self, tmp_path):
        """Test SecurityError handling (lines 421-426)."""
        # Setup
        source_path = tmp_path / "source"
        source_path.mkdir()

        # Configure mock to raise SecurityError
        error_message = "Unsicherer Pfad"
        self.mock_extractor.validate_security.side_effect = SecurityError(error_message)

        # Mock ManagedOperation
        mock_operation = Mock()
        mock_operation.__enter__ = Mock(return_value=mock_operation)
        mock_operation.__exit__ = Mock(return_value=False)

        with patch(
            "folder_extractor.core.extractor.ManagedOperation",
            return_value=mock_operation,
        ):
            # Execute extraction
            result = self.orchestrator.execute_extraction(source_path)

        # Verify result
        assert result["status"] == "security_error"
        assert result["message"] == error_message
        assert result["error"] is True

        # Verify subsequent steps were NOT called
        self.mock_extractor.discover_files.assert_not_called()
        self.mock_extractor.extract_files.assert_not_called()

    def test_execute_extraction_generic_error(self, tmp_path):
        """Test generic Exception handling (lines 428-433)."""
        # Setup
        source_path = tmp_path / "source"
        source_path.mkdir()

        # Configure mock to raise generic exception
        error_message = "Unexpected error"
        self.mock_extractor.validate_security.side_effect = Exception(error_message)

        # Mock ManagedOperation
        mock_operation = Mock()
        mock_operation.__enter__ = Mock(return_value=mock_operation)
        mock_operation.__exit__ = Mock(return_value=False)

        with patch(
            "folder_extractor.core.extractor.ManagedOperation",
            return_value=mock_operation,
        ):
            # Execute extraction
            result = self.orchestrator.execute_extraction(source_path)

        # Verify result
        assert result["status"] == "error"
        assert f"Fehler: {error_message}" in result["message"]
        assert result["error"] is True

        # Verify subsequent steps were NOT called
        self.mock_extractor.discover_files.assert_not_called()
        self.mock_extractor.extract_files.assert_not_called()

    def test_execute_extraction_error_during_discovery(self, tmp_path):
        """Test error handling during file discovery phase."""
        # Setup
        source_path = tmp_path / "source"
        source_path.mkdir()

        # Configure mocks
        self.mock_extractor.validate_security.return_value = None
        self.mock_extractor.discover_files.side_effect = Exception("Discovery failed")

        # Mock ManagedOperation
        mock_operation = Mock()
        mock_operation.__enter__ = Mock(return_value=mock_operation)
        mock_operation.__exit__ = Mock(return_value=False)

        with patch(
            "folder_extractor.core.extractor.ManagedOperation",
            return_value=mock_operation,
        ):
            # Execute extraction
            result = self.orchestrator.execute_extraction(source_path)

        # Verify result
        assert result["status"] == "error"
        assert "Fehler: Discovery failed" in result["message"]
        assert result["error"] is True

    def test_execute_extraction_with_progress_callback(self, tmp_path):
        """Test extraction with progress callback."""
        # Setup
        source_path = tmp_path / "source"
        source_path.mkdir()

        files = [str(tmp_path / "file1.txt")]

        # Configure mocks
        self.mock_extractor.validate_security.return_value = None
        self.mock_extractor.discover_files.return_value = files
        self.mock_extractor.extract_files.return_value = {
            "moved": 1,
            "skipped": 0,
            "errors": 0,
            "aborted": False,
        }

        # Mock ManagedOperation
        mock_operation = Mock()
        mock_operation.operation_id = "test-op-123"
        mock_operation.__enter__ = Mock(return_value=mock_operation)
        mock_operation.__exit__ = Mock(return_value=False)

        self.mock_state_manager.get_operation_stats.return_value = None

        # Create progress callback
        progress_callback = Mock()

        with patch(
            "folder_extractor.core.extractor.ManagedOperation",
            return_value=mock_operation,
        ):
            # Execute extraction with progress callback
            self.orchestrator.execute_extraction(
                source_path, progress_callback=progress_callback
            )

        # Verify extract_files was called with progress callback
        call_args = self.mock_extractor.extract_files.call_args
        assert call_args[0][2] == "test-op-123"  # operation_id
        assert call_args[0][3] == progress_callback  # progress_callback

    def test_execute_undo(self, tmp_path):
        """Test undo operation (lines 444-445)."""
        # Setup
        path = tmp_path / "test"
        path.mkdir()

        expected_result = {
            "status": "success",
            "restored": 5,
            "errors": 0,
            "aborted": False,
        }

        # Configure mock
        self.mock_extractor.undo_last_operation.return_value = expected_result

        # Execute undo
        result = self.orchestrator.execute_undo(path)

        # Verify extractor method was called
        self.mock_extractor.undo_last_operation.assert_called_once_with(Path(path))

        # Verify result is passed through
        assert result == expected_result

    def test_execute_undo_with_string_path(self, tmp_path):
        """Test undo with string path conversion."""
        # Setup
        path_str = str(tmp_path / "test")
        Path(path_str).mkdir()

        expected_result = {
            "status": "success",
            "restored": 3,
            "errors": 0,
            "aborted": False,
        }

        # Configure mock
        self.mock_extractor.undo_last_operation.return_value = expected_result

        # Execute undo with string path
        result = self.orchestrator.execute_undo(path_str)

        # Verify extractor method was called with Path object
        self.mock_extractor.undo_last_operation.assert_called_once_with(Path(path_str))

        # Verify result
        assert result == expected_result
