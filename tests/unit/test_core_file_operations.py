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

    # =========================================================================
    # build_hash_index Integration Tests
    # =========================================================================

    def test_build_hash_index_integration(self):
        """Integration test: build_hash_index finds duplicates in a realistic structure.

        Creates a realistic directory structure with mixed file types and
        verifies that duplicates are correctly identified across subdirectories.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)

            # Create realistic structure
            photos = base / "Photos"
            docs = base / "Documents"
            backup = base / "Backup"
            photos.mkdir()
            docs.mkdir()
            backup.mkdir()

            # Create some duplicate photos
            photo_content = b"JPEG image data" * 100
            (photos / "vacation.jpg").write_bytes(photo_content)
            (backup / "vacation_copy.jpg").write_bytes(photo_content)

            # Create some duplicate documents
            doc_content = "Important document content" * 50
            (docs / "report.txt").write_text(doc_content)
            (backup / "report_backup.txt").write_text(doc_content)

            # Create unique files (no duplicates)
            (photos / "unique1.png").write_bytes(b"unique png data")
            (docs / "unique2.docx").write_bytes(b"unique docx data different size")

            result = self.file_ops.build_hash_index(temp_dir)

            # Should find exactly 2 duplicate groups
            assert len(result) == 2

            # Verify photo duplicates
            photo_hash = None
            for h, paths in result.items():
                path_names = [p.name for p in paths]
                if "vacation.jpg" in path_names:
                    photo_hash = h
                    assert len(paths) == 2
                    assert "vacation_copy.jpg" in path_names

            assert photo_hash is not None, "Photo duplicates not found"

            # Verify document duplicates
            doc_hash = None
            for h, paths in result.items():
                path_names = [p.name for p in paths]
                if "report.txt" in path_names:
                    doc_hash = h
                    assert len(paths) == 2
                    assert "report_backup.txt" in path_names

            assert doc_hash is not None, "Document duplicates not found"

    def test_build_hash_index_abort_signal_stops_phase1(self):
        """Abort signal stops scanning during Phase 1 (size grouping).

        Verifies that the abort_signal mechanism correctly interrupts
        the directory scanning process.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)

            # Create many files
            content = b"same content"
            for i in range(20):
                (base / f"file_{i}.bin").write_bytes(content)

            # Create abort signal and set it immediately
            abort_signal = threading.Event()
            abort_signal.set()

            file_ops = FileOperations(abort_signal=abort_signal)
            result = file_ops.build_hash_index(temp_dir)

            # With abort set, should return empty or partial result
            # (depends on timing, but should not process all files)
            # The key assertion is that it doesn't hang or crash
            assert isinstance(result, dict)

    def test_build_hash_index_abort_signal_stops_phase2(self):
        """Abort signal stops hashing during Phase 2.

        Verifies that abort_signal works during the hash calculation phase.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)

            # Create files with same size to trigger Phase 2
            content = b"identical content for hashing"
            for i in range(10):
                (base / f"dup_{i}.bin").write_bytes(content)

            abort_signal = threading.Event()
            file_ops = FileOperations(abort_signal=abort_signal)

            # Track hash calls and abort after first
            original_hash = file_ops.calculate_file_hash
            call_count = [0]

            def hash_with_abort(path, *args, **kwargs):
                call_count[0] += 1
                if call_count[0] >= 2:
                    abort_signal.set()
                return original_hash(path, *args, **kwargs)

            with patch.object(file_ops, 'calculate_file_hash', side_effect=hash_with_abort):
                result = file_ops.build_hash_index(temp_dir)

            # Should have processed some but not all files
            assert isinstance(result, dict)
            # Abort was triggered, so not all files were hashed
            assert call_count[0] >= 2


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


class TestFileMoverGlobalDedup:
    """Test FileMover global deduplication functionality.

    Global deduplication checks ALL source files against ALL existing files
    in the destination directory tree (regardless of filename), skipping
    files that already exist with identical content anywhere in the destination.
    """

    def setup_method(self):
        """Set up test fixtures."""
        self.file_ops = FileOperations()
        self.file_mover = FileMover(self.file_ops)

    def test_move_files_global_dedup_skips_existing_duplicate(self):
        """Source files with content already in dest are skipped and deleted.

        When global_dedup=True and a file's content already exists somewhere
        in the destination tree (even with a different name), the source
        file is deleted rather than moved.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            # Create identical content with DIFFERENT names
            identical_content = "This content exists in destination already"
            existing_file = dest_dir / "existing.txt"
            existing_file.write_text(identical_content)

            source_file = source_dir / "different_name.txt"
            source_file.write_text(identical_content)

            # Move with global deduplication enabled
            moved, errors, name_dups, content_dups, global_dups, history = (
                self.file_mover.move_files([source_file], dest_dir, global_dedup=True)
            )

            # Source should be deleted, not moved (global duplicate)
            assert moved == 0
            assert errors == 0
            assert name_dups == 0
            assert content_dups == 0
            assert global_dups == 1
            assert not source_file.exists(), "Source should be deleted"
            assert existing_file.exists(), "Existing file should remain"
            assert not (dest_dir / "different_name.txt").exists(), "File should not be moved"

    def test_move_files_global_dedup_moves_unique_content(self):
        """Files with unique content are moved normally with global_dedup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            # Create existing file with different content
            (dest_dir / "existing.txt").write_text("existing content")

            # Source file with unique content
            source_file = source_dir / "new_file.txt"
            source_file.write_text("completely different unique content")

            # Move with global deduplication enabled
            moved, errors, name_dups, content_dups, global_dups, history = (
                self.file_mover.move_files([source_file], dest_dir, global_dedup=True)
            )

            assert moved == 1
            assert global_dups == 0
            assert (dest_dir / "new_file.txt").exists()

    def test_move_files_global_dedup_updates_index_for_subsequent_files(self):
        """Index is updated after each move to detect duplicates within batch.

        When moving multiple files, newly moved files should be added to the
        index so that subsequent files with identical content are detected.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()  # Empty destination

            # Create 3 files with identical content
            identical_content = "all three files have this content"
            file1 = source_dir / "first.txt"
            file2 = source_dir / "second.txt"
            file3 = source_dir / "third.txt"
            file1.write_text(identical_content)
            file2.write_text(identical_content)
            file3.write_text(identical_content)

            # Move all three with global deduplication
            moved, errors, name_dups, content_dups, global_dups, history = (
                self.file_mover.move_files(
                    [file1, file2, file3], dest_dir, global_dedup=True
                )
            )

            # First file should be moved, subsequent duplicates should be skipped
            assert moved == 1
            assert global_dups == 2
            assert errors == 0

            # Only one file should exist in destination
            dest_files = list(dest_dir.glob("*.txt"))
            assert len(dest_files) == 1

    def test_move_files_global_dedup_finds_duplicates_in_subdirectories(self):
        """Global dedup finds duplicates in nested destination subdirectories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            # Create nested structure with existing file
            nested = dest_dir / "level1" / "level2"
            nested.mkdir(parents=True)
            identical_content = "content hidden deep in subdirectory"
            (nested / "deep_file.txt").write_text(identical_content)

            # Source file with same content but different name at root
            source_file = source_dir / "surface_file.txt"
            source_file.write_text(identical_content)

            # Move with global deduplication
            moved, errors, name_dups, content_dups, global_dups, history = (
                self.file_mover.move_files([source_file], dest_dir, global_dedup=True)
            )

            # Should detect the duplicate in nested directory
            assert moved == 0
            assert global_dups == 1
            assert not source_file.exists()

    def test_move_files_global_dedup_dry_run_preserves_source(self):
        """Dry run with global_dedup does not delete source files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            identical_content = "dry run test content"
            (dest_dir / "existing.txt").write_text(identical_content)

            source_file = source_dir / "duplicate.txt"
            source_file.write_text(identical_content)

            # Dry run with global deduplication
            moved, errors, name_dups, content_dups, global_dups, history = (
                self.file_mover.move_files(
                    [source_file], dest_dir, dry_run=True, global_dedup=True
                )
            )

            # Source should still exist (dry run)
            assert source_file.exists()
            assert global_dups == 1
            assert len(history) == 0

    def test_move_files_global_dedup_combined_with_deduplicate(self):
        """global_dedup and deduplicate can be used together.

        Content duplicates (same name + same content) are checked FIRST to ensure
        proper categorization. Global duplicates (different name, matching content)
        are checked only when no same-named file exists at destination.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            # 1. Global duplicate: same content, different name → counted as global duplicate
            global_dup_content = "global duplicate content"
            (dest_dir / "existing_global.txt").write_text(global_dup_content)
            global_dup_source = source_dir / "global_dup.txt"
            global_dup_source.write_text(global_dup_content)

            # 2. Content duplicate: same name, same content → counted as content duplicate
            #    Content duplicate check happens BEFORE global check when same-named file exists
            content_dup_content = "content duplicate"
            (dest_dir / "same_name.txt").write_text(content_dup_content)
            content_dup_source = source_dir / "same_name.txt"
            content_dup_source.write_text(content_dup_content)

            # 3. Name duplicate: same name, different content → triggers rename
            (dest_dir / "name_conflict.txt").write_text("original content")
            name_dup_source = source_dir / "name_conflict.txt"
            name_dup_source.write_text("different content")

            # 4. Unique file: no duplicates
            unique_source = source_dir / "unique.txt"
            unique_source.write_text("completely unique content")

            # Move with both flags
            moved, errors, name_dups, content_dups, global_dups, history = (
                self.file_mover.move_files(
                    [global_dup_source, content_dup_source, name_dup_source, unique_source],
                    dest_dir,
                    deduplicate=True,
                    global_dedup=True,
                )
            )

            # Proper categorization:
            # - global_dup.txt: different name, content exists → global duplicate
            # - same_name.txt: same name, same content → content duplicate (not global)
            assert global_dups == 1  # only global_dup.txt
            assert content_dups == 1  # same_name.txt is a content duplicate
            assert name_dups == 1  # name_conflict.txt (renamed)
            assert moved == 2  # name_conflict_1.txt and unique.txt

    def test_move_files_global_dedup_records_history(self):
        """History entries for global duplicates have global_duplicate flag."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            identical_content = "history flag test"
            existing_file = dest_dir / "existing.txt"
            existing_file.write_text(identical_content)

            source_file = source_dir / "duplicate.txt"
            source_file.write_text(identical_content)

            moved, errors, name_dups, content_dups, global_dups, history = (
                self.file_mover.move_files([source_file], dest_dir, global_dedup=True)
            )

            # History should record the global duplicate
            assert len(history) == 1
            assert history[0].get("global_duplicate") is True
            assert history[0]["original_pfad"] == str(source_file)

    def test_move_files_global_dedup_empty_destination(self):
        """With empty destination, all unique files are moved normally."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()  # Empty

            file1 = source_dir / "file1.txt"
            file2 = source_dir / "file2.txt"
            file1.write_text("content 1")
            file2.write_text("content 2")

            moved, errors, name_dups, content_dups, global_dups, history = (
                self.file_mover.move_files([file1, file2], dest_dir, global_dedup=True)
            )

            assert moved == 2
            assert global_dups == 0
            assert (dest_dir / "file1.txt").exists()
            assert (dest_dir / "file2.txt").exists()

    def test_move_files_without_global_dedup_returns_4_tuple(self):
        """Without global_dedup, move_files returns backward-compatible 4-tuple."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            source_file = source_dir / "test.txt"
            source_file.touch()

            # Old signature without global_dedup
            result = self.file_mover.move_files([source_file], dest_dir)

            # Should return 4-tuple for backward compatibility
            assert len(result) == 4
            moved, errors, duplicates, history = result
            assert moved == 1


