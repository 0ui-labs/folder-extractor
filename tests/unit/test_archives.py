"""
Tests for archive handling with security validation.

These tests verify:
1. Archive format detection (ZIP, TAR, TAR.GZ, etc.)
2. Safe extraction of valid archives
3. Zip Slip attack prevention (path traversal protection)
"""

from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path

import pytest

# These imports will fail until we implement the module - that's expected in TDD
from folder_extractor.core.archives import (
    IArchiveHandler,
    TarHandler,
    ZipHandler,
    get_archive_handler,
)
from folder_extractor.core.extractor import SecurityError
from folder_extractor.core.file_operations import FileOperationError

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def create_zip_archive(tmp_path):
    """
    Factory fixture to create ZIP archives with specified contents.

    Usage:
        zip_path = create_zip_archive({"file.txt": "content", "dir/nested.txt": "nested"})
    """

    def _create(files: dict[str, str], name: str = "test.zip") -> Path:
        zip_path = tmp_path / name
        with zipfile.ZipFile(zip_path, "w") as zf:
            for filename, content in files.items():
                zf.writestr(filename, content)
        return zip_path

    return _create


@pytest.fixture
def create_tar_archive(tmp_path):
    """
    Factory fixture to create TAR archives with specified contents.

    Usage:
        tar_path = create_tar_archive({"file.txt": "content"}, compression="gz")
    """

    def _create(
        files: dict[str, str], name: str = "test.tar", compression: str = ""
    ) -> Path:
        if compression:
            name = f"{name}.{compression}"
            mode = f"w:{compression}"
        else:
            mode = "w"

        tar_path = tmp_path / name
        with tarfile.open(tar_path, mode) as tf:
            for filename, content in files.items():
                data = content.encode("utf-8")
                info = tarfile.TarInfo(name=filename)
                info.size = len(data)
                tf.addfile(info, io.BytesIO(data))
        return tar_path

    return _create


@pytest.fixture
def extraction_dir(tmp_path):
    """Create a dedicated extraction directory for tests."""
    extract_dir = tmp_path / "extracted"
    extract_dir.mkdir()
    return extract_dir


# =============================================================================
# TestZipHandler - ZIP Archive Handling
# =============================================================================


class TestZipHandler:
    """Tests for ZIP archive handling with security validation."""

    # -------------------------------------------------------------------------
    # Format Detection Tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "filename",
        [
            "archive.zip",
            "ARCHIVE.ZIP",
            "Archive.Zip",
            "my.file.zip",
        ],
    )
    def test_is_supported_accepts_zip_extensions(self, filename):
        """ZIP handler recognizes .zip files regardless of case."""
        handler = ZipHandler()
        assert handler.is_supported(Path(filename)) is True

    @pytest.mark.parametrize(
        "filename",
        [
            "archive.tar",
            "archive.tar.gz",
            "document.pdf",
            "image.png",
            "noextension",
            "fake.zip.txt",
        ],
    )
    def test_is_supported_rejects_non_zip_files(self, filename):
        """ZIP handler rejects files without .zip extension."""
        handler = ZipHandler()
        assert handler.is_supported(Path(filename)) is False

    # -------------------------------------------------------------------------
    # Valid Extraction Tests
    # -------------------------------------------------------------------------

    def test_extract_creates_files_with_correct_content(
        self, create_zip_archive, extraction_dir
    ):
        """Extracting a ZIP creates files with their original content."""
        zip_path = create_zip_archive(
            {
                "file1.txt": "Hello World",
                "file2.pdf": "PDF content here",
            }
        )

        handler = ZipHandler()
        handler.extract(zip_path, extraction_dir)

        assert (extraction_dir / "file1.txt").read_text() == "Hello World"
        assert (extraction_dir / "file2.pdf").read_text() == "PDF content here"

    def test_extract_preserves_directory_structure(
        self, create_zip_archive, extraction_dir
    ):
        """Extracting a ZIP preserves nested directory structure."""
        zip_path = create_zip_archive(
            {
                "root.txt": "root file",
                "subdir/nested.txt": "nested content",
                "subdir/deep/deeper.txt": "deep content",
            }
        )

        handler = ZipHandler()
        handler.extract(zip_path, extraction_dir)

        assert (extraction_dir / "root.txt").exists()
        assert (
            extraction_dir / "subdir" / "nested.txt"
        ).read_text() == "nested content"
        assert (
            extraction_dir / "subdir" / "deep" / "deeper.txt"
        ).read_text() == "deep content"

    def test_extract_handles_empty_directories(self, tmp_path, extraction_dir):
        """Extracting a ZIP with empty directories creates those directories."""
        zip_path = tmp_path / "with_empty_dir.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            # Add an empty directory entry (ends with /)
            zf.writestr("empty_dir/", "")
            zf.writestr("file.txt", "content")

        handler = ZipHandler()
        handler.extract(zip_path, extraction_dir)

        assert (extraction_dir / "empty_dir").is_dir()
        assert (extraction_dir / "file.txt").exists()

    # -------------------------------------------------------------------------
    # Security Tests - Zip Slip Prevention
    # -------------------------------------------------------------------------

    def test_extract_blocks_path_traversal_attack(self, tmp_path, extraction_dir):
        """
        Zip Slip attack is blocked: archive entries with '../' are rejected.

        This is a critical security test. Malicious archives can contain
        entries like '../../../etc/passwd' to write files outside the
        extraction directory.
        """
        # Create malicious ZIP with path traversal
        evil_zip = tmp_path / "evil.zip"
        with zipfile.ZipFile(evil_zip, "w") as zf:
            info = zipfile.ZipInfo("../../evil.txt")
            zf.writestr(info, "malicious content")

        handler = ZipHandler()

        with pytest.raises(SecurityError, match="[Zz]ip [Ss]lip"):
            handler.extract(evil_zip, extraction_dir)

        # Verify the file was NOT created outside extraction directory
        assert not (tmp_path / "evil.txt").exists()
        assert not (extraction_dir.parent / "evil.txt").exists()

    def test_extract_blocks_absolute_path_in_archive(self, tmp_path, extraction_dir):
        """Archives with absolute paths are rejected as potential attacks."""
        evil_zip = tmp_path / "absolute.zip"
        with zipfile.ZipFile(evil_zip, "w") as zf:
            info = zipfile.ZipInfo("/etc/passwd")
            zf.writestr(info, "fake passwd content")

        handler = ZipHandler()

        with pytest.raises(SecurityError):
            handler.extract(evil_zip, extraction_dir)

    def test_extract_isolates_to_target_directory(self, tmp_path, extraction_dir):
        """
        Extraction is properly isolated to the target directory.

        This test verifies that extraction doesn't create files outside
        the designated extraction directory, protecting against any
        potential directory escape attempts.

        Note: Symlink handling in ZIP files is platform-specific and
        our implementation converts symlinks to regular files containing
        the target path, rather than creating actual symlinks.
        """
        # Create a file outside the extraction directory
        outside_file = tmp_path / "secret.txt"
        outside_file.write_text("sensitive data")

        # Create a ZIP with normal content
        test_zip = tmp_path / "test.zip"
        with zipfile.ZipFile(test_zip, "w") as zf:
            zf.writestr("normal.txt", "normal content")
            zf.writestr("subdir/nested.txt", "nested content")

        handler = ZipHandler()
        handler.extract(test_zip, extraction_dir)

        # Verify extraction worked correctly
        assert (extraction_dir / "normal.txt").read_text() == "normal content"
        assert (extraction_dir / "subdir" / "nested.txt").read_text() == "nested content"

        # Verify the outside file was not touched
        assert outside_file.read_text() == "sensitive data"

        # Verify no unexpected files were created outside extraction_dir
        expected_files = {"test.zip", "secret.txt", "extracted"}
        actual_files = {f.name for f in tmp_path.iterdir()}
        assert actual_files == expected_files

    # -------------------------------------------------------------------------
    # Error Handling Tests
    # -------------------------------------------------------------------------

    def test_extract_raises_file_operation_error_for_corrupted_zip(
        self, tmp_path, extraction_dir
    ):
        """Corrupted ZIP files raise FileOperationError with context."""
        corrupted_zip = tmp_path / "corrupted.zip"
        corrupted_zip.write_bytes(b"This is not a valid ZIP file content")

        handler = ZipHandler()

        with pytest.raises(FileOperationError, match="Invalid or corrupted ZIP"):
            handler.extract(corrupted_zip, extraction_dir)

    def test_extract_raises_file_operation_error_for_nonexistent_zip(
        self, tmp_path, extraction_dir
    ):
        """Non-existent ZIP files raise FileOperationError."""
        missing_zip = tmp_path / "missing.zip"

        handler = ZipHandler()

        with pytest.raises(FileOperationError, match="Failed to extract ZIP"):
            handler.extract(missing_zip, extraction_dir)


