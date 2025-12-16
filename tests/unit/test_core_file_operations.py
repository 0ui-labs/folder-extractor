"""
Unit tests for the core file operations module.
"""
import os
import pytest
from pathlib import Path
import tempfile
import shutil
import threading
from unittest.mock import Mock, patch

from folder_extractor.core.file_operations import (
    FileOperations,
    FileMover,
    HistoryManager,
    FileOperationError
)


class TestFileOperations:
    """Test FileOperations class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.file_ops = FileOperations()
    
    def test_generate_unique_name_no_conflict(self):
        """Test unique name generation when no conflict."""
        with tempfile.TemporaryDirectory() as temp_dir:
            name = self.file_ops.generate_unique_name(temp_dir, "test.txt")
            assert name == "test.txt"
    
    def test_generate_unique_name_with_conflicts(self):
        """Test unique name generation with existing files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create existing files
            Path(temp_dir, "test.txt").touch()
            Path(temp_dir, "test_1.txt").touch()
            
            name = self.file_ops.generate_unique_name(temp_dir, "test.txt")
            assert name == "test_2.txt"
    
    def test_generate_unique_name_no_extension(self):
        """Test unique name for files without extension."""
        with tempfile.TemporaryDirectory() as temp_dir:
            Path(temp_dir, "README").touch()
            
            name = self.file_ops.generate_unique_name(temp_dir, "README")
            assert name == "README_1"
    
    def test_move_file_success(self):
        """Test successful file move."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create source file
            source = Path(temp_dir, "source.txt")
            source.write_text("content")
            
            # Move file
            dest = Path(temp_dir, "dest.txt")
            result = self.file_ops.move_file(str(source), str(dest))
            
            assert result is True
            assert not source.exists()
            assert dest.exists()
            assert dest.read_text() == "content"
    
    def test_move_file_dry_run(self):
        """Test file move in dry run mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir, "source.txt")
            source.write_text("content")
            
            dest = Path(temp_dir, "dest.txt")
            result = self.file_ops.move_file(str(source), str(dest), dry_run=True)
            
            assert result is True
            assert source.exists()  # File should still exist
            assert not dest.exists()
    
    def test_move_file_cross_filesystem(self):
        """Test file move across filesystems (simulated)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir, "source.txt")
            source.write_text("content")
            dest = Path(temp_dir, "dest.txt")
            
            # Mock os.rename to fail, forcing copy+delete
            with patch('os.rename', side_effect=OSError):
                result = self.file_ops.move_file(str(source), str(dest))
                
                assert result is True
                assert not source.exists()
                assert dest.exists()
                assert dest.read_text() == "content"
    
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
    
    def test_remove_empty_directories(self):
        """Test removing empty directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create empty directories
            (Path(temp_dir) / "empty1").mkdir()
            (Path(temp_dir) / "empty2" / "nested").mkdir(parents=True)
            
            # Create non-empty directory
            non_empty = Path(temp_dir) / "non_empty"
            non_empty.mkdir()
            (non_empty / "file.txt").touch()
            
            removed = self.file_ops.remove_empty_directories(temp_dir)
            
            assert removed >= 3  # empty1, empty2, nested
            assert not (Path(temp_dir) / "empty1").exists()
            assert not (Path(temp_dir) / "empty2").exists()
            assert non_empty.exists()
    
    def test_remove_empty_directories_with_hidden(self):
        """Test removing directories with hidden files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Directory with hidden file
            hidden_dir = Path(temp_dir) / "hidden_dir"
            hidden_dir.mkdir()
            (hidden_dir / ".hidden").touch()
            
            # Without include_hidden - should remove
            removed = self.file_ops.remove_empty_directories(temp_dir, include_hidden=False)
            assert removed == 1
            assert not hidden_dir.exists()
            
            # Recreate
            hidden_dir.mkdir()
            (hidden_dir / ".hidden").touch()
            
            # With include_hidden - should keep
            removed = self.file_ops.remove_empty_directories(temp_dir, include_hidden=True)
            assert removed == 0
            assert hidden_dir.exists()


class TestHistoryManager:
    """Test HistoryManager class."""
    
    def test_save_and_load_history(self):
        """Test saving and loading history."""
        with tempfile.TemporaryDirectory() as temp_dir:
            operations = [
                {
                    "original_pfad": "/old/path/file.txt",
                    "neuer_pfad": "/new/path/file.txt",
                    "original_name": "file.txt",
                    "neuer_name": "file.txt",
                    "zeitstempel": "2024-01-01T12:00:00"
                }
            ]
            
            # Save history
            history_file = HistoryManager.save_history(operations, temp_dir)
            assert os.path.exists(history_file)
            
            # Load history
            loaded = HistoryManager.load_history(temp_dir)
            assert loaded is not None
            assert "operationen" in loaded
            assert len(loaded["operationen"]) == 1
            assert loaded["operationen"][0]["original_pfad"] == "/old/path/file.txt"
    
    def test_load_nonexistent_history(self):
        """Test loading when no history exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            loaded = HistoryManager.load_history(temp_dir)
            assert loaded is None
    
    def test_delete_history(self):
        """Test deleting history file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create history
            HistoryManager.save_history([{"test": "data"}], temp_dir)
            
            # Delete
            result = HistoryManager.delete_history(temp_dir)
            assert result is True
            
            # Try to load
            loaded = HistoryManager.load_history(temp_dir)
            assert loaded is None
            
            # Delete again - should return False
            result = HistoryManager.delete_history(temp_dir)
            assert result is False


class TestFileMover:
    """Test FileMover class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.file_ops = FileOperations()
        self.file_mover = FileMover(self.file_ops)
    
    def test_move_files_success(self):
        """Test moving multiple files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            source_dir.mkdir()
            dest_dir = Path(temp_dir) / "dest"
            dest_dir.mkdir()
            
            # Create test files
            files = []
            for i in range(3):
                file_path = source_dir / f"file{i}.txt"
                file_path.write_text(f"content{i}")
                files.append(str(file_path))
            
            # Move files
            moved, errors, duplicates, history = self.file_mover.move_files(
                files, str(dest_dir)
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
    
    def test_move_files_with_duplicates(self):
        """Test moving files with duplicate names."""
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            source_dir.mkdir()
            dest_dir = Path(temp_dir) / "dest"
            dest_dir.mkdir()
            
            # Create existing file in destination
            (dest_dir / "duplicate.txt").write_text("existing")
            
            # Create source file with same name
            source_file = source_dir / "duplicate.txt"
            source_file.write_text("new")
            
            # Move file
            moved, errors, duplicates, history = self.file_mover.move_files(
                [str(source_file)], str(dest_dir)
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
            source_dir = Path(temp_dir) / "source"
            source_dir.mkdir()
            
            # Create many files
            files = []
            for i in range(100):
                file_path = source_dir / f"file{i}.txt"
                file_path.touch()
                files.append(str(file_path))
            
            # Set abort signal
            abort_signal.set()
            
            # Move files
            moved, errors, duplicates, history = file_mover.move_files(
                files, temp_dir
            )
            
            # Should have moved very few files
            assert moved < len(files)
    
    def test_move_files_sorted(self):
        """Test moving files sorted by type."""
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            source_dir.mkdir()
            dest_dir = Path(temp_dir) / "dest"
            dest_dir.mkdir()
            
            # Create various file types
            files = []
            test_files = [
                "document.pdf",
                "image.jpg",
                "script.py",
                "data.json"
            ]
            
            for filename in test_files:
                file_path = source_dir / filename
                file_path.touch()
                files.append(str(file_path))
            
            # Move files sorted
            moved, errors, duplicates, history, created_folders = \
                self.file_mover.move_files_sorted(files, str(dest_dir))
            
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
    
    def test_move_files_with_progress_callback(self):
        """Test progress callback during file move."""
        progress_calls = []
        
        def progress_callback(current, total, filepath, error=None):
            progress_calls.append({
                'current': current,
                'total': total,
                'filepath': filepath,
                'error': error
            })
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            test_file = Path(temp_dir) / "test.txt"
            test_file.touch()
            
            # Move with callback
            self.file_mover.move_files(
                [str(test_file)], temp_dir,
                progress_callback=progress_callback
            )
            
            assert len(progress_calls) == 1
            assert progress_calls[0]['current'] == 1
            assert progress_calls[0]['total'] == 1
            assert progress_calls[0]['error'] is None


