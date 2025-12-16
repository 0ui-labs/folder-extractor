"""
Unit tests for the core extractor module.
"""
import os
import pytest
from pathlib import Path
import tempfile
import threading
from unittest.mock import Mock, MagicMock, patch

from folder_extractor.core.extractor import (
    FileExtractor,
    ExtractionOrchestrator,
    SecurityError,
    ExtractionError
)
from folder_extractor.config.settings import settings
from folder_extractor.core.file_discovery import FileDiscovery
from folder_extractor.core.file_operations import FileOperations, HistoryManager


class TestFileExtractor:
    """Test FileExtractor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Reset settings
        settings.reset_to_defaults()
        self.extractor = FileExtractor()
    
    def test_validate_security_safe_path(self):
        """Test security validation with safe path."""
        home = Path.home()
        safe_path = str(home / "Desktop" / "test")
        
        # Create directory
        Path(safe_path).mkdir(parents=True, exist_ok=True)
        
        # Should not raise
        self.extractor.validate_security(safe_path)
        
        # Cleanup
        Path(safe_path).rmdir()
    
    def test_validate_security_unsafe_path(self):
        """Test security validation with unsafe path."""
        unsafe_paths = ["/etc", "/usr/bin", str(Path.home())]
        
        for path in unsafe_paths:
            with pytest.raises(SecurityError):
                self.extractor.validate_security(path)
    
    def test_discover_files_basic(self):
        """Test basic file discovery."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test structure
            subdir = Path(temp_dir) / "subdir"
            subdir.mkdir()
            (subdir / "file1.txt").touch()
            (subdir / "file2.pdf").touch()
            
            # Mock file discovery to return our files
            mock_discovery = Mock()
            mock_discovery.find_files.return_value = [
                str(subdir / "file1.txt"),
                str(subdir / "file2.pdf")
            ]
            
            extractor = FileExtractor(file_discovery=mock_discovery)
            files = extractor.discover_files(temp_dir)
            
            assert len(files) == 2
            mock_discovery.find_files.assert_called_once()
    
    def test_filter_by_domain(self):
        """Test domain filtering for weblink files."""
        files = [
            "/path/to/file.txt",
            "/path/to/youtube.url",
            "/path/to/github.webloc",
            "/path/to/other.url"
        ]
        
        # Mock domain checking
        mock_discovery = Mock()
        mock_discovery.check_weblink_domain.side_effect = [
            True,   # youtube.url matches
            False,  # github.webloc doesn't match
            False   # other.url doesn't match
        ]
        
        extractor = FileExtractor(file_discovery=mock_discovery)
        filtered = extractor.filter_by_domain(files, ["youtube.com"])
        
        # Should keep non-weblink files and matching weblinks
        assert len(filtered) == 2
        assert "/path/to/file.txt" in filtered
        assert "/path/to/youtube.url" in filtered
    
    def test_extract_files_normal_mode(self):
        """Test file extraction in normal mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create source files
            source_dir = Path(temp_dir) / "source"
            source_dir.mkdir()
            files = []
            for i in range(3):
                file_path = source_dir / f"file{i}.txt"
                file_path.touch()
                files.append(str(file_path))
            
            # Extract files
            result = self.extractor.extract_files(files, temp_dir)
            
            assert result["moved"] == 3
            assert result["errors"] == 0
            assert result["duplicates"] == 0
            assert len(result["history"]) == 3
            assert result["created_folders"] == []
    
    def test_extract_files_sort_by_type(self):
        """Test file extraction with sort by type."""
        settings.set("sort_by_type", True)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create source files
            source_dir = Path(temp_dir) / "source"
            source_dir.mkdir()
            files = [
                str((source_dir / "doc.pdf").touch() or source_dir / "doc.pdf"),
                str((source_dir / "img.jpg").touch() or source_dir / "img.jpg"),
                str((source_dir / "script.py").touch() or source_dir / "script.py")
            ]
            
            # Extract files
            result = self.extractor.extract_files(files, temp_dir)
            
            assert result["moved"] == 3
            assert "PDF" in result["created_folders"]
            assert "JPEG" in result["created_folders"]
            assert "PYTHON" in result["created_folders"]
    
    def test_extract_files_dry_run(self):
        """Test extraction in dry run mode."""
        settings.set("dry_run", True)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create source file
            source_file = Path(temp_dir) / "source.txt"
            source_file.touch()
            
            # Extract
            result = self.extractor.extract_files([str(source_file)], temp_dir)
            
            # File should still exist in original location
            assert source_file.exists()
            assert result["moved"] == 1
            assert len(result["history"]) == 0  # No history in dry run
    
    def test_undo_last_operation(self):
        """Test undo functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create history
            operations = [{
                "original_pfad": str(Path(temp_dir) / "original" / "file.txt"),
                "neuer_pfad": str(Path(temp_dir) / "new" / "file.txt"),
                "original_name": "file.txt",
                "neuer_name": "file.txt",
                "zeitstempel": "2024-01-01T12:00:00"
            }]
            
            # Create the "moved" file
            new_dir = Path(temp_dir) / "new"
            new_dir.mkdir()
            (new_dir / "file.txt").write_text("content")
            
            # Save history
            HistoryManager.save_history(operations, temp_dir)
            
            # Undo
            restored = self.extractor.undo_last_operation(temp_dir)
            
            assert restored == 1
            assert (Path(temp_dir) / "original" / "file.txt").exists()
            assert not (new_dir / "file.txt").exists()
    
    def test_undo_no_history(self):
        """Test undo when no history exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            restored = self.extractor.undo_last_operation(temp_dir)
            assert restored == 0


class TestExtractionOrchestrator:
    """Test ExtractionOrchestrator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        settings.reset_to_defaults()
        self.mock_extractor = Mock()
        self.orchestrator = ExtractionOrchestrator(self.mock_extractor)
    
    def test_execute_extraction_success(self):
        """Test successful extraction workflow."""
        # Set up mocks
        self.mock_extractor.discover_files.return_value = [
            "/file1.txt", "/file2.txt"
        ]
        self.mock_extractor.extract_files.return_value = {
            "moved": 2,
            "errors": 0,
            "duplicates": 0,
            "history": [],
            "created_folders": [],
            "removed_directories": 0
        }
        
        # Execute
        result = self.orchestrator.execute_extraction("/safe/path")
        
        assert result["status"] == "success"
        assert result["total_files"] == 2
        assert result["moved"] == 2
        
        self.mock_extractor.validate_security.assert_called_once_with("/safe/path")
        self.mock_extractor.discover_files.assert_called_once()
        self.mock_extractor.extract_files.assert_called_once()
    
    def test_execute_extraction_no_files(self):
        """Test extraction when no files found."""
        self.mock_extractor.discover_files.return_value = []
        
        result = self.orchestrator.execute_extraction("/safe/path")
        
        assert result["status"] == "no_files"
        assert "Keine Dateien" in result["message"]
    
    def test_execute_extraction_cancelled(self):
        """Test extraction when user cancels."""
        self.mock_extractor.discover_files.return_value = ["/file.txt"]
        
        # Confirmation callback returns False
        confirmation = Mock(return_value=False)
        
        result = self.orchestrator.execute_extraction(
            "/safe/path",
            confirmation_callback=confirmation
        )
        
        assert result["status"] == "cancelled"
        confirmation.assert_called_once_with(1)
    
    def test_execute_extraction_security_error(self):
        """Test extraction with security error."""
        self.mock_extractor.validate_security.side_effect = SecurityError("Unsafe!")
        
        with pytest.raises(SecurityError):
            self.orchestrator.execute_extraction("/unsafe/path")
    
    def test_execute_undo_success(self):
        """Test successful undo operation."""
        self.mock_extractor.undo_last_operation.return_value = 5
        
        result = self.orchestrator.execute_undo("/safe/path")
        
        assert result["status"] == "success"
        assert result["restored"] == 5
        assert "5 Dateien" in result["message"]
    
    def test_execute_undo_no_history(self):
        """Test undo when no history exists."""
        self.mock_extractor.undo_last_operation.return_value = 0
        
        result = self.orchestrator.execute_undo("/safe/path")
        
        assert result["status"] == "no_history"
        assert result["restored"] == 0


class TestIntegration:
    """Integration tests with real components."""
    
    def test_full_extraction_workflow(self):
        """Test complete extraction workflow."""
        # Use safe test directory
        home = Path.home()
        test_dir = home / "Desktop" / "extractor_test"
        test_dir.mkdir(exist_ok=True)
        
        try:
            # Create test structure
            source_dir = test_dir / "source"
            source_dir.mkdir()
            
            # Create test files
            (source_dir / "doc.pdf").touch()
            (source_dir / "img.jpg").touch()
            (source_dir / ".hidden.txt").touch()
            
            # Create extractor
            extractor = FileExtractor()
            orchestrator = ExtractionOrchestrator(extractor)
            
            # Execute extraction
            result = orchestrator.execute_extraction(str(test_dir))
            
            assert result["status"] == "success"
            assert result["moved"] == 2  # Hidden file excluded by default
            assert result["errors"] == 0
            
            # Check files were moved
            assert (test_dir / "doc.pdf").exists()
            assert (test_dir / "img.jpg").exists()
            assert not (source_dir / "doc.pdf").exists()
            assert not (source_dir / "img.jpg").exists()
            
            # Test undo
            undo_result = orchestrator.execute_undo(str(test_dir))
            assert undo_result["restored"] == 2
            
            # Files should be back
            assert (source_dir / "doc.pdf").exists()
            assert (source_dir / "img.jpg").exists()
            
        finally:
            # Cleanup
            import shutil
            if test_dir.exists():
                shutil.rmtree(test_dir)
    
    def test_extraction_with_abort(self):
        """Test extraction with abort signal."""
        abort_signal = threading.Event()
        
        # Create extractor with abort signal
        extractor = FileExtractor(abort_signal=abort_signal)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create many files
            source_dir = Path(temp_dir) / "source"
            source_dir.mkdir()
            files = []
            for i in range(100):
                file_path = source_dir / f"file{i}.txt"
                file_path.touch()
                files.append(str(file_path))
            
            # Set abort signal immediately
            abort_signal.set()
            
            # Extract - should be interrupted
            result = extractor.extract_files(files, temp_dir)
            
            # Should have processed fewer files
            assert result["moved"] < len(files)