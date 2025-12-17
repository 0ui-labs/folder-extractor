"""
Unit tests for the core extractor module.
"""
import pytest
from pathlib import Path
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
    
    def test_discover_files_basic(self, tmp_path):
        """Test basic file discovery."""
        # Create test structure
        subdir = tmp_path / "subdir"
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
        files = extractor.discover_files(tmp_path)

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
    
    def test_extract_files_normal_mode(self, tmp_path):
        """Test file extraction in normal mode."""
        # Create source files
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        files = []
        for i in range(3):
            file_path = source_dir / f"file{i}.txt"
            file_path.touch()
            files.append(str(file_path))

        # Extract files
        result = self.extractor.extract_files(files, tmp_path)

        assert result["moved"] == 3
        assert result["errors"] == 0
        assert result["duplicates"] == 0
        assert len(result["history"]) == 3
        assert result["created_folders"] == []
    
    def test_extract_files_sort_by_type(self, tmp_path):
        """Test file extraction with sort by type."""
        settings.set("sort_by_type", True)

        # Create source files
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        files = [
            str((source_dir / "doc.pdf").touch() or source_dir / "doc.pdf"),
            str((source_dir / "img.jpg").touch() or source_dir / "img.jpg"),
            str((source_dir / "script.py").touch() or source_dir / "script.py")
        ]

        # Extract files
        result = self.extractor.extract_files(files, tmp_path)

        assert result["moved"] == 3
        assert "PDF" in result["created_folders"]
        assert "JPEG" in result["created_folders"]
        assert "PYTHON" in result["created_folders"]
    
    def test_extract_files_dry_run(self, tmp_path):
        """Test extraction in dry run mode."""
        settings.set("dry_run", True)

        # Create source file
        source_file = tmp_path / "source.txt"
        source_file.touch()

        # Extract
        result = self.extractor.extract_files([str(source_file)], tmp_path)

        # File should still exist in original location
        assert source_file.exists()
        assert result["moved"] == 1
        assert len(result["history"]) == 0  # No history in dry run
    
    def test_undo_last_operation(self, tmp_path):
        """Test undo functionality."""
        # Create history
        operations = [{
            "original_pfad": str(tmp_path / "original" / "file.txt"),
            "neuer_pfad": str(tmp_path / "new" / "file.txt"),
            "original_name": "file.txt",
            "neuer_name": "file.txt",
            "zeitstempel": "2024-01-01T12:00:00"
        }]

        # Create the "moved" file
        new_dir = tmp_path / "new"
        new_dir.mkdir()
        (new_dir / "file.txt").write_text("content")

        # Save history
        HistoryManager.save_history(operations, tmp_path)

        # Undo
        restored = self.extractor.undo_last_operation(tmp_path)

        assert restored == 1
        assert (tmp_path / "original" / "file.txt").exists()
        assert not (new_dir / "file.txt").exists()
    
    def test_undo_no_history(self, tmp_path):
        """Test undo when no history exists."""
        restored = self.extractor.undo_last_operation(tmp_path)
        assert restored == 0

    def test_filter_by_domain_no_domains(self):
        """Test filter_by_domain with empty/None domains list (covers line 121)."""
        files = [
            "/path/to/file.txt",
            "/path/to/youtube.url",
            "/path/to/github.webloc"
        ]

        # Test with None
        filtered = self.extractor.filter_by_domain(files, None)
        assert len(filtered) == 3
        assert filtered == files

        # Test with empty list
        filtered = self.extractor.filter_by_domain(files, [])
        assert len(filtered) == 3
        assert filtered == files

    def test_extract_files_with_domain_filter(self, tmp_path):
        """Test extraction with domain_filter setting (covers line 152)."""
        # Set domain filter
        settings.set("domain_filter", ["youtube.com"])

        # Create source files including weblinks
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # Create regular file
        regular_file = source_dir / "file.txt"
        regular_file.touch()

        # Create weblink files
        youtube_file = source_dir / "youtube.url"
        youtube_file.touch()
        github_file = source_dir / "github.url"
        github_file.touch()

        files = [str(regular_file), str(youtube_file), str(github_file)]

        # Mock domain checking
        mock_discovery = Mock()
        mock_discovery.check_weblink_domain.side_effect = [
            True,   # youtube.url matches
            False   # github.url doesn't match
        ]

        extractor = FileExtractor(file_discovery=mock_discovery)

        # Extract files with domain filter
        result = extractor.extract_files(files, tmp_path)

        # Should only move regular file and matching weblink
        assert result["moved"] == 2
        assert result["errors"] == 0

    def test_undo_with_abort_signal(self, tmp_path):
        """Test undo operation being interrupted by abort signal (covers line 224)."""
        abort_signal = threading.Event()

        # Create extractor with abort signal
        extractor = FileExtractor(abort_signal=abort_signal)

        # Create history with multiple operations
        operations = []
        for i in range(5):
            operations.append({
                "original_pfad": str(tmp_path / "original" / f"file{i}.txt"),
                "neuer_pfad": str(tmp_path / "new" / f"file{i}.txt"),
                "original_name": f"file{i}.txt",
                "neuer_name": f"file{i}.txt",
                "zeitstempel": "2024-01-01T12:00:00"
            })

        # Create the "moved" files
        new_dir = tmp_path / "new"
        new_dir.mkdir()
        for i in range(5):
            (new_dir / f"file{i}.txt").write_text(f"content{i}")

        # Save history
        HistoryManager.save_history(operations, tmp_path)

        # Set abort signal before undo
        abort_signal.set()

        # Undo should be interrupted
        restored = extractor.undo_last_operation(tmp_path)

        # Should have restored 0 files due to immediate abort
        assert restored == 0

    def test_undo_with_file_error(self, tmp_path):
        """Test undo when file operation fails (covers lines 241-243)."""
        # Create history with two operations - one will fail, one will succeed
        operations = [
            {
                "original_pfad": str(tmp_path / "original" / "file1.txt"),
                "neuer_pfad": str(tmp_path / "new" / "file1.txt"),
                "original_name": "file1.txt",
                "neuer_name": "file1.txt",
                "zeitstempel": "2024-01-01T12:00:00"
            },
            {
                "original_pfad": str(tmp_path / "original" / "file2.txt"),
                "neuer_pfad": str(tmp_path / "new" / "file2.txt"),
                "original_name": "file2.txt",
                "neuer_name": "file2.txt",
                "zeitstempel": "2024-01-01T12:00:00"
            }
        ]

        # Create the "moved" files
        new_dir = tmp_path / "new"
        new_dir.mkdir()
        (new_dir / "file1.txt").write_text("content1")
        (new_dir / "file2.txt").write_text("content2")

        # Save history
        HistoryManager.save_history(operations, tmp_path)

        # Mock file_operations.move_file to raise exception on first call, succeed on second
        mock_file_ops = Mock()
        mock_file_ops.move_file.side_effect = [
            Exception("Simulated file error"),  # First call fails
            None  # Second call succeeds (but won't be reached due to reverse order)
        ]
        mock_file_ops.remove_empty_directories.return_value = 0

        # Create extractor with mocked file operations
        extractor = FileExtractor(file_operations=mock_file_ops)

        # Undo should handle the error gracefully and continue
        restored = extractor.undo_last_operation(tmp_path)

        # Should have tried both operations (reversed order)
        # Due to reverse order: file2 fails, but file1 might succeed
        # Actually, with side_effect, first call (file2 in reverse) fails, second (file1) succeeds
        assert restored == 1  # One file successfully restored despite the error
        assert mock_file_ops.move_file.call_count == 2


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
    
    def test_extraction_with_abort(self, tmp_path):
        """Test extraction with abort signal."""
        abort_signal = threading.Event()

        # Create extractor with abort signal
        extractor = FileExtractor(abort_signal=abort_signal)

        # Create many files
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        files = []
        for i in range(100):
            file_path = source_dir / f"file{i}.txt"
            file_path.touch()
            files.append(str(file_path))

        # Set abort signal immediately
        abort_signal.set()

        # Extract - should be interrupted
        result = extractor.extract_files(files, tmp_path)

        # Should have processed fewer files
        assert result["moved"] < len(files)