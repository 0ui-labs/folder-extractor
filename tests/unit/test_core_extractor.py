"""
Unit tests for the core extractor module.
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

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

        # Create mock state manager with all required methods
        self.mock_state_manager = Mock()
        self.mock_abort_signal = Mock()
        self.mock_abort_signal.is_set.return_value = False
        self.mock_state_manager.get_abort_signal.return_value = self.mock_abort_signal
        self.mock_state_manager.update_operation_stats = Mock()
        self.mock_state_manager.get_value = Mock(return_value=False)
        self.mock_state_manager.start_operation = Mock(return_value="test-op-123")
        self.mock_state_manager.end_operation = Mock()

        self.extractor = EnhancedFileExtractor(state_manager=self.mock_state_manager)

    def test_validate_security_accepts_safe_path(self):
        """Safe paths (Desktop, Downloads, Documents) are accepted without exception."""
        home = Path.home()
        safe_path = str(home / "Desktop" / "test")

        Path(safe_path).mkdir(parents=True, exist_ok=True)
        try:
            # No exception means path is accepted
            self.extractor.validate_security(safe_path)
        finally:
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
            str(subdir / "file2.pdf"),
        ]

        extractor = EnhancedFileExtractor(
            file_discovery=mock_discovery, state_manager=self.mock_state_manager
        )
        files = extractor.discover_files(tmp_path)

        assert len(files) == 2
        mock_discovery.find_files.assert_called_once()

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
            str((source_dir / "script.py").touch() or source_dir / "script.py"),
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
        # Create directories
        original_dir = tmp_path / "original"
        original_dir.mkdir()
        new_dir = tmp_path / "new"
        new_dir.mkdir()

        # Create history
        operations = [
            {
                "original_pfad": str(original_dir / "file.txt"),
                "neuer_pfad": str(new_dir / "file.txt"),
                "original_name": "file.txt",
                "neuer_name": "file.txt",
                "zeitstempel": "2024-01-01T12:00:00",
            }
        ]

        # Create the "moved" file (simulating the file was moved from original to new)
        (new_dir / "file.txt").write_text("content")

        # Save history using the extractor's history manager
        self.extractor.history_manager.save_history(operations, str(tmp_path))

        # Undo - now returns a dict
        result = self.extractor.undo_last_operation(tmp_path)

        assert result["restored"] == 1
        assert result["status"] == "success"
        assert (tmp_path / "original" / "file.txt").exists()
        assert not (new_dir / "file.txt").exists()

    def test_undo_no_history(self, tmp_path):
        """Test undo when no history exists."""
        result = self.extractor.undo_last_operation(tmp_path)
        assert result["restored"] == 0
        assert result["status"] == "no_history"

    def test_extract_files_with_abort(self, tmp_path):
        """Test extraction with abort signal."""
        # Set abort signal
        abort_signal = Mock()
        abort_signal.is_set.return_value = True
        self.mock_state_manager.get_abort_signal.return_value = abort_signal

        extractor = EnhancedFileExtractor(state_manager=self.mock_state_manager)

        # Create many files
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        files = []
        for i in range(100):
            file_path = source_dir / f"file{i}.txt"
            file_path.touch()
            files.append(str(file_path))

        # Extract - should be interrupted
        result = extractor.extract_files(files, tmp_path)

        # Should have processed fewer files due to abort
        assert result["moved"] < len(files)


class TestEnhancedExtractionOrchestrator:
    """Test EnhancedExtractionOrchestrator class."""

    def setup_method(self):
        """Set up test fixtures."""
        settings.reset_to_defaults()
        self.mock_extractor = Mock()
        self.mock_state_manager = Mock()
        self.mock_state_manager.get_abort_signal.return_value = Mock(
            is_set=Mock(return_value=False)
        )
        self.mock_state_manager.get_operation_stats = Mock(return_value=None)
        self.mock_state_manager.start_operation = Mock(return_value="op-123")
        self.mock_state_manager.end_operation = Mock()

        self.orchestrator = EnhancedExtractionOrchestrator(
            self.mock_extractor, self.mock_state_manager
        )

    def test_execute_extraction_success(self):
        """Test successful extraction workflow."""
        # Set up mocks
        self.mock_extractor.discover_files.return_value = ["/file1.txt", "/file2.txt"]
        self.mock_extractor.extract_files.return_value = {
            "moved": 2,
            "errors": 0,
            "duplicates": 0,
            "history": [],
            "created_folders": [],
            "removed_directories": 0,
        }

        # Execute
        result = self.orchestrator.execute_extraction("/safe/path")

        assert result["status"] == "success"
        assert result["files_found"] == 2
        assert result["moved"] == 2

        self.mock_extractor.validate_security.assert_called_once()
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
            "/safe/path", confirmation_callback=confirmation
        )

        assert result["status"] == "cancelled"
        confirmation.assert_called_once_with(1)

    def test_execute_extraction_confirmed(self):
        """Test extraction when user confirms (branch 393->404)."""
        self.mock_extractor.discover_files.return_value = ["/file.txt"]
        self.mock_extractor.extract_files.return_value = {
            "status": "success",
            "moved": 1,
            "errors": 0,
            "duplicates": 0,
        }

        # Confirmation callback returns True - user confirms
        confirmation = Mock(return_value=True)

        result = self.orchestrator.execute_extraction(
            "/safe/path", confirmation_callback=confirmation
        )

        # Should proceed to extraction
        assert result["status"] == "success"
        confirmation.assert_called_once_with(1)
        self.mock_extractor.extract_files.assert_called_once()

    def test_execute_extraction_security_error(self):
        """Test extraction with security error."""
        self.mock_extractor.validate_security.side_effect = SecurityError("Unsafe!")

        # Now returns error dict instead of raising
        result = self.orchestrator.execute_extraction("/unsafe/path")

        assert result["status"] == "security_error"
        assert "Unsafe!" in result["message"]

    def test_execute_undo_success(self):
        """Test successful undo operation."""
        self.mock_extractor.undo_last_operation.return_value = {
            "status": "success",
            "restored": 5,
            "message": "5 Dateien zurück verschoben",
        }

        result = self.orchestrator.execute_undo("/safe/path")

        assert result["status"] == "success"
        assert result["restored"] == 5

    def test_execute_undo_no_history(self):
        """Test undo when no history exists."""
        self.mock_extractor.undo_last_operation.return_value = {
            "status": "no_history",
            "restored": 0,
            "message": "Keine History gefunden",
        }

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

            # Create extractor with default state manager
            extractor = EnhancedFileExtractor()
            orchestrator = EnhancedExtractionOrchestrator(extractor)

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
