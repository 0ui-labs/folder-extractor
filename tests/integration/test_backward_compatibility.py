"""
Test backward compatibility with legacy architecture.
"""
import os
import sys
from pathlib import Path
from unittest.mock import patch
import pytest
import json

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from folder_extractor.config.settings import settings
from folder_extractor.core.state_manager import reset_state_manager


@pytest.fixture
def compat_test_env(tmp_path):
    """Set up test environment for backward compatibility tests.

    Uses pytest's tmp_path fixture for automatic cleanup and cross-platform support.
    Patches is_safe_path to allow tmp_path as a valid test location.
    """
    # Reset state
    reset_state_manager()
    settings.reset_to_defaults()

    # Create test directory inside tmp_path (cross-platform)
    test_dir = tmp_path / f"folder_extractor_compat_{tmp_path.name}"
    test_dir.mkdir(parents=True, exist_ok=True)

    original_cwd = Path.cwd()

    # Patch is_safe_path to allow our test directory
    def mock_is_safe_path(path):
        """Allow test_dir and its subdirectories as safe paths."""
        try:
            path = Path(path).resolve()
            test_dir_resolved = test_dir.resolve()
            # Check if path is test_dir or a subdirectory of it
            return path == test_dir_resolved or test_dir_resolved in path.parents
        except Exception:
            return False

    with patch('folder_extractor.utils.path_validators.is_safe_path', mock_is_safe_path), \
         patch('folder_extractor.core.extractor.is_safe_path', mock_is_safe_path):
        yield {
            "test_dir": test_dir,
            "original_cwd": original_cwd,
            "tmp_path": tmp_path
        }

    # Cleanup: restore cwd (tmp_path is automatically cleaned up by pytest)
    os.chdir(original_cwd)


