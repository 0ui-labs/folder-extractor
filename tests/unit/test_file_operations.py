"""
Unit tests for file operation functions.
"""

import os
from pathlib import Path

from folder_extractor.main import (
    entferne_leere_ordner,
    generiere_eindeutigen_namen,
    ist_sicherer_pfad,
    pruefe_weblink_domain,
)


class TestUniqueNameGeneration:
    """Test unique name generation."""

    def test_no_conflict(self, tmp_path):
        """Test when no file exists."""
        name = generiere_eindeutigen_namen(tmp_path, "test.txt")
        assert name == "test.txt"

    def test_single_conflict(self, tmp_path):
        """Test with one existing file."""
        # Create existing file
        (tmp_path / "test.txt").touch()

        name = generiere_eindeutigen_namen(tmp_path, "test.txt")
        assert name == "test_1.txt"

    def test_multiple_conflicts(self, tmp_path):
        """Test with multiple existing files."""
        # Create existing files
        (tmp_path / "test.txt").touch()
        (tmp_path / "test_1.txt").touch()
        (tmp_path / "test_2.txt").touch()

        name = generiere_eindeutigen_namen(tmp_path, "test.txt")
        assert name == "test_3.txt"

    def test_no_extension(self, tmp_path):
        """Test files without extension."""
        (tmp_path / "README").touch()

        name = generiere_eindeutigen_namen(tmp_path, "README")
        assert name == "README_1"

    def test_multiple_dots(self, tmp_path):
        """Test files with multiple dots."""
        (tmp_path / "archive.tar.gz").touch()

        name = generiere_eindeutigen_namen(tmp_path, "archive.tar.gz")
        assert name == "archive.tar_1.gz"

    def test_gap_in_numbering(self, tmp_path):
        """Test when there's a gap in numbering."""
        # Create files with gap
        (tmp_path / "test.txt").touch()
        (tmp_path / "test_1.txt").touch()
        (tmp_path / "test_3.txt").touch()  # Gap at _2

        name = generiere_eindeutigen_namen(tmp_path, "test.txt")
        assert name == "test_2.txt"

    def test_high_numbers(self, tmp_path):
        """Test with high numbered files."""
        # Create files up to 99
        (tmp_path / "test.txt").touch()
        for i in range(1, 100):
            (tmp_path / f"test_{i}.txt").touch()

        name = generiere_eindeutigen_namen(tmp_path, "test.txt")
        assert name == "test_100.txt"


class TestSafePathValidation:
    """Test safe path validation."""

    def test_desktop_paths(self):
        """Test Desktop paths are allowed."""
        home = Path.home()
        desktop_paths = [
            home / "Desktop",
            home / "Desktop" / "subfolder",
            home / "Desktop" / "deep" / "nested" / "folder",
        ]

        for path in desktop_paths:
            # Create path if needed
            path.mkdir(parents=True, exist_ok=True)
            assert ist_sicherer_pfad(path) is True
            # Cleanup
            if "subfolder" in str(path) or "deep" in str(path):
                parent = path.parent
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

        assert ist_sicherer_pfad(downloads) is True

        # Cleanup
        downloads.rmdir()

    def test_documents_paths(self):
        """Test Documents paths are allowed."""
        home = Path.home()
        documents = home / "Documents" / "test_folder"
        documents.mkdir(parents=True, exist_ok=True)

        assert ist_sicherer_pfad(documents) is True

        # Cleanup
        documents.rmdir()

    def test_unsafe_system_paths(self):
        """Test system paths are rejected."""
        unsafe_paths = [
            Path("/"),
            Path("/etc"),
            Path("/usr"),
            Path("/bin"),
            Path("/System"),
            Path("C:\\Windows") if os.name == "nt" else Path("/usr/bin"),
            Path("C:\\Program Files") if os.name == "nt" else Path("/opt"),
        ]

        for path in unsafe_paths:
            assert ist_sicherer_pfad(path) is False

    def test_home_directory_rejected(self):
        """Test home directory itself is rejected."""
        assert ist_sicherer_pfad(Path.home()) is False

    def test_unsafe_home_subdirs(self):
        """Test unsafe home subdirectories are rejected."""
        home = Path.home()
        unsafe_subdirs = [
            home / "Library",
            home / "Applications",
            home / ".ssh",
            home / ".config",
        ]

        for path in unsafe_subdirs:
            assert ist_sicherer_pfad(path) is False

    def test_case_sensitivity(self):
        """Test case variations of safe paths."""
        home = Path.home()

        # Different case variations
        variations = [
            home / "desktop" / "test",
            home / "DESKTOP" / "test",
            home / "DeskTop" / "test",
        ]

        for path in variations:
            # On case-insensitive systems, these might be valid
            # The function should handle this appropriately
            # Just ensure it doesn't crash
            result = ist_sicherer_pfad(path)
            assert isinstance(result, bool)


class TestEmptyFolderRemoval:
    """Test empty folder removal functionality."""

    def test_remove_single_empty_folder(self, tmp_path):
        """Test removing a single empty folder."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        removed = entferne_leere_ordner(tmp_path)

        assert removed == 1
        assert not empty_dir.exists()

    def test_keep_non_empty_folders(self, tmp_path):
        """Test that non-empty folders are kept."""
        # Create folder with file
        non_empty = tmp_path / "non_empty"
        non_empty.mkdir()
        (non_empty / "file.txt").touch()

        removed = entferne_leere_ordner(tmp_path)

        assert removed == 0
        assert non_empty.exists()

    def test_nested_empty_folders(self, tmp_path):
        """Test removing nested empty folders."""
        # Create nested structure
        nested = tmp_path / "level1" / "level2" / "level3"
        nested.mkdir(parents=True)

        removed = entferne_leere_ordner(tmp_path)

        # Should remove all empty folders
        assert removed >= 3
        assert not (tmp_path / "level1").exists()

    def test_mixed_empty_and_full(self, tmp_path):
        """Test mixed empty and non-empty folders."""
        # Empty folders
        (tmp_path / "empty1").mkdir()
        (tmp_path / "empty2").mkdir()

        # Non-empty folder
        full = tmp_path / "full"
        full.mkdir()
        (full / "file.txt").touch()

        # Nested with file at bottom
        nested = tmp_path / "nested" / "deep"
        nested.mkdir(parents=True)
        (nested / "file.txt").touch()

        removed = entferne_leere_ordner(tmp_path)

        assert removed == 2  # empty1 and empty2
        assert not (tmp_path / "empty1").exists()
        assert not (tmp_path / "empty2").exists()
        assert full.exists()
        assert nested.exists()

    def test_hidden_files_handling(self, tmp_path):
        """Test handling of hidden files."""
        # Folder with only hidden file
        hidden_only = tmp_path / "hidden_only"
        hidden_only.mkdir()
        (hidden_only / ".hidden").touch()

        # Test without include_hidden - should remove
        removed = entferne_leere_ordner(tmp_path, include_hidden=False)
        assert removed == 1
        assert not hidden_only.exists()

        # Recreate for second test
        hidden_only.mkdir()
        (hidden_only / ".hidden").touch()

        # Test with include_hidden - should keep
        removed = entferne_leere_ordner(tmp_path, include_hidden=True)
        assert removed == 0
        assert hidden_only.exists()


class TestWebLinkDomainCheck:
    """Test web link domain checking."""

    def test_url_file_parsing(self, tmp_path):
        """Test parsing of .url files."""
        # Create .url file
        url_file = tmp_path / "test.url"
        url_file.write_text(
            "[InternetShortcut]\nURL=https://www.youtube.com/watch?v=123\n"
        )

        # Test matching domain
        assert pruefe_weblink_domain(url_file, ["youtube.com"]) is True
        assert pruefe_weblink_domain(url_file, ["github.com"]) is False

    def test_webloc_file_parsing(self, tmp_path):
        """Test parsing of .webloc files."""
        # Create .webloc file
        webloc_file = tmp_path / "test.webloc"
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
        assert pruefe_weblink_domain(webloc_file, ["github.com"]) is True
        assert pruefe_weblink_domain(webloc_file, ["youtube.com"]) is False

    def test_invalid_file_format(self, tmp_path):
        """Test handling of invalid file formats."""
        # Create invalid file
        invalid_file = tmp_path / "test.url"
        invalid_file.write_text("This is not a valid URL file")

        # Should return False for invalid format
        assert pruefe_weblink_domain(invalid_file, ["any.com"]) is False

    def test_nonexistent_file(self):
        """Test handling of nonexistent files."""
        result = pruefe_weblink_domain(Path("/nonexistent/file.url"), ["any.com"])
        assert result is False

    def test_multiple_domains(self, tmp_path):
        """Test checking against multiple domains."""
        url_file = tmp_path / "test.url"
        url_file.write_text(
            "[InternetShortcut]\nURL=https://stackoverflow.com/questions/123\n"
        )

        # Test with multiple allowed domains
        domains = ["github.com", "youtube.com", "stackoverflow.com"]
        assert pruefe_weblink_domain(url_file, domains) is True

        # Test with non-matching domains
        domains = ["github.com", "youtube.com"]
        assert pruefe_weblink_domain(url_file, domains) is False
