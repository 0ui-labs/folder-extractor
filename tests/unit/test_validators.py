"""
Unit tests for validator modules.
"""
import pytest
import tempfile
from pathlib import Path

from folder_extractor.utils.file_validators import (
    is_temp_or_system_file,
    is_git_path,
    is_hidden_file,
    should_include_file,
    validate_file_extension
)

from folder_extractor.utils.path_validators import (
    is_safe_path,
    get_safe_path_info,
    normalize_path,
    is_subdirectory
)


class TestFileValidators:
    """Test file validation functions."""
    
    def test_temp_system_file_detection(self):
        """Test temporary and system file detection."""
        # System files
        assert is_temp_or_system_file(".DS_Store") is True
        assert is_temp_or_system_file("Thumbs.db") is True
        assert is_temp_or_system_file("desktop.ini") is True
        
        # Temp files
        assert is_temp_or_system_file("file.tmp") is True
        assert is_temp_or_system_file("~$temp.doc") is True
        assert is_temp_or_system_file(".swp") is True
        
        # Normal files
        assert is_temp_or_system_file("document.pdf") is False
        assert is_temp_or_system_file("normal.txt") is False
    
    def test_git_path_detection(self):
        """Test git path detection."""
        # Git internal paths
        assert is_git_path(".git/config") is True
        assert is_git_path("project/.git/HEAD") is True
        assert is_git_path("path/to/.git/objects/abc") is True
        
        # Normal paths
        assert is_git_path("src/main.py") is False
        assert is_git_path(".gitignore") is False
    
    def test_is_hidden_file(self):
        """Test hidden file detection."""
        assert is_hidden_file(".hidden") is True
        assert is_hidden_file(".DS_Store") is True
        assert is_hidden_file("normal.txt") is False
        assert is_hidden_file(".") is False  # Current directory
        assert is_hidden_file("..") is False  # Parent directory
    
    def test_should_include_file(self):
        """Test comprehensive file inclusion logic."""
        # Normal files should be included
        assert should_include_file("document.pdf", include_hidden=False) is True
        
        # System files should be excluded
        assert should_include_file(".DS_Store", include_hidden=False) is False
        assert should_include_file(".DS_Store", include_hidden=True) is False
        
        # Hidden files depend on setting
        assert should_include_file(".hidden", include_hidden=False) is False
        assert should_include_file(".hidden", include_hidden=True) is True
        
        # Git files always excluded
        assert should_include_file(".git/config", include_hidden=True) is False
    
    def test_validate_file_extension(self):
        """Test file extension validation."""
        # No filter allows all
        assert validate_file_extension("file.pdf", None) is True
        assert validate_file_extension("file.txt", None) is True
        
        # With filter
        pdf_filter = [".pdf"]
        assert validate_file_extension("file.pdf", pdf_filter) is True
        assert validate_file_extension("file.PDF", pdf_filter) is True
        assert validate_file_extension("file.txt", pdf_filter) is False
        
        # Multiple extensions
        multi_filter = [".pdf", ".jpg", ".png"]
        assert validate_file_extension("doc.pdf", multi_filter) is True
        assert validate_file_extension("img.jpg", multi_filter) is True
        assert validate_file_extension("doc.txt", multi_filter) is False


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
            str(home / "Library")
        ]
        
        for path in test_paths:
            # Create directory if it's supposed to be safe
            if any(safe in path for safe in ["Desktop", "Downloads", "Documents"]):
                Path(path).mkdir(parents=True, exist_ok=True)
            
            old_result = old_func(path)
            new_result = is_safe_path(path)
            assert old_result == new_result, f"Mismatch for '{path}'"
    
    def test_get_safe_path_info(self):
        """Test detailed path safety information."""
        home = Path.home()
        
        # Safe path
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
    
    def test_normalize_path(self):
        """Test path normalization."""
        # Test tilde expansion
        normalized = normalize_path("~/Desktop")
        assert normalized == str(Path.home() / "Desktop")
        
        # Test relative path
        cwd = Path.cwd()
        normalized = normalize_path("./test")
        assert normalized == str(cwd / "test")
        
        # Test already absolute
        abs_path = "/tmp/test"
        assert normalize_path(abs_path) == abs_path
    
    def test_is_subdirectory(self):
        """Test subdirectory checking."""
        # Simple case
        assert is_subdirectory("/parent", "/parent/child") is True
        assert is_subdirectory("/parent", "/parent/child/grandchild") is True
        
        # Not subdirectory
        assert is_subdirectory("/parent", "/other") is False
        assert is_subdirectory("/parent/child", "/parent") is False
        
        # Same directory
        assert is_subdirectory("/same", "/same") is True