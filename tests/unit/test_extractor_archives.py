"""
Tests for archive integration in EnhancedFileExtractor.

These tests verify:
1. Archive detection (_is_archive method)
2. Handler selection (_get_archive_handler method)
3. Archive processing (_process_archives method)
4. Integration with extract_files workflow
"""

from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path
from typing import List
from unittest.mock import Mock, patch

import pytest

from folder_extractor.config.settings import settings
from folder_extractor.core.extractor import EnhancedFileExtractor


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def extractor():
    """Create a fresh EnhancedFileExtractor instance."""
    return EnhancedFileExtractor()


@pytest.fixture
def create_zip_archive(tmp_path):
    """
    Factory fixture to create ZIP archives with specified contents.

    Usage:
        zip_path = create_zip_archive({"file.txt": "content"})
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


@pytest.fixture(autouse=True)
def reset_settings():
    """Reset settings before each test."""
    settings.reset_to_defaults()
    yield
    settings.reset_to_defaults()


# =============================================================================
# Test _is_archive - Archive Detection
# =============================================================================


class TestIsArchive:
    """Tests for archive file detection based on extension."""

    @pytest.mark.parametrize(
        "filename",
        [
            "archive.zip",
            "Archive.ZIP",
            "my.file.zip",
        ],
    )
    def test_recognizes_zip_files(self, extractor, filename):
        """ZIP files are recognized as archives."""
        assert extractor._is_archive(Path(filename)) is True
        assert extractor._is_archive(filename) is True  # Also accepts str

    @pytest.mark.parametrize(
        "filename",
        [
            "backup.tar",
            "backup.tar.gz",
            "backup.tar.bz2",
            "backup.tar.xz",
            "backup.tgz",
            "ARCHIVE.TAR.GZ",
        ],
    )
    def test_recognizes_tar_files(self, extractor, filename):
        """TAR files (including compressed variants) are recognized as archives."""
        assert extractor._is_archive(Path(filename)) is True

    @pytest.mark.parametrize(
        "filename",
        [
            "document.pdf",
            "image.png",
            "readme.txt",
            "script.py",
            "noextension",
            "fake.zip.txt",  # Extension is .txt, not .zip
            "archive.rar",  # RAR is not supported
            "archive.7z",  # 7z is not supported
        ],
    )
    def test_rejects_non_archive_files(self, extractor, filename):
        """Non-archive files are not recognized as archives."""
        assert extractor._is_archive(Path(filename)) is False

    def test_handles_path_objects_and_strings(self, extractor):
        """Method accepts both Path objects and strings."""
        assert extractor._is_archive(Path("test.zip")) is True
        assert extractor._is_archive("test.zip") is True
        assert extractor._is_archive(Path("test.pdf")) is False
        assert extractor._is_archive("test.pdf") is False


# =============================================================================
# Test _get_archive_handler - Handler Selection
# =============================================================================


class TestGetArchiveHandler:
    """Tests for archive handler selection based on file type."""

    def test_returns_zip_handler_for_zip_files(self, extractor):
        """ZIP files get a ZipHandler."""
        from folder_extractor.core.archives import ZipHandler

        handler = extractor._get_archive_handler(Path("test.zip"))
        assert handler is not None
        assert isinstance(handler, ZipHandler)

    def test_returns_tar_handler_for_tar_files(self, extractor):
        """TAR files get a TarHandler."""
        from folder_extractor.core.archives import TarHandler

        handler = extractor._get_archive_handler(Path("backup.tar"))
        assert handler is not None
        assert isinstance(handler, TarHandler)

    def test_returns_tar_handler_for_compressed_tar(self, extractor):
        """Compressed TAR files get a TarHandler."""
        from folder_extractor.core.archives import TarHandler

        for ext in [".tar.gz", ".tar.bz2", ".tgz"]:
            handler = extractor._get_archive_handler(Path(f"backup{ext}"))
            assert handler is not None
            assert isinstance(handler, TarHandler)

    def test_returns_none_for_non_archives(self, extractor):
        """Non-archive files return None."""
        handler = extractor._get_archive_handler(Path("document.pdf"))
        assert handler is None

    def test_accepts_string_paths(self, extractor):
        """Method accepts string paths in addition to Path objects."""
        handler = extractor._get_archive_handler("test.zip")
        assert handler is not None


# =============================================================================
# Test _process_archives - Archive Processing Logic
# =============================================================================


class TestProcessArchives:
    """Tests for archive processing behavior."""

    def test_returns_unchanged_files_when_feature_disabled(self, extractor, tmp_path):
        """When extract_archives is False, files are returned unchanged."""
        settings.set("extract_archives", False)

        files = [str(tmp_path / "test.zip"), str(tmp_path / "doc.pdf")]
        destination = tmp_path / "dest"
        destination.mkdir()

        result_files, archive_results = extractor._process_archives(
            files=files,
            destination=destination,
            operation_id=None,
            progress_callback=None,
            indexing_callback=None,
        )

        assert result_files == files
        assert archive_results == {}

    def test_extracts_archives_when_feature_enabled(
        self, extractor, create_zip_archive, tmp_path
    ):
        """When extract_archives is True, archives are extracted."""
        settings.set("extract_archives", True)

        # Create a ZIP with some files
        zip_path = create_zip_archive(
            {"file1.txt": "Hello", "file2.txt": "World"},
            name="archive.zip",
        )

        # Create destination in a safe location (mock is_safe_path)
        destination = tmp_path / "dest"
        destination.mkdir()

        files = [str(zip_path)]

        with patch(
            "folder_extractor.core.extractor.is_safe_path", return_value=True
        ):
            result_files, archive_results = extractor._process_archives(
                files=files,
                destination=destination,
                operation_id=None,
                progress_callback=None,
                indexing_callback=None,
            )

        # Archive should be removed from files list (already processed)
        assert str(zip_path) not in result_files
        # Archive results should contain stats
        assert "archives_processed" in archive_results
        assert archive_results["archives_processed"] == 1

    def test_keeps_non_archive_files_in_list(
        self, extractor, create_zip_archive, tmp_path
    ):
        """Non-archive files remain in the files list after processing."""
        settings.set("extract_archives", True)

        zip_path = create_zip_archive({"inner.txt": "content"})
        pdf_path = tmp_path / "document.pdf"
        pdf_path.write_text("PDF content")

        destination = tmp_path / "dest"
        destination.mkdir()

        files = [str(zip_path), str(pdf_path)]

        with patch(
            "folder_extractor.core.extractor.is_safe_path", return_value=True
        ):
            result_files, _ = extractor._process_archives(
                files=files,
                destination=destination,
                operation_id=None,
                progress_callback=None,
                indexing_callback=None,
            )

        # PDF should still be in the list
        assert str(pdf_path) in result_files
        # ZIP should be removed (processed)
        assert str(zip_path) not in result_files

    def test_deletes_archives_when_delete_archives_enabled(
        self, extractor, create_zip_archive, tmp_path
    ):
        """Archives are deleted after extraction when delete_archives is True."""
        settings.set("extract_archives", True)
        settings.set("delete_archives", True)

        zip_path = create_zip_archive({"file.txt": "content"})
        assert zip_path.exists()

        destination = tmp_path / "dest"
        destination.mkdir()

        with patch(
            "folder_extractor.core.extractor.is_safe_path", return_value=True
        ):
            extractor._process_archives(
                files=[str(zip_path)],
                destination=destination,
                operation_id=None,
                progress_callback=None,
                indexing_callback=None,
            )

        # Archive should be deleted
        assert not zip_path.exists()

    def test_keeps_archives_when_delete_archives_disabled(
        self, extractor, create_zip_archive, tmp_path
    ):
        """Archives are kept after extraction when delete_archives is False."""
        settings.set("extract_archives", True)
        settings.set("delete_archives", False)

        zip_path = create_zip_archive({"file.txt": "content"})

        destination = tmp_path / "dest"
        destination.mkdir()

        with patch(
            "folder_extractor.core.extractor.is_safe_path", return_value=True
        ):
            extractor._process_archives(
                files=[str(zip_path)],
                destination=destination,
                operation_id=None,
                progress_callback=None,
                indexing_callback=None,
            )

        # Archive should still exist
        assert zip_path.exists()

    def test_handles_extraction_errors_gracefully(self, extractor, tmp_path):
        """Extraction errors don't crash the process, they're counted."""
        settings.set("extract_archives", True)

        # Create a corrupted ZIP
        corrupted_zip = tmp_path / "corrupted.zip"
        corrupted_zip.write_bytes(b"not a valid zip file")

        destination = tmp_path / "dest"
        destination.mkdir()

        with patch(
            "folder_extractor.core.extractor.is_safe_path", return_value=True
        ):
            result_files, archive_results = extractor._process_archives(
                files=[str(corrupted_zip)],
                destination=destination,
                operation_id=None,
                progress_callback=None,
                indexing_callback=None,
            )

        # Error should be recorded
        assert archive_results.get("archive_errors", 0) >= 1

    def test_calls_progress_callback_during_extraction(
        self, extractor, create_zip_archive, tmp_path
    ):
        """Progress callback is invoked during archive processing."""
        settings.set("extract_archives", True)

        zip_path = create_zip_archive({"file.txt": "content"})
        destination = tmp_path / "dest"
        destination.mkdir()

        progress_calls = []

        def progress_callback(current, total, filename, error):
            progress_calls.append((current, total, filename, error))

        with patch(
            "folder_extractor.core.extractor.is_safe_path", return_value=True
        ):
            extractor._process_archives(
                files=[str(zip_path)],
                destination=destination,
                operation_id=None,
                progress_callback=progress_callback,
                indexing_callback=None,
            )

        # Progress callback should have been called
        assert len(progress_calls) > 0

    def test_respects_abort_signal(self, extractor, create_zip_archive, tmp_path):
        """Processing stops when abort signal is set."""
        settings.set("extract_archives", True)

        # Create multiple archives
        zip1 = create_zip_archive({"file1.txt": "1"}, name="archive1.zip")
        zip2 = create_zip_archive({"file2.txt": "2"}, name="archive2.zip")

        destination = tmp_path / "dest"
        destination.mkdir()

        # Set abort signal before processing using the correct method
        extractor.state_manager.request_abort()

        with patch(
            "folder_extractor.core.extractor.is_safe_path", return_value=True
        ):
            _, archive_results = extractor._process_archives(
                files=[str(zip1), str(zip2)],
                destination=destination,
                operation_id=None,
                progress_callback=None,
                indexing_callback=None,
            )

        # Should have aborted before processing all archives
        assert archive_results.get("aborted", False) is True

        # Clean up abort signal
        extractor.state_manager.clear_abort()