class TestBackwardCompatibility:
    """Test backward compatibility features."""

    def test_legacy_history_format_reading(self, compat_test_env):
        """Test reading history in legacy format."""
        from folder_extractor.core.file_operations import HistoryManager

        test_dir = compat_test_env["test_dir"]

        # Create legacy history file
        history_file = test_dir / ".folder_extractor_history.json"
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

        # Load history - API accepts both str and Path (backward compatibility)
        loaded = HistoryManager.load_history(str(test_dir))

        assert loaded is not None
        assert "operationen" in loaded
        assert len(loaded["operationen"]) == 1
        assert loaded["operationen"][0]["original_pfad"] == "/old/path/file.txt"

    def test_settings_migration(self, compat_test_env):
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

    def test_enhanced_cli_with_legacy_args(self, compat_test_env):
        """Test enhanced CLI with legacy command line arguments."""
        from folder_extractor.cli.app import EnhancedFolderExtractorCLI

        test_dir = compat_test_env["test_dir"]

        # Create test structure
        sub_dir = test_dir / "subdir"
        sub_dir.mkdir()
        (sub_dir / "file1.txt").write_text("content1")
        (sub_dir / "file2.pdf").write_text("content2")

        os.chdir(test_dir)

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

    @pytest.mark.skip(reason="Legacy architecture fallback feature not implemented")
    def test_main_selector_legacy_fallback(self, compat_test_env):
        """Test main selector falls back to legacy when needed."""
        import subprocess

        test_dir = compat_test_env["test_dir"]

        # Test with FOLDER_EXTRACTOR_ARCH=legacy
        env = os.environ.copy()
        env["FOLDER_EXTRACTOR_ARCH"] = "legacy"

        # Create test structure
        sub_dir = test_dir / "subdir"
        sub_dir.mkdir()
        (sub_dir / "file.txt").write_text("content")

        # Run main.py in legacy mode
        result = subprocess.run(
            [sys.executable, "-m", "folder_extractor.main_final", "--dry-run"],
            cwd=str(test_dir),
            env=env,
            capture_output=True,
            text=True
        )

        # Check it ran without errors
        assert result.returncode == 0
        assert "legacy architecture" in result.stderr.lower()

    def test_mixed_history_format(self, compat_test_env):
        """Test handling mixed format history (German and English fields)."""
        from folder_extractor.core.extractor import EnhancedFileExtractor

        test_dir = compat_test_env["test_dir"]

        # Create mixed format history
        history_file = test_dir / ".folder_extractor_history.json"
        mixed_history = {
            "zeitstempel": "2024-01-01T12:00:00",
            "version": "1.0",
            "operationen": [
                {
                    # German format
                    "original_pfad": str(test_dir / "subdir" / "file1.txt"),
                    "neuer_pfad": str(test_dir / "file1.txt")
                },
                {
                    # English format (hypothetical future version)
                    "original_path": str(test_dir / "subdir" / "file2.txt"),
                    "new_path": str(test_dir / "file2.txt")
                }
            ]
        }

        # Create moved files
        (test_dir / "file1.txt").write_text("content1")
        (test_dir / "file2.txt").write_text("content2")

        # Create subdir
        subdir = test_dir / "subdir"
        subdir.mkdir()

        # Save history
        history_file.write_text(json.dumps(mixed_history))

        # Test undo works with both formats - API accepts str (backward compatibility)
        extractor = EnhancedFileExtractor()
        result = extractor.undo_last_operation(str(test_dir))

        assert result["status"] == "success"
        assert result["restored"] == 2

    def test_settings_compatibility(self, compat_test_env):
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

    def test_string_path_acceptance_in_extractor(self, compat_test_env):
        """Test dass EnhancedFileExtractor String-Pfade akzeptiert.

        Dies ist ein expliziter Backward-Kompatibilitäts-Test, der sicherstellt,
        dass die API weiterhin String-Eingaben akzeptiert und intern zu Path
        konvertiert wird. Vergleicht String- und Path-Aufrufe auf Äquivalenz.
        """
        from folder_extractor.core.extractor import EnhancedFileExtractor

        test_dir = compat_test_env["test_dir"]

        # Create test structure
        sub_dir = test_dir / "subdir"
        sub_dir.mkdir()
        (sub_dir / "file.txt").write_text("content")

        os.chdir(test_dir)

        extractor = EnhancedFileExtractor()

        # Test with String path (backward compatibility)
        files_from_string = extractor.discover_files(str(test_dir))
        assert len(files_from_string) >= 1

        # Test with Path object (new style)
        files_from_path = extractor.discover_files(test_dir)
        assert len(files_from_path) >= 1

        # Verify: String and Path input produce identical results
        # This confirms internal conversion to Path is consistent
        assert files_from_string == files_from_path, (
            "String and Path inputs should produce identical file lists"
        )

        # Verify: Returned paths are strings (API contract)
        for file_path in files_from_string:
            assert isinstance(file_path, str), (
                f"Expected str, got {type(file_path).__name__}"
            )

        # Verify: Returned paths are valid and can be converted to Path
        for file_path in files_from_string:
            converted = Path(file_path)
            assert converted.exists(), f"Path should exist: {file_path}"

    def test_string_path_acceptance_in_orchestrator(self, compat_test_env):
        """Test dass EnhancedExtractionOrchestrator String-Pfade akzeptiert.

        Dies ist ein expliziter Backward-Kompatibilitäts-Test, der sicherstellt,
        dass die Orchestrator-API weiterhin String-Eingaben akzeptiert und intern
        zu Path konvertiert wird. Vergleicht String- und Path-Aufrufe auf Äquivalenz.
        """
        from folder_extractor.core.extractor import (
            EnhancedFileExtractor,
            EnhancedExtractionOrchestrator
        )
        from folder_extractor.core.state_manager import reset_state_manager

        test_dir = compat_test_env["test_dir"]

        # Create test structure
        sub_dir = test_dir / "subdir"
        sub_dir.mkdir()
        (sub_dir / "file1.txt").write_text("content1")
        (sub_dir / "file2.txt").write_text("content2")

        os.chdir(test_dir)

        # Use dry_run mode for both tests
        settings.set("dry_run", True)

        # Test 1: String path (backward compatibility)
        reset_state_manager()
        extractor_str = EnhancedFileExtractor()
        orchestrator_str = EnhancedExtractionOrchestrator(extractor_str)

        result_from_string = orchestrator_str.execute_extraction(
            str(test_dir),
            confirmation_callback=lambda x: True
        )

        # Test 2: Path object (new style)
        reset_state_manager()
        extractor_path = EnhancedFileExtractor()
        orchestrator_path = EnhancedExtractionOrchestrator(extractor_path)

        result_from_path = orchestrator_path.execute_extraction(
            test_dir,
            confirmation_callback=lambda x: True
        )

        # Verify: Both calls return valid results
        assert result_from_string is not None
        assert result_from_path is not None

        # Verify: Both have required fields (API contract)
        required_fields = ["status", "files_found"]
        for field in required_fields:
            assert field in result_from_string, f"Missing field: {field}"
            assert field in result_from_path, f"Missing field: {field}"

        # Verify: String and Path input produce equivalent results
        # (same status, same file count - confirms consistent Path conversion)
        assert result_from_string["status"] == result_from_path["status"], (
            "String and Path inputs should produce same status"
        )
        assert result_from_string["files_found"] == result_from_path["files_found"], (
            "String and Path inputs should find same number of files"
        )

        # Verify: Operation completed successfully
        assert result_from_string["status"] == "success"
        assert result_from_string["files_found"] >= 2
