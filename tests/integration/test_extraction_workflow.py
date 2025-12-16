"""
Integration tests for the complete extraction workflow.
"""
import os
import tempfile
import shutil
from pathlib import Path
import pytest

from folder_extractor.cli.app_v2 import EnhancedFolderExtractorCLI
from folder_extractor.core.state_manager import reset_state_manager
from folder_extractor.config.settings import settings


class TestExtractionWorkflow:
    """Test complete extraction workflow."""
    
    def setup_method(self):
        """Set up test environment."""
        # Reset state
        reset_state_manager()
        settings.reset_to_defaults()
        
        # Create temporary test directory in Desktop (safe path)
        desktop = Path.home() / "Desktop"
        self.test_dir = tempfile.mkdtemp(dir=str(desktop), prefix="folder_extractor_test_")
        self.original_cwd = os.getcwd()
    
    def teardown_method(self):
        """Clean up test environment."""
        # Restore working directory
        os.chdir(self.original_cwd)
        
        # Remove test directory
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def create_test_structure(self):
        """Create test directory structure with files."""
        # Create subdirectories
        sub1 = Path(self.test_dir) / "subdir1"
        sub2 = Path(self.test_dir) / "subdir2"
        sub1_nested = sub1 / "nested"
        
        sub1.mkdir()
        sub2.mkdir()
        sub1_nested.mkdir()
        
        # Create test files
        files = [
            (sub1 / "file1.txt", "Content 1"),
            (sub1 / "file2.pdf", "PDF content"),
            (sub2 / "file3.jpg", "Image data"),
            (sub1_nested / "file4.txt", "Nested content"),
            (Path(self.test_dir) / "root.txt", "Root file"),
        ]
        
        for filepath, content in files:
            filepath.write_text(content)
        
        return files
    
    def test_basic_extraction(self):
        """Test basic file extraction."""
        # Create test structure
        self.create_test_structure()
        os.chdir(self.test_dir)
        
        # Run extraction
        cli = EnhancedFolderExtractorCLI()
        
        # Mock confirmation to auto-accept
        cli.interface.confirm_operation = lambda x: True
        
        # Execute and capture any errors
        try:
            result = cli.run(["--dry-run"])
            # Check success
            assert result == 0
        except Exception as e:
            print(f"Error during extraction: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def test_extraction_with_depth_limit(self):
        """Test extraction with depth limit."""
        # Create test structure
        self.create_test_structure()
        os.chdir(self.test_dir)
        
        # Run extraction with depth limit
        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True
        
        # Execute with depth=1 (should exclude nested files)
        result = cli.run(["--depth", "1", "--dry-run"])
        
        assert result == 0
    
    def test_extraction_with_type_filter(self):
        """Test extraction with file type filter."""
        # Create test structure
        self.create_test_structure()
        os.chdir(self.test_dir)
        
        # Run extraction filtering only txt files
        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True
        
        result = cli.run(["--type", "txt", "--dry-run"])
        
        assert result == 0
    
    def test_extraction_with_sort_by_type(self):
        """Test extraction with sort by type."""
        # Create test structure
        self.create_test_structure()
        os.chdir(self.test_dir)
        
        # Run extraction with sort by type
        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True
        
        result = cli.run(["--sort-by-type", "--dry-run"])
        
        assert result == 0
    
    def test_abort_handling(self):
        """Test abort functionality."""
        # Create test structure
        self.create_test_structure()
        os.chdir(self.test_dir)
        
        # Run extraction
        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True
        
        # Request abort immediately
        cli.state_manager.request_abort()
        
        result = cli.run(["--dry-run"])
        
        # Should still return 0 (aborted is not an error)
        assert result == 0
    
    def test_no_files_found(self):
        """Test when no files are found."""
        # Create empty directory
        empty_dir = Path(self.test_dir) / "empty"
        empty_dir.mkdir()
        os.chdir(empty_dir)
        
        # Run extraction
        cli = EnhancedFolderExtractorCLI()
        
        result = cli.run([])
        
        # Should return 0 (no files is not an error)
        assert result == 0
    
    def test_security_validation(self):
        """Test security validation."""
        # Try to run in a non-safe directory
        unsafe_dir = tempfile.mkdtemp(dir="/tmp")
        os.chdir(unsafe_dir)
        
        try:
            # Run extraction
            cli = EnhancedFolderExtractorCLI()
            result = cli.run([])
            
            # Should fail with security error
            assert result == 1
        finally:
            os.chdir(self.original_cwd)
            shutil.rmtree(unsafe_dir)
    
    def test_user_cancellation(self):
        """Test user cancellation during confirmation."""
        # Create test structure
        self.create_test_structure()
        os.chdir(self.test_dir)
        
        # Run extraction
        cli = EnhancedFolderExtractorCLI()
        
        # Mock confirmation to decline
        cli.interface.confirm_operation = lambda x: False
        
        result = cli.run([])
        
        # Should return 0 (cancellation is not an error)
        assert result == 0


class TestUndoWorkflow:
    """Test undo functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        reset_state_manager()
        settings.reset_to_defaults()
        
        # Create temporary test directory in Desktop (safe path)
        desktop = Path.home() / "Desktop"
        self.test_dir = tempfile.mkdtemp(dir=str(desktop), prefix="folder_extractor_test_")
        self.original_cwd = os.getcwd()
    
    def teardown_method(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_undo_no_history(self):
        """Test undo when no history exists."""
        os.chdir(self.test_dir)
        
        # Run undo
        cli = EnhancedFolderExtractorCLI()
        result = cli.run(["--undo"])
        
        # Should return 1 (no history to undo)
        assert result == 1
    
    def test_undo_with_history(self):
        """Test undo with existing history."""
        os.chdir(self.test_dir)
        
        # Create fake history file
        history_file = Path(self.test_dir) / ".folder_extractor_history.json"
        history_data = {
            "zeitstempel": "2024-01-01T12:00:00",
            "version": "1.0",
            "operationen": [
                {
                    "original_pfad": str(Path(self.test_dir) / "subdir" / "file.txt"),
                    "neuer_pfad": str(Path(self.test_dir) / "file.txt")
                }
            ]
        }
        
        # Create the moved file and subdirectory
        moved_file = Path(self.test_dir) / "file.txt"
        moved_file.write_text("test content")
        
        # Create the subdirectory for undo operation
        subdir = Path(self.test_dir) / "subdir"
        subdir.mkdir(exist_ok=True)
        
        # Save history
        import json
        history_file.write_text(json.dumps(history_data))
        
        # Run undo
        cli = EnhancedFolderExtractorCLI()
        result = cli.run(["--undo"])
        
        # Should succeed
        assert result == 0


class TestStateManagement:
    """Test state management integration."""
    
    def setup_method(self):
        """Set up test environment."""
        reset_state_manager()
        settings.reset_to_defaults()
    
    def test_state_persistence(self):
        """Test that state persists across operations."""
        from folder_extractor.core.state_manager import get_state_manager
        
        # Set some state
        state_manager = get_state_manager()
        state_manager.set_value("test_key", "test_value")
        
        # Create new CLI instance
        cli = EnhancedFolderExtractorCLI()
        
        # State should be available
        assert cli.state_manager.get_value("test_key") == "test_value"
    
    def test_operation_tracking(self):
        """Test operation tracking."""
        from folder_extractor.core.state_manager import get_state_manager
        
        state_manager = get_state_manager()
        
        # Create test directory
        with tempfile.TemporaryDirectory() as test_dir:
            # Create a file
            sub_dir = Path(test_dir) / "subdir"
            sub_dir.mkdir()
            (sub_dir / "file.txt").write_text("content")
            
            os.chdir(test_dir)
            
            # Run extraction
            cli = EnhancedFolderExtractorCLI()
            cli.interface.confirm_operation = lambda x: True
            
            result = cli.run(["--dry-run"])
            
            # Check operations were tracked
            all_ops = state_manager.get_all_operations()
            assert len(all_ops) > 0
            
            # Check operation has statistics
            for op_id, stats in all_ops.items():
                if stats.operation_type == "extraction":
                    assert stats.files_processed >= 0
                    assert stats.end_time is not None