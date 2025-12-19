"""
Unit tests for validator modules.
"""

import os
import tempfile
from pathlib import Path

from folder_extractor.utils.file_validators import (
    is_git_path,
    is_hidden_file,
    is_temp_or_system_file,
    should_include_file,
    validate_file_extension,
)
from folder_extractor.utils.path_validators import (
    get_safe_path_info,
    is_safe_path,
    is_subdirectory,
    normalize_path,
)


class TestFileValidators:
    """Test file validation functions."""

    def test_temp_system_file_detection(self):
        """Test temporary and system file detection."""
        # System files (strings)
        assert is_temp_or_system_file(".DS_Store") is True
        assert is_temp_or_system_file("Thumbs.db") is True
        assert is_temp_or_system_file("desktop.ini") is True

        # Temp files (strings)
        assert is_temp_or_system_file("file.tmp") is True
        assert is_temp_or_system_file("~$temp.doc") is True
        assert is_temp_or_system_file(".swp") is True

        # Normal files (strings)
        assert is_temp_or_system_file("document.pdf") is False
        assert is_temp_or_system_file("normal.txt") is False

        # System files (Path objects) - TDD Red Phase
        assert is_temp_or_system_file(Path(".DS_Store")) is True
        assert is_temp_or_system_file(Path("Thumbs.db")) is True
        assert is_temp_or_system_file(Path("desktop.ini")) is True

        # Temp files (Path objects) - TDD Red Phase
        assert is_temp_or_system_file(Path("file.tmp")) is True
        assert is_temp_or_system_file(Path("~$temp.doc")) is True
        assert is_temp_or_system_file(Path(".swp")) is True

        # Normal files (Path objects) - TDD Red Phase
        assert is_temp_or_system_file(Path("document.pdf")) is False
        assert is_temp_or_system_file(Path("normal.txt")) is False

    def test_git_path_detection(self):
        """Test git path detection."""
        # Git internal paths (strings)
        assert is_git_path(".git/config") is True
        assert is_git_path("project/.git/HEAD") is True
        assert is_git_path("path/to/.git/objects/abc") is True

        # Normal paths (strings)
        assert is_git_path("src/main.py") is False
        assert is_git_path(".gitignore") is False

        # Git internal paths (Path objects)
        assert is_git_path(Path(".git/config")) is True
        assert is_git_path(Path("project/.git/HEAD")) is True
        assert is_git_path(Path("path/to/.git/objects/abc")) is True

        # Normal paths (Path objects)
        assert is_git_path(Path("src/main.py")) is False
        assert is_git_path(Path(".gitignore")) is False

    def test_is_hidden_file(self):
        """Test hidden file detection."""
        # Test with strings
        assert is_hidden_file(".hidden") is True
        assert is_hidden_file(".DS_Store") is True
        assert is_hidden_file("normal.txt") is False
        assert is_hidden_file(".") is False  # Current directory
        assert is_hidden_file("..") is False  # Parent directory

        # Test with Path objects - TDD Red Phase
        assert is_hidden_file(Path(".hidden")) is True
        assert is_hidden_file(Path(".DS_Store")) is True
        assert is_hidden_file(Path("normal.txt")) is False
        assert is_hidden_file(Path(".")) is False  # Current directory
        assert is_hidden_file(Path("..")) is False  # Parent directory

    def test_should_include_file(self):
        """Test comprehensive file inclusion logic."""
        # Normal files should be included (strings)
        assert should_include_file("document.pdf", include_hidden=False) is True

        # System files should be excluded (strings)
        assert should_include_file(".DS_Store", include_hidden=False) is False
        assert should_include_file(".DS_Store", include_hidden=True) is False

        # Hidden files depend on setting (strings)
        assert should_include_file(".hidden", include_hidden=False) is False
        assert should_include_file(".hidden", include_hidden=True) is True

        # Git files always excluded (strings)
        assert should_include_file(".git/config", include_hidden=True) is False

        # Normal files should be included (Path objects)
        assert should_include_file(Path("document.pdf"), include_hidden=False) is True

        # System files should be excluded (Path objects)
        assert should_include_file(Path(".DS_Store"), include_hidden=False) is False
        assert should_include_file(Path(".DS_Store"), include_hidden=True) is False

        # Hidden files depend on setting (Path objects)
        assert should_include_file(Path(".hidden"), include_hidden=False) is False
        assert should_include_file(Path(".hidden"), include_hidden=True) is True

        # Git files always excluded (Path objects)
        assert should_include_file(Path(".git/config"), include_hidden=True) is False

    def test_validate_file_extension(self):
        """Test file extension validation."""
        # No filter allows all (strings)
        assert validate_file_extension("file.pdf", None) is True
        assert validate_file_extension("file.txt", None) is True

        # With filter (strings)
        pdf_filter = [".pdf"]
        assert validate_file_extension("file.pdf", pdf_filter) is True
        assert validate_file_extension("file.PDF", pdf_filter) is True
        assert validate_file_extension("file.txt", pdf_filter) is False

        # Multiple extensions (strings)
        multi_filter = [".pdf", ".jpg", ".png"]
        assert validate_file_extension("doc.pdf", multi_filter) is True
        assert validate_file_extension("img.jpg", multi_filter) is True
        assert validate_file_extension("doc.txt", multi_filter) is False

        # No filter allows all (Path objects) - TDD Red Phase
        assert validate_file_extension(Path("file.pdf"), None) is True
        assert validate_file_extension(Path("file.txt"), None) is True

        # With filter (Path objects) - TDD Red Phase
        assert validate_file_extension(Path("file.pdf"), pdf_filter) is True
        assert validate_file_extension(Path("file.PDF"), pdf_filter) is True
        assert validate_file_extension(Path("file.txt"), pdf_filter) is False

        # Multiple extensions (Path objects) - TDD Red Phase
        assert validate_file_extension(Path("doc.pdf"), multi_filter) is True
        assert validate_file_extension(Path("img.jpg"), multi_filter) is True
        assert validate_file_extension(Path("doc.txt"), multi_filter) is False

    def test_path_object_compatibility(self):
        """Test that functions work with both str and Path objects."""
        from typing import get_type_hints

        # CRITICAL: Check type hints first - this is the actual TDD requirement
        # All functions must have Union[str, Path] type hints for path parameters

        # Check is_temp_or_system_file type hints
        temp_hints = get_type_hints(is_temp_or_system_file)
        filename_type = temp_hints.get("filename")
        assert hasattr(filename_type, "__args__"), (
            "is_temp_or_system_file must have Union[str, Path] type hint for filename parameter"
        )

        # Check is_hidden_file type hints
        hidden_hints = get_type_hints(is_hidden_file)
        path_type = hidden_hints.get("path")
        assert hasattr(path_type, "__args__"), (
            "is_hidden_file must have Union[str, Path] type hint for path parameter"
        )

        # Check validate_file_extension type hints
        validate_hints = get_type_hints(validate_file_extension)
        filepath_type = validate_hints.get("filepath")
        assert hasattr(filepath_type, "__args__"), (
            "validate_file_extension must have Union[str, Path] type hint for filepath parameter"
        )

        # Test cases for is_temp_or_system_file
        temp_system_cases = [
            (".DS_Store", True),
            ("document.pdf", False),
            ("Thumbs.db", True),
            ("normal.txt", False),
        ]

        for filename, expected in temp_system_cases:
            # Test is_temp_or_system_file with both str and Path
            assert is_temp_or_system_file(filename) == expected
            assert is_temp_or_system_file(Path(filename)) == expected

        # Test cases for is_hidden_file
        hidden_cases = [
            (".hidden", True),
            (".DS_Store", True),
            ("normal.txt", False),
            ("document.pdf", False),
        ]

        for filename, expected in hidden_cases:
            # Test is_hidden_file with both str and Path
            assert is_hidden_file(filename) == expected
            assert is_hidden_file(Path(filename)) == expected


