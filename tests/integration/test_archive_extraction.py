"""
Integration tests for archive extraction feature (Deep Extraction).

This module tests the archive extraction functionality including:
- Basic ZIP and TAR.GZ archive extraction
- Archive extraction with --delete-archives flag
- Combination with --sort-by-type and --deduplicate
- Security (Zip Slip protection)
- Error handling (corrupted archives, empty archives)
- Nested archives
- Dry-run mode
- Full workflow integration with undo
"""

from __future__ import annotations

import io
import os
import shutil
import tarfile
import zipfile
from pathlib import Path

import pytest


# Skip entire module if CLI app cannot be imported (Python 3.8 lacks google-generativeai)
def _can_import_cli_app() -> bool:
    """Check if the CLI app module can be imported."""
    try:
        from folder_extractor.cli.app import EnhancedFolderExtractorCLI  # noqa: F401

        return True
    except ImportError:
        return False


pytestmark = pytest.mark.skipif(
    not _can_import_cli_app(),
    reason="CLI app requires google-generativeai (Python 3.9+)",
)

# Import after skip marker to avoid import errors on Python 3.8
from folder_extractor.cli.app import EnhancedFolderExtractorCLI  # noqa: E402
from folder_extractor.config.settings import settings  # noqa: E402
from folder_extractor.core.state_manager import reset_state_manager  # noqa: E402

# =============================================================================
# Helper Functions for Archive Creation
# =============================================================================


def create_zip_archive(archive_path: Path, files: dict[str, str | bytes]) -> Path:
    """
    Create a ZIP archive with specified files.

    Args:
        archive_path: Path where the ZIP archive should be created
        files: Dict mapping relative paths to file contents (str or bytes)

    Returns:
        Path to the created archive

    Example:
        create_zip_archive(Path("test.zip"), {"doc.pdf": "PDF content", "img.jpg": b"bytes"})
    """
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            if isinstance(content, bytes):
                zf.writestr(name, content)
            else:
                zf.writestr(name, content.encode("utf-8"))
    return archive_path


def create_tar_archive(archive_path: Path, files: dict[str, str | bytes]) -> Path:
    """
    Create a TAR archive with specified files.

    Args:
        archive_path: Path where the TAR archive should be created
        files: Dict mapping relative paths to file contents

    Returns:
        Path to the created archive
    """
    with tarfile.open(archive_path, "w") as tf:
        for name, content in files.items():
            if isinstance(content, str):
                content = content.encode("utf-8")
            tarinfo = tarfile.TarInfo(name=name)
            tarinfo.size = len(content)
            tf.addfile(tarinfo, io.BytesIO(content))
    return archive_path


def create_tar_gz_archive(archive_path: Path, files: dict[str, str | bytes]) -> Path:
    """
    Create a TAR.GZ (gzipped tar) archive with specified files.

    Args:
        archive_path: Path where the TAR.GZ archive should be created
        files: Dict mapping relative paths to file contents

    Returns:
        Path to the created archive
    """
    with tarfile.open(archive_path, "w:gz") as tf:
        for name, content in files.items():
            if isinstance(content, str):
                content = content.encode("utf-8")
            tarinfo = tarfile.TarInfo(name=name)
            tarinfo.size = len(content)
            tf.addfile(tarinfo, io.BytesIO(content))
    return archive_path


def create_malicious_zip(archive_path: Path) -> Path:
    """
    Create a ZIP archive with path traversal attempt (Zip Slip attack).

    The archive contains entries with "../" in their paths attempting to
    escape the extraction directory.

    Args:
        archive_path: Path where the malicious ZIP should be created

    Returns:
        Path to the created archive
    """
    with zipfile.ZipFile(archive_path, "w") as zf:
        # Add a file that attempts to escape to parent directories
        zf.writestr("../../evil.txt", "Malicious content")
        # Also add an absolute path attempt
        zf.writestr("../escape.txt", "Escape attempt")
        # And a valid file for comparison
        zf.writestr("normal.txt", "Normal content")
    return archive_path


def configure_settings_for_test(**kwargs) -> None:
    """
    Configure settings for a test case.

    Resets settings to defaults and applies provided overrides.

    Args:
        **kwargs: Settings to override (e.g., extract_archives=True)
    """
    settings.reset_to_defaults()
    for key, value in kwargs.items():
        settings.set(key, value)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def archive_test_env(tmp_path):
    """
    Set up test environment for archive extraction tests.

    Creates a Desktop-based test directory (required for security validation)
    with a downloads subdirectory containing test archives.

    Yields:
        Dict with:
        - root: Path to test root directory
        - downloads: Path to downloads subdirectory
        - archives: List of created archive paths
    """
    # Reset state for clean test
    reset_state_manager()
    settings.reset_to_defaults()

    # Create test directory in Desktop (safe path for security checks)
    desktop = Path.home() / "Desktop"
    test_dir = desktop / f"archive_test_{tmp_path.name}"
    test_dir.mkdir(parents=True, exist_ok=True)

    # Create downloads subdirectory
    downloads = test_dir / "downloads"
    downloads.mkdir()

    # Create test archives
    archives = []

    # ZIP archive with a PDF
    zip_path = downloads / "archiv.zip"
    create_zip_archive(zip_path, {"dok.pdf": "PDF content for testing"})
    archives.append(zip_path)

    # ZIP archive with images
    images_zip = downloads / "bilder.zip"
    create_zip_archive(
        images_zip, {"foto1.jpg": b"JPEG data 1", "foto2.png": b"PNG data 2"}
    )
    archives.append(images_zip)

    # TAR.GZ archive with documents
    tar_gz_path = downloads / "dokumente.tar.gz"
    create_tar_gz_archive(
        tar_gz_path, {"report.pdf": "Report content", "notes.txt": "Notes content"}
    )
    archives.append(tar_gz_path)

    original_cwd = Path.cwd()

    yield {
        "root": test_dir,
        "downloads": downloads,
        "archives": archives,
        "original_cwd": original_cwd,
    }

    # Cleanup
    os.chdir(original_cwd)
    if test_dir.exists():
        shutil.rmtree(test_dir)


# =============================================================================
# Test Classes
# =============================================================================


class TestBasicArchiveExtraction:
    """Test basic archive extraction functionality."""

    def test_extract_single_zip_archive(self, archive_test_env):
        """A single ZIP archive is extracted and its contents are moved to root.

        When --extract-archives is enabled, ZIP files are unpacked and
        their contents are processed like regular files.
        """
        root = archive_test_env["root"]
        downloads = archive_test_env["downloads"]

        # Create a simple ZIP with one file
        zip_path = downloads / "simple.zip"
        create_zip_archive(zip_path, {"dok.pdf": "PDF content"})

        # Remove other test archives to isolate this test
        for archive in archive_test_env["archives"]:
            if archive.exists() and archive != zip_path:
                archive.unlink()

        os.chdir(root)

        # Configure and run
        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--extract-archives"])

        # Assertions
        assert result == 0, "CLI should exit successfully"
        assert (root / "dok.pdf").exists(), "Extracted file should be in root"
        assert (root / "dok.pdf").read_text() == "PDF content", (
            "Content should be correct"
        )
        # Archive should still exist (delete-archives not set)
        assert (downloads / "simple.zip").exists(), "Archive should still exist"

    def test_extract_tar_gz_archive(self, archive_test_env):
        """TAR.GZ archives are extracted correctly with all contents.

        The handler auto-detects compression format and extracts
        all files from the archive.
        """
        root = archive_test_env["root"]
        downloads = archive_test_env["downloads"]

        # Create TAR.GZ with multiple files
        tar_gz_path = downloads / "docs.tar.gz"
        create_tar_gz_archive(
            tar_gz_path, {"report.pdf": "Report", "notes.txt": "Notes"}
        )

        # Remove other archives
        for archive in archive_test_env["archives"]:
            if archive.exists() and archive != tar_gz_path:
                archive.unlink()

        os.chdir(root)

        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--extract-archives"])

        # Assertions
        assert result == 0
        assert (root / "report.pdf").exists(), "First extracted file should exist"
        assert (root / "notes.txt").exists(), "Second extracted file should exist"
        assert (downloads / "docs.tar.gz").exists(), "Archive should still exist"

    def test_extract_with_delete_archives(self, archive_test_env):
        """Archives are deleted after extraction when --delete-archives is set.

        This combines extraction with cleanup, removing the source
        archive after its contents have been successfully extracted.
        """
        root = archive_test_env["root"]
        downloads = archive_test_env["downloads"]

        # Create a ZIP
        zip_path = downloads / "delete_me.zip"
        create_zip_archive(zip_path, {"dok.pdf": "Content"})

        # Remove other archives
        for archive in archive_test_env["archives"]:
            if archive.exists() and archive != zip_path:
                archive.unlink()

        os.chdir(root)

        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--extract-archives", "--delete-archives"])

        # Assertions
        assert result == 0
        assert (root / "dok.pdf").exists(), "Extracted file should exist"
        assert not (downloads / "delete_me.zip").exists(), "Archive should be deleted"

    def test_no_extraction_without_flag(self, archive_test_env):
        """Archives are treated as regular files when --extract-archives is not set.

        By default, ZIP and TAR files are moved like any other file,
        not unpacked.
        """
        root = archive_test_env["root"]
        downloads = archive_test_env["downloads"]

        # Create a ZIP
        zip_path = downloads / "normal.zip"
        create_zip_archive(zip_path, {"dok.pdf": "Content"})

        # Remove other archives
        for archive in archive_test_env["archives"]:
            if archive.exists() and archive != zip_path:
                archive.unlink()

        os.chdir(root)

        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        # Run WITHOUT --extract-archives
        result = cli.run([])

        # Assertions
        assert result == 0
        # The ZIP should be moved to root, not extracted
        assert (root / "normal.zip").exists(), "Archive should be moved to root"
        # The PDF inside should NOT be extracted
        assert not (root / "dok.pdf").exists(), "Content should NOT be extracted"


class TestArchiveExtractionWithSorting:
    """Test archive extraction combined with --sort-by-type."""

    def test_extract_archive_with_sort_by_type(self, archive_test_env):
        """Extracted files are sorted into type folders.

        When both --extract-archives and --sort-by-type are enabled,
        files from archives are sorted into appropriate type folders.
        """
        root = archive_test_env["root"]
        downloads = archive_test_env["downloads"]

        # Create ZIP with mixed file types
        zip_path = downloads / "mixed.zip"
        create_zip_archive(
            zip_path,
            {"dok.pdf": "PDF", "foto.jpg": b"JPEG data", "musik.mp3": b"MP3 data"},
        )

        # Remove other archives
        for archive in archive_test_env["archives"]:
            if archive.exists() and archive != zip_path:
                archive.unlink()

        os.chdir(root)

        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--extract-archives", "--sort-by-type"])

        # Assertions
        assert result == 0
        assert (root / "PDF" / "dok.pdf").exists(), "PDF should be in PDF folder"
        assert (root / "JPEG" / "foto.jpg").exists(), "JPEG should be in JPEG folder"
        assert (root / "AUDIO" / "musik.mp3").exists(), "MP3 should be in AUDIO folder"

    def test_extract_archive_all_contents_extracted(self, archive_test_env):
        """All files from archives are extracted regardless of type filter.

        The --type filter operates at discovery level to find archives,
        but once an archive is processed, ALL its contents are extracted.
        This ensures archive contents remain complete and consistent.

        To filter specific types, use --type without archive types to
        avoid processing archives entirely.
        """
        root = archive_test_env["root"]
        downloads = archive_test_env["downloads"]

        # Create ZIP with mixed types
        zip_path = downloads / "mixed_types.zip"
        create_zip_archive(
            zip_path,
            {"dok.pdf": "PDF content", "foto.jpg": b"JPEG", "musik.mp3": b"MP3"},
        )

        # Remove other archives
        for archive in archive_test_env["archives"]:
            if archive.exists() and archive != zip_path:
                archive.unlink()

        os.chdir(root)

        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        # Run extraction with archive extraction enabled
        # All contents from the archive should be extracted
        result = cli.run(["--extract-archives"])

        # Assertions
        assert result == 0
        # All files from the archive are extracted to root (flat extraction)
        assert (root / "dok.pdf").exists(), "PDF should be extracted"
        assert (root / "foto.jpg").exists(), "JPG should be extracted"
        assert (root / "musik.mp3").exists(), "MP3 should be extracted"

    def test_type_filter_excludes_archives_not_matching_filter(self, archive_test_env):
        """Type filter prevents archive discovery when archive type not in filter.

        When --type pdf is used with --extract-archives, archives (.zip, .tar.gz)
        are NOT discovered because their file extensions don't match the filter.
        This means archives are skipped entirely - their contents are never examined.

        This is the expected CLI semantics: the type filter operates at the
        file discovery level, not at the archive content level.
        """
        root = archive_test_env["root"]
        downloads = archive_test_env["downloads"]

        # Create ZIP with mixed types including PDF
        zip_path = downloads / "mixed_for_filter.zip"
        create_zip_archive(
            zip_path,
            {"dok.pdf": "PDF content", "foto.jpg": b"JPEG", "musik.mp3": b"MP3"},
        )

        # Also create a regular PDF file to verify filter works
        regular_pdf = downloads / "regular.pdf"
        regular_pdf.write_text("Regular PDF content")

        # Remove other archives
        for archive in archive_test_env["archives"]:
            if archive.exists() and archive != zip_path:
                archive.unlink()

        os.chdir(root)

        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        # Run with --type pdf - this will NOT discover the ZIP file
        # because .zip extension doesn't match .pdf filter
        result = cli.run(["--extract-archives", "--type", "pdf"])

        # Assertions
        assert result == 0

        # The regular PDF should be moved to root (it matches the filter)
        # Note: Without --sort-by-type, files go directly to root
        pdf_in_root = (root / "regular.pdf").exists()
        pdf_in_pdf_folder = (root / "PDF" / "regular.pdf").exists()
        assert pdf_in_root or pdf_in_pdf_folder, (
            "Regular PDF should be moved (matches filter)"
        )

        # Archive contents should NOT be extracted because the archive
        # itself (.zip) doesn't match the --type pdf filter
        # Check both root and any type folders
        dok_in_root = (root / "dok.pdf").exists()
        dok_in_pdf_folder = (root / "PDF" / "dok.pdf").exists()
        assert not dok_in_root and not dok_in_pdf_folder, (
            "PDF from archive should NOT be extracted (archive not discovered)"
        )
        assert not (root / "foto.jpg").exists(), (
            "JPG from archive should NOT be extracted"
        )
        assert not (root / "musik.mp3").exists(), (
            "MP3 from archive should NOT be extracted"
        )

        # The archive itself should remain in downloads (not moved, not extracted)
        assert (downloads / "mixed_for_filter.zip").exists(), (
            "Archive should remain untouched when not matching filter"
        )


class TestArchiveExtractionWithDeduplication:
    """Test archive extraction with deduplication features."""

    def test_extract_archive_with_deduplicate(self, archive_test_env):
        """Content deduplication works with extracted archive files.

        When --deduplicate is combined with --extract-archives, files
        with identical content (same hash) are deduplicated.
        """
        root = archive_test_env["root"]
        downloads = archive_test_env["downloads"]

        identical_content = "Same content for dedup test"

        # Create existing file in root
        (root / "existing.txt").write_text(identical_content)

        # Create ZIP with file that has identical content
        zip_path = downloads / "dedup.zip"
        create_zip_archive(zip_path, {"existing.txt": identical_content})

        # Remove other archives
        for archive in archive_test_env["archives"]:
            if archive.exists() and archive != zip_path:
                archive.unlink()

        os.chdir(root)

        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--extract-archives", "--deduplicate"])

        # Assertions
        assert result == 0
        # Only one file should exist (deduplicated)
        existing_files = list(root.glob("existing*.txt"))
        assert len(existing_files) == 1, (
            f"Should have 1 file (deduplicated), found {len(existing_files)}"
        )

    def test_extract_archive_with_global_dedup(self, archive_test_env):
        """Global deduplication checks against entire destination tree.

        When --global-dedup is combined with --extract-archives, files
        are checked against all existing files in the destination,
        regardless of filename.
        """
        root = archive_test_env["root"]
        downloads = archive_test_env["downloads"]

        identical_content = "Same content different name"

        # Create existing file with different name
        (root / "original.txt").write_text(identical_content)

        # Create ZIP with file that has identical content but different name
        zip_path = downloads / "global_dedup.zip"
        create_zip_archive(zip_path, {"different_name.txt": identical_content})

        # Remove other archives
        for archive in archive_test_env["archives"]:
            if archive.exists() and archive != zip_path:
                archive.unlink()

        os.chdir(root)

        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--extract-archives", "--global-dedup"])

        # Assertions
        assert result == 0
        # Original should exist
        assert (root / "original.txt").exists()
        # The duplicate (same content, different name) should NOT be copied
        assert not (root / "different_name.txt").exists(), (
            "Global duplicate should not be copied"
        )

    def test_extract_multiple_archives_with_dedup(self, archive_test_env):
        """Multiple archives with duplicate content are deduplicated.

        When multiple archives contain files with identical content,
        only one copy is kept.
        """
        root = archive_test_env["root"]
        downloads = archive_test_env["downloads"]

        identical_content = "Duplicate content in multiple archives"

        # Create two archives with same content
        zip1 = downloads / "archive1.zip"
        zip2 = downloads / "archive2.zip"
        create_zip_archive(zip1, {"file.txt": identical_content})
        create_zip_archive(zip2, {"file.txt": identical_content})

        # Remove other archives
        for archive in archive_test_env["archives"]:
            if archive.exists() and archive not in [zip1, zip2]:
                archive.unlink()

        os.chdir(root)

        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--extract-archives", "--deduplicate"])

        # Assertions
        assert result == 0
        # Only one file should exist
        file_count = len(list(root.glob("file*.txt")))
        assert file_count == 1, f"Should have 1 file (deduplicated), found {file_count}"


class TestArchiveSecurityAndErrors:
    """Test security features and error handling for archives."""

    def test_zip_slip_protection(self, archive_test_env):
        """Malicious archives with path traversal are blocked.

        The Zip Slip protection prevents extraction of files that
        would escape the target directory via ../ paths.
        """
        root = archive_test_env["root"]
        downloads = archive_test_env["downloads"]

        # Create malicious ZIP
        malicious_zip = downloads / "malicious.zip"
        create_malicious_zip(malicious_zip)

        # Remove other archives
        for archive in archive_test_env["archives"]:
            if archive.exists() and archive != malicious_zip:
                archive.unlink()

        os.chdir(root)

        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        cli.run(["--extract-archives"])

        # The CLI should handle the error gracefully
        # The malicious files should NOT exist outside the target
        assert not (root.parent / "evil.txt").exists(), (
            "Malicious file should NOT escape"
        )
        assert not (root.parent / "escape.txt").exists(), (
            "Escape attempt should be blocked"
        )

    def test_corrupted_archive_handling(self, archive_test_env):
        """Corrupted archives are handled gracefully without crashing.

        When an archive is corrupted, an error is logged but the
        extraction process continues with other files.
        """
        root = archive_test_env["root"]
        downloads = archive_test_env["downloads"]

        # Create a corrupted ZIP (invalid bytes)
        corrupted_zip = downloads / "corrupted.zip"
        corrupted_zip.write_bytes(b"This is not a valid ZIP file!")

        # Also create a valid ZIP to verify processing continues
        valid_zip = downloads / "valid.zip"
        create_zip_archive(valid_zip, {"valid.txt": "Valid content"})

        # Remove default test archives
        for archive in archive_test_env["archives"]:
            if archive.exists():
                archive.unlink()

        os.chdir(root)

        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--extract-archives"])

        # Should not crash - CLI handles errors
        assert result == 0 or result == 1  # May return error code but shouldn't crash
        # Valid file should still be extracted
        assert (root / "valid.txt").exists(), (
            "Valid archive content should be extracted"
        )

    def test_empty_archive(self, archive_test_env):
        """Empty archives are handled without errors.

        An archive with no entries is valid and should be processed
        without causing any errors.
        """
        root = archive_test_env["root"]
        downloads = archive_test_env["downloads"]

        # Create empty ZIP
        empty_zip = downloads / "empty.zip"
        with zipfile.ZipFile(empty_zip, "w"):
            pass  # Create empty archive

        # Remove other archives
        for archive in archive_test_env["archives"]:
            if archive.exists() and archive != empty_zip:
                archive.unlink()

        os.chdir(root)

        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--extract-archives"])

        # Should complete without errors
        assert result == 0

    def test_archive_with_nested_directories(self, archive_test_env):
        """Archives with nested directory structures are extracted correctly.

        Files in nested directories within archives should be extracted
        and flattened to the destination.
        """
        root = archive_test_env["root"]
        downloads = archive_test_env["downloads"]

        # Create ZIP with nested structure
        nested_zip = downloads / "nested_dirs.zip"
        create_zip_archive(
            nested_zip,
            {
                "folder1/folder2/deep.txt": "Deep content",
                "folder1/shallow.txt": "Shallow content",
            },
        )

        # Remove other archives
        for archive in archive_test_env["archives"]:
            if archive.exists() and archive != nested_zip:
                archive.unlink()

        os.chdir(root)

        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--extract-archives"])

        # Assertions
        assert result == 0
        # Both files should be extracted (flattened to root or temp structure)
        # The actual behavior depends on implementation - files should exist
        all_txt_files = list(root.rglob("*.txt"))
        assert len(all_txt_files) >= 2, (
            f"Should have at least 2 txt files, found {len(all_txt_files)}"
        )


class TestNestedArchives:
    """Test extraction of nested archives (archives within archives)."""

    def test_nested_archive_extraction(self, archive_test_env):
        """Archives within archives are extracted recursively.

        When an archive contains another archive, both are processed
        and the inner archive's contents are also extracted.
        """
        root = archive_test_env["root"]
        downloads = archive_test_env["downloads"]

        # Create inner ZIP
        inner_content = {"dok.pdf": "Final document"}
        inner_zip_bytes = io.BytesIO()
        with zipfile.ZipFile(inner_zip_bytes, "w") as inner_zf:
            for name, content in inner_content.items():
                inner_zf.writestr(name, content)
        inner_zip_bytes.seek(0)

        # Create outer ZIP containing the inner ZIP
        outer_zip = downloads / "outer.zip"
        with zipfile.ZipFile(outer_zip, "w") as outer_zf:
            outer_zf.writestr("inner.zip", inner_zip_bytes.read())

        # Remove other archives
        for archive in archive_test_env["archives"]:
            if archive.exists() and archive != outer_zip:
                archive.unlink()

        os.chdir(root)

        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--extract-archives"])

        # Assertions
        assert result == 0
        # The final document from the nested archive should exist
        assert (root / "dok.pdf").exists(), (
            "Document from nested archive should be extracted"
        )

    def test_archive_in_subdirectory(self, archive_test_env):
        """Archives in subdirectories are discovered and processed.

        When an archive is located in a subdirectory, it should still
        be found and extracted when within the depth limit.
        """
        root = archive_test_env["root"]
        downloads = archive_test_env["downloads"]

        # Create subdirectory with archive
        subdir = downloads / "subdir"
        subdir.mkdir()
        sub_zip = subdir / "sub.zip"
        create_zip_archive(sub_zip, {"sub_doc.txt": "Subdirectory content"})

        # Remove default archives
        for archive in archive_test_env["archives"]:
            if archive.exists():
                archive.unlink()

        os.chdir(root)

        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--extract-archives", "--depth", "2"])

        # Assertions
        assert result == 0
        # Document from subdirectory archive should be extracted
        assert (root / "sub_doc.txt").exists(), (
            "Document from subdirectory archive should be extracted"
        )


class TestArchiveExtractionWithDryRun:
    """Test dry-run mode with archive extraction."""

    def test_dry_run_archive_extraction(self, archive_test_env):
        """Dry-run shows what would happen without actual extraction.

        In dry-run mode, archives are analyzed but no files are
        actually moved or extracted.
        """
        root = archive_test_env["root"]
        downloads = archive_test_env["downloads"]

        # Create ZIP
        zip_path = downloads / "dryrun.zip"
        create_zip_archive(zip_path, {"dok.pdf": "Content"})

        # Remove other archives
        for archive in archive_test_env["archives"]:
            if archive.exists() and archive != zip_path:
                archive.unlink()

        os.chdir(root)

        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--extract-archives", "--dry-run"])

        # Assertions
        assert result == 0
        # No files should be extracted in dry-run
        assert not (root / "dok.pdf").exists(), (
            "File should NOT be extracted in dry-run"
        )
        # Archive should remain unchanged
        assert (downloads / "dryrun.zip").exists(), "Archive should still exist"


class TestArchiveExtractionIntegration:
    """Test full workflow integration with archives."""

    def test_full_workflow_with_archives(self, archive_test_env):
        """Complete workflow processes archives alongside regular files.

        This test verifies that archives are correctly processed when
        combined with regular files and multiple features.
        """
        root = archive_test_env["root"]
        downloads = archive_test_env["downloads"]

        # Create mixed content
        # Archive 1: PDF and JPG
        zip1 = downloads / "archive1.zip"
        create_zip_archive(zip1, {"doc1.pdf": "PDF 1", "img1.jpg": b"JPEG 1"})

        # Archive 2: TXT and MP3
        tar_gz = downloads / "archive2.tar.gz"
        create_tar_gz_archive(tar_gz, {"notes.txt": "Notes", "song.mp3": b"MP3 data"})

        # Regular file (not in archive)
        (downloads / "normal.pdf").write_text("Normal PDF")

        # Remove default archives
        for archive in archive_test_env["archives"]:
            if archive.exists() and archive not in [zip1, tar_gz]:
                archive.unlink()

        os.chdir(root)

        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--extract-archives", "--sort-by-type", "--deduplicate"])

        # Assertions
        assert result == 0

        # Check type folders exist and contain files
        assert (root / "PDF").exists(), "PDF folder should exist"
        assert (root / "JPEG").exists(), "JPEG folder should exist"
        assert (root / "TEXT").exists(), "TEXT folder should exist"
        assert (root / "AUDIO").exists(), "AUDIO folder should exist"

        # Verify file counts in each folder
        pdf_files = list((root / "PDF").glob("*.pdf"))
        assert len(pdf_files) >= 2, f"Expected at least 2 PDFs, found {len(pdf_files)}"

    def test_archive_extraction_with_undo(self, archive_test_env):
        """Undo moves extracted files back to their original temp location.

        For archive extraction, the undo operation moves files back to
        their original location (the temp extraction directory). Since
        the temp directory is cleaned up after extraction, undo recreates
        it. The archive itself remains unchanged by the undo operation.

        Note: This behavior is a consequence of how history tracks file
        movements - it doesn't "know" the file came from an archive.
        """
        root = archive_test_env["root"]
        downloads = archive_test_env["downloads"]

        # Create simple ZIP
        zip_path = downloads / "undo_test.zip"
        create_zip_archive(zip_path, {"undo_doc.txt": "Document for undo test"})

        # Remove other archives
        for archive in archive_test_env["archives"]:
            if archive.exists() and archive != zip_path:
                archive.unlink()

        os.chdir(root)

        # First: Extract
        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--extract-archives"])
        assert result == 0
        assert (root / "undo_doc.txt").exists(), "File should be extracted"

        # Archive should still exist (delete_archives not set)
        assert (downloads / "undo_test.zip").exists(), (
            "Archive should still exist after extraction"
        )

        # Second: Undo
        reset_state_manager()  # Reset for new operation
        cli2 = EnhancedFolderExtractorCLI()
        undo_result = cli2.run(["--undo"])

        # Verify undo completed successfully
        assert undo_result == 0, "Undo operation should complete successfully"

        # After undo: extracted file should no longer be in root
        # (it was moved back to the recreated temp directory)
        assert not (root / "undo_doc.txt").exists(), (
            "Extracted file should be moved away from root after undo"
        )

        # Archive remains unchanged (undo doesn't affect the archive itself)
        assert (downloads / "undo_test.zip").exists(), (
            "Archive should remain unchanged after undo"
        )


@pytest.mark.integration
class TestArchiveExtractionMarkers:
    """Tests with explicit pytest markers for categorization."""

    @pytest.mark.slow
    def test_large_archive_extraction(self, archive_test_env):
        """Large archives with many files are processed correctly.

        This test verifies performance and correctness with larger
        archive contents.
        """
        root = archive_test_env["root"]
        downloads = archive_test_env["downloads"]

        # Create archive with many files
        files = {f"file_{i}.txt": f"Content {i}" for i in range(50)}
        large_zip = downloads / "large.zip"
        create_zip_archive(large_zip, files)

        # Remove other archives
        for archive in archive_test_env["archives"]:
            if archive.exists() and archive != large_zip:
                archive.unlink()

        os.chdir(root)

        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        result = cli.run(["--extract-archives"])

        # Assertions
        assert result == 0
        extracted_files = list(root.glob("file_*.txt"))
        assert len(extracted_files) == 50, (
            f"All 50 files should be extracted, found {len(extracted_files)}"
        )

    @pytest.mark.security
    def test_absolute_path_in_archive_blocked(self, archive_test_env):
        """Archives with absolute paths are handled safely.

        Absolute paths in archive entries should be rejected or
        normalized to prevent arbitrary file writes.
        """
        root = archive_test_env["root"]
        downloads = archive_test_env["downloads"]

        # Create ZIP with absolute path entry (attempt)
        abs_zip = downloads / "absolute.zip"
        with zipfile.ZipFile(abs_zip, "w") as zf:
            # Try to write to absolute path
            zf.writestr("/tmp/escape.txt", "Escape content")
            zf.writestr("normal.txt", "Normal content")

        # Remove other archives
        for archive in archive_test_env["archives"]:
            if archive.exists() and archive != abs_zip:
                archive.unlink()

        os.chdir(root)

        cli = EnhancedFolderExtractorCLI()
        cli.interface.confirm_operation = lambda x: True

        cli.run(["--extract-archives"])

        # The absolute path entry should be blocked
        assert not Path("/tmp/escape.txt").exists(), (
            "Absolute path escape should be blocked"
        )
