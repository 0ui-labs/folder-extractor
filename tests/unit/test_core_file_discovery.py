"""
Unit tests for the core file discovery module.
"""
import os
import pytest
from pathlib import Path
import tempfile
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
    
    def test_find_files_basic(self):
        """Test basic file discovery."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create file structure
            (Path(temp_dir) / "subdir1").mkdir()
            (Path(temp_dir) / "subdir2").mkdir()
            
            # Create files
            (Path(temp_dir) / "subdir1" / "file1.txt").touch()
            (Path(temp_dir) / "subdir1" / "file2.pdf").touch()
            (Path(temp_dir) / "subdir2" / "file3.txt").touch()
            
            # Find files
            files = self.file_discovery.find_files(temp_dir)
            
            assert len(files) == 3
            filenames = [os.path.basename(f) for f in files]
            assert "file1.txt" in filenames
            assert "file2.pdf" in filenames
            assert "file3.txt" in filenames
    
    def test_find_files_max_depth(self):
        """Test file discovery with depth limit."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create nested structure
            deep_path = Path(temp_dir) / "level1" / "level2" / "level3"
            deep_path.mkdir(parents=True)
            
            # Create files at different levels
            (Path(temp_dir) / "level1" / "file1.txt").touch()
            (Path(temp_dir) / "level1" / "level2" / "file2.txt").touch()
            (deep_path / "file3.txt").touch()
            
            # Test different depths
            files_depth1 = self.file_discovery.find_files(temp_dir, max_depth=1)
            assert len(files_depth1) == 1  # Only file1.txt
            
            files_depth2 = self.file_discovery.find_files(temp_dir, max_depth=2)
            assert len(files_depth2) == 2  # file1.txt and file2.txt
            
            files_unlimited = self.file_discovery.find_files(temp_dir, max_depth=0)
            assert len(files_unlimited) == 3  # All files
    
    def test_find_files_type_filter(self):
        """Test file discovery with type filtering."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subdir = Path(temp_dir) / "subdir"
            subdir.mkdir()
            
            # Create various file types
            (subdir / "doc.txt").touch()
            (subdir / "doc.pdf").touch()
            (subdir / "image.jpg").touch()
            (subdir / "data.json").touch()
            
            # Filter for specific types
            txt_files = self.file_discovery.find_files(
                temp_dir, file_type_filter=[".txt"]
            )
            assert len(txt_files) == 1
            assert txt_files[0].endswith("doc.txt")
            
            # Multiple types
            doc_files = self.file_discovery.find_files(
                temp_dir, file_type_filter=[".txt", ".pdf"]
            )
            assert len(doc_files) == 2
    
    def test_find_files_hidden_files(self):
        """Test handling of hidden files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subdir = Path(temp_dir) / "subdir"
            subdir.mkdir()
            hidden_dir = Path(temp_dir) / ".hidden"
            hidden_dir.mkdir()
            
            # Create files
            (subdir / "visible.txt").touch()
            (subdir / ".hidden.txt").touch()
            (hidden_dir / "file.txt").touch()
            
            # Without include_hidden
            files = self.file_discovery.find_files(temp_dir, include_hidden=False)
            assert len(files) == 1
            assert files[0].endswith("visible.txt")
            
            # With include_hidden
            files = self.file_discovery.find_files(temp_dir, include_hidden=True)
            assert len(files) == 3
    
    def test_find_files_abort_signal(self):
        """Test abort signal handling."""
        abort_signal = threading.Event()
        file_discovery = FileDiscovery(abort_signal)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create many subdirectories
            for i in range(10):
                subdir = Path(temp_dir) / f"subdir{i}"
                subdir.mkdir()
                (subdir / "file.txt").touch()
            
            # Set abort signal
            abort_signal.set()
            
            # Should return fewer files due to abort
            files = file_discovery.find_files(temp_dir)
            assert len(files) < 10
    
    def test_check_url_file(self):
        """Test checking Windows .url files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create .url file
            url_file = Path(temp_dir) / "youtube.url"
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
    
    def test_check_webloc_file(self):
        """Test checking macOS .webloc files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create .webloc file
            webloc_file = Path(temp_dir) / "github.webloc"
            
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
    
    def test_check_weblink_invalid_format(self):
        """Test handling of invalid weblink files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Invalid .url file
            invalid_url = Path(temp_dir) / "invalid.url"
            invalid_url.write_text("Not a valid URL file")
            
            assert self.file_discovery.check_weblink_domain(
                str(invalid_url), ["any.com"]
            ) is False
            
            # Invalid .webloc file
            invalid_webloc = Path(temp_dir) / "invalid.webloc"
            invalid_webloc.write_text("Not valid XML")
            
            assert self.file_discovery.check_weblink_domain(
                str(invalid_webloc), ["any.com"]
            ) is False


class TestFileFilter:
    """Test FileFilter class."""
    
    def test_extension_filter(self):
        """Test extension filtering."""
        filter = FileFilter()
        filter.add_extension_filter([".txt", ".pdf"])
        
        assert filter.apply("/path/to/file.txt") is True
        assert filter.apply("/path/to/file.pdf") is True
        assert filter.apply("/path/to/file.jpg") is False
    
    def test_size_filter(self):
        """Test size filtering."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files of different sizes
            small_file = Path(temp_dir) / "small.txt"
            small_file.write_text("small")  # 5 bytes
            
            large_file = Path(temp_dir) / "large.txt"
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
    
    def test_combined_filters(self):
        """Test combining multiple filters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            test_file = Path(temp_dir) / "test_document.txt"
            test_file.write_text("x" * 500)  # 500 bytes
            
            # Create filter with multiple conditions
            filter = FileFilter()
            filter.add_extension_filter([".txt", ".pdf"])
            filter.add_size_filter(min_size=100, max_size=1000)
            filter.add_name_pattern_filter("test_*")
            
            # Should pass all filters
            assert filter.apply(str(test_file)) is True
            
            # Create file that fails one filter
            other_file = Path(temp_dir) / "other.txt"
            other_file.write_text("x" * 500)
            
            # Fails pattern filter
            assert filter.apply(str(other_file)) is False


class TestCompatibility:
    """Test compatibility with original functions."""
    
    def test_find_files_compatibility(self):
        """Test that new implementation matches old behavior."""
        from folder_extractor.main import finde_dateien as old_func
        file_discovery = FileDiscovery()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test structure
            (Path(temp_dir) / "subdir").mkdir()
            (Path(temp_dir) / ".hidden").mkdir()
            
            (Path(temp_dir) / "subdir" / "file.txt").touch()
            (Path(temp_dir) / "subdir" / ".hidden.txt").touch()
            (Path(temp_dir) / ".hidden" / "secret.txt").touch()
            
            # Compare results
            old_result = set(old_func(temp_dir, max_tiefe=0, include_hidden=False))
            new_result = set(file_discovery.find_files(temp_dir, max_depth=0, 
                                                      include_hidden=False))
            
            assert old_result == new_result
    
    def test_weblink_domain_compatibility(self):
        """Test that new implementation matches old behavior."""
        from folder_extractor.main import pruefe_weblink_domain as old_func
        file_discovery = FileDiscovery()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test .url file
            url_file = Path(temp_dir) / "test.url"
            url_file.write_text(
                "[InternetShortcut]\n"
                "URL=https://www.youtube.com/watch?v=123\n"
            )
            
            domains = ["youtube.com"]
            
            old_result = old_func(str(url_file), domains)
            new_result = file_discovery.check_weblink_domain(str(url_file), domains)
            
            assert old_result == new_result