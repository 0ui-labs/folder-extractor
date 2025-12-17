"""
Unit tests for the core file discovery module.
"""
import pytest
from pathlib import Path
import threading
import xml.etree.ElementTree as ET

from folder_extractor.core.file_discovery import (
    FileDiscovery,
    FileFilter
)


class TestFileDiscovery:
    """Test FileDiscovery class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.file_discovery = FileDiscovery()
    
    def test_find_files_basic(self, tmp_path):
        """Test basic file discovery."""
        # Create file structure
        (tmp_path / "subdir1").mkdir()
        (tmp_path / "subdir2").mkdir()

        # Create files
        (tmp_path / "subdir1" / "file1.txt").touch()
        (tmp_path / "subdir1" / "file2.pdf").touch()
        (tmp_path / "subdir2" / "file3.txt").touch()

        # Find files
        files = self.file_discovery.find_files(str(tmp_path))

        assert len(files) == 3
        filenames = [Path(f).name for f in files]
        assert "file1.txt" in filenames
        assert "file2.pdf" in filenames
        assert "file3.txt" in filenames
    
    def test_find_files_max_depth(self, tmp_path):
        """Test file discovery with depth limit."""
        # Create nested structure
        deep_path = tmp_path / "level1" / "level2" / "level3"
        deep_path.mkdir(parents=True)

        # Create files at different levels
        (tmp_path / "level1" / "file1.txt").touch()
        (tmp_path / "level1" / "level2" / "file2.txt").touch()
        (deep_path / "file3.txt").touch()

        # Test different depths
        files_depth1 = self.file_discovery.find_files(str(tmp_path), max_depth=1)
        assert len(files_depth1) == 1  # Only file1.txt

        files_depth2 = self.file_discovery.find_files(str(tmp_path), max_depth=2)
        assert len(files_depth2) == 2  # file1.txt and file2.txt

        files_unlimited = self.file_discovery.find_files(str(tmp_path), max_depth=0)
        assert len(files_unlimited) == 3  # All files
    
    def test_find_files_type_filter(self, tmp_path):
        """Test file discovery with type filtering."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        # Create various file types
        (subdir / "doc.txt").touch()
        (subdir / "doc.pdf").touch()
        (subdir / "image.jpg").touch()
        (subdir / "data.json").touch()

        # Filter for specific types
        txt_files = self.file_discovery.find_files(
            str(tmp_path), file_type_filter=[".txt"]
        )
        assert len(txt_files) == 1
        assert txt_files[0].endswith("doc.txt")

        # Multiple types
        doc_files = self.file_discovery.find_files(
            str(tmp_path), file_type_filter=[".txt", ".pdf"]
        )
        assert len(doc_files) == 2
    
    def test_find_files_hidden_files(self, tmp_path):
        """Test handling of hidden files."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        hidden_dir = tmp_path / ".hidden"
        hidden_dir.mkdir()

        # Create files
        (subdir / "visible.txt").touch()
        (subdir / ".hidden.txt").touch()
        (hidden_dir / "file.txt").touch()

        # Without include_hidden
        files = self.file_discovery.find_files(str(tmp_path), include_hidden=False)
        assert len(files) == 1
        assert files[0].endswith("visible.txt")

        # With include_hidden
        files = self.file_discovery.find_files(str(tmp_path), include_hidden=True)
        assert len(files) == 3
    
    def test_find_files_abort_signal(self, tmp_path):
        """Test abort signal handling."""
        abort_signal = threading.Event()
        file_discovery = FileDiscovery(abort_signal)

        # Create many subdirectories
        for i in range(10):
            subdir = tmp_path / f"subdir{i}"
            subdir.mkdir()
            (subdir / "file.txt").touch()

        # Set abort signal
        abort_signal.set()

        # Should return fewer files due to abort
        files = file_discovery.find_files(str(tmp_path))
        assert len(files) < 10
    
    def test_check_url_file(self, tmp_path):
        """Test checking Windows .url files."""
        # Create .url file
        url_file = tmp_path / "youtube.url"
        url_file.write_text(
            "[InternetShortcut]\n"
            "URL=https://www.youtube.com/watch?v=123\n"
            "IconIndex=0\n"
        )

        # Check domain
        assert self.file_discovery.check_weblink_domain(
            str(url_file), ["youtube.com"]
        ) is True

        assert self.file_discovery.check_weblink_domain(
            str(url_file), ["github.com"]
        ) is False
    
    def test_check_webloc_file(self, tmp_path):
        """Test checking macOS .webloc files."""
        # Create .webloc file
        webloc_file = tmp_path / "github.webloc"

        # Create plist structure
        plist = ET.Element("plist", version="1.0")
        dict_elem = ET.SubElement(plist, "dict")
        ET.SubElement(dict_elem, "key").text = "URL"
        ET.SubElement(dict_elem, "string").text = "https://github.com/user/repo"

        # Write XML
        tree = ET.ElementTree(plist)
        tree.write(str(webloc_file), encoding="UTF-8", xml_declaration=True)

        # Check domain
        assert self.file_discovery.check_weblink_domain(
            str(webloc_file), ["github.com"]
        ) is True

        assert self.file_discovery.check_weblink_domain(
            str(webloc_file), ["youtube.com"]
        ) is False
    
    def test_check_weblink_nonexistent(self):
        """Test checking non-existent weblink files."""
        result = self.file_discovery.check_weblink_domain(
            "/nonexistent/file.url", ["any.com"]
        )
        assert result is False
    
    def test_check_weblink_invalid_format(self, tmp_path):
        """Test handling of invalid weblink files."""
        # Invalid .url file
        invalid_url = tmp_path / "invalid.url"
        invalid_url.write_text("Not a valid URL file")

        assert self.file_discovery.check_weblink_domain(
            str(invalid_url), ["any.com"]
        ) is False

        # Invalid .webloc file
        invalid_webloc = tmp_path / "invalid.webloc"
        invalid_webloc.write_text("Not valid XML")

        assert self.file_discovery.check_weblink_domain(
            str(invalid_webloc), ["any.com"]
        ) is False

    def test_find_files_accepts_string_path(self, tmp_path):
        """Verify backward compatibility with string paths."""
        # Create test structure
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file.txt").touch()

        # Test with string path
        files = self.file_discovery.find_files(str(tmp_path))

        assert len(files) == 1
        assert files[0].endswith("file.txt")
        assert isinstance(files[0], str)

    def test_find_files_accepts_path_object(self, tmp_path):
        """Verify Path objects are accepted."""
        # Create test structure
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file.txt").touch()

        # Test with Path object
        files = self.file_discovery.find_files(tmp_path)

        assert len(files) == 1
        assert files[0].endswith("file.txt")
        assert isinstance(files[0], str)

    def test_find_files_includes_root_files(self, tmp_path):
        """Test that files in root directory are included."""
        # Create files in root and subdirectory
        (tmp_path / "root_file.txt").touch()
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "subdir_file.txt").touch()

        # Find all files
        files = self.file_discovery.find_files(tmp_path)

        assert len(files) == 2
        filenames = [Path(f).name for f in files]
        assert "root_file.txt" in filenames
        assert "subdir_file.txt" in filenames

    def test_find_files_root_only_with_max_depth_zero(self, tmp_path):
        """Test that max_depth=0 returns all files including root (unlimited depth)."""
        # Create nested structure
        (tmp_path / "root.txt").touch()
        level1 = tmp_path / "level1"
        level1.mkdir()
        (level1 / "level1.txt").touch()
        level2 = level1 / "level2"
        level2.mkdir()
        (level2 / "level2.txt").touch()

        # max_depth=0 means unlimited
        files = self.file_discovery.find_files(tmp_path, max_depth=0)

        assert len(files) == 3
        filenames = [Path(f).name for f in files]
        assert "root.txt" in filenames
        assert "level1.txt" in filenames
        assert "level2.txt" in filenames

    def test_check_weblink_unsupported_extension(self, tmp_path):
        """Test that unsupported file extensions return False."""
        # Create a .txt file (not .url or .webloc)
        txt_file = tmp_path / "link.txt"
        txt_file.write_text("https://example.com")

        result = self.file_discovery.check_weblink_domain(
            str(txt_file), ["example.com"]
        )
        assert result is False

    def test_check_weblink_accepts_path_object(self, tmp_path):
        """Verify Path objects are accepted for weblink checking."""
        # Create .url file
        url_file = tmp_path / "test.url"
        url_file.write_text(
            "[InternetShortcut]\n"
            "URL=https://www.example.com/page\n"
        )

        # Test with Path object
        result = self.file_discovery.check_weblink_domain(
            url_file, ["example.com"]
        )
        assert result is True

    def test_calculate_depth(self, tmp_path):
        """Test depth calculation between directories."""
        # Create nested structure
        level1 = tmp_path / "level1"
        level2 = level1 / "level2"
        level3 = level2 / "level3"
        level3.mkdir(parents=True)

        # Test various depths
        assert self.file_discovery._calculate_depth(tmp_path, tmp_path) == 0
        assert self.file_discovery._calculate_depth(tmp_path, level1) == 1
        assert self.file_discovery._calculate_depth(tmp_path, level2) == 2
        assert self.file_discovery._calculate_depth(tmp_path, level3) == 3

    def test_calculate_depth_accepts_path_objects(self, tmp_path):
        """Test that _calculate_depth accepts both strings and Path objects."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        # Test with Path objects
        assert self.file_discovery._calculate_depth(tmp_path, subdir) == 1
        # Test with strings
        assert self.file_discovery._calculate_depth(str(tmp_path), str(subdir)) == 1
        # Test mixed
        assert self.file_discovery._calculate_depth(tmp_path, str(subdir)) == 1

    def test_calculate_depth_unrelated_paths(self, tmp_path):
        """Test depth calculation with unrelated paths."""
        # Create two separate directories
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        # Unrelated paths should return 0
        result = self.file_discovery._calculate_depth(dir1, dir2)
        assert result == 0


class TestFileFilter:
    """Test FileFilter class."""
    
    def test_extension_filter(self):
        """Test extension filtering."""
        filter = FileFilter()
        filter.add_extension_filter([".txt", ".pdf"])
        
        assert filter.apply("/path/to/file.txt") is True
        assert filter.apply("/path/to/file.pdf") is True
        assert filter.apply("/path/to/file.jpg") is False
    
    def test_size_filter(self, tmp_path):
        """Test size filtering."""
        # Create files of different sizes
        small_file = tmp_path / "small.txt"
        small_file.write_text("small")  # 5 bytes

        large_file = tmp_path / "large.txt"
        large_file.write_text("x" * 1000)  # 1000 bytes

        # Test min size
        filter = FileFilter()
        filter.add_size_filter(min_size=100)

        assert filter.apply(str(small_file)) is False
        assert filter.apply(str(large_file)) is True

        # Test max size
        filter = FileFilter()
        filter.add_size_filter(max_size=100)

        assert filter.apply(str(small_file)) is True
        assert filter.apply(str(large_file)) is False

        # Test range
        filter = FileFilter()
        filter.add_size_filter(min_size=10, max_size=500)

        assert filter.apply(str(small_file)) is False
        assert filter.apply(str(large_file)) is False
    
    def test_name_pattern_filter(self):
        """Test filename pattern filtering."""
        filter = FileFilter()
        filter.add_name_pattern_filter("test_*.txt")
        
        assert filter.apply("/path/to/test_file.txt") is True
        assert filter.apply("/path/to/test_123.txt") is True
        assert filter.apply("/path/to/other.txt") is False
        assert filter.apply("/path/to/test_file.pdf") is False
    
    def test_combined_filters(self, tmp_path):
        """Test combining multiple filters."""
        # Create test file
        test_file = tmp_path / "test_document.txt"
        test_file.write_text("x" * 500)  # 500 bytes

        # Create filter with multiple conditions
        filter = FileFilter()
        filter.add_extension_filter([".txt", ".pdf"])
        filter.add_size_filter(min_size=100, max_size=1000)
        filter.add_name_pattern_filter("test_*")

        # Should pass all filters
        assert filter.apply(str(test_file)) is True

        # Create file that fails one filter
        other_file = tmp_path / "other.txt"
        other_file.write_text("x" * 500)

        # Fails pattern filter
        assert filter.apply(str(other_file)) is False

    def test_size_filter_nonexistent_file(self):
        """Test size filter with non-existent file."""
        filter = FileFilter()
        filter.add_size_filter(min_size=0)

        # Non-existent file should return False (OSError handling)
        result = filter.apply("/nonexistent/path/file.txt")
        assert result is False
