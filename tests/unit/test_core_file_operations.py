"""
Unit tests for the core file operations module.
"""

import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from folder_extractor.core.file_operations import (
    FileMover,
    FileOperationError,
    FileOperations,
    HistoryManager,
)


class TestFileOperations:
    """Test FileOperations class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.file_ops = FileOperations()

    def test_generate_unique_name_no_conflict(self):
        """Test unique name generation when no conflict."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            # Test with Path object
            name = self.file_ops.generate_unique_name(temp_path, "test.txt")
            assert name == "test.txt"

    def test_generate_unique_name_with_conflicts(self):
        """Test unique name generation with existing files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            # Create existing files
            (temp_path / "test.txt").touch()
            (temp_path / "test_1.txt").touch()

            # Test with Path object
            name = self.file_ops.generate_unique_name(temp_path, "test.txt")
            assert name == "test_2.txt"

    def test_generate_unique_name_no_extension(self):
        """Test unique name for files without extension."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "README").touch()

            # Test with Path object
            name = self.file_ops.generate_unique_name(temp_path, "README")
            assert name == "README_1"

    def test_generate_unique_name_with_string(self):
        """Test unique name generation with string path (backward compatibility)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with string (backward compatibility)
            name = self.file_ops.generate_unique_name(temp_dir, "test.txt")
            assert name == "test.txt"

    def test_move_file_success(self):
        """Test successful file move."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            # Create source file
            source = temp_path / "source.txt"
            source.write_text("content")

            # Move file - using Path objects directly
            dest = temp_path / "dest.txt"
            result = self.file_ops.move_file(source, dest)

            assert result is True
            assert not source.exists()
            assert dest.exists()
            assert dest.read_text() == "content"

    def test_move_file_dry_run(self):
        """Test file move in dry run mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source = temp_path / "source.txt"
            source.write_text("content")

            dest = temp_path / "dest.txt"
            result = self.file_ops.move_file(source, dest, dry_run=True)

            assert result is True
            assert source.exists()  # File should still exist
            assert not dest.exists()

    def test_move_file_cross_filesystem(self):
        """Test file move across filesystems (simulated)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source = temp_path / "source.txt"
            source.write_text("content")
            dest = temp_path / "dest.txt"

            # Mock Path.rename to fail, forcing copy+delete
            with patch.object(Path, "rename", side_effect=OSError):
                result = self.file_ops.move_file(source, dest)

                assert result is True
                assert not source.exists()
                assert dest.exists()
                assert dest.read_text() == "content"

    def test_move_file_with_string(self):
        """Test file move with string paths (backward compatibility)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source = temp_path / "source.txt"
            source.write_text("content")

            # Move file using strings
            dest_str = str(temp_path / "dest.txt")
            result = self.file_ops.move_file(str(source), dest_str)

            assert result is True
            assert not source.exists()
            assert Path(dest_str).exists()

    def test_move_file_mixed_types(self):
        """Test file move with mixed Path and str arguments."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source = temp_path / "source.txt"
            source.write_text("content")

            # Move file using Path source and str destination
            dest = temp_path / "dest.txt"
            result = self.file_ops.move_file(source, str(dest))

            assert result is True
            assert not source.exists()
            assert dest.exists()

    def test_move_file_copy_failure_raises_error(self):
        """Test that FileOperationError is raised when copy fails after rename fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source = temp_path / "source.txt"
            source.write_text("content")
            dest = temp_path / "dest.txt"

            # Mock Path.rename to fail (simulating cross-filesystem)
            # AND shutil.copy2 to fail
            with patch.object(Path, "rename", side_effect=OSError), patch(
                "shutil.copy2", side_effect=PermissionError("No permission")
            ):
                with pytest.raises(FileOperationError) as exc_info:
                    self.file_ops.move_file(source, dest)

                assert "Failed to move file" in str(exc_info.value)

    def test_determine_type_folder_known_types(self):
        """Test folder determination for known file types."""
        assert self.file_ops.determine_type_folder("document.pdf") == "PDF"
        assert self.file_ops.determine_type_folder("script.py") == "PYTHON"
        assert self.file_ops.determine_type_folder("IMAGE.JPG") == "JPEG"
        assert self.file_ops.determine_type_folder("page.html") == "HTML"

    def test_determine_type_folder_unknown_type(self):
        """Test folder determination for unknown file types."""
        assert self.file_ops.determine_type_folder("file.xyz") == "XYZ"
        assert self.file_ops.determine_type_folder("data.custom") == "CUSTOM"

    def test_determine_type_folder_no_extension(self):
        """Test folder determination for files without extension."""
        assert self.file_ops.determine_type_folder("README") == "OHNE_ERWEITERUNG"
        assert self.file_ops.determine_type_folder("Makefile") == "OHNE_ERWEITERUNG"

    def test_determine_type_folder_with_path(self):
        """Test folder determination with Path object."""
        assert self.file_ops.determine_type_folder(Path("document.pdf")) == "PDF"
        assert self.file_ops.determine_type_folder(Path("script.py")) == "PYTHON"
        assert self.file_ops.determine_type_folder(Path("/some/path/file.xyz")) == "XYZ"

    def test_remove_empty_directories(self):
        """Test removing empty directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            # Create empty directories
            (temp_path / "empty1").mkdir()
            (temp_path / "empty2" / "nested").mkdir(parents=True)

            # Create non-empty directory
            non_empty = temp_path / "non_empty"
            non_empty.mkdir()
            (non_empty / "file.txt").touch()

            # Test with Path object
            removed = self.file_ops.remove_empty_directories(temp_path)

            assert removed >= 3  # empty1, empty2, nested
            assert not (temp_path / "empty1").exists()
            assert not (temp_path / "empty2").exists()
            assert non_empty.exists()

    def test_remove_empty_directories_with_string(self):
        """Test removing empty directories with string path (backward compatibility)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            # Create empty directory
            (temp_path / "empty").mkdir()

            # Test with string (backward compatibility)
            removed = self.file_ops.remove_empty_directories(temp_dir)

            assert removed == 1
            assert not (temp_path / "empty").exists()

    def test_remove_empty_directories_with_hidden(self):
        """Test removing directories with hidden files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            # Directory with hidden file
            hidden_dir = temp_path / "hidden_dir"
            hidden_dir.mkdir()
            (hidden_dir / ".hidden").touch()

            # Without include_hidden - should remove
            removed = self.file_ops.remove_empty_directories(
                temp_path, include_hidden=False
            )
            assert removed == 1
            assert not hidden_dir.exists()

            # Recreate
            hidden_dir.mkdir()
            (hidden_dir / ".hidden").touch()

            # With include_hidden - should keep
            removed = self.file_ops.remove_empty_directories(
                temp_path, include_hidden=True
            )
            assert removed == 0
            assert hidden_dir.exists()

    def test_remove_empty_directories_permission_error(self):
        """Test that PermissionError is caught and directory is skipped."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            # Create empty directory
            empty_dir = temp_path / "empty_dir"
            empty_dir.mkdir()

            # Mock iterdir to raise PermissionError for the empty_dir
            original_iterdir = Path.iterdir

            def mock_iterdir(self):
                if self == empty_dir:
                    raise PermissionError("Access denied")
                return original_iterdir(self)

            with patch.object(Path, "iterdir", mock_iterdir):
                removed = self.file_ops.remove_empty_directories(temp_path)

                # Inaccessible directory is skipped, not deleted
                assert removed == 0
                assert empty_dir.exists()

    def test_remove_empty_directories_with_hidden_subdir(self):
        """Test removing directories with hidden subdirectories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            # Directory with hidden subdirectory (not just hidden file)
            parent_dir = temp_path / "parent_dir"
            parent_dir.mkdir()
            hidden_subdir = parent_dir / ".hidden_dir"
            hidden_subdir.mkdir()

            # Without include_hidden - should remove hidden subdir and parent
            removed = self.file_ops.remove_empty_directories(
                temp_path, include_hidden=False
            )
            assert removed == 2  # Both hidden_subdir and parent_dir
            assert not parent_dir.exists()

    def test_remove_empty_directories_with_hidden_subdir_containing_files(self):
        """Test removing directories with hidden subdirectories that contain files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            # Directory with hidden subdirectory containing files
            parent_dir = temp_path / "parent_dir"
            parent_dir.mkdir()
            hidden_subdir = parent_dir / ".hidden_dir"
            hidden_subdir.mkdir()
            # Add a file inside the hidden subdir - this forces shutil.rmtree to be used
            (hidden_subdir / "file.txt").write_text("content")

            # Without include_hidden - should remove hidden subdir (with rmtree) and parent
            removed = self.file_ops.remove_empty_directories(
                temp_path, include_hidden=False
            )
            assert (
                removed == 1
            )  # Only parent_dir (hidden subdir is removed via rmtree, not counted)
            assert not parent_dir.exists()

    def test_remove_empty_directories_include_hidden_true_empty_dir(self):
        """Test removing empty directory with include_hidden=True (branch 169->177)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            # Create completely empty directory
            empty_dir = temp_path / "empty_dir"
            empty_dir.mkdir()

            # With include_hidden=True, should still remove empty directory
            # This tests the branch 169->177 where we skip hidden file cleanup
            removed = self.file_ops.remove_empty_directories(
                temp_path, include_hidden=True
            )
            assert removed == 1
            assert not empty_dir.exists()

    def test_remove_empty_directories_multiple_hidden_files(self):
        """Test removing directory with multiple hidden files (branch 171->170)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            # Directory with multiple hidden files
            hidden_dir = temp_path / "hidden_dir"
            hidden_dir.mkdir()
            (hidden_dir / ".hidden1").touch()
            (hidden_dir / ".hidden2").touch()
            (hidden_dir / ".hidden3").touch()

            # Without include_hidden - should remove all hidden files and the directory
            # This tests the loop continuation branch 171->170
            removed = self.file_ops.remove_empty_directories(
                temp_path, include_hidden=False
            )
            assert removed == 1
            assert not hidden_dir.exists()

    def test_remove_empty_directories_multiple_hidden_subdirs(self):
        """Test removing directory with multiple hidden subdirectories (branch 174->170)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            # Directory with multiple hidden subdirectories
            parent_dir = temp_path / "parent_dir"
            parent_dir.mkdir()
            (parent_dir / ".hidden_dir1").mkdir()
            (parent_dir / ".hidden_dir2").mkdir()

            # Without include_hidden - should remove all hidden subdirs and the parent
            # This tests the loop continuation after shutil.rmtree (branch 174->170)
            removed = self.file_ops.remove_empty_directories(
                temp_path, include_hidden=False
            )
            # 3 directories: .hidden_dir1, .hidden_dir2, parent_dir
            assert removed == 3
            assert not parent_dir.exists()

    def test_remove_empty_directories_mixed_hidden_content(self):
        """Test removing directory with mixed hidden files and directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            # Directory with both hidden files and hidden subdirectories
            parent_dir = temp_path / "parent_dir"
            parent_dir.mkdir()
            (parent_dir / ".hidden_file").touch()
            (parent_dir / ".hidden_dir").mkdir()
            (parent_dir / ".hidden_dir" / "nested_file.txt").write_text("content")

            # Without include_hidden - should remove everything
            removed = self.file_ops.remove_empty_directories(
                temp_path, include_hidden=False
            )
            # Only parent_dir counted (hidden items cleaned via rmtree/unlink)
            assert removed == 1
            assert not parent_dir.exists()

    def test_remove_empty_directories_skips_files_in_rglob(self):
        """Test that files returned by rglob are properly skipped.

        This ensures coverage of the 'continue' branch when iterating
        over non-directory entries from rglob('*').
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create deeply nested structure with files at various levels
            level1 = temp_path / "level1"
            level2 = level1 / "level2"
            level2.mkdir(parents=True)

            # Create files at different levels
            (temp_path / "root_file.txt").touch()
            (level1 / "level1_file.txt").touch()
            (level2 / "level2_file.txt").touch()

            # Create empty directories that SHOULD be removed
            (temp_path / "empty_dir").mkdir()

            # Call remove_empty_directories - it should skip the files
            # and only remove empty_dir
            removed = self.file_ops.remove_empty_directories(temp_path)

            # Only empty_dir should be removed (not the dirs with files)
            assert removed == 1
            assert not (temp_path / "empty_dir").exists()

            # Directories with files should still exist
            assert level1.exists()
            assert level2.exists()

            # Files should still exist
            assert (temp_path / "root_file.txt").exists()
            assert (level1 / "level1_file.txt").exists()
            assert (level2 / "level2_file.txt").exists()


