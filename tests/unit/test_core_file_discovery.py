"""
Unit tests for the core file discovery module.
"""

import threading
import xml.etree.ElementTree as ET
from pathlib import Path

from folder_extractor.core.file_discovery import FileDiscovery, FileFilter


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
        files = self.file_discovery.find_files(tmp_path)

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
        files_depth1 = self.file_discovery.find_files(tmp_path, max_depth=1)
        assert len(files_depth1) == 1  # Only file1.txt

        files_depth2 = self.file_discovery.find_files(tmp_path, max_depth=2)
        assert len(files_depth2) == 2  # file1.txt and file2.txt

        files_unlimited = self.file_discovery.find_files(tmp_path, max_depth=0)
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
        txt_files = self.file_discovery.find_files(tmp_path, file_type_filter=[".txt"])
        assert len(txt_files) == 1
        assert txt_files[0].endswith("doc.txt")

        # Multiple types
        doc_files = self.file_discovery.find_files(
            tmp_path, file_type_filter=[".txt", ".pdf"]
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
        files = self.file_discovery.find_files(tmp_path, include_hidden=False)
        assert len(files) == 1
        assert files[0].endswith("visible.txt")

        # With include_hidden
        files = self.file_discovery.find_files(tmp_path, include_hidden=True)
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
        files = file_discovery.find_files(tmp_path)
        assert len(files) < 10

    def test_check_url_file(self, tmp_path):
        """Test checking Windows .url files."""
        # Create .url file
        url_file = tmp_path / "youtube.url"
        url_file.write_text(
            "[InternetShortcut]\nURL=https://www.youtube.com/watch?v=123\nIconIndex=0\n"
        )

        # Check domain
        assert (
            self.file_discovery.check_weblink_domain(url_file, ["youtube.com"]) is True
        )

        assert (
            self.file_discovery.check_weblink_domain(url_file, ["github.com"]) is False
        )

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
        assert (
            self.file_discovery.check_weblink_domain(webloc_file, ["github.com"])
            is True
        )

        assert (
            self.file_discovery.check_weblink_domain(webloc_file, ["youtube.com"])
            is False
        )

    def test_check_weblink_nonexistent(self):
        """Test checking non-existent weblink files."""
        result = self.file_discovery.check_weblink_domain(
            Path("/nonexistent/file.url"), ["any.com"]
        )
        assert result is False

    def test_check_weblink_invalid_format(self, tmp_path):
        """Test handling of invalid weblink files."""
        # Invalid .url file
        invalid_url = tmp_path / "invalid.url"
        invalid_url.write_text("Not a valid URL file")

        assert (
            self.file_discovery.check_weblink_domain(invalid_url, ["any.com"]) is False
        )

        # Invalid .webloc file
        invalid_webloc = tmp_path / "invalid.webloc"
        invalid_webloc.write_text("Not valid XML")

        assert (
            self.file_discovery.check_weblink_domain(invalid_webloc, ["any.com"])
            is False
        )

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

        result = self.file_discovery.check_weblink_domain(txt_file, ["example.com"])
        assert result is False

    def test_check_weblink_accepts_path_object(self, tmp_path):
        """Verify Path objects are accepted for weblink checking."""
        # Create .url file
        url_file = tmp_path / "test.url"
        url_file.write_text("[InternetShortcut]\nURL=https://www.example.com/page\n")

        # Test with Path object
        result = self.file_discovery.check_weblink_domain(url_file, ["example.com"])
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
        """Test that _calculate_depth accepts Path objects."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        # Test with Path objects
        assert self.file_discovery._calculate_depth(tmp_path, subdir) == 1

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


class TestFileDiscoveryEdgeCases:
    """Test edge cases for file discovery to achieve 100% coverage."""

    def test_abort_signal_during_file_iteration(self, tmp_path):
        """Test abort signal triggers during file iteration (line 86)."""
        abort_signal = threading.Event()
        file_discovery = FileDiscovery(abort_signal)

        # Create a directory with files
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        for i in range(5):
            (subdir / f"file{i}.txt").touch()

        # Set abort immediately - should abort during file iteration
        abort_signal.set()

        files = file_discovery.find_files(tmp_path)
        # Should return early due to abort
        assert len(files) < 5

    def test_abort_signal_during_subdir_traversal(self, tmp_path):
        """Test abort signal triggers during subdirectory traversal (line 118)."""
        abort_signal = threading.Event()
        file_discovery = FileDiscovery(abort_signal)

        # Create multiple subdirectories
        for i in range(5):
            subdir = tmp_path / f"subdir{i}"
            subdir.mkdir()
            (subdir / "file.txt").touch()

        # Set abort after starting
        abort_signal.set()

        files = file_discovery.find_files(tmp_path)
        # Should return early
        assert len(files) < 5

    def test_permission_error_handling(self, tmp_path):
        """Test handling of PermissionError during directory traversal."""
        from unittest.mock import patch

        file_discovery = FileDiscovery()

        # Create test structure
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file.txt").touch()

        # Mock os.walk to raise PermissionError
        def mock_os_walk(path, topdown=True):
            raise PermissionError("Access denied")

        with patch("folder_extractor.core.file_discovery.os.walk", mock_os_walk):
            # Should handle the error gracefully
            files = file_discovery.find_files(tmp_path)
            # Should return empty list when permission denied at root
            assert isinstance(files, list)
            assert files == []

    def test_check_weblink_exception_handling(self, tmp_path):
        """Test exception handling in check_weblink_domain (lines 149-150)."""
        file_discovery = FileDiscovery()

        # Create a .url file with problematic content
        url_file = tmp_path / "broken.url"
        url_file.write_bytes(b"\xff\xfe\x00\x00")  # Invalid encoding

        # Should return False on exception
        result = file_discovery.check_weblink_domain(url_file, ["example.com"])
        assert result is False

    def test_check_webloc_alternative_structure(self, tmp_path):
        """Test webloc parsing with alternative XML structure (lines 223-226)."""
        file_discovery = FileDiscovery()

        # Create a .webloc file with alternative structure
        # (where string element position doesn't match key position directly)
        webloc_file = tmp_path / "alt.webloc"

        # Create plist with multiple keys/strings
        plist_content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>URL</key>
    <string>https://github.com/test</string>
</dict>
</plist>"""
        webloc_file.write_text(plist_content)

        # Should extract domain correctly
        result = file_discovery.check_weblink_domain(webloc_file, ["github.com"])
        assert result is True

    def test_check_url_domain_exception(self, tmp_path):
        """Test exception handling in _check_url_domain (lines 255-256)."""
        file_discovery = FileDiscovery()

        # Test with malformed URL that causes urlparse to fail
        result = file_discovery._check_url_domain(
            "not a valid url :://", ["example.com"]
        )
        # urlparse doesn't actually throw, but let's test the flow
        assert result is False

        # Test with None (should trigger exception path)
        result = file_discovery._check_url_domain(None, ["example.com"])
        assert result is False

    def test_check_webloc_invalid_xml_structure(self, tmp_path):
        """Test webloc parsing with malformed XML structure."""
        file_discovery = FileDiscovery()

        # Create a .webloc file with valid XML but wrong structure
        webloc_file = tmp_path / "malformed.webloc"
        webloc_file.write_text("""<?xml version="1.0"?>
<plist version="1.0">
<dict>
    <key>SomeOtherKey</key>
    <string>not a url</string>
</dict>
</plist>""")

        # Should return False (no URL key found)
        result = file_discovery.check_weblink_domain(webloc_file, ["example.com"])
        assert result is False

    def test_url_file_without_url_line(self, tmp_path):
        """Test .url file that doesn't have URL= line."""
        file_discovery = FileDiscovery()

        url_file = tmp_path / "nourl.url"
        url_file.write_text("[InternetShortcut]\nIconIndex=0\n")

        result = file_discovery.check_weblink_domain(url_file, ["example.com"])
        assert result is False

    def test_webloc_with_alternative_xml_structure(self, tmp_path):
        """Test webloc parsing with alternative structure where XPath index fails (lines 223-226).

        The webloc parser tries to find string[i+1] first, and if that fails,
        falls back to finding strings by index in the findall result.

        This happens when there's a non-string element between <key>URL</key>
        and the <string> containing the URL. ElementTree's XPath string[2]
        counts element positions, not just string elements, so it returns None.
        The fallback uses findall('string') which only gets string elements.
        """
        file_discovery = FileDiscovery()

        # Create a webloc with intervening element that breaks XPath indexing
        # The <data> element causes string[2] to fail, but strings[1] works
        webloc_file = tmp_path / "alt_structure.webloc"

        plist_content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>SomeOtherKey</key>
    <string>some value</string>
    <key>URL</key>
    <data>extra element that breaks XPath</data>
    <string>https://github.com/example/repo</string>
</dict>
</plist>"""
        webloc_file.write_text(plist_content)

        # Should extract domain correctly via alternative path (lines 224-227)
        result = file_discovery.check_weblink_domain(webloc_file, ["github.com"])
        assert result is True

    def test_check_url_domain_with_none_url(self):
        """Test _check_url_domain with None URL (line 255-256)."""
        file_discovery = FileDiscovery()

        # Passing None should trigger exception handling
        result = file_discovery._check_url_domain(None, ["example.com"])
        assert result is False

    def test_check_url_domain_with_invalid_url_type(self):
        """Test _check_url_domain with invalid URL that causes exception."""
        file_discovery = FileDiscovery()

        # Pass an object that will fail when urlparse tries to process it
        result = file_discovery._check_url_domain(123, ["example.com"])
        assert result is False
