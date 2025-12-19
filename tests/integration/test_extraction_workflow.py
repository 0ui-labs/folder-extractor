"""
Integration tests for the complete extraction workflow.
"""

import os
import shutil
from pathlib import Path

import pytest

from folder_extractor.cli.app import EnhancedFolderExtractorCLI
from folder_extractor.config.settings import settings
from folder_extractor.core.state_manager import reset_state_manager


@pytest.fixture
def workflow_test_env(tmp_path):
    """Set up test environment for extraction workflow tests.

    Uses pytest's tmp_path fixture combined with a Desktop-based test directory
    for security validation compatibility.
    """
    # Reset state
    reset_state_manager()
    settings.reset_to_defaults()

    # Create test directory in Desktop (safe path) - required for security checks
    desktop = Path.home() / "Desktop"
    test_dir = desktop / f"folder_extractor_test_{tmp_path.name}"
    test_dir.mkdir(parents=True, exist_ok=True)

    original_cwd = Path.cwd()

    yield {"test_dir": test_dir, "original_cwd": original_cwd, "tmp_path": tmp_path}

    # Cleanup
    os.chdir(original_cwd)
    if test_dir.exists():
        shutil.rmtree(test_dir)


def create_test_structure(test_dir: Path) -> list:
    """Create test directory structure with files.

    Args:
        test_dir: Path to the test directory

    Returns:
        List of tuples (filepath, content) for created files
    """
    # Create subdirectories
    sub1 = test_dir / "subdir1"
    sub2 = test_dir / "subdir2"
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
        (test_dir / "root.txt", "Root file"),
    ]

    for filepath, content in files:
        filepath.write_text(content)

    return files


class TestExtractionWorkflow:
    """Test complete extraction workflow."""

    def test_basic_extraction(self, workflow_test_env):
        """Test basic file extraction."""
        test_dir = workflow_test_env["test_dir"]

        # Create test structure
        create_test_structure(test_dir)
        os.chdir(test_dir)

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

    def test_extraction_with_depth_limit(self, workflow_test_env):
        """Test extraction with depth limit."""
        test_dir = workflow_test_env["test_dir"]

        # Create test structure
        create_test_structure(test_dir)
        os.chdir(test_dir)

        # Run extraction with depth limit
        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        # Execute with depth=1 (should exclude nested files)
        result = cli.run(["--depth", "1", "--dry-run"])

        assert result == 0

    def test_extraction_with_type_filter(self, workflow_test_env):
        """Test extraction with file type filter."""
        test_dir = workflow_test_env["test_dir"]

        # Create test structure
        create_test_structure(test_dir)
        os.chdir(test_dir)

        # Run extraction filtering only txt files
        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--type", "txt", "--dry-run"])

        assert result == 0

    def test_extraction_with_sort_by_type(self, workflow_test_env):
        """Test extraction with sort by type."""
        test_dir = workflow_test_env["test_dir"]

        # Create test structure
        create_test_structure(test_dir)
        os.chdir(test_dir)

        # Run extraction with sort by type
        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--sort-by-type", "--dry-run"])

        assert result == 0

    def test_abort_handling(self, workflow_test_env):
        """Test abort functionality."""
        test_dir = workflow_test_env["test_dir"]

        # Create test structure
        create_test_structure(test_dir)
        os.chdir(test_dir)

        # Run extraction
        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        # Request abort immediately
        cli.state_manager.request_abort()

        result = cli.run(["--dry-run"])

        # Should still return 0 (aborted is not an error)
        assert result == 0

    def test_no_files_found(self, workflow_test_env):
        """Test when no files are found."""
        test_dir = workflow_test_env["test_dir"]

        # Create empty directory
        empty_dir = test_dir / "empty"
        empty_dir.mkdir()
        os.chdir(empty_dir)

        # Run extraction
        cli = EnhancedFolderExtractorCLI()

        result = cli.run([])

        # Should return 0 (no files is not an error)
        assert result == 0

    def test_security_validation(self, workflow_test_env):
        """Test security validation."""
        original_cwd = workflow_test_env["original_cwd"]
        tmp_path = workflow_test_env["tmp_path"]

        # Create unsafe directory using tmp_path (outside safe directories)
        unsafe_dir = tmp_path / "unsafe_test"
        unsafe_dir.mkdir(parents=True, exist_ok=True)
        os.chdir(unsafe_dir)

        try:
            # Run extraction
            cli = EnhancedFolderExtractorCLI()
            result = cli.run([])

            # Should fail with security error
            assert result == 1
        finally:
            os.chdir(original_cwd)

    def test_user_cancellation(self, workflow_test_env):
        """Test user cancellation during confirmation."""
        test_dir = workflow_test_env["test_dir"]

        # Create test structure
        create_test_structure(test_dir)
        os.chdir(test_dir)

        # Run extraction
        cli = EnhancedFolderExtractorCLI()

        # Mock confirmation to decline
        cli.interface.confirm_operation = lambda x: False

        result = cli.run([])

        # Should return 0 (cancellation is not an error)
        assert result == 0


class TestUndoWorkflow:
    """Test undo functionality."""

    def test_undo_no_history(self, workflow_test_env):
        """Test undo when no history exists."""
        test_dir = workflow_test_env["test_dir"]
        os.chdir(test_dir)

        # Run undo
        cli = EnhancedFolderExtractorCLI()
        result = cli.run(["--undo"])

        # Should return 1 (no history to undo)
        assert result == 1

    def test_undo_with_history(self, workflow_test_env):
        """Test undo with existing history."""
        test_dir = workflow_test_env["test_dir"]
        os.chdir(test_dir)

        # Create fake history file
        import json

        history_file = test_dir / ".folder_extractor_history.json"
        history_data = {
            "zeitstempel": "2024-01-01T12:00:00",
            "version": "1.0",
            "operationen": [
                {
                    "original_pfad": str(test_dir / "subdir" / "file.txt"),
                    "neuer_pfad": str(test_dir / "file.txt"),
                }
            ],
        }

        # Create the moved file and subdirectory
        moved_file = test_dir / "file.txt"
        moved_file.write_text("test content")

        # Create the subdirectory for undo operation
        subdir = test_dir / "subdir"
        subdir.mkdir(exist_ok=True)

        # Save history
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

    def test_operation_tracking(self, workflow_test_env):
        """Test operation tracking."""
        from folder_extractor.core.state_manager import get_state_manager

        test_dir = workflow_test_env["test_dir"]
        state_manager = get_state_manager()

        # Create a file in test_dir
        sub_dir = test_dir / "subdir"
        sub_dir.mkdir()
        (sub_dir / "file.txt").write_text("content")

        os.chdir(test_dir)

        # Run extraction
        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        assert cli.run(["--dry-run"]) == 0  # CLI should succeed

        # Check operations were tracked
        all_ops = state_manager.get_all_operations()
        assert len(all_ops) > 0

        # Check operation has statistics
        for _op_id, stats in all_ops.items():
            if stats.operation_type == "extraction":
                assert stats.files_processed >= 0
                assert stats.end_time is not None
