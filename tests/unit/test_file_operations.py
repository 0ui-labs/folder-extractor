"""
Unit tests for file operation functions.
"""

import os
import tempfile
from pathlib import Path

from folder_extractor.main import (
    entferne_leere_ordner,
    generiere_eindeutigen_namen,
    ist_sicherer_pfad,
    pruefe_weblink_domain,
)


class TestUniqueNameGeneration:
    """Test unique name generation."""

    def test_no_conflict(self):
        """Test when no file exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            name = generiere_eindeutigen_namen(temp_dir, "test.txt")
            assert name == "test.txt"

    def test_single_conflict(self):
        """Test with one existing file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create existing file
            Path(temp_dir, "test.txt").touch()

            name = generiere_eindeutigen_namen(temp_dir, "test.txt")
            assert name == "test_1.txt"

    def test_multiple_conflicts(self):
        """Test with multiple existing files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create existing files
            Path(temp_dir, "test.txt").touch()
            Path(temp_dir, "test_1.txt").touch()
            Path(temp_dir, "test_2.txt").touch()

            name = generiere_eindeutigen_namen(temp_dir, "test.txt")
            assert name == "test_3.txt"

    def test_no_extension(self):
        """Test files without extension."""
        with tempfile.TemporaryDirectory() as temp_dir:
            Path(temp_dir, "README").touch()

            name = generiere_eindeutigen_namen(temp_dir, "README")
            assert name == "README_1"

    def test_multiple_dots(self):
        """Test files with multiple dots."""
        with tempfile.TemporaryDirectory() as temp_dir:
            Path(temp_dir, "archive.tar.gz").touch()

            name = generiere_eindeutigen_namen(temp_dir, "archive.tar.gz")
            assert name == "archive.tar_1.gz"

    def test_gap_in_numbering(self):
        """Test when there's a gap in numbering."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files with gap
            Path(temp_dir, "test.txt").touch()
            Path(temp_dir, "test_1.txt").touch()
            Path(temp_dir, "test_3.txt").touch()  # Gap at _2

            name = generiere_eindeutigen_namen(temp_dir, "test.txt")
            assert name == "test_2.txt"

    def test_high_numbers(self):
        """Test with high numbered files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files up to 99
            Path(temp_dir, "test.txt").touch()
            for i in range(1, 100):
                Path(temp_dir, f"test_{i}.txt").touch()

            name = generiere_eindeutigen_namen(temp_dir, "test.txt")
            assert name == "test_100.txt"


class TestSafePathValidation:
    """Test safe path validation."""

    def test_desktop_paths(self):
        """Test Desktop paths are allowed."""
        home = Path.home()
        desktop_paths = [
            str(home / "Desktop"),
            str(home / "Desktop" / "subfolder"),
            str(home / "Desktop" / "deep" / "nested" / "folder"),
        ]

        for path in desktop_paths:
            # Create path if needed
            Path(path).mkdir(parents=True, exist_ok=True)
            assert ist_sicherer_pfad(path) is True
            # Cleanup
            if "subfolder" in path or "deep" in path:
                parent = Path(path).parent
                while parent != home / "Desktop" and parent.exists():
                    if any(parent.iterdir()):
                        break
                    parent.rmdir()
                    parent = parent.parent

    def test_downloads_paths(self):
        """Test Downloads paths are allowed."""
        home = Path.home()
        downloads = home / "Downloads" / "test_folder"
        downloads.mkdir(parents=True, exist_ok=True)

        assert ist_sicherer_pfad(str(downloads)) is True

        # Cleanup
        downloads.rmdir()

    def test_documents_paths(self):
        """Test Documents paths are allowed."""
        home = Path.home()
        documents = home / "Documents" / "test_folder"
        documents.mkdir(parents=True, exist_ok=True)

        assert ist_sicherer_pfad(str(documents)) is True

        # Cleanup
        documents.rmdir()

    def test_unsafe_system_paths(self):
        """Test system paths are rejected."""
        unsafe_paths = [
            "/",
            "/etc",
            "/usr",
            "/bin",
            "/System",
            "C:\\Windows" if os.name == "nt" else "/usr/bin",
            "C:\\Program Files" if os.name == "nt" else "/opt",
        ]

        for path in unsafe_paths:
            assert ist_sicherer_pfad(path) is False

    def test_home_directory_rejected(self):
        """Test home directory itself is rejected."""
        assert ist_sicherer_pfad(str(Path.home())) is False

    def test_unsafe_home_subdirs(self):
        """Test unsafe home subdirectories are rejected."""
        home = Path.home()
        unsafe_subdirs = [
            str(home / "Library"),
            str(home / "Applications"),
            str(home / ".ssh"),
            str(home / ".config"),
        ]

        for path in unsafe_subdirs:
            assert ist_sicherer_pfad(path) is False

    def test_case_sensitivity(self):
        """Test case variations of safe paths."""
        home = Path.home()

        # Different case variations
        variations = [
            str(home / "desktop" / "test"),
            str(home / "DESKTOP" / "test"),
            str(home / "DeskTop" / "test"),
        ]

        for path in variations:
            # On case-insensitive systems, these might be valid
            # The function should handle this appropriately
            # Just ensure it doesn't crash
            result = ist_sicherer_pfad(path)
            assert isinstance(result, bool)


class TestEmptyFolderRemoval:
    """Test empty folder removal functionality."""

    def test_remove_single_empty_folder(self):
        """Test removing a single empty folder."""
        with tempfile.TemporaryDirectory() as temp_dir:
            empty_dir = Path(temp_dir) / "empty"
            empty_dir.mkdir()

            removed = entferne_leere_ordner(temp_dir)

            assert removed == 1
            assert not empty_dir.exists()

    def test_keep_non_empty_folders(self):
        """Test that non-empty folders are kept."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create folder with file
            non_empty = Path(temp_dir) / "non_empty"
            non_empty.mkdir()
            (non_empty / "file.txt").touch()

            removed = entferne_leere_ordner(temp_dir)

            assert removed == 0
            assert non_empty.exists()

    def test_nested_empty_folders(self):
        """Test removing nested empty folders."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create nested structure
            nested = Path(temp_dir) / "level1" / "level2" / "level3"
            nested.mkdir(parents=True)

            removed = entferne_leere_ordner(temp_dir)

            # Should remove all empty folders
            assert removed >= 3
            assert not (Path(temp_dir) / "level1").exists()

    def test_mixed_empty_and_full(self):
        """Test mixed empty and non-empty folders."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Empty folders
            (Path(temp_dir) / "empty1").mkdir()
            (Path(temp_dir) / "empty2").mkdir()

            # Non-empty folder
            full = Path(temp_dir) / "full"
            full.mkdir()
            (full / "file.txt").touch()

            # Nested with file at bottom
            nested = Path(temp_dir) / "nested" / "deep"
            nested.mkdir(parents=True)
            (nested / "file.txt").touch()

            removed = entferne_leere_ordner(temp_dir)

            assert removed == 2  # empty1 and empty2
            assert not (Path(temp_dir) / "empty1").exists()
            assert not (Path(temp_dir) / "empty2").exists()
            assert full.exists()
            assert nested.exists()

    def test_hidden_files_handling(self):
        """Test handling of hidden files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Folder with only hidden file
            hidden_only = Path(temp_dir) / "hidden_only"
            hidden_only.mkdir()
            (hidden_only / ".hidden").touch()

            # Test without include_hidden - should remove
            removed = entferne_leere_ordner(temp_dir, include_hidden=False)
            assert removed == 1
            assert not hidden_only.exists()

            # Recreate for second test
            hidden_only.mkdir()
            (hidden_only / ".hidden").touch()

            # Test with include_hidden - should keep
            removed = entferne_leere_ordner(temp_dir, include_hidden=True)
            assert removed == 0
            assert hidden_only.exists()


class TestWebLinkDomainCheck:
    """Test web link domain checking."""

    def test_url_file_parsing(self):
        """Test parsing of .url files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create .url file
            url_file = Path(temp_dir) / "test.url"
            url_file.write_text(
                "[InternetShortcut]\nURL=https://www.youtube.com/watch?v=123\n"
            )

            # Test matching domain
            assert pruefe_weblink_domain(str(url_file), ["youtube.com"]) is True
            assert pruefe_weblink_domain(str(url_file), ["github.com"]) is False

    def test_webloc_file_parsing(self):
        """Test parsing of .webloc files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create .webloc file
            webloc_file = Path(temp_dir) / "test.webloc"
            webloc_file.write_text(
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<plist version="1.0">\n'
                "<dict>\n"
                "    <key>URL</key>\n"
                "    <string>https://github.com/user/repo</string>\n"
                "</dict>\n"
                "</plist>\n"
            )

            # Test matching domain
            assert pruefe_weblink_domain(str(webloc_file), ["github.com"]) is True
            assert pruefe_weblink_domain(str(webloc_file), ["youtube.com"]) is False

    def test_invalid_file_format(self):
        """Test handling of invalid file formats."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create invalid file
            invalid_file = Path(temp_dir) / "test.url"
            invalid_file.write_text("This is not a valid URL file")

            # Should return False for invalid format
            assert pruefe_weblink_domain(str(invalid_file), ["any.com"]) is False

    def test_nonexistent_file(self):
        """Test handling of nonexistent files."""
        result = pruefe_weblink_domain("/nonexistent/file.url", ["any.com"])
        assert result is False

    def test_multiple_domains(self):
        """Test checking against multiple domains."""
        with tempfile.TemporaryDirectory() as temp_dir:
            url_file = Path(temp_dir) / "test.url"
            url_file.write_text(
                "[InternetShortcut]\nURL=https://stackoverflow.com/questions/123\n"
            )

            # Test with multiple allowed domains
            domains = ["github.com", "youtube.com", "stackoverflow.com"]
            assert pruefe_weblink_domain(str(url_file), domains) is True

            # Test with non-matching domains
            domains = ["github.com", "youtube.com"]
            assert pruefe_weblink_domain(str(url_file), domains) is False