class TestHistoryManager:
    """Test HistoryManager class."""

    def test_save_and_load_history(self):
        """Test saving and loading history."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            operations = [
                {
                    "original_pfad": "/old/path/file.txt",
                    "neuer_pfad": "/new/path/file.txt",
                    "original_name": "file.txt",
                    "neuer_name": "file.txt",
                    "zeitstempel": "2024-01-01T12:00:00",
                }
            ]

            # Save history with Path object
            history_file = HistoryManager.save_history(operations, temp_path)
            assert Path(history_file).exists()

            # Load history with Path object
            loaded = HistoryManager.load_history(temp_path)
            assert loaded is not None
            assert "operationen" in loaded
            assert len(loaded["operationen"]) == 1
            assert loaded["operationen"][0]["original_pfad"] == "/old/path/file.txt"

    def test_save_and_load_history_with_string(self):
        """Test saving and loading history with string path (backward compatibility)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            operations = [{"test": "data"}]

            # Save history with string
            history_file = HistoryManager.save_history(operations, temp_dir)
            assert Path(history_file).exists()

            # Load history with string
            loaded = HistoryManager.load_history(temp_dir)
            assert loaded is not None

    def test_load_nonexistent_history(self):
        """Test loading when no history exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            loaded = HistoryManager.load_history(temp_path)
            assert loaded is None

    def test_load_corrupted_history(self):
        """Test loading corrupted history file returns None."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            # Create corrupted history file with invalid JSON
            history_file = temp_path / ".folder_extractor_history.json"
            history_file.write_text("{ invalid json }")

            loaded = HistoryManager.load_history(temp_path)
            assert loaded is None

    def test_delete_history(self):
        """Test deleting history file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            # Create history
            HistoryManager.save_history([{"test": "data"}], temp_path)

            # Delete with Path object
            result = HistoryManager.delete_history(temp_path)
            assert result is True

            # Try to load
            loaded = HistoryManager.load_history(temp_path)
            assert loaded is None

            # Delete again - should return False
            result = HistoryManager.delete_history(temp_path)
            assert result is False


class TestFileMover:
    """Test FileMover class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.file_ops = FileOperations()
        self.file_mover = FileMover(self.file_ops)

    def test_move_files_success(self):
        """Test moving multiple files with Path objects."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            # Create test files - use Path objects in list
            files = []
            for i in range(3):
                file_path = source_dir / f"file{i}.txt"
                file_path.write_text(f"content{i}")
                files.append(file_path)  # Path objects directly

            # Move files with Path destination
            moved, errors, duplicates, history = self.file_mover.move_files(
                files, dest_dir
            )

            assert moved == 3
            assert errors == 0
            assert duplicates == 0
            assert len(history) == 3

            # Check files exist in destination
            for i in range(3):
                dest_file = dest_dir / f"file{i}.txt"
                assert dest_file.exists()
                assert dest_file.read_text() == f"content{i}"

    def test_move_files_with_strings(self):
        """Test moving multiple files with string paths (backward compatibility)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            # Create test files - use strings
            files = []
            for i in range(2):
                file_path = source_dir / f"file{i}.txt"
                file_path.write_text(f"content{i}")
                files.append(str(file_path))

            # Move files with string destination
            moved, errors, duplicates, history = self.file_mover.move_files(
                files, str(dest_dir)
            )

            assert moved == 2
            assert errors == 0

    def test_move_files_with_duplicates(self):
        """Test moving files with duplicate names."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            # Create existing file in destination
            (dest_dir / "duplicate.txt").write_text("existing")

            # Create source file with same name
            source_file = source_dir / "duplicate.txt"
            source_file.write_text("new")

            # Move file with Path objects
            moved, errors, duplicates, history = self.file_mover.move_files(
                [source_file], dest_dir
            )

            assert moved == 1
            assert duplicates == 1
            assert (dest_dir / "duplicate_1.txt").exists()
            assert (dest_dir / "duplicate_1.txt").read_text() == "new"

    def test_move_files_with_abort(self):
        """Test aborting file move operation."""
        abort_signal = threading.Event()
        file_mover = FileMover(self.file_ops, abort_signal)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()

            # Create many files - use Path objects
            files = []
            for i in range(100):
                file_path = source_dir / f"file{i}.txt"
                file_path.touch()
                files.append(file_path)

            # Set abort signal
            abort_signal.set()

            # Move files with Path destination
            moved, errors, duplicates, history = file_mover.move_files(files, temp_path)

            # Should have moved very few files
            assert moved < len(files)

    def test_move_files_sorted(self):
        """Test moving files sorted by type with Path objects."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            # Create various file types - use Path objects
            files = []
            test_files = ["document.pdf", "image.jpg", "script.py", "data.json"]

            for filename in test_files:
                file_path = source_dir / filename
                file_path.touch()
                files.append(file_path)

            # Move files sorted with Path destination
            moved, errors, duplicates, history, created_folders = (
                self.file_mover.move_files_sorted(files, dest_dir)
            )

            assert moved == 4
            assert errors == 0
            assert "PDF" in created_folders
            assert "JPEG" in created_folders
            assert "PYTHON" in created_folders
            assert "JSON" in created_folders

            # Check files are in correct folders
            assert (dest_dir / "PDF" / "document.pdf").exists()
            assert (dest_dir / "JPEG" / "image.jpg").exists()
            assert (dest_dir / "PYTHON" / "script.py").exists()
            assert (dest_dir / "JSON" / "data.json").exists()

    def test_move_files_sorted_with_strings(self):
        """Test moving files sorted by type with strings (backward compatibility)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            # Create test file - use string
            file_path = source_dir / "test.pdf"
            file_path.touch()

            # Move files sorted with string paths
            moved, errors, duplicates, history, created_folders = (
                self.file_mover.move_files_sorted([str(file_path)], str(dest_dir))
            )

            assert moved == 1
            assert "PDF" in created_folders

    def test_move_files_with_progress_callback(self):
        """Test progress callback during file move."""
        progress_calls = []

        def progress_callback(current, total, filepath, error=None):
            progress_calls.append(
                {
                    "current": current,
                    "total": total,
                    "filepath": filepath,
                    "error": error,
                }
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            # Create test file
            test_file = temp_path / "test.txt"
            test_file.touch()

            # Move with callback - use Path objects
            self.file_mover.move_files(
                [test_file], temp_path, progress_callback=progress_callback
            )

            assert len(progress_calls) == 1
            assert progress_calls[0]["current"] == 1
            assert progress_calls[0]["total"] == 1
            assert progress_calls[0]["error"] is None

    def test_move_files_with_error(self):
        """Test error handling during file move with callback."""
        progress_calls = []

        def progress_callback(current, total, filepath, error=None):
            progress_calls.append(
                {
                    "current": current,
                    "total": total,
                    "filepath": filepath,
                    "error": error,
                }
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            # Create test file
            test_file = temp_path / "test.txt"
            test_file.touch()

            # Mock move_file to raise exception
            with patch.object(
                self.file_ops, "move_file", side_effect=Exception("Test error")
            ):
                moved, errors, duplicates, history = self.file_mover.move_files(
                    [test_file], dest_dir, progress_callback=progress_callback
                )

            assert moved == 0
            assert errors == 1
            assert len(progress_calls) == 2  # One for progress, one for error
            assert progress_calls[1]["error"] == "Test error"

    def test_move_files_sorted_with_abort(self):
        """Test aborting sorted file move operation."""
        abort_signal = threading.Event()
        file_mover = FileMover(self.file_ops, abort_signal)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            # Create many files
            files = []
            for i in range(100):
                file_path = source_dir / f"file{i}.pdf"
                file_path.touch()
                files.append(file_path)

            # Set abort signal
            abort_signal.set()

            # Move files sorted
            moved, errors, duplicates, history, created_folders = (
                file_mover.move_files_sorted(files, dest_dir)
            )

            # Should have moved very few files
            assert moved < len(files)

    def test_move_files_sorted_with_error(self):
        """Test error handling during sorted file move with callback."""
        progress_calls = []

        def progress_callback(current, total, filepath, error=None):
            progress_calls.append(
                {
                    "current": current,
                    "total": total,
                    "filepath": filepath,
                    "error": error,
                }
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            # Create test file
            test_file = source_dir / "test.pdf"
            test_file.touch()

            # Mock move_file to raise exception
            with patch.object(
                self.file_ops, "move_file", side_effect=Exception("Test error")
            ):
                moved, errors, duplicates, history, created_folders = (
                    self.file_mover.move_files_sorted(
                        [test_file], dest_dir, progress_callback=progress_callback
                    )
                )

            assert moved == 0
            assert errors == 1
            assert progress_calls[-1]["error"] == "Test error"

    def test_move_files_sorted_with_duplicates(self):
        """Test sorted move with duplicate filenames."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            # Create PDF folder with existing file
            pdf_folder = dest_dir / "PDF"
            pdf_folder.mkdir()
            (pdf_folder / "document.pdf").write_text("existing")

            # Create source file with same name
            source_file = source_dir / "document.pdf"
            source_file.write_text("new")

            # Move file sorted
            moved, errors, duplicates, history, created_folders = (
                self.file_mover.move_files_sorted([source_file], dest_dir)
            )

            assert moved == 1
            assert duplicates == 1
            assert (pdf_folder / "document_1.pdf").exists()
            assert (pdf_folder / "document_1.pdf").read_text() == "new"


class TestFileMoverDeduplication:
    """Test FileMover deduplication functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.file_ops = FileOperations()
        self.file_mover = FileMover(self.file_ops)

    def test_move_files_with_deduplicate_identical_content(self):
        """Files with identical content are skipped and source is deleted."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            # Create identical content in both locations
            identical_content = "This is identical content for deduplication test"
            source_file = source_dir / "duplicate.txt"
            source_file.write_text(identical_content)
            dest_file = dest_dir / "duplicate.txt"
            dest_file.write_text(identical_content)

            # Move with deduplication enabled
            moved, errors, duplicates, content_duplicates, history = (
                self.file_mover.move_files([source_file], dest_dir, deduplicate=True)
            )

            # Source should be deleted, not moved (content duplicate)
            assert moved == 0
            assert errors == 0
            assert duplicates == 0
            assert content_duplicates == 1
            assert not source_file.exists()
            # Destination should still have original content
            assert dest_file.exists()
            assert dest_file.read_text() == identical_content

    def test_move_files_with_deduplicate_different_content(self):
        """Files with different content are renamed (normal duplicate handling)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            # Create files with different content but same name
            source_file = source_dir / "file.txt"
            source_file.write_text("source content - different")
            dest_file = dest_dir / "file.txt"
            dest_file.write_text("destination content - different")

            # Move with deduplication enabled
            moved, errors, duplicates, content_duplicates, history = (
                self.file_mover.move_files([source_file], dest_dir, deduplicate=True)
            )

            # Should be renamed since content differs
            assert moved == 1
            assert errors == 0
            assert duplicates == 1  # Name duplicate, renamed
            assert content_duplicates == 0
            assert not source_file.exists()
            assert dest_file.exists()  # Original kept
            assert (dest_dir / "file_1.txt").exists()  # Renamed file
            assert (dest_dir / "file_1.txt").read_text() == "source content - different"

    def test_move_files_deduplicate_disabled_renames_identical_files(self):
        """Without deduplicate flag, identical files are renamed (old behavior)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            identical_content = "identical content"
            source_file = source_dir / "same.txt"
            source_file.write_text(identical_content)
            dest_file = dest_dir / "same.txt"
            dest_file.write_text(identical_content)

            # Move WITHOUT deduplication - old 4-tuple return
            moved, errors, duplicates, history = self.file_mover.move_files(
                [source_file], dest_dir, deduplicate=False
            )

            # Should rename even though content is identical
            assert moved == 1
            assert duplicates == 1
            assert (dest_dir / "same_1.txt").exists()

    def test_move_files_deduplicate_dry_run_preserves_source(self):
        """Dry run with deduplicate does not delete source files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            identical_content = "dry run test content"
            source_file = source_dir / "dryrun.txt"
            source_file.write_text(identical_content)
            dest_file = dest_dir / "dryrun.txt"
            dest_file.write_text(identical_content)

            # Dry run with deduplication
            moved, errors, duplicates, content_duplicates, history = (
                self.file_mover.move_files(
                    [source_file], dest_dir, dry_run=True, deduplicate=True
                )
            )

            # Source should still exist (dry run)
            assert source_file.exists()
            assert content_duplicates == 1
            # No history recorded in dry run
            assert len(history) == 0

    def test_move_files_deduplicate_history_entry_has_flag(self):
        """History entries for content duplicates have content_duplicate flag."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            identical_content = "history flag test"
            source_file = source_dir / "flagtest.txt"
            source_file.write_text(identical_content)
            dest_file = dest_dir / "flagtest.txt"
            dest_file.write_text(identical_content)

            moved, errors, duplicates, content_duplicates, history = (
                self.file_mover.move_files([source_file], dest_dir, deduplicate=True)
            )

            # History should record the content duplicate
            assert len(history) == 1
            assert history[0].get("content_duplicate") is True
            assert history[0]["original_pfad"] == str(source_file)

    def test_move_files_sorted_with_deduplicate_identical(self):
        """Sorted move with deduplicate skips identical content files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            # Create PDF folder with existing file
            pdf_folder = dest_dir / "PDF"
            pdf_folder.mkdir()
            identical_content = "PDF content for dedup test"
            (pdf_folder / "document.pdf").write_text(identical_content)

            # Create source file with identical content
            source_file = source_dir / "document.pdf"
            source_file.write_text(identical_content)

            # Move sorted with deduplication
            moved, errors, duplicates, content_duplicates, history, created_folders = (
                self.file_mover.move_files_sorted(
                    [source_file], dest_dir, deduplicate=True
                )
            )

            assert moved == 0
            assert content_duplicates == 1
            assert not source_file.exists()
            # Original in PDF folder unchanged
            assert (pdf_folder / "document.pdf").read_text() == identical_content

    def test_move_files_sorted_with_deduplicate_different_content(self):
        """Sorted move with deduplicate renames files with different content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            # Create PDF folder with existing file
            pdf_folder = dest_dir / "PDF"
            pdf_folder.mkdir()
            (pdf_folder / "report.pdf").write_text("existing PDF content")

            # Create source file with different content
            source_file = source_dir / "report.pdf"
            source_file.write_text("new PDF content - different")

            # Move sorted with deduplication
            moved, errors, duplicates, content_duplicates, history, created_folders = (
                self.file_mover.move_files_sorted(
                    [source_file], dest_dir, deduplicate=True
                )
            )

            assert moved == 1
            assert duplicates == 1  # Name conflict, renamed
            assert content_duplicates == 0
            assert (pdf_folder / "report_1.pdf").exists()
            assert (pdf_folder / "report_1.pdf").read_text() == "new PDF content - different"

    def test_move_files_sorted_deduplicate_disabled_returns_old_signature(self):
        """Without deduplicate, move_files_sorted returns 5-tuple (backward compat)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            source_file = source_dir / "test.pdf"
            source_file.touch()

            # Old signature without deduplicate
            moved, errors, duplicates, history, created_folders = (
                self.file_mover.move_files_sorted([source_file], dest_dir)
            )

            assert moved == 1
            assert isinstance(created_folders, list)

    def test_move_files_deduplicate_hash_error_falls_back_to_rename(self):
        """Hash calculation error falls back to normal rename behavior."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            source_file = source_dir / "hashfail.txt"
            source_file.write_text("content")
            dest_file = dest_dir / "hashfail.txt"
            dest_file.write_text("content")

            # Mock hash calculation to fail
            with patch.object(
                self.file_ops,
                "calculate_file_hash",
                side_effect=FileOperationError("Hash failed"),
            ):
                moved, errors, duplicates, content_duplicates, history = (
                    self.file_mover.move_files(
                        [source_file], dest_dir, deduplicate=True
                    )
                )

            # Should fall back to rename behavior
            assert moved == 1
            assert duplicates == 1
            assert content_duplicates == 0
            assert (dest_dir / "hashfail_1.txt").exists()

    def test_move_files_no_conflict_with_deduplicate_moves_normally(self):
        """Files without name conflict move normally even with deduplicate enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            source_file = source_dir / "unique.txt"
            source_file.write_text("unique content")

            # No existing file at destination
            moved, errors, duplicates, content_duplicates, history = (
                self.file_mover.move_files([source_file], dest_dir, deduplicate=True)
            )

            assert moved == 1
            assert duplicates == 0
            assert content_duplicates == 0
            assert (dest_dir / "unique.txt").exists()