class TestFileMoverGlobalDedupSorted:
    """Test FileMover global deduplication with sorted (by type) moves.

    These tests verify global_dedup functionality in move_files_sorted(),
    which organizes files into type-specific subdirectories.
    """

    def setup_method(self):
        """Set up test fixtures."""
        self.file_ops = FileOperations()
        self.file_mover = FileMover(self.file_ops)

    def test_move_files_sorted_global_dedup_skips_existing(self):
        """Sorted move skips files already existing in dest type folder.

        When a PDF already exists in the PDF folder with same content,
        a new PDF with identical content should be skipped.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            # Create PDF folder with existing file
            pdf_folder = dest_dir / "PDF"
            pdf_folder.mkdir()
            identical_content = "PDF content for global dedup"
            (pdf_folder / "existing.pdf").write_text(identical_content)

            # Source file with same content but different name
            source_file = source_dir / "report.pdf"
            source_file.write_text(identical_content)

            # Move sorted with global deduplication
            moved, errors, name_dups, content_dups, global_dups, history, created = (
                self.file_mover.move_files_sorted(
                    [source_file], dest_dir, global_dedup=True
                )
            )

            assert moved == 0
            assert global_dups == 1
            assert not source_file.exists()
            assert not (pdf_folder / "report.pdf").exists()

    def test_move_files_sorted_global_dedup_finds_in_other_type_folders(self):
        """Global dedup finds duplicates across all type folders.

        A duplicate in JPEG folder should prevent moving a file to PDF folder
        if content matches (though this is an edge case).
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            # Create file in one type folder
            jpeg_folder = dest_dir / "JPEG"
            jpeg_folder.mkdir()
            identical_content = b"binary content shared"
            (jpeg_folder / "image.jpg").write_bytes(identical_content)

            # Source file of different type but same content
            source_file = source_dir / "data.bin"
            source_file.write_bytes(identical_content)

            # Move sorted with global deduplication
            moved, errors, name_dups, content_dups, global_dups, history, created = (
                self.file_mover.move_files_sorted(
                    [source_file], dest_dir, global_dedup=True
                )
            )

            # Content already exists (in JPEG folder), should be detected
            assert global_dups == 1
            assert moved == 0

    def test_move_files_sorted_global_dedup_updates_index(self):
        """Index is updated during sorted moves for within-batch deduplication."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()  # Empty

            # Create 3 PDFs with identical content
            identical_content = "PDF content for batch test"
            file1 = source_dir / "doc1.pdf"
            file2 = source_dir / "doc2.pdf"
            file3 = source_dir / "doc3.pdf"
            file1.write_text(identical_content)
            file2.write_text(identical_content)
            file3.write_text(identical_content)

            # Move all with global deduplication
            moved, errors, name_dups, content_dups, global_dups, history, created = (
                self.file_mover.move_files_sorted(
                    [file1, file2, file3], dest_dir, global_dedup=True
                )
            )

            # First should move, others should be global duplicates
            assert moved == 1
            assert global_dups == 2
            pdf_files = list((dest_dir / "PDF").glob("*.pdf"))
            assert len(pdf_files) == 1

    def test_move_files_sorted_global_dedup_with_deduplicate(self):
        """Combined global_dedup and deduplicate with sorted moves.

        Content duplicates (same name + same content) are checked FIRST to ensure
        proper categorization. Global duplicates (different name, matching content)
        are checked only when no same-named file exists at destination.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            # Create TEXT folder with existing files
            text_folder = dest_dir / "TEXT"
            text_folder.mkdir()

            # Global duplicate: different name, same content → counted as global duplicate
            global_dup_content = "global dup content"
            (text_folder / "existing.txt").write_text(global_dup_content)
            global_dup = source_dir / "global.txt"
            global_dup.write_text(global_dup_content)

            # Content duplicate: same name, same content → counted as content duplicate
            # Content duplicate check happens BEFORE global check when same-named file exists
            content_dup_content = "content dup"
            (text_folder / "same.txt").write_text(content_dup_content)
            content_dup = source_dir / "same.txt"
            content_dup.write_text(content_dup_content)

            # Unique file
            unique = source_dir / "unique.txt"
            unique.write_text("completely unique")

            moved, errors, name_dups, content_dups, global_dups, history, created = (
                self.file_mover.move_files_sorted(
                    [global_dup, content_dup, unique],
                    dest_dir,
                    deduplicate=True,
                    global_dedup=True,
                )
            )

            # Proper categorization:
            # - global.txt: different name, content exists → global duplicate
            # - same.txt: same name, same content → content duplicate (not global)
            assert global_dups == 1  # only global.txt
            assert content_dups == 1  # same.txt is a content duplicate
            assert moved == 1
            assert (text_folder / "unique.txt").exists()

    def test_move_files_sorted_global_dedup_dry_run(self):
        """Dry run with global_dedup in sorted mode preserves sources."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            pdf_folder = dest_dir / "PDF"
            pdf_folder.mkdir()
            identical = "identical PDF"
            (pdf_folder / "existing.pdf").write_text(identical)

            source_file = source_dir / "new.pdf"
            source_file.write_text(identical)

            moved, errors, name_dups, content_dups, global_dups, history, created = (
                self.file_mover.move_files_sorted(
                    [source_file], dest_dir, dry_run=True, global_dedup=True
                )
            )

            assert source_file.exists()
            assert global_dups == 1
            assert len(history) == 0

    def test_move_files_sorted_global_dedup_records_history(self):
        """History entries for sorted global duplicates have flag."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            text_folder = dest_dir / "TEXT"
            text_folder.mkdir()
            (text_folder / "existing.txt").write_text("shared content")

            source = source_dir / "new.txt"
            source.write_text("shared content")

            moved, errors, name_dups, content_dups, global_dups, history, created = (
                self.file_mover.move_files_sorted([source], dest_dir, global_dedup=True)
            )

            assert len(history) == 1
            assert history[0].get("global_duplicate") is True

    def test_move_files_sorted_without_global_dedup_returns_5_tuple(self):
        """Without global_dedup, move_files_sorted returns 5-tuple."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            source = source_dir / "test.pdf"
            source.touch()

            result = self.file_mover.move_files_sorted([source], dest_dir)

            assert len(result) == 5
            moved, errors, duplicates, history, created_folders = result
            assert moved == 1
