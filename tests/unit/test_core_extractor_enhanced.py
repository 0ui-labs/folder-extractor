"""
Unit tests for the enhanced extractor module.
"""

import threading
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from folder_extractor.config.constants import MESSAGES
from folder_extractor.core.extractor import (
    EnhancedExtractionOrchestrator,
    EnhancedFileExtractor,
    SecurityError,
)


@pytest.fixture
def enhanced_extractor_with_mocks(settings_fixture):
    """Create EnhancedFileExtractor with mocked dependencies."""
    # Create mocks
    mock_file_discovery = Mock()
    mock_file_operations = Mock()
    mock_state_manager = Mock()
    mock_history_manager = Mock()

    # Configure state manager mock
    abort_signal = threading.Event()
    mock_state_manager.get_abort_signal.return_value = abort_signal

    # Create extractor with mocks and settings
    extractor = EnhancedFileExtractor(
        settings=settings_fixture,
        file_discovery=mock_file_discovery,
        file_operations=mock_file_operations,
        state_manager=mock_state_manager,
    )
    # Replace history manager with mock
    extractor.history_manager = mock_history_manager

    # Attach mocks to extractor for test access
    extractor.mock_file_discovery = mock_file_discovery
    extractor.mock_file_operations = mock_file_operations
    extractor.mock_state_manager = mock_state_manager
    extractor.mock_history_manager = mock_history_manager
    extractor.abort_signal = abort_signal

    return extractor


class TestEnhancedFileExtractor:
    """Test EnhancedFileExtractor class."""

    def test_validate_security_accepts_safe_path(self, enhanced_extractor_with_mocks):
        """Safe paths (Desktop, Downloads, Documents) are accepted without exception."""
        home = Path.home()
        safe_path = str(home / "Desktop" / "test")

        # No exception means path is accepted
        enhanced_extractor_with_mocks.validate_security(safe_path)

    def test_validate_security_unsafe_path(self, enhanced_extractor_with_mocks):
        """Test security validation with unsafe path."""
        unsafe_paths = ["/etc", "/usr/bin", str(Path.home())]

        for path in unsafe_paths:
            with pytest.raises(SecurityError):
                enhanced_extractor_with_mocks.validate_security(path)

    def test_discover_files_basic(self, enhanced_extractor_with_mocks, tmp_path):
        """Test basic file discovery."""
        enhanced_extractor_with_mocks.mock_file_discovery.find_files.return_value = [
            str(tmp_path / "file1.txt"),
            str(tmp_path / "file2.pdf"),
        ]

        files = enhanced_extractor_with_mocks.discover_files(tmp_path)

        assert len(files) == 2
        enhanced_extractor_with_mocks.mock_file_discovery.find_files.assert_called_once_with(
            directory=tmp_path,
            max_depth=0,
            file_type_filter=None,
            include_hidden=False,
        )

    def test_extract_files_saves_history(self, enhanced_extractor_with_mocks, settings_fixture, tmp_path):
        """Test that history is saved after successful extraction (line 195)."""
        # Setup - set file_type_filter to avoid triggering empty directory removal
        settings_fixture.set("file_type_filter", [".txt"])

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
            mock_mover.move_files.return_value = (3, 0, 0, 0, 0, history)

            # Mock ProgressTracker
            with patch("folder_extractor.core.extractor.ProgressTracker"):
                # Execute extraction
                result = enhanced_extractor_with_mocks.extract_files(files, destination)

        # Verify history was saved (line 195)
        enhanced_extractor_with_mocks.mock_history_manager.save_history.assert_called_once_with(
            history, destination
        )
        assert result["moved"] == 3
        assert len(result["history"]) == 3

    def test_extract_files_with_abort_signal(self, enhanced_extractor_with_mocks, settings_fixture, tmp_path):
        """Test that aborted flag is set when abort_signal is triggered (line 199)."""
        # Setup - set file_type_filter to avoid triggering empty directory removal
        settings_fixture.set("file_type_filter", [".txt"])

        files = [str(tmp_path / f"file{i}.txt") for i in range(3)]
        destination = tmp_path / "dest"
        destination.mkdir()

        # Set abort signal before extraction
        enhanced_extractor_with_mocks.abort_signal.set()

        # Mock FileMover behavior
        with patch("folder_extractor.core.extractor.FileMover") as MockFileMover:
            mock_mover = MockFileMover.return_value
            mock_mover.move_files.return_value = (1, 0, 0, 0, 0, [])

            # Mock ProgressTracker
            with patch("folder_extractor.core.extractor.ProgressTracker"):
                # Execute extraction
                result = enhanced_extractor_with_mocks.extract_files(files, destination)

        # Verify aborted flag was set (line 199)
        assert result["aborted"] is True

    def test_extract_files_removes_empty_directories(self, enhanced_extractor_with_mocks, settings_fixture, tmp_path):
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
            mock_mover.move_files.return_value = (1, 0, 0, 0, 0, history)

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
                        enhanced_extractor_with_mocks,
                        "_remove_empty_directories",
                        return_value={"removed": 1, "skipped": []},
                    ) as mock_remove:
                        # Execute extraction (not dry run, not sort by type, no file type filter, moved > 0)
                        settings_fixture.set("dry_run", False)
                        settings_fixture.set("sort_by_type", False)
                        settings_fixture.set("file_type_filter", None)

                        result = enhanced_extractor_with_mocks.extract_files(files, destination)

        # Verify _remove_empty_directories was called (lines 207-211)
        mock_remove.assert_called_once()
        assert result["removed_directories"] == 1

    def test_remove_empty_directories(self, enhanced_extractor_with_mocks, tmp_path):
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
        result = enhanced_extractor_with_mocks._remove_empty_directories(tmp_path, temp_files)

        # Verify empty directories were removed (deepest first)
        # nested_empty, empty_subdir2 (becomes empty after nested_empty removed), and empty_subdir1
        assert result["removed"] == 3
        assert not nested_empty.exists()
        assert not empty1.exists()
        assert not empty2.exists()

        # Verify non-empty directory still exists
        assert non_empty.exists()
        assert (non_empty / "file.txt").exists()

    def test_remove_empty_directories_respects_hidden_setting(self, enhanced_extractor_with_mocks, settings_fixture, tmp_path):
        """Test that _remove_empty_directories respects include_hidden setting."""
        # Create directory with only hidden file
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        hidden_file = subdir / ".hidden"
        hidden_file.write_text("hidden content")

        # Test with include_hidden=False (default)
        # Hidden files are ignored, so directory is considered empty
        # Hidden files should be deleted, then the directory
        settings_fixture.set("include_hidden", False)
        result = enhanced_extractor_with_mocks._remove_empty_directories(tmp_path, [])

        # Directory SHOULD be removed because hidden files are cleaned up first
        assert result["removed"] == 1
        assert not subdir.exists()
        assert not hidden_file.exists()

    def test_remove_empty_directories_with_include_hidden(self, enhanced_extractor_with_mocks, settings_fixture, tmp_path):
        """Test that hidden files prevent directory removal when include_hidden=True."""
        # Create directory with only hidden file
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        hidden_file = subdir / ".hidden"
        hidden_file.write_text("hidden content")

        # Test with include_hidden=True
        settings_fixture.set("include_hidden", True)
        result = enhanced_extractor_with_mocks._remove_empty_directories(tmp_path, [])

        # Directory should NOT be removed since hidden file counts
        assert result["removed"] == 0
        assert subdir.exists()

    def test_remove_empty_directories_with_temp_files(self, enhanced_extractor_with_mocks, tmp_path):
        """Test that temp files don't prevent directory removal."""
        # Create directory with only temp file
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        temp_file = subdir / ".DS_Store"
        temp_file.write_text("temp")

        temp_files = [".DS_Store"]

        # Execute removal
        result = enhanced_extractor_with_mocks._remove_empty_directories(tmp_path, temp_files)

        # Directory SHOULD be removed because temp files are cleaned up first
        assert result["removed"] == 1
        assert not subdir.exists()
        assert not temp_file.exists()

    def test_remove_empty_directories_skips_inaccessible_directories(self, enhanced_extractor_with_mocks, tmp_path):
        """Directories that raise OSError on iterdir are skipped, not crashed on."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        with patch.object(Path, "iterdir", side_effect=OSError("Permission denied")):
            result = enhanced_extractor_with_mocks._remove_empty_directories(tmp_path, [])

            assert result["removed"] == 0
            # Verify the error was logged in skipped
            assert len(result["skipped"]) > 0

    def test_remove_empty_directories_skips_undeletable_directories(self, enhanced_extractor_with_mocks, tmp_path):
        """Directories that raise OSError on rmdir are skipped and preserved."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        with patch.object(Path, "rmdir", side_effect=OSError("Cannot remove")):
            result = enhanced_extractor_with_mocks._remove_empty_directories(tmp_path, [])

            assert result["removed"] == 0
            assert subdir.exists()  # Directory preserved despite removal attempt
            # Verify the error was logged in skipped
            assert len(result["skipped"]) > 0

    def test_undo_with_abort_signal(self, enhanced_extractor_with_mocks, tmp_path):
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
        enhanced_extractor_with_mocks.mock_history_manager.load_history.return_value = history_data

        # Mock ManagedOperation context manager
        mock_operation = Mock()
        mock_operation.abort_signal = enhanced_extractor_with_mocks.abort_signal
        mock_operation.update_stats = Mock()
        mock_operation.__enter__ = Mock(return_value=mock_operation)
        mock_operation.__exit__ = Mock(return_value=False)

        # Set abort signal before undo starts
        enhanced_extractor_with_mocks.abort_signal.set()

        # Mock ProgressTracker
        with patch("folder_extractor.core.extractor.ProgressTracker"):
            # Mock ManagedOperation
            with patch(
                "folder_extractor.core.extractor.ManagedOperation",
                return_value=mock_operation,
            ):
                # Execute undo
                result = enhanced_extractor_with_mocks.undo_last_operation(tmp_path)

        # Verify undo was interrupted (line 306 - break when abort_signal is set)
        assert result["restored"] == 0  # No files restored due to immediate abort
        assert result["aborted"] is True

        # Verify file_operations.move_file was never called due to abort
        enhanced_extractor_with_mocks.mock_file_operations.move_file.assert_not_called()

    def test_undo_with_file_error(self, enhanced_extractor_with_mocks, tmp_path):
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
        enhanced_extractor_with_mocks.mock_history_manager.load_history.return_value = history_data

        # Mock file_operations to raise exception on first call, succeed on second
        enhanced_extractor_with_mocks.mock_file_operations.move_file.side_effect = [
            Exception("Simulated file error"),  # First call (file2 in reverse) fails
            None,  # Second call (file1 in reverse) succeeds
        ]

        # Mock ManagedOperation context manager
        mock_operation = Mock()
        mock_operation.abort_signal = enhanced_extractor_with_mocks.abort_signal  # Not set
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
                result = enhanced_extractor_with_mocks.undo_last_operation(tmp_path)

        # Verify exception was handled (lines 321-328)
        assert result["restored"] == 1  # One file successfully restored
        assert result["errors"] == 1  # One error occurred

        # Verify both operations were attempted
        assert enhanced_extractor_with_mocks.mock_file_operations.move_file.call_count == 2

        # Verify progress was updated with error
        calls = mock_progress.increment.call_args_list
        assert len(calls) == 2
        # First call (file2) should have error
        assert calls[0][1].get("error") is not None or len(calls[0][0]) > 1

    def test_undo_no_history(self, enhanced_extractor_with_mocks, tmp_path):
        """Test undo when no history exists."""
        # Mock no history
        enhanced_extractor_with_mocks.mock_history_manager.load_history.return_value = None

        result = enhanced_extractor_with_mocks.undo_last_operation(tmp_path)

        assert result["status"] == "no_history"
        assert result["restored"] == 0

    def test_undo_empty_operations(self, enhanced_extractor_with_mocks, tmp_path):
        """Test undo with empty operations list."""
        # Mock history with empty operations
        history_data = {}
        enhanced_extractor_with_mocks.mock_history_manager.load_history.return_value = history_data

        result = enhanced_extractor_with_mocks.undo_last_operation(tmp_path)

        assert result["status"] == "no_history"
        assert result["restored"] == 0

    def test_undo_restores_deduplicated_file_by_copying(self, enhanced_extractor_with_mocks, tmp_path):
        """Deduplicated files are restored by copying from the duplicate source.

        When a file was skipped during extraction because it was a duplicate
        (content_duplicate=True), the undo operation should restore it by
        copying from the file it was a duplicate of (neuer_pfad field).

        The original file no longer exists (was deleted during dedup), so
        the undo must copy from neuer_pfad back to original_pfad.
        """
        # Setup: Create destination directory with the "original" file
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()
        original_file = dest_dir / "original.txt"
        original_file.write_text("test content")

        # Setup: Create empty source directory (file was deleted during dedup)
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # Create history with a deduplicated file entry
        # neuer_pfad points to the file that still exists
        # original_pfad is where it should be restored to
        operations = [
            {
                "original_pfad": str(source_dir / "duplicate.txt"),
                "neuer_pfad": str(original_file),
                "original_name": "duplicate.txt",
                "neuer_name": "original.txt",
                "zeitstempel": "2024-01-01T12:00:00",
                "content_duplicate": True,
                "duplicate_of": str(original_file),  # Reference to the remaining file
            }
        ]

        history_data = {"operationen": operations}
        enhanced_extractor_with_mocks.mock_history_manager.load_history.return_value = history_data

        # Mock ManagedOperation context manager
        mock_operation = Mock()
        mock_operation.abort_signal = enhanced_extractor_with_mocks.abort_signal  # Not set
        mock_operation.update_stats = Mock()
        mock_operation.__enter__ = Mock(return_value=mock_operation)
        mock_operation.__exit__ = Mock(return_value=False)

        # Execute undo - let shutil.copy2 run without mocking
        with patch("folder_extractor.core.extractor.ProgressTracker"):
            with patch(
                "folder_extractor.core.extractor.ManagedOperation",
                return_value=mock_operation,
            ):
                result = enhanced_extractor_with_mocks.undo_last_operation(tmp_path)

        # Verify: The deduplicated file should be restored
        assert result["restored"] == 1, f"Expected 1 restored file, got {result}"
        assert result["errors"] == 0, f"Expected no errors, got {result}"
        assert result["aborted"] is False

        # Critical assertion: The file should exist and have correct content
        restored_file = source_dir / "duplicate.txt"
        assert restored_file.exists(), (
            "Deduplizierte Datei wurde nicht wiederhergestellt"
        )
        assert restored_file.read_text() == "test content", (
            "Dateiinhalt stimmt nicht überein"
        )

        # Verify: The original file in dest should still exist (copied, not moved)
        assert original_file.exists(), "Original file should still exist after copy"

    def test_undo_deduplicated_file_source_deleted(self, enhanced_extractor_with_mocks, tmp_path):
        """Undo gracefully handles missing source file for deduplicated entries.

        When a deduplicated file's source (neuer_pfad) no longer exists,
        the undo operation should report an error but continue processing
        other entries without crashing.
        """
        # Setup: Create empty source directory
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # Setup: dest directory exists but the file does NOT
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()
        # Note: original_file is NOT created - simulating deletion

        # Create history with a deduplicated file entry pointing to missing file
        missing_file_path = str(dest_dir / "deleted_original.txt")
        operations = [
            {
                "original_pfad": str(source_dir / "duplicate.txt"),
                "neuer_pfad": missing_file_path,  # Does not exist!
                "original_name": "duplicate.txt",
                "neuer_name": "deleted_original.txt",
                "zeitstempel": "2024-01-01T12:00:00",
                "content_duplicate": True,
            }
        ]

        history_data = {"operationen": operations}
        enhanced_extractor_with_mocks.mock_history_manager.load_history.return_value = history_data

        # Mock ManagedOperation context manager
        mock_operation = Mock()
        mock_operation.abort_signal = enhanced_extractor_with_mocks.abort_signal
        mock_operation.update_stats = Mock()
        mock_operation.__enter__ = Mock(return_value=mock_operation)
        mock_operation.__exit__ = Mock(return_value=False)

        # Configure move_file mock to raise FileNotFoundError (realistic behavior)
        enhanced_extractor_with_mocks.mock_file_operations.move_file.side_effect = FileNotFoundError(
            f"Source file not found: {missing_file_path}"
        )

        # Execute undo
        with patch("folder_extractor.core.extractor.ProgressTracker"):
            with patch(
                "folder_extractor.core.extractor.ManagedOperation",
                return_value=mock_operation,
            ):
                result = enhanced_extractor_with_mocks.undo_last_operation(tmp_path)

        # Verify: Operation should fail gracefully with error count
        assert result["restored"] == 0, (
            "No files should be restored when source missing"
        )
        assert result["errors"] == 1, "Should report one error for missing source"
        assert result["aborted"] is False, "Should not abort, just report error"

        # The file should NOT exist since source was missing
        restored_file = source_dir / "duplicate.txt"
        assert not restored_file.exists(), (
            "File should not be created when source missing"
        )

    def test_undo_global_duplicate_by_copying(self, enhanced_extractor_with_mocks, tmp_path):
        """Global duplicates are restored by copying, same as content duplicates.

        Files marked with global_duplicate=True should be restored by copying
        from neuer_pfad back to original_pfad, preserving the file at destination.
        """
        # Setup: Create destination directory with the file
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()
        original_file = dest_dir / "global_original.txt"
        original_file.write_text("global duplicate content")

        # Setup: Create empty source directory
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # Create history with a global duplicate entry
        operations = [
            {
                "original_pfad": str(source_dir / "global_dup.txt"),
                "neuer_pfad": str(original_file),
                "original_name": "global_dup.txt",
                "neuer_name": "global_original.txt",
                "zeitstempel": "2024-01-01T12:00:00",
                "global_duplicate": True,  # Global duplicate flag instead of content_duplicate
            }
        ]

        history_data = {"operationen": operations}
        enhanced_extractor_with_mocks.mock_history_manager.load_history.return_value = history_data

        # Mock ManagedOperation context manager
        mock_operation = Mock()
        mock_operation.abort_signal = enhanced_extractor_with_mocks.abort_signal
        mock_operation.update_stats = Mock()
        mock_operation.__enter__ = Mock(return_value=mock_operation)
        mock_operation.__exit__ = Mock(return_value=False)

        # Execute undo
        with patch("folder_extractor.core.extractor.ProgressTracker"):
            with patch(
                "folder_extractor.core.extractor.ManagedOperation",
                return_value=mock_operation,
            ):
                result = enhanced_extractor_with_mocks.undo_last_operation(tmp_path)

        # Verify: The global duplicate should be restored
        assert result["restored"] == 1, f"Expected 1 restored file, got {result}"
        assert result["errors"] == 0, f"Expected no errors, got {result}"

        # Critical assertion: The file should exist with correct content
        restored_file = source_dir / "global_dup.txt"
        assert restored_file.exists(), "Global duplicate should be restored"
        assert restored_file.read_text() == "global duplicate content", (
            "Content should match original"
        )

        # Verify: Original file at dest should still exist (copied, not moved)
        assert original_file.exists(), "Original should still exist after copy"

    def test_undo_duplicate_updates_progress_correctly(self, enhanced_extractor_with_mocks, tmp_path):
        """Progress is correctly tracked for mixed entries (normal + duplicates).

        When undoing a history with a mix of normal files and duplicates,
        the ProgressTracker.increment should be called once per entry,
        and ManagedOperation.update_stats should receive correct values.
        """
        # Setup: Create test directories and files
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()

        # Create files that exist in dest (for undo to work)
        normal_file = dest_dir / "normal.txt"
        normal_file.write_text("normal content")

        content_dup_source = dest_dir / "content_original.txt"
        content_dup_source.write_text("content duplicate")

        global_dup_source = dest_dir / "global_original.txt"
        global_dup_source.write_text("global duplicate")

        # Create history with 3 entries: 1 normal, 1 content_duplicate, 1 global_duplicate
        operations = [
            {
                "original_pfad": str(source_dir / "normal_restored.txt"),
                "neuer_pfad": str(normal_file),
                "original_name": "normal_restored.txt",
                "neuer_name": "normal.txt",
                "zeitstempel": "2024-01-01T12:00:00",
            },
            {
                "original_pfad": str(source_dir / "content_dup_restored.txt"),
                "neuer_pfad": str(content_dup_source),
                "original_name": "content_dup_restored.txt",
                "neuer_name": "content_original.txt",
                "zeitstempel": "2024-01-01T12:00:01",
                "content_duplicate": True,
            },
            {
                "original_pfad": str(source_dir / "global_dup_restored.txt"),
                "neuer_pfad": str(global_dup_source),
                "original_name": "global_dup_restored.txt",
                "neuer_name": "global_original.txt",
                "zeitstempel": "2024-01-01T12:00:02",
                "global_duplicate": True,
            },
        ]

        history_data = {"operationen": operations}
        enhanced_extractor_with_mocks.mock_history_manager.load_history.return_value = history_data

        # Mock ManagedOperation context manager to track update_stats calls
        mock_operation = Mock()
        mock_operation.abort_signal = enhanced_extractor_with_mocks.abort_signal
        mock_operation.update_stats = Mock()
        mock_operation.__enter__ = Mock(return_value=mock_operation)
        mock_operation.__exit__ = Mock(return_value=False)

        # Execute undo with mocked ProgressTracker
        with patch("folder_extractor.core.extractor.ProgressTracker") as MockProgress:
            mock_progress = MockProgress.return_value

            with patch(
                "folder_extractor.core.extractor.ManagedOperation",
                return_value=mock_operation,
            ):
                result = enhanced_extractor_with_mocks.undo_last_operation(tmp_path)

        # Verify all 3 files restored successfully
        assert result["restored"] == 3, f"Expected 3 restored, got {result}"
        assert result["errors"] == 0, f"Expected 0 errors, got {result}"

        # Verify ProgressTracker.increment called 3 times (once per entry)
        assert mock_progress.increment.call_count == 3, (
            f"Expected 3 increment calls, got {mock_progress.increment.call_count}"
        )

        # Verify ManagedOperation.update_stats called 3 times with success values
        assert mock_operation.update_stats.call_count == 3, (
            f"Expected 3 update_stats calls, got {mock_operation.update_stats.call_count}"
        )

        # Each call should report files_processed=1 and files_moved=1 (success)
        for call in mock_operation.update_stats.call_args_list:
            kwargs = call.kwargs if call.kwargs else {}
            # Allow positional or keyword args
            if kwargs:
                assert kwargs.get("files_processed") == 1
                assert kwargs.get("files_moved") == 1
            else:
                # Positional args
                args = call.args if call.args else ()
                assert len(args) == 0 or args == ()

    def test_undo_duplicate_respects_abort_signal_mid_operation(self, enhanced_extractor_with_mocks, tmp_path):
        """Undo stops processing after abort signal is set during duplicate restore.

        When the abort signal is set during the copy operation for a duplicate,
        the undo loop should break and only partially restore files.
        """
        # Setup: Create test directories and source files
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()

        # Create 3 source files that would be copied
        file1 = dest_dir / "file1.txt"
        file1.write_text("content 1")
        file2 = dest_dir / "file2.txt"
        file2.write_text("content 2")
        file3 = dest_dir / "file3.txt"
        file3.write_text("content 3")

        # Create history with 3 content_duplicate entries
        operations = [
            {
                "original_pfad": str(source_dir / "dup1.txt"),
                "neuer_pfad": str(file1),
                "original_name": "dup1.txt",
                "neuer_name": "file1.txt",
                "zeitstempel": "2024-01-01T12:00:00",
                "content_duplicate": True,
            },
            {
                "original_pfad": str(source_dir / "dup2.txt"),
                "neuer_pfad": str(file2),
                "original_name": "dup2.txt",
                "neuer_name": "file2.txt",
                "zeitstempel": "2024-01-01T12:00:01",
                "content_duplicate": True,
            },
            {
                "original_pfad": str(source_dir / "dup3.txt"),
                "neuer_pfad": str(file3),
                "original_name": "dup3.txt",
                "neuer_name": "file3.txt",
                "zeitstempel": "2024-01-01T12:00:02",
                "content_duplicate": True,
            },
        ]

        history_data = {"operationen": operations}
        enhanced_extractor_with_mocks.mock_history_manager.load_history.return_value = history_data

        # Mock ManagedOperation - abort signal NOT set initially
        mock_operation = Mock()
        mock_operation.abort_signal = enhanced_extractor_with_mocks.abort_signal
        mock_operation.update_stats = Mock()
        mock_operation.__enter__ = Mock(return_value=mock_operation)
        mock_operation.__exit__ = Mock(return_value=False)

        # Track copy2 calls and set abort after first successful copy
        copy_call_count = [0]
        original_copy2 = __import__("shutil").copy2

        def copy2_with_abort(src, dst):
            result = original_copy2(src, dst)
            copy_call_count[0] += 1
            if copy_call_count[0] == 1:
                # Set abort signal after first copy completes
                enhanced_extractor_with_mocks.abort_signal.set()
            return result

        # Execute undo
        with patch("folder_extractor.core.extractor.ProgressTracker"):
            with patch(
                "folder_extractor.core.extractor.ManagedOperation",
                return_value=mock_operation,
            ):
                with patch("shutil.copy2", side_effect=copy2_with_abort):
                    result = enhanced_extractor_with_mocks.undo_last_operation(tmp_path)

        # Verify: Only 1 file should be restored before abort
        assert result["restored"] == 1, (
            f"Expected 1 restored (abort after first), got {result}"
        )
        assert result["aborted"] is True, "Should report aborted=True"
        assert result["errors"] == 0, "No errors, just aborted"

        # Verify: Only the first file (processed in reverse order: dup3) should exist
        # Operations are processed in REVERSE, so dup3 is first
        assert (source_dir / "dup3.txt").exists(), (
            "First (reversed) file should be restored"
        )
        assert not (source_dir / "dup2.txt").exists(), (
            "Second file should NOT be restored"
        )
        assert not (source_dir / "dup1.txt").exists(), (
            "Third file should NOT be restored"
        )

    def test_extract_files_dry_run_no_history(self, enhanced_extractor_with_mocks, settings_fixture, tmp_path):
        """Test that history is not saved in dry run mode."""
        # Setup
        files = [str(tmp_path / "file.txt")]
        destination = tmp_path / "dest"
        destination.mkdir()

        settings_fixture.set("dry_run", True)

        # Mock FileMover behavior
        with patch("folder_extractor.core.extractor.FileMover") as MockFileMover:
            mock_mover = MockFileMover.return_value
            mock_mover.move_files.return_value = (1, 0, 0, 0, 0, [])

            # Mock ProgressTracker
            with patch("folder_extractor.core.extractor.ProgressTracker"):
                # Execute extraction
                enhanced_extractor_with_mocks.extract_files(files, destination)

        # Verify history was NOT saved in dry run
        enhanced_extractor_with_mocks.mock_history_manager.save_history.assert_not_called()

    def test_extract_files_no_history_when_no_files_moved(self, enhanced_extractor_with_mocks, settings_fixture, tmp_path):
        """Test that history is not saved when no files were moved."""
        # Setup
        files = [str(tmp_path / "file.txt")]
        destination = tmp_path / "dest"
        destination.mkdir()

        # Mock FileMover to return 0 moved files
        with patch("folder_extractor.core.extractor.FileMover") as MockFileMover:
            mock_mover = MockFileMover.return_value
            mock_mover.move_files.return_value = (0, 0, 0, 0, 0, [])

            # Mock ProgressTracker
            with patch("folder_extractor.core.extractor.ProgressTracker"):
                # Execute extraction
                result = enhanced_extractor_with_mocks.extract_files(files, destination)

        # Verify history was NOT saved when no files moved
        enhanced_extractor_with_mocks.mock_history_manager.save_history.assert_not_called()
        assert result["moved"] == 0

    def test_extract_files_sort_by_type_mode(self, enhanced_extractor_with_mocks, settings_fixture, tmp_path):
        """Test extraction in sort by type mode."""
        # Setup
        files = [str(tmp_path / "file.txt")]
        destination = tmp_path / "dest"
        destination.mkdir()

        settings_fixture.set("sort_by_type", True)

        # Mock FileMover behavior for sorted mode
        with patch("folder_extractor.core.extractor.FileMover") as MockFileMover:
            mock_mover = MockFileMover.return_value
            history = [
                {
                    "original_pfad": files[0],
                    "neuer_pfad": str(destination / "TXT" / "file.txt"),
                }
            ]
            mock_mover.move_files_sorted.return_value = (
                1,
                0,
                0,
                0,
                0,
                history,
                ["TXT"],
            )

            # Mock ProgressTracker
            with patch("folder_extractor.core.extractor.ProgressTracker"):
                # Execute extraction
                result = enhanced_extractor_with_mocks.extract_files(files, destination)

        # Verify sort by type was used
        mock_mover.move_files_sorted.assert_called_once()
        assert result["created_folders"] == ["TXT"]

    def test_extract_files_updates_operation_stats(self, enhanced_extractor_with_mocks, settings_fixture, tmp_path):
        """Test that operation stats are updated via state manager."""
        # Setup - set file_type_filter to avoid triggering empty directory removal
        settings_fixture.set("file_type_filter", [".txt"])

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
            mock_mover.move_files.return_value = (1, 0, 0, 0, 0, history)

            # Mock ProgressTracker and capture callback
            with patch("folder_extractor.core.extractor.ProgressTracker"):
                # Execute extraction with operation_id
                enhanced_extractor_with_mocks.extract_files(
                    files, destination, operation_id=operation_id
                )

        # Verify state manager methods were called
        enhanced_extractor_with_mocks.mock_state_manager.get_abort_signal.assert_called()
        # Note: update_operation_stats is called via progress callback,
        # which is complex to verify without actually triggering it


class TestEnhancedFileExtractorIntegration:
    """Integration tests with minimal mocking."""

    def test_remove_empty_directories_complete_workflow(self, enhanced_extractor_with_mocks, tmp_path):
        """Integration test for complete empty directory removal workflow."""
        # Create complex directory structure
        (tmp_path / "level1" / "level2" / "level3").mkdir(parents=True)
        (tmp_path / "level1" / "level2_with_file").mkdir(parents=True)
        (tmp_path / "level1" / "level2_with_file" / "file.txt").write_text("content")
        (tmp_path / "empty_at_root").mkdir()

        # Remove empty directories
        temp_files = [".DS_Store", ".gitkeep"]
        result = enhanced_extractor_with_mocks._remove_empty_directories(tmp_path, temp_files)

        # Verify correct directories were removed
        # level3, level2, level1 (eventually), empty_at_root should be removed
        # level2_with_file and its parent should remain
        assert result["removed"] >= 2  # At least level3 and empty_at_root
        assert not (tmp_path / "empty_at_root").exists()
        assert (tmp_path / "level1" / "level2_with_file").exists()
        assert (tmp_path / "level1" / "level2_with_file" / "file.txt").exists()


@pytest.fixture
def orchestrator_with_mocks(settings_fixture):
    """Create EnhancedExtractionOrchestrator with mocked dependencies."""
    mock_extractor = Mock()
    mock_state_manager = Mock()

    orchestrator = EnhancedExtractionOrchestrator(
        extractor=mock_extractor, state_manager=mock_state_manager
    )

    # Attach mocks to orchestrator for test access
    orchestrator.mock_extractor = mock_extractor
    orchestrator.mock_state_manager = mock_state_manager

    return orchestrator


class TestEnhancedExtractionOrchestrator:
    """Test EnhancedExtractionOrchestrator class."""

    @pytest.mark.skip(reason="Orchestrator no longer creates default state_manager - accepts None")
    def test_init_with_default_state_manager(self, orchestrator_with_mocks, settings_fixture):
        """Test __init__ creates default state manager (lines 357-358)."""
        # NOTE: This functionality was removed - orchestrator now accepts Optional state_manager
        # Create orchestrator without state manager
        orchestrator = EnhancedExtractionOrchestrator(extractor=orchestrator_with_mocks.mock_extractor)
        assert orchestrator.state_manager is None

    def test_execute_extraction_success(self, orchestrator_with_mocks, settings_fixture, tmp_path):
        """Test successful extraction workflow (lines 373-419)."""
        # Setup
        source_path = tmp_path / "source"
        source_path.mkdir()

        files = [str(tmp_path / "file1.txt"), str(tmp_path / "file2.txt")]

        # Configure mocks
        orchestrator_with_mocks.mock_extractor.validate_security.return_value = None
        orchestrator_with_mocks.mock_extractor.discover_files.return_value = files
        orchestrator_with_mocks.mock_extractor.extract_files.return_value = {
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
        orchestrator_with_mocks.mock_state_manager.get_operation_stats.return_value = mock_stats

        with patch(
            "folder_extractor.core.extractor.ManagedOperation",
            return_value=mock_operation,
        ):
            # Execute extraction
            result = orchestrator_with_mocks.execute_extraction(source_path)

        # Verify workflow
        orchestrator_with_mocks.mock_extractor.validate_security.assert_called_once()
        orchestrator_with_mocks.mock_extractor.discover_files.assert_called_once_with(Path(source_path))
        orchestrator_with_mocks.mock_extractor.extract_files.assert_called_once()

        # Verify result
        assert result["status"] == "success"
        assert result["files_found"] == 2
        assert result["moved"] == 2
        assert result["operation_id"] == "test-op-123"
        assert result["duration"] == 1.5
        assert result["success_rate"] == 100.0

    def test_execute_extraction_no_files(self, orchestrator_with_mocks, settings_fixture, tmp_path):
        """Test when no files found (lines 384-389)."""
        # Setup
        source_path = tmp_path / "source"
        source_path.mkdir()

        # Configure mocks
        orchestrator_with_mocks.mock_extractor.validate_security.return_value = None
        orchestrator_with_mocks.mock_extractor.discover_files.return_value = []

        # Mock ManagedOperation
        mock_operation = Mock()
        mock_operation.__enter__ = Mock(return_value=mock_operation)
        mock_operation.__exit__ = Mock(return_value=False)

        with patch(
            "folder_extractor.core.extractor.ManagedOperation",
            return_value=mock_operation,
        ):
            # Execute extraction
            result = orchestrator_with_mocks.execute_extraction(source_path)

        # Verify result
        assert result["status"] == "no_files"
        assert result["message"] == MESSAGES["NO_FILES_FOUND"]
        assert result["files_found"] == 0

        # Verify extract_files was NOT called
        orchestrator_with_mocks.mock_extractor.extract_files.assert_not_called()

    def test_execute_extraction_cancelled(self, orchestrator_with_mocks, settings_fixture, tmp_path):
        """Test when user cancels (lines 392-398)."""
        # Setup
        source_path = tmp_path / "source"
        source_path.mkdir()

        files = [str(tmp_path / "file1.txt")]

        # Configure mocks
        orchestrator_with_mocks.mock_extractor.validate_security.return_value = None
        orchestrator_with_mocks.mock_extractor.discover_files.return_value = files
        orchestrator_with_mocks.mock_extractor.settings.get.return_value = False  # dry_run=False

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
            result = orchestrator_with_mocks.execute_extraction(
                source_path, confirmation_callback=confirmation_callback
            )

        # Verify confirmation was called
        confirmation_callback.assert_called_once_with(len(files))

        # Verify result
        assert result["status"] == "cancelled"
        assert result["message"] == MESSAGES["OPERATION_CANCELLED"]
        assert result["files_found"] == 1

        # Verify extract_files was NOT called
        orchestrator_with_mocks.mock_extractor.extract_files.assert_not_called()

    def test_execute_extraction_dry_run_no_confirmation(self, orchestrator_with_mocks, settings_fixture, tmp_path):
        """Test that confirmation is skipped in dry run mode (line 392)."""
        # Setup
        source_path = tmp_path / "source"
        source_path.mkdir()

        files = [str(tmp_path / "file1.txt")]

        # Enable dry run
        settings_fixture.set("dry_run", True)

        # Configure mocks
        orchestrator_with_mocks.mock_extractor.validate_security.return_value = None
        orchestrator_with_mocks.mock_extractor.discover_files.return_value = files
        orchestrator_with_mocks.mock_extractor.extract_files.return_value = {
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

        orchestrator_with_mocks.mock_state_manager.get_operation_stats.return_value = None

        # Create confirmation callback that should NOT be called
        confirmation_callback = Mock(return_value=False)

        with patch(
            "folder_extractor.core.extractor.ManagedOperation",
            return_value=mock_operation,
        ):
            # Execute extraction with confirmation callback in dry run mode
            result = orchestrator_with_mocks.execute_extraction(
                source_path, confirmation_callback=confirmation_callback
            )

        # Verify confirmation was NOT called in dry run
        confirmation_callback.assert_not_called()

        # Verify extract_files WAS called
        orchestrator_with_mocks.mock_extractor.extract_files.assert_called_once()

        # Verify result
        assert result["status"] == "success"

    def test_execute_extraction_security_error(self, orchestrator_with_mocks, settings_fixture, tmp_path):
        """Test SecurityError handling (lines 421-426)."""
        # Setup
        source_path = tmp_path / "source"
        source_path.mkdir()

        # Configure mock to raise SecurityError
        error_message = "Unsicherer Pfad"
        orchestrator_with_mocks.mock_extractor.validate_security.side_effect = SecurityError(error_message)

        # Mock ManagedOperation
        mock_operation = Mock()
        mock_operation.__enter__ = Mock(return_value=mock_operation)
        mock_operation.__exit__ = Mock(return_value=False)

        with patch(
            "folder_extractor.core.extractor.ManagedOperation",
            return_value=mock_operation,
        ):
            # Execute extraction
            result = orchestrator_with_mocks.execute_extraction(source_path)

        # Verify result
        assert result["status"] == "security_error"
        assert result["message"] == error_message
        assert result["error"] is True

        # Verify subsequent steps were NOT called
        orchestrator_with_mocks.mock_extractor.discover_files.assert_not_called()
        orchestrator_with_mocks.mock_extractor.extract_files.assert_not_called()

    def test_execute_extraction_generic_error(self, orchestrator_with_mocks, settings_fixture, tmp_path):
        """Test generic Exception handling (lines 428-433)."""
        # Setup
        source_path = tmp_path / "source"
        source_path.mkdir()

        # Configure mock to raise generic exception
        error_message = "Unexpected error"
        orchestrator_with_mocks.mock_extractor.validate_security.side_effect = Exception(error_message)

        # Mock ManagedOperation
        mock_operation = Mock()
        mock_operation.__enter__ = Mock(return_value=mock_operation)
        mock_operation.__exit__ = Mock(return_value=False)

        with patch(
            "folder_extractor.core.extractor.ManagedOperation",
            return_value=mock_operation,
        ):
            # Execute extraction
            result = orchestrator_with_mocks.execute_extraction(source_path)

        # Verify result
        assert result["status"] == "error"
        assert f"Fehler: {error_message}" in result["message"]
        assert result["error"] is True

        # Verify subsequent steps were NOT called
        orchestrator_with_mocks.mock_extractor.discover_files.assert_not_called()
        orchestrator_with_mocks.mock_extractor.extract_files.assert_not_called()

    def test_execute_extraction_error_during_discovery(self, orchestrator_with_mocks, settings_fixture, tmp_path):
        """Test error handling during file discovery phase."""
        # Setup
        source_path = tmp_path / "source"
        source_path.mkdir()

        # Configure mocks
        orchestrator_with_mocks.mock_extractor.validate_security.return_value = None
        orchestrator_with_mocks.mock_extractor.discover_files.side_effect = Exception("Discovery failed")

        # Mock ManagedOperation
        mock_operation = Mock()
        mock_operation.__enter__ = Mock(return_value=mock_operation)
        mock_operation.__exit__ = Mock(return_value=False)

        with patch(
            "folder_extractor.core.extractor.ManagedOperation",
            return_value=mock_operation,
        ):
            # Execute extraction
            result = orchestrator_with_mocks.execute_extraction(source_path)

        # Verify result
        assert result["status"] == "error"
        assert "Fehler: Discovery failed" in result["message"]
        assert result["error"] is True

    def test_execute_extraction_with_progress_callback(self, orchestrator_with_mocks, settings_fixture, tmp_path):
        """Test extraction with progress callback."""
        # Setup
        source_path = tmp_path / "source"
        source_path.mkdir()

        files = [str(tmp_path / "file1.txt")]

        # Configure mocks
        orchestrator_with_mocks.mock_extractor.validate_security.return_value = None
        orchestrator_with_mocks.mock_extractor.discover_files.return_value = files
        orchestrator_with_mocks.mock_extractor.extract_files.return_value = {
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

        orchestrator_with_mocks.mock_state_manager.get_operation_stats.return_value = None

        # Create progress callback
        progress_callback = Mock()

        with patch(
            "folder_extractor.core.extractor.ManagedOperation",
            return_value=mock_operation,
        ):
            # Execute extraction with progress callback
            orchestrator_with_mocks.execute_extraction(
                source_path, progress_callback=progress_callback
            )

        # Verify extract_files was called with progress callback
        call_args = orchestrator_with_mocks.mock_extractor.extract_files.call_args
        assert call_args[0][2] == "test-op-123"  # operation_id
        assert call_args[0][3] == progress_callback  # progress_callback

    def test_execute_undo(self, orchestrator_with_mocks, tmp_path):
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
        orchestrator_with_mocks.mock_extractor.undo_last_operation.return_value = expected_result

        # Execute undo
        result = orchestrator_with_mocks.execute_undo(path)

        # Verify extractor method was called
        orchestrator_with_mocks.mock_extractor.undo_last_operation.assert_called_once_with(Path(path))

        # Verify result is passed through
        assert result == expected_result



class TestProcessSingleFile:
    """Test process_single_file method for watch mode single-file processing."""

    def test_process_single_file_skips_discovery(self, orchestrator_with_mocks, tmp_path):
        """Processing a single file bypasses file discovery entirely."""
        # Setup
        filepath = tmp_path / "new_file.pdf"
        filepath.touch()
        destination = tmp_path

        # Configure mocks
        orchestrator_with_mocks.mock_extractor.validate_security.return_value = None
        orchestrator_with_mocks.mock_extractor.extract_files.return_value = {
            "moved": 1,
            "errors": 0,
            "history": [],
        }

        # Mock ManagedOperation with abort signal
        mock_operation = Mock()
        mock_operation.operation_id = "single-file-op"
        mock_abort_signal = Mock()
        mock_abort_signal.is_set.return_value = False
        mock_operation.abort_signal = mock_abort_signal
        mock_operation.__enter__ = Mock(return_value=mock_operation)
        mock_operation.__exit__ = Mock(return_value=False)

        with patch(
            "folder_extractor.core.extractor.ManagedOperation",
            return_value=mock_operation,
        ):
            result = orchestrator_with_mocks.process_single_file(filepath, destination)

        # Verify discovery was NOT called
        orchestrator_with_mocks.mock_extractor.discover_files.assert_not_called()

        # Verify extract_files was called with just the single file
        orchestrator_with_mocks.mock_extractor.extract_files.assert_called_once()
        call_kwargs = orchestrator_with_mocks.mock_extractor.extract_files.call_args[1]
        assert call_kwargs.get("files") == [str(filepath)]

        # Verify result
        assert result["status"] == "success"
        assert result["moved"] == 1

    def test_process_single_file_validates_security(self, orchestrator_with_mocks, tmp_path):
        """Security validation is performed before processing."""
        filepath = tmp_path / "file.txt"
        filepath.touch()

        # Configure mock to raise security error
        orchestrator_with_mocks.mock_extractor.validate_security.side_effect = SecurityError("Unsafe path")

        # Mock ManagedOperation
        mock_operation = Mock()
        mock_operation.__enter__ = Mock(return_value=mock_operation)
        mock_operation.__exit__ = Mock(return_value=False)

        with patch(
            "folder_extractor.core.extractor.ManagedOperation",
            return_value=mock_operation,
        ):
            result = orchestrator_with_mocks.process_single_file(filepath, tmp_path)

        assert result["status"] == "security_error"
        assert "Unsafe path" in result["message"]

    def test_process_single_file_respects_abort_signal(self, orchestrator_with_mocks, tmp_path):
        """Abort signal from state_manager is checked before processing."""
        filepath = tmp_path / "file.txt"
        filepath.touch()

        # Configure mocks
        orchestrator_with_mocks.mock_extractor.validate_security.return_value = None

        # Mock ManagedOperation with abort signal set
        mock_operation = Mock()
        mock_operation.operation_id = "abort-test"
        mock_abort_signal = Mock()
        mock_abort_signal.is_set.return_value = True
        mock_operation.abort_signal = mock_abort_signal
        mock_operation.__enter__ = Mock(return_value=mock_operation)
        mock_operation.__exit__ = Mock(return_value=False)

        with patch(
            "folder_extractor.core.extractor.ManagedOperation",
            return_value=mock_operation,
        ):
            result = orchestrator_with_mocks.process_single_file(filepath, tmp_path)

        # Extract files should not be called when abort is requested
        orchestrator_with_mocks.mock_extractor.extract_files.assert_not_called()
        assert result["status"] == "aborted"

    def test_process_single_file_handles_nonexistent_file(self, orchestrator_with_mocks, tmp_path):
        """Gracefully handles attempt to process a file that doesn't exist."""
        filepath = tmp_path / "nonexistent.txt"

        # Configure mocks
        orchestrator_with_mocks.mock_extractor.validate_security.return_value = None

        # Mock ManagedOperation
        mock_operation = Mock()
        mock_operation.operation_id = "missing-file-op"
        mock_abort_signal = Mock()
        mock_abort_signal.is_set.return_value = False
        mock_operation.abort_signal = mock_abort_signal
        mock_operation.__enter__ = Mock(return_value=mock_operation)
        mock_operation.__exit__ = Mock(return_value=False)

        with patch(
            "folder_extractor.core.extractor.ManagedOperation",
            return_value=mock_operation,
        ):
            result = orchestrator_with_mocks.process_single_file(filepath, tmp_path)

        # Should return error status, not crash
        assert result["status"] == "error"
        assert (
            "existiert nicht" in result["message"]
            or "not exist" in result["message"].lower()
        )

    def test_process_single_file_passes_progress_callback(self, orchestrator_with_mocks, tmp_path):
        """Progress callback is forwarded to extract_files."""
        filepath = tmp_path / "file.pdf"
        filepath.touch()

        # Configure mocks
        orchestrator_with_mocks.mock_extractor.validate_security.return_value = None
        orchestrator_with_mocks.mock_extractor.extract_files.return_value = {"moved": 1, "errors": 0}

        progress_callback = Mock()

        # Mock ManagedOperation
        mock_operation = Mock()
        mock_operation.operation_id = "progress-test"
        mock_abort_signal = Mock()
        mock_abort_signal.is_set.return_value = False
        mock_operation.abort_signal = mock_abort_signal
        mock_operation.__enter__ = Mock(return_value=mock_operation)
        mock_operation.__exit__ = Mock(return_value=False)

        with patch(
            "folder_extractor.core.extractor.ManagedOperation",
            return_value=mock_operation,
        ):
            orchestrator_with_mocks.process_single_file(
                filepath, tmp_path, progress_callback=progress_callback
            )

        # Verify progress_callback was passed to extract_files
        call_kwargs = orchestrator_with_mocks.mock_extractor.extract_files.call_args[1]
        assert call_kwargs.get("progress_callback") == progress_callback