class TestPathValidators:
    """Test path validation functions."""

    def test_safe_path_compatibility(self):
        """Test compatibility with original function."""
        from folder_extractor.main import ist_sicherer_pfad as old_func

        home = Path.home()
        test_paths = [
            str(home / "Desktop" / "test"),
            str(home / "Downloads" / "test"),
            str(home / "Documents" / "test"),
            "/etc/passwd",
            str(home),
            str(home / "Library"),
        ]

        for path in test_paths:
            # Create directory if it's supposed to be safe
            if any(safe in path for safe in ["Desktop", "Downloads", "Documents"]):
                Path(path).mkdir(parents=True, exist_ok=True)

            old_result = old_func(path)
            new_result = is_safe_path(path)
            assert old_result == new_result, f"Mismatch for '{path}'"

        # Additional test cases with Path objects
        path_object_tests = [
            home / "Desktop" / "test",
            home / "Downloads" / "test",
            home / "Documents" / "test",
            Path("/etc/passwd"),
            home,
            home / "Library",
        ]

        for path_obj in path_object_tests:
            # Create directory if it's supposed to be safe
            if any(
                safe in str(path_obj) for safe in ["Desktop", "Downloads", "Documents"]
            ):
                path_obj.mkdir(parents=True, exist_ok=True)

            old_result = old_func(str(path_obj))
            new_result = is_safe_path(path_obj)
            assert old_result == new_result, f"Mismatch for Path object '{path_obj}'"

    def test_get_safe_path_info(self):
        """Test detailed path safety information."""
        home = Path.home()

        # Safe path (string)
        safe, reason = get_safe_path_info(str(home / "Desktop" / "test"))
        assert safe is True
        assert "Desktop" in reason

        # Unsafe path - outside home
        safe, reason = get_safe_path_info("/etc")
        assert safe is False
        assert "outside home" in reason

        # Unsafe path - wrong folder
        safe, reason = get_safe_path_info(str(home / "Pictures"))
        assert safe is False
        assert "not in allowed folders" in reason

        # Test with Path objects
        safe, reason = get_safe_path_info(home / "Desktop" / "test")
        assert safe is True
        assert "Desktop" in reason

        safe, reason = get_safe_path_info(Path("/etc"))
        assert safe is False
        assert "outside home" in reason

        safe, reason = get_safe_path_info(home / "Pictures")
        assert safe is False
        assert "not in allowed folders" in reason

    def test_normalize_path(self):
        """Test path normalization."""

        # Test tilde expansion (string)
        normalized = normalize_path("~/Desktop")
        assert normalized == str(Path.home() / "Desktop")

        # Test relative path - use a known valid directory to avoid CWD issues
        # from other tests that may have deleted their temp directories
        try:
            original_cwd = os.getcwd()
        except (FileNotFoundError, OSError):
            original_cwd = str(Path.home())
            os.chdir(original_cwd)

        with tempfile.TemporaryDirectory() as temp_dir:
            # Resolve temp_dir to handle macOS /var -> /private/var symlink
            resolved_temp = str(Path(temp_dir).resolve())
            os.chdir(resolved_temp)
            try:
                normalized = normalize_path("./test")
                assert normalized == str(Path(resolved_temp) / "test")
            finally:
                os.chdir(original_cwd)

        # Test already absolute - resolve handles symlinks (e.g., /tmp -> /private/tmp on macOS)
        abs_path = "/tmp/test"
        assert normalize_path(abs_path) == str(Path(abs_path).resolve())

        # Test with Path objects
        normalized = normalize_path(Path("~/Desktop"))
        assert normalized == str(Path.home() / "Desktop")

        with tempfile.TemporaryDirectory() as temp_dir:
            resolved_temp = str(Path(temp_dir).resolve())
            try:
                original_cwd = os.getcwd()
            except (FileNotFoundError, OSError):
                original_cwd = str(Path.home())
                os.chdir(original_cwd)

            os.chdir(resolved_temp)
            try:
                normalized = normalize_path(Path("./test"))
                assert normalized == str(Path(resolved_temp) / "test")
            finally:
                os.chdir(original_cwd)

    def test_is_subdirectory(self):
        """Test subdirectory checking."""
        # Simple case (strings)
        assert is_subdirectory("/parent", "/parent/child") is True
        assert is_subdirectory("/parent", "/parent/child/grandchild") is True

        # Not subdirectory
        assert is_subdirectory("/parent", "/other") is False
        assert is_subdirectory("/parent/child", "/parent") is False

        # Same directory
        assert is_subdirectory("/same", "/same") is True

        # Test with Path objects
        assert is_subdirectory(Path("/parent"), Path("/parent/child")) is True
        assert (
            is_subdirectory(Path("/parent"), Path("/parent/child/grandchild")) is True
        )

        # Not subdirectory (Path objects)
        assert is_subdirectory(Path("/parent"), Path("/other")) is False
        assert is_subdirectory(Path("/parent/child"), Path("/parent")) is False

        # Same directory (Path objects)
        assert is_subdirectory(Path("/same"), Path("/same")) is True

    def test_path_object_acceptance(self):
        """Explicitly verify all functions accept Path objects.

        This test verifies that functions have proper type hints and
        explicitly document Path object support through Union[str, Path].
        """
        from typing import get_type_hints

        home = Path.home()

        # Test type hints - these should show Union[str, Path] support
        # This will fail until we update the type annotations
        is_safe_path_hints = get_type_hints(is_safe_path)
        get_type_hints(get_safe_path_info)
        get_type_hints(normalize_path)
        get_type_hints(is_subdirectory)

        # Verify Path is in the type hints (Union[str, Path])
        # Note: This is the actual TDD requirement - type hints must be updated
        assert (
            hasattr(is_safe_path_hints.get("path", None), "__args__")
            or is_safe_path_hints.get("path").__name__ == "Path"
        ), "is_safe_path should have Union[str, Path] type hint for path parameter"

        # Test is_safe_path with Path object
        desktop_path = home / "Desktop" / "pathlib_test"
        desktop_path.mkdir(parents=True, exist_ok=True)
        result = is_safe_path(desktop_path)
        assert isinstance(result, bool), (
            "is_safe_path should return bool for Path object"
        )

        # Test get_safe_path_info with Path object
        safe, reason = get_safe_path_info(desktop_path)
        assert isinstance(safe, bool), (
            "get_safe_path_info should return bool for Path object"
        )
        assert isinstance(reason, str), (
            "get_safe_path_info should return string reason for Path object"
        )

        # Test normalize_path with Path object
        normalized = normalize_path(Path("~/Desktop"))
        assert isinstance(normalized, str), (
            "normalize_path should return string for Path object"
        )
        assert normalized == str(home / "Desktop")

        # Test is_subdirectory with Path objects
        parent = Path("/test/parent")
        child = Path("/test/parent/child")
        result = is_subdirectory(parent, child)
        assert isinstance(result, bool), (
            "is_subdirectory should return bool for Path objects"
        )
        assert result is True

    def test_edge_cases_for_coverage(self):
        """Test edge cases to achieve 100% coverage.

        Tests exception handlers and edge cases in path_validators.py:
        - Line 40-41: General exception in is_safe_path
        - Line 64: Empty path parts in get_safe_path_info
        - Line 71-72: General exception in get_safe_path_info
        """
        from unittest.mock import patch

        # Test is_safe_path with general exception (lines 40-41)
        with patch("folder_extractor.utils.path_validators.Path") as mock_path:
            mock_path.side_effect = Exception("Mocked exception")
            result = is_safe_path("/some/path")
            assert result is False

        # Test get_safe_path_info for home directory itself (line 64 - empty parts)
        home = Path.home()
        safe, reason = get_safe_path_info(home)
        assert safe is False
        assert "Invalid path structure" in reason

        # Test get_safe_path_info with general exception (lines 71-72)
        with patch("folder_extractor.utils.path_validators.Path") as mock_path:
            mock_path.side_effect = Exception("Mocked exception")
            safe, reason = get_safe_path_info("/some/path")
            assert safe is False
            assert "Error validating path" in reason


class TestFileValidatorEdgeCases:
    """Test edge cases for file validators to achieve 100% coverage."""

    def test_case_insensitive_system_file_detection(self):
        """Test case-insensitive matching of system files (line 68)."""
        # Test lowercase variants of SYSTEM_FILES
        assert is_temp_or_system_file("thumbs.db") is True  # lowercase of Thumbs.db
        assert is_temp_or_system_file("desktop.INI") is True  # mixed case
        assert is_temp_or_system_file("THUMBS.DB") is True  # uppercase

    def test_editor_temp_file_patterns_ending_with_star(self):
        """Test wildcard patterns from EDITOR_TEMP_FILES that end with * (lines 77-79)."""
        # Test patterns that end with * like "~$" prefix files
        # These are patterns like "~$*" that match anything starting with "~$"
        assert is_temp_or_system_file("~$document.docx") is True
        assert is_temp_or_system_file("~$spreadsheet.xlsx") is True

    def test_tilde_dollar_prefix(self):
        """Test ~$ prefix for Office temp files (line 88)."""
        assert is_temp_or_system_file("~$MyWord.docx") is True
        assert is_temp_or_system_file("~$Excel.xlsx") is True

    def test_dot_tilde_prefix(self):
        """Test .~ prefix (line 88)."""
        assert is_temp_or_system_file(".~lock.document.docx#") is True
        assert is_temp_or_system_file(".~temp_file") is True

    def test_emacs_hash_temp_files(self):
        """Test #...# pattern for Emacs autosave files (line 91)."""
        assert is_temp_or_system_file("#autosave#") is True
        assert is_temp_or_system_file("#backup#") is True
        # But not files that just start with #
        assert is_temp_or_system_file("#not_temp.txt") is False

    def test_dot_hash_prefix(self):
        """Test .# prefix for Emacs lock files (line 91)."""
        assert is_temp_or_system_file(".#lockfile") is True
        assert is_temp_or_system_file(".#document.txt") is True

    def test_tilde_suffix(self):
        """Test ~ suffix for backup files (line 94)."""
        assert is_temp_or_system_file("document.txt~") is True
        assert is_temp_or_system_file("backup~") is True

    def test_macos_resource_fork_prefix(self):
        """Test ._ prefix for macOS resource forks (line 98)."""
        assert is_temp_or_system_file("._document.pdf") is True
        assert is_temp_or_system_file("._image.jpg") is True
        assert is_temp_or_system_file("._DS_Store") is True
