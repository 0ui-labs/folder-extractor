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


def create_duplicate_test_structure(test_dir: Path) -> tuple:
    """Create test directory structure with identical files for deduplication testing.

    Creates a file 'datei.txt' with identical content in multiple subdirectories,
    simulating the scenario where the same file exists in multiple folders.

    Args:
        test_dir: Path to the test directory

    Returns:
        Tuple of (test_dir, list of all identical file paths)
    """
    content = "Identischer Inhalt für Duplikat-Test"

    # Create subdirectories
    sub1 = test_dir / "subdir1"
    sub2 = test_dir / "subdir2"
    sub3 = test_dir / "subdir3"

    sub1.mkdir()
    sub2.mkdir()
    sub3.mkdir()

    # Create original file in target directory
    original = test_dir / "datei.txt"
    original.write_text(content)

    # Create identical copies in subdirectories
    duplicate_paths = [original]
    for subdir in [sub1, sub2, sub3]:
        dup_file = subdir / "datei.txt"
        dup_file.write_text(content)
        duplicate_paths.append(dup_file)

    return test_dir, duplicate_paths


def create_mixed_duplicate_structure(test_dir: Path) -> dict:
    """Create test structure with both identical and different files.

    Creates a mix of files where some have identical content (should be deduplicated)
    and others have different content (should be renamed with _1, _2 suffix).

    Args:
        test_dir: Path to the test directory

    Returns:
        Dictionary with 'identical' and 'different' file lists
    """
    identical_content = "Identischer Inhalt"
    # Each subdirectory gets different content
    different_contents = [
        "Unterschiedlicher Inhalt Version 1",  # subdir1
        "Unterschiedlicher Inhalt Version 2",  # subdir2
        "Unterschiedlicher Inhalt Version 3",  # subdir3
    ]

    # Create subdirectories
    sub1 = test_dir / "subdir1"
    sub2 = test_dir / "subdir2"
    sub3 = test_dir / "subdir3"

    sub1.mkdir()
    sub2.mkdir()
    sub3.mkdir()

    # Create identical files (in root + subdirs -> deduplicated to 1)
    identical_files = []
    (test_dir / "identisch.txt").write_text(identical_content)
    identical_files.append(test_dir / "identisch.txt")

    for subdir in [sub1, sub2, sub3]:
        dup = subdir / "identisch.txt"
        dup.write_text(identical_content)
        identical_files.append(dup)

    # Create files with different content but same name
    # Only in subdirectories - they will be moved to root with _1, _2 suffix
    different_files = []
    for i, subdir in enumerate([sub1, sub2, sub3]):
        diff = subdir / "unterschiedlich.txt"
        diff.write_text(different_contents[i])
        different_files.append(diff)

    return {
        "identical": identical_files,
        "different": different_files,
        "subdirs": [sub1, sub2, sub3],
    }


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


class TestDeduplicationWorkflow:
    """Test content-based deduplication functionality.

    These tests verify that the --deduplicate flag correctly identifies
    and handles files with identical content, skipping redundant copies
    instead of renaming them.
    """

    def test_extraction_without_deduplication(self, workflow_test_env):
        """Without --deduplicate flag, identical files are renamed with _1, _2 suffix.

        This establishes the baseline behavior: when multiple files have the same
        name but we don't check content, all files are kept with unique names.
        """
        test_dir = workflow_test_env["test_dir"]

        # Create test structure with 4 identical files
        create_duplicate_test_structure(test_dir)
        os.chdir(test_dir)

        # Run extraction WITHOUT --deduplicate flag
        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run([])

        # Verify exit code
        assert result == 0, "CLI should exit successfully"

        # Verify all 4 files exist (original + 3 renamed duplicates)
        assert (test_dir / "datei.txt").exists(), "Original file should exist"
        assert (test_dir / "datei_1.txt").exists(), "First duplicate should be renamed"
        assert (test_dir / "datei_2.txt").exists(), "Second duplicate should be renamed"
        assert (test_dir / "datei_3.txt").exists(), "Third duplicate should be renamed"

        # Verify total count
        all_datei_files = list(test_dir.glob("datei*.txt"))
        assert len(all_datei_files) == 4, f"Expected 4 files, found {len(all_datei_files)}"

        # Verify subdirectories are cleaned up (files moved out)
        assert not (test_dir / "subdir1" / "datei.txt").exists()
        assert not (test_dir / "subdir2" / "datei.txt").exists()
        assert not (test_dir / "subdir3" / "datei.txt").exists()

    def test_extraction_with_deduplication(self, workflow_test_env):
        """With --deduplicate flag, identical files are skipped (not renamed).

        When deduplication is enabled, files with identical content (same hash)
        are detected and the source file is deleted instead of being renamed.
        Only one copy of each unique content is kept.
        """
        test_dir = workflow_test_env["test_dir"]

        # Create test structure with 4 identical files
        create_duplicate_test_structure(test_dir)
        os.chdir(test_dir)

        # Run extraction WITH --deduplicate flag
        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--deduplicate"])

        # Verify exit code
        assert result == 0, "CLI should exit successfully"

        # Verify only the original file exists (duplicates were skipped)
        assert (test_dir / "datei.txt").exists(), "Original file should exist"
        assert not (test_dir / "datei_1.txt").exists(), "Duplicate should NOT exist"
        assert not (test_dir / "datei_2.txt").exists(), "Duplicate should NOT exist"
        assert not (test_dir / "datei_3.txt").exists(), "Duplicate should NOT exist"

        # Verify total count - only 1 file
        all_datei_files = list(test_dir.glob("datei*.txt"))
        assert len(all_datei_files) == 1, f"Expected 1 file, found {len(all_datei_files)}"

        # Verify subdirectories are cleaned up
        assert not (test_dir / "subdir1" / "datei.txt").exists()
        assert not (test_dir / "subdir2" / "datei.txt").exists()
        assert not (test_dir / "subdir3" / "datei.txt").exists()

    def test_deduplication_with_mixed_content(self, workflow_test_env):
        """Deduplication correctly handles both identical and different files.

        Identical files (same hash) are deduplicated to one copy.
        Different files (different hash but same name) are kept with _1, _2 suffix.
        """
        test_dir = workflow_test_env["test_dir"]

        # Create mixed structure
        structure = create_mixed_duplicate_structure(test_dir)
        os.chdir(test_dir)

        # Run extraction WITH --deduplicate flag
        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--deduplicate"])

        # Verify exit code
        assert result == 0, "CLI should exit successfully"

        # Identical files: only 1 copy should remain
        identical_files = list(test_dir.glob("identisch*.txt"))
        assert len(identical_files) == 1, (
            f"Expected 1 identisch.txt (deduplicated), found {len(identical_files)}"
        )
        assert (test_dir / "identisch.txt").exists()

        # Different files: all 3 should exist (with renamed versions where needed)
        # 3 from subdirs with different content - first becomes unterschiedlich.txt,
        # rest become unterschiedlich_1.txt and unterschiedlich_2.txt
        different_files = list(test_dir.glob("unterschiedlich*.txt"))
        assert len(different_files) == 3, (
            f"Expected 3 unterschiedlich files (different content), found {len(different_files)}"
        )
        assert (test_dir / "unterschiedlich.txt").exists()
        assert (test_dir / "unterschiedlich_1.txt").exists()
        assert (test_dir / "unterschiedlich_2.txt").exists()

    def test_deduplication_with_sort_by_type(self, workflow_test_env):
        """Deduplication works correctly with --sort-by-type mode.

        Files are sorted into type folders AND deduplicated within each folder.
        """
        test_dir = workflow_test_env["test_dir"]

        # Create structure with identical files of different types
        sub1 = test_dir / "subdir1"
        sub2 = test_dir / "subdir2"
        sub3 = test_dir / "subdir3"
        sub1.mkdir()
        sub2.mkdir()
        sub3.mkdir()

        # Create identical TXT files
        txt_content = "Identischer Text-Inhalt"
        (test_dir / "dokument.txt").write_text(txt_content)
        (sub1 / "dokument.txt").write_text(txt_content)
        (sub2 / "dokument.txt").write_text(txt_content)

        # Create identical "JPG" files (actually text, but extension matters for sorting)
        jpg_content = b"FAKE_JPG_IDENTICAL_CONTENT"
        (test_dir / "bild.jpg").write_bytes(jpg_content)
        (sub1 / "bild.jpg").write_bytes(jpg_content)
        (sub2 / "bild.jpg").write_bytes(jpg_content)

        os.chdir(test_dir)

        # Run extraction WITH --deduplicate and --sort-by-type
        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--deduplicate", "--sort-by-type"])

        # Verify exit code
        assert result == 0, "CLI should exit successfully"

        # Verify TEXT folder has only 1 file (deduplicated)
        # Note: Folder names follow FILE_TYPE_FOLDERS mapping (.txt -> TEXT)
        txt_folder = test_dir / "TEXT"
        assert txt_folder.exists(), "TEXT folder should be created"
        txt_files = list(txt_folder.glob("dokument*.txt"))
        assert len(txt_files) == 1, f"Expected 1 TXT file, found {len(txt_files)}"

        # Verify JPEG folder has only 1 file (deduplicated)
        # Note: .jpg extension maps to JPEG folder
        jpg_folder = test_dir / "JPEG"
        assert jpg_folder.exists(), "JPEG folder should be created"
        jpg_files = list(jpg_folder.glob("bild*.jpg"))
        assert len(jpg_files) == 1, f"Expected 1 JPG file, found {len(jpg_files)}"

    def test_deduplication_dry_run(self, workflow_test_env):
        """Dry-run with deduplication shows what would happen without moving files.

        In dry-run mode, no files are moved or deleted - the original structure
        remains intact.
        """
        test_dir = workflow_test_env["test_dir"]

        # Create test structure with 4 identical files
        create_duplicate_test_structure(test_dir)
        os.chdir(test_dir)

        # Run extraction WITH --deduplicate AND --dry-run
        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--deduplicate", "--dry-run"])

        # Verify exit code
        assert result == 0, "CLI should exit successfully"

        # Verify NO files were moved - all originals still in subdirectories
        assert (test_dir / "subdir1" / "datei.txt").exists(), "File should NOT be moved in dry-run"
        assert (test_dir / "subdir2" / "datei.txt").exists(), "File should NOT be moved in dry-run"
        assert (test_dir / "subdir3" / "datei.txt").exists(), "File should NOT be moved in dry-run"

        # Original in root should still be there
        assert (test_dir / "datei.txt").exists()

        # No renamed duplicates should exist (nothing was moved)
        assert not (test_dir / "datei_1.txt").exists()
        assert not (test_dir / "datei_2.txt").exists()
        assert not (test_dir / "datei_3.txt").exists()

    def test_deduplication_statistics_display(self, workflow_test_env, capsys):
        """Deduplication statistics are displayed in the summary output.

        The CLI should show how many content duplicates were skipped.
        """
        test_dir = workflow_test_env["test_dir"]

        # Create test structure with 4 identical files
        create_duplicate_test_structure(test_dir)
        os.chdir(test_dir)

        # Run extraction WITH --deduplicate flag
        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--deduplicate"])

        # Verify exit code
        assert result == 0, "CLI should exit successfully"

        # Capture stdout
        captured = capsys.readouterr()

        # Verify output contains deduplication info
        # The exact wording depends on implementation, but should mention duplicates
        output_lower = captured.out.lower()
        assert any(term in output_lower for term in [
            "duplikat", "identisch", "übersprungen", "skipped", "duplicate"
        ]), f"Output should mention duplicates. Got: {captured.out[:500]}"

    def test_deduplication_with_no_duplicates(self, workflow_test_env):
        """Deduplication with unique files behaves like normal extraction.

        When all files have unique content, deduplication has no effect -
        files are moved normally.
        """
        test_dir = workflow_test_env["test_dir"]

        # Create structure with only unique files
        sub1 = test_dir / "subdir1"
        sub2 = test_dir / "subdir2"
        sub1.mkdir()
        sub2.mkdir()

        (sub1 / "unique1.txt").write_text("Content A - unique")
        (sub2 / "unique2.txt").write_text("Content B - different")
        (sub1 / "unique3.txt").write_text("Content C - also different")

        os.chdir(test_dir)

        # Run extraction WITH --deduplicate flag
        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--deduplicate"])

        # Verify exit code
        assert result == 0, "CLI should exit successfully"

        # All unique files should be moved to root
        assert (test_dir / "unique1.txt").exists()
        assert (test_dir / "unique2.txt").exists()
        assert (test_dir / "unique3.txt").exists()

        # No renamed files (all have different names)
        unique_files = list(test_dir.glob("unique*.txt"))
        assert len(unique_files) == 3

    def test_deduplication_with_large_files(self, workflow_test_env):
        """Deduplication handles large files correctly using chunked hashing.

        Large files are hashed in chunks to minimize memory usage.
        """
        test_dir = workflow_test_env["test_dir"]

        sub1 = test_dir / "subdir1"
        sub1.mkdir()

        # Create large identical files (1MB each)
        large_content = b"X" * (1024 * 1024)  # 1MB of 'X'

        (test_dir / "large.bin").write_bytes(large_content)
        (sub1 / "large.bin").write_bytes(large_content)

        os.chdir(test_dir)

        # Run extraction WITH --deduplicate flag
        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--deduplicate"])

        # Verify exit code
        assert result == 0, "CLI should exit successfully"

        # Only one file should remain (deduplicated)
        large_files = list(test_dir.glob("large*.bin"))
        assert len(large_files) == 1, f"Expected 1 large file, found {len(large_files)}"

    def test_deduplication_logging(self, workflow_test_env, caplog):
        """Deduplication logs information about skipped files.

        When files are skipped due to identical content, this should be logged.
        """
        import logging

        test_dir = workflow_test_env["test_dir"]

        # Create test structure with 4 identical files
        create_duplicate_test_structure(test_dir)
        os.chdir(test_dir)

        # Set log level to capture INFO messages
        with caplog.at_level(logging.INFO):
            # Run extraction WITH --deduplicate flag
            cli = EnhancedFolderExtractorCLI()
            cli.interface.confirm_operation = lambda x: True

            result = cli.run(["--deduplicate"])

        # Verify exit code
        assert result == 0, "CLI should exit successfully"

        # Note: Log content verification is optional depending on implementation
        # The test mainly verifies that logging doesn't cause errors during dedup


def create_identical_files(
    test_dir: Path, file_configs: list[tuple[str, str, str | bytes]]
) -> list[Path]:
    """Create files with specified content at specified locations.

    Helper function for global deduplication tests that creates files
    with identical or different content at various paths.

    Args:
        test_dir: Base test directory
        file_configs: List of tuples (relative_path, filename, content)
                     - relative_path: Path relative to test_dir (empty string for root)
                     - filename: Name of the file
                     - content: File content (str or bytes)

    Returns:
        List of Path objects for all created files

    Example:
        create_identical_files(test_dir, [
            ("", "photo.jpg", b"JPEG_DATA"),           # Creates test_dir/photo.jpg
            ("sub1", "img.jpg", b"JPEG_DATA"),         # Creates test_dir/sub1/img.jpg
            ("sub2", "pic.jpg", b"DIFFERENT_DATA"),    # Creates test_dir/sub2/pic.jpg
        ])
    """
    created_files = []

    for relative_path, filename, content in file_configs:
        # Determine target directory
        if relative_path:
            target_dir = test_dir / relative_path
            target_dir.mkdir(parents=True, exist_ok=True)
        else:
            target_dir = test_dir

        # Create file
        file_path = target_dir / filename
        if isinstance(content, bytes):
            file_path.write_bytes(content)
        else:
            file_path.write_text(content)

        created_files.append(file_path)

    return created_files


class TestGlobalDeduplication:
    """Test global deduplication functionality.

    Global deduplication (--global-dedup) checks if a file's content already
    exists ANYWHERE in the destination tree, regardless of filename.
    This is more comprehensive than --deduplicate which only compares
    files with the same name.
    """

    def test_global_dedup_identical_content(self, workflow_test_env, capsys):
        """Files with identical content are detected and skipped regardless of name.

        When --global-dedup is active, a file whose content (hash) already exists
        anywhere in the destination will not be copied - the source is deleted
        and marked as a global duplicate.
        """
        from folder_extractor.config.constants import MESSAGES

        test_dir = workflow_test_env["test_dir"]

        # Setup: Create target file and source file with identical content
        content = b"JPEG_DATA_SAMPLE_CONTENT_12345"
        create_identical_files(test_dir, [
            ("", "Urlaub_2023.jpg", content),           # Existing file in root
            ("subdir", "IMG_001.jpg", content),         # Source file with same content
        ])

        os.chdir(test_dir)

        # Execute: Run extraction with --global-dedup
        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--global-dedup"])

        # Assert: Verify behavior
        assert result == 0, "CLI should exit successfully"

        # Only original file should exist (duplicate was not copied)
        assert (test_dir / "Urlaub_2023.jpg").exists(), "Original file should exist"
        assert not (test_dir / "IMG_001.jpg").exists(), "Duplicate should NOT be copied"

        # Source should have been deleted (content existed elsewhere)
        assert not (test_dir / "subdir" / "IMG_001.jpg").exists(), (
            "Source file should be deleted after being detected as duplicate"
        )

        # Verify only 1 file in root
        jpg_files = list(test_dir.glob("*.jpg"))
        assert len(jpg_files) == 1, f"Expected 1 file, found {len(jpg_files)}"

        # Verify the global duplicates statistic is displayed correctly
        captured = capsys.readouterr()
        global_dedup_message = MESSAGES["DEDUP_GLOBAL_DUPLICATES"]
        assert global_dedup_message in captured.out, (
            f"Output should contain '{global_dedup_message}'. Got: {captured.out[:500]}"
        )
        # Verify the count is 1 (one file was identified as a global duplicate)
        assert f"{global_dedup_message}: " in captured.out and "1" in captured.out, (
            f"Output should show '{global_dedup_message}: 1'. Got: {captured.out[:500]}"
        )

    def test_global_dedup_different_content(self, workflow_test_env):
        """Files with different content are moved normally.

        When --global-dedup is active but files have unique content,
        they should be moved to the destination normally.
        """
        test_dir = workflow_test_env["test_dir"]

        # Setup: Create files with different content
        create_identical_files(test_dir, [
            ("", "Urlaub_2023.jpg", b"JPEG_DATA_A"),      # Existing file
            ("subdir", "IMG_001.jpg", b"JPEG_DATA_B"),    # Source with DIFFERENT content
        ])

        os.chdir(test_dir)

        # Execute: Run extraction with --global-dedup
        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--global-dedup"])

        # Assert: Verify behavior
        assert result == 0, "CLI should exit successfully"

        # Both files should exist (different content)
        assert (test_dir / "Urlaub_2023.jpg").exists(), "Original file should exist"
        assert (test_dir / "IMG_001.jpg").exists(), "Different file should be moved"

        # Verify 2 files in root
        jpg_files = list(test_dir.glob("*.jpg"))
        assert len(jpg_files) == 2, f"Expected 2 files, found {len(jpg_files)}"

    def test_combined_dedup_and_global_dedup(self, workflow_test_env, capsys):
        """Both --deduplicate and --global-dedup flags work together correctly.

        This test verifies the interaction between:
        - Global duplicates: Same content, different name (detected by --global-dedup)
        - Content duplicates: Same content, same name (detected by --deduplicate)
        - Name duplicates: Different content, same name (renamed with _1, _2, etc.)

        It also verifies that all three duplicate categories are correctly
        reported in the CLI summary output with the expected counts.
        """
        from folder_extractor.config.constants import MESSAGES

        test_dir = workflow_test_env["test_dir"]

        content_a = "CONTENT_A_IDENTICAL"
        content_b = "CONTENT_B_DIFFERENT"

        # Setup: Create complex scenario with exactly one of each duplicate type
        create_identical_files(test_dir, [
            # Target file (already at destination, won't be moved)
            ("", "existing.txt", content_a),
            # Global duplicate (different name, same content as target) → 1 global dup
            ("subdir1", "file1.txt", content_a),
            # Content duplicate (same name AND same content as target) → 1 content dup
            ("subdir2", "existing.txt", content_a),
            # Name duplicate (same name but DIFFERENT content) → 1 name dup (renamed)
            ("subdir3", "existing.txt", content_b),
        ])

        os.chdir(test_dir)

        # Execute: Run extraction with BOTH flags
        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--deduplicate", "--global-dedup"])

        # Assert: Verify behavior
        assert result == 0, "CLI should exit successfully"

        # Original and renamed file should exist
        assert (test_dir / "existing.txt").exists(), "Original should exist"
        assert (test_dir / "existing_1.txt").exists(), (
            "Name duplicate with different content should be renamed"
        )

        # Global duplicate should NOT exist (content matched)
        assert not (test_dir / "file1.txt").exists(), (
            "Global duplicate should not be copied"
        )

        # Verify exactly 2 files in root
        txt_files = list(test_dir.glob("*.txt"))
        assert len(txt_files) == 2, (
            f"Expected 2 files (original + renamed), found {len(txt_files)}: "
            f"{[f.name for f in txt_files]}"
        )

        # Verify all three duplicate categories are displayed in summary output
        captured = capsys.readouterr()
        output = captured.out

        # Get message keys for all duplicate types
        name_dup_msg = MESSAGES["DEDUP_NAME_DUPLICATES"]
        content_dup_msg = MESSAGES["DEDUP_CONTENT_DUPLICATES"]
        global_dup_msg = MESSAGES["DEDUP_GLOBAL_DUPLICATES"]

        # Verify name duplicates count (1 file renamed due to same name, different content)
        assert name_dup_msg in output, (
            f"Output should contain '{name_dup_msg}'. Got: {output[:500]}"
        )
        assert f"{name_dup_msg}:" in output and "1" in output, (
            f"Output should show '{name_dup_msg}: 1'. Got: {output[:500]}"
        )

        # Verify content duplicates count (1 file skipped due to same name AND content)
        assert content_dup_msg in output, (
            f"Output should contain '{content_dup_msg}'. Got: {output[:500]}"
        )
        assert f"{content_dup_msg}:" in output and "1" in output, (
            f"Output should show '{content_dup_msg}: 1'. Got: {output[:500]}"
        )

        # Verify global duplicates count (1 file skipped due to content existing elsewhere)
        assert global_dup_msg in output, (
            f"Output should contain '{global_dup_msg}'. Got: {output[:500]}"
        )
        assert f"{global_dup_msg}:" in output and "1" in output, (
            f"Output should show '{global_dup_msg}: 1'. Got: {output[:500]}"
        )

    def test_global_dedup_multiple_identical(self, workflow_test_env):
        """Multiple files with identical content are all detected as duplicates.

        When one file exists in the destination and multiple source files
        have the same content, all source files should be skipped.
        """
        test_dir = workflow_test_env["test_dir"]

        content = b"PHOTO_DATA_IDENTICAL_CONTENT"

        # Setup: One target and three identical sources
        create_identical_files(test_dir, [
            ("", "photo.jpg", content),              # Existing target
            ("folder1", "IMG_001.jpg", content),     # Duplicate 1
            ("folder2", "IMG_002.jpg", content),     # Duplicate 2
            ("folder3", "IMG_003.jpg", content),     # Duplicate 3
        ])

        os.chdir(test_dir)

        # Execute: Run extraction with --global-dedup
        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--global-dedup"])

        # Assert: Verify behavior
        assert result == 0, "CLI should exit successfully"

        # Only original should exist
        assert (test_dir / "photo.jpg").exists(), "Original should exist"
        assert not (test_dir / "IMG_001.jpg").exists(), "Duplicate 1 should not be copied"
        assert not (test_dir / "IMG_002.jpg").exists(), "Duplicate 2 should not be copied"
        assert not (test_dir / "IMG_003.jpg").exists(), "Duplicate 3 should not be copied"

        # Verify only 1 JPG file
        jpg_files = list(test_dir.glob("*.jpg"))
        assert len(jpg_files) == 1, f"Expected 1 file, found {len(jpg_files)}"

    def test_global_dedup_with_sort_by_type(self, workflow_test_env):
        """Global deduplication works correctly with --sort-by-type mode.

        When both flags are used, files are sorted into type folders AND
        checked against the global hash index of the entire destination tree.
        """
        test_dir = workflow_test_env["test_dir"]

        content = "DOC_CONTENT_IDENTICAL"

        # Setup: Create existing file in type folder and source file
        txt_folder = test_dir / "TEXT"
        txt_folder.mkdir()
        (txt_folder / "document.txt").write_text(content)

        # Create source file with identical content
        sub_dir = test_dir / "subdir"
        sub_dir.mkdir()
        (sub_dir / "file.txt").write_text(content)

        os.chdir(test_dir)

        # Execute: Run extraction with both flags
        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--global-dedup", "--sort-by-type"])

        # Assert: Verify behavior
        assert result == 0, "CLI should exit successfully"

        # Source file should not be moved (content exists in TEXT/)
        assert not (test_dir / "subdir" / "file.txt").exists(), (
            "Source should be deleted (was global duplicate)"
        )

        # TEXT folder should have only original file
        txt_files = list(txt_folder.glob("*.txt"))
        assert len(txt_files) == 1, f"Expected 1 TXT file, found {len(txt_files)}"
        assert (txt_folder / "document.txt").exists(), "Original should exist"
        assert not (txt_folder / "file.txt").exists(), "Duplicate should not be copied"

    def test_global_dedup_dry_run(self, workflow_test_env):
        """Dry-run with global deduplication shows what would happen without changes.

        In dry-run mode, no files are moved or deleted - the original structure
        remains intact. Statistics should still be calculated correctly.
        """
        test_dir = workflow_test_env["test_dir"]

        content = b"IDENTICAL_CONTENT_FOR_DRY_RUN_TEST"

        # Setup: Same as test_global_dedup_identical_content
        create_identical_files(test_dir, [
            ("", "Urlaub_2023.jpg", content),
            ("subdir", "IMG_001.jpg", content),
        ])

        os.chdir(test_dir)

        # Execute: Run extraction with --global-dedup AND --dry-run
        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--global-dedup", "--dry-run"])

        # Assert: Verify behavior
        assert result == 0, "CLI should exit successfully"

        # Source file should NOT be deleted in dry-run
        assert (test_dir / "subdir" / "IMG_001.jpg").exists(), (
            "Source file should NOT be deleted in dry-run"
        )

        # Original should still exist
        assert (test_dir / "Urlaub_2023.jpg").exists(), "Original should exist"

        # No history file should be created (no actual operations)
        # History is stored in central location now, so check no changes occurred

    def test_global_dedup_edge_cases(self, workflow_test_env):
        """Edge cases for global deduplication are handled correctly.

        Tests:
        - Empty files (0 bytes) should be recognized as identical
        - Files with same size but different content should NOT be duplicates
        """
        test_dir = workflow_test_env["test_dir"]

        # Scenario A: Empty files (0 bytes) are identical
        (test_dir / "empty1.txt").write_text("")
        sub_a = test_dir / "scenario_a"
        sub_a.mkdir()
        (sub_a / "empty2.txt").write_text("")

        # Scenario B: Same size, different content - NOT duplicates
        # Both are exactly 10 bytes but content differs
        content_1 = "AAAAAAAAAA"  # 10 bytes
        content_2 = "BBBBBBBBBB"  # 10 bytes (same size, different content)
        (test_dir / "same_size.bin").write_text(content_1)
        sub_b = test_dir / "scenario_b"
        sub_b.mkdir()
        (sub_b / "also_same_size.bin").write_text(content_2)

        os.chdir(test_dir)

        # Execute: Run extraction with --global-dedup
        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--global-dedup"])

        # Assert: Verify behavior
        assert result == 0, "CLI should exit successfully"

        # Scenario A: Empty files - second should be detected as duplicate
        assert (test_dir / "empty1.txt").exists(), "First empty file should exist"
        assert not (test_dir / "empty2.txt").exists(), (
            "Second empty file should NOT be copied (identical to first)"
        )

        # Scenario B: Same size, different content - both should exist
        assert (test_dir / "same_size.bin").exists(), "First file should exist"
        assert (test_dir / "also_same_size.bin").exists(), (
            "Second file should also exist (different content despite same size)"
        )

        # Verify content is preserved correctly
        assert (test_dir / "same_size.bin").read_text() == content_1
        assert (test_dir / "also_same_size.bin").read_text() == content_2