# =============================================================================
# TestTarHandler - TAR Archive Handling
# =============================================================================


class TestTarHandler:
    """Tests for TAR archive handling with security validation."""

    # -------------------------------------------------------------------------
    # Format Detection Tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "filename",
        [
            "archive.tar",
            "archive.tar.gz",
            "archive.tgz",
            "archive.tar.bz2",
            "ARCHIVE.TAR.GZ",
            "archive.TAR",
        ],
    )
    def test_is_supported_accepts_tar_extensions(self, filename):
        """TAR handler recognizes various TAR formats regardless of case."""
        handler = TarHandler()
        assert handler.is_supported(Path(filename)) is True

    @pytest.mark.parametrize(
        "filename",
        [
            "archive.zip",
            "document.pdf",
            "image.png",
            "archive.tar.zip",
            "file.gz",  # .gz alone is not a TAR
        ],
    )
    def test_is_supported_rejects_non_tar_files(self, filename):
        """TAR handler rejects files that are not TAR archives."""
        handler = TarHandler()
        assert handler.is_supported(Path(filename)) is False

    # -------------------------------------------------------------------------
    # Valid Extraction Tests
    # -------------------------------------------------------------------------

    def test_extract_creates_files_with_correct_content(
        self, create_tar_archive, extraction_dir
    ):
        """Extracting a TAR creates files with their original content."""
        tar_path = create_tar_archive(
            {
                "file1.txt": "Hello TAR",
                "file2.log": "Log content",
            }
        )

        handler = TarHandler()
        handler.extract(tar_path, extraction_dir)

        assert (extraction_dir / "file1.txt").read_text() == "Hello TAR"
        assert (extraction_dir / "file2.log").read_text() == "Log content"

    def test_extract_handles_gzip_compression(self, create_tar_archive, extraction_dir):
        """TAR.GZ archives are correctly decompressed and extracted."""
        tar_path = create_tar_archive(
            {"compressed.txt": "This was compressed"},
            name="test.tar",
            compression="gz",
        )

        handler = TarHandler()
        handler.extract(tar_path, extraction_dir)

        assert (extraction_dir / "compressed.txt").read_text() == "This was compressed"

    def test_extract_handles_bzip2_compression(
        self, create_tar_archive, extraction_dir
    ):
        """TAR.BZ2 archives are correctly decompressed and extracted."""
        tar_path = create_tar_archive(
            {"bz2file.txt": "BZ2 compressed content"},
            name="test.tar",
            compression="bz2",
        )

        handler = TarHandler()
        handler.extract(tar_path, extraction_dir)

        assert (extraction_dir / "bz2file.txt").read_text() == "BZ2 compressed content"

    def test_extract_preserves_directory_structure(
        self, create_tar_archive, extraction_dir
    ):
        """Extracting a TAR preserves nested directory structure."""
        tar_path = create_tar_archive(
            {
                "root.txt": "root",
                "level1/file.txt": "level 1",
                "level1/level2/deep.txt": "level 2",
            }
        )

        handler = TarHandler()
        handler.extract(tar_path, extraction_dir)

        assert (extraction_dir / "root.txt").exists()
        assert (extraction_dir / "level1" / "file.txt").exists()
        assert (extraction_dir / "level1" / "level2" / "deep.txt").exists()

    # -------------------------------------------------------------------------
    # Security Tests - Path Traversal Prevention
    # -------------------------------------------------------------------------

    def test_extract_blocks_path_traversal_attack(self, tmp_path, extraction_dir):
        """
        TAR path traversal attack is blocked: entries with '../' are rejected.

        This is a critical security test for TAR archives.
        """
        evil_tar = tmp_path / "evil.tar"
        with tarfile.open(evil_tar, "w") as tf:
            info = tarfile.TarInfo(name="../../escape.sh")
            info.size = 0
            tf.addfile(info, io.BytesIO(b"#!/bin/bash\nrm -rf /"))

        handler = TarHandler()

        with pytest.raises(SecurityError, match="[Ss]lip|[Ee]scape|[Tt]raversal"):
            handler.extract(evil_tar, extraction_dir)

        # Verify the file was NOT created outside extraction directory
        assert not (tmp_path / "escape.sh").exists()

    def test_extract_blocks_absolute_path_in_archive(self, tmp_path, extraction_dir):
        """TAR archives with absolute paths are rejected as potential attacks."""
        evil_tar = tmp_path / "absolute.tar"
        with tarfile.open(evil_tar, "w") as tf:
            info = tarfile.TarInfo(name="/tmp/evil.txt")
            info.size = 4
            tf.addfile(info, io.BytesIO(b"evil"))

        handler = TarHandler()

        with pytest.raises(SecurityError):
            handler.extract(evil_tar, extraction_dir)

    # -------------------------------------------------------------------------
    # Error Handling Tests
    # -------------------------------------------------------------------------

    def test_extract_raises_file_operation_error_for_corrupted_tar(
        self, tmp_path, extraction_dir
    ):
        """Corrupted TAR files raise FileOperationError with context."""
        corrupted_tar = tmp_path / "corrupted.tar"
        corrupted_tar.write_bytes(b"This is not a valid TAR file content")

        handler = TarHandler()

        with pytest.raises(FileOperationError, match="Invalid or corrupted TAR"):
            handler.extract(corrupted_tar, extraction_dir)

    def test_extract_raises_file_operation_error_for_nonexistent_tar(
        self, tmp_path, extraction_dir
    ):
        """Non-existent TAR files raise FileOperationError."""
        missing_tar = tmp_path / "missing.tar"

        handler = TarHandler()

        with pytest.raises(FileOperationError, match="Failed to extract TAR"):
            handler.extract(missing_tar, extraction_dir)


# =============================================================================
# TestArchiveHandlerFactory - Handler Selection
# =============================================================================


class TestArchiveHandlerFactory:
    """Tests for the archive handler factory function."""

    def test_returns_zip_handler_for_zip_files(self):
        """Factory returns ZipHandler for .zip files."""
        handler = get_archive_handler(Path("document.zip"))

        assert handler is not None
        assert isinstance(handler, ZipHandler)

    def test_returns_tar_handler_for_tar_files(self):
        """Factory returns TarHandler for .tar files."""
        handler = get_archive_handler(Path("backup.tar"))

        assert handler is not None
        assert isinstance(handler, TarHandler)

    def test_returns_tar_handler_for_compressed_tar(self):
        """Factory returns TarHandler for compressed TAR files."""
        for extension in [".tar.gz", ".tgz", ".tar.bz2"]:
            handler = get_archive_handler(Path(f"archive{extension}"))
            assert handler is not None
            assert isinstance(handler, TarHandler)

    def test_returns_none_for_unsupported_files(self):
        """Factory returns None for non-archive files."""
        handler = get_archive_handler(Path("document.pdf"))
        assert handler is None

    def test_returns_none_for_files_without_extension(self):
        """Factory returns None for files without extension."""
        handler = get_archive_handler(Path("README"))
        assert handler is None

    def test_handler_interface_is_correctly_typed(self):
        """Returned handlers implement IArchiveHandler interface."""
        zip_handler = get_archive_handler(Path("test.zip"))
        tar_handler = get_archive_handler(Path("test.tar"))

        # Both should be instances of IArchiveHandler
        assert isinstance(zip_handler, IArchiveHandler)
        assert isinstance(tar_handler, IArchiveHandler)

        # Both should have required methods
        assert hasattr(zip_handler, "extract")
        assert hasattr(zip_handler, "is_supported")
        assert hasattr(tar_handler, "extract")
        assert hasattr(tar_handler, "is_supported")
