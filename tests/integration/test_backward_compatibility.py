"""
Test backward compatibility with legacy architecture.
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path
import pytest
import json

# Add parent to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from folder_extractor.config.settings import settings
from folder_extractor.core.state_manager import reset_state_manager


class TestBackwardCompatibility:
    """Test backward compatibility features."""
    
    def setup_method(self):
        """Set up test environment."""
        # Reset state
        reset_state_manager()
        settings.reset_to_defaults()
        
        # Create temporary test directory in Desktop (safe path)
        desktop = Path.home() / "Desktop"
        self.test_dir = tempfile.mkdtemp(dir=str(desktop), prefix="folder_extractor_compat_")
        self.original_cwd = os.getcwd()
    
    def teardown_method(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_legacy_history_format_reading(self):
        """Test reading history in legacy format."""
        from folder_extractor.core.file_operations import HistoryManager
        
        # Create legacy history file
        history_file = Path(self.test_dir) / ".folder_extractor_history.json"
        legacy_history = {
            "zeitstempel": "2024-01-01T12:00:00",
            "version": "1.0",
            "operationen": [
                {
                    "original_pfad": "/old/path/file.txt",
                    "neuer_pfad": "/new/path/file.txt",
                    "original_name": "file.txt",
                    "neuer_name": "file.txt",
                    "zeitstempel": "2024-01-01T12:00:00"
                }
            ]
        }
        
        history_file.write_text(json.dumps(legacy_history, ensure_ascii=False))
        
        # Load history
        loaded = HistoryManager.load_history(self.test_dir)
        
        assert loaded is not None
        assert "operationen" in loaded
        assert len(loaded["operationen"]) == 1
        assert loaded["operationen"][0]["original_pfad"] == "/old/path/file.txt"
    
    def test_settings_migration(self):
        """Test settings migration to state manager."""
        from folder_extractor.core.migration import MigrationHelper
        from folder_extractor.core.state_manager import get_state_manager
        
        # Set some settings
        settings.set("max_depth", 5)
        settings.set("file_type_filter", "pdf")
        settings.set("dry_run", True)
        
        # Migrate
        MigrationHelper.migrate_settings()
        
        # Check state manager has settings
        state_manager = get_state_manager()
        assert state_manager.get_value("max_depth") == 5
        assert state_manager.get_value("file_type_filter") == "pdf"
        assert state_manager.get_value("dry_run") is True
    
    def test_extractor_adapter(self):
        """Test extractor adapter for new interface."""
        from folder_extractor.core.migration import ExtractorAdapter
        from folder_extractor.core.extractor_v2 import EnhancedFileExtractor
        
        # Create enhanced extractor
        enhanced_extractor = EnhancedFileExtractor()
        
        # Create adapter
        adapter = ExtractorAdapter(enhanced_extractor)
        
        # Test methods exist
        assert hasattr(adapter, "extract_files")
        assert hasattr(adapter, "undo_last_operation")
    
    def test_enhanced_cli_with_legacy_args(self):
        """Test enhanced CLI with legacy command line arguments."""
        from folder_extractor.cli.app_v2 import EnhancedFolderExtractorCLI
        
        # Create test structure
        sub_dir = Path(self.test_dir) / "subdir"
        sub_dir.mkdir()
        (sub_dir / "file1.txt").write_text("content1")
        (sub_dir / "file2.pdf").write_text("content2")
        
        os.chdir(self.test_dir)
        
        # Test legacy arguments work with new CLI
        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True
        
        # Test various legacy argument combinations
        result = cli.run(["--dry-run", "--depth", "2"])
        assert result == 0
        
        result = cli.run(["--dry-run", "--type", "txt"])
        assert result == 0
        
        result = cli.run(["--dry-run", "--sort-by-type"])
        assert result == 0
    
    def test_main_selector_legacy_fallback(self):
        """Test main selector falls back to legacy when needed."""
        import subprocess
        
        # Test with FOLDER_EXTRACTOR_ARCH=legacy
        env = os.environ.copy()
        env["FOLDER_EXTRACTOR_ARCH"] = "legacy"
        
        # Create test structure
        sub_dir = Path(self.test_dir) / "subdir"
        sub_dir.mkdir()
        (sub_dir / "file.txt").write_text("content")
        
        # Run main.py in legacy mode
        result = subprocess.run(
            [sys.executable, "-m", "folder_extractor.main_final", "--dry-run"],
            cwd=self.test_dir,
            env=env,
            capture_output=True,
            text=True
        )
        
        # Check it ran without errors
        assert result.returncode == 0
        assert "legacy architecture" in result.stderr.lower()
    
    def test_mixed_history_format(self):
        """Test handling mixed format history (German and English fields)."""
        from folder_extractor.core.extractor_v2 import EnhancedFileExtractor
        
        # Create mixed format history
        history_file = Path(self.test_dir) / ".folder_extractor_history.json"
        mixed_history = {
            "zeitstempel": "2024-01-01T12:00:00",
            "version": "1.0",
            "operationen": [
                {
                    # German format
                    "original_pfad": str(Path(self.test_dir) / "subdir" / "file1.txt"),
                    "neuer_pfad": str(Path(self.test_dir) / "file1.txt")
                },
                {
                    # English format (hypothetical future version)
                    "original_path": str(Path(self.test_dir) / "subdir" / "file2.txt"),
                    "new_path": str(Path(self.test_dir) / "file2.txt")
                }
            ]
        }
        
        # Create moved files
        (Path(self.test_dir) / "file1.txt").write_text("content1")
        (Path(self.test_dir) / "file2.txt").write_text("content2")
        
        # Create subdir
        subdir = Path(self.test_dir) / "subdir"
        subdir.mkdir()
        
        # Save history
        history_file.write_text(json.dumps(mixed_history))
        
        # Test undo works with both formats
        extractor = EnhancedFileExtractor()
        result = extractor.undo_last_operation(self.test_dir)
        
        assert result["status"] == "success"
        assert result["restored"] == 2
    
    def test_settings_compatibility(self):
        """Test that settings work with both old and new architecture."""
        # Test basic settings operations
        settings.set("max_depth", 3)
        settings.set("file_type_filter", "pdf")
        settings.set("include_hidden", True)
        settings.set("sort_by_type", True)
        
        # Verify settings
        assert settings.get("max_depth") == 3
        assert settings.get("file_type_filter") == "pdf"
        assert settings.get("include_hidden") is True
        assert settings.get("sort_by_type") is True
        
        # Test settings migration to state manager
        from folder_extractor.core.migration import MigrationHelper
        from folder_extractor.core.state_manager import get_state_manager
        
        MigrationHelper.migrate_settings()
        
        # Verify state manager has the same settings
        state_manager = get_state_manager()
        assert state_manager.get_value("max_depth") == 3
        assert state_manager.get_value("file_type_filter") == "pdf"