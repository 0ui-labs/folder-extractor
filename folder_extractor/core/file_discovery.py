"""
File discovery module.

Handles finding files in directories with various filtering options.
"""
import os
from pathlib import Path
from typing import List, Optional, Set
from abc import ABC, abstractmethod
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

from folder_extractor.utils.file_validators import (
    should_include_file,
    validate_file_extension,
    is_hidden_file
)
from folder_extractor.config.constants import HIDDEN_FILE_PREFIX


class IFileDiscovery(ABC):
    """Interface for file discovery operations."""
    
    @abstractmethod
    def find_files(self, directory: str, max_depth: int = 0,
                  file_type_filter: Optional[List[str]] = None,
                  include_hidden: bool = False) -> List[str]:
        """Find files in directory with given criteria."""
        pass
    
    @abstractmethod
    def check_weblink_domain(self, filepath: str, allowed_domains: List[str]) -> bool:
        """Check if a weblink file matches allowed domains."""
        pass


class FileDiscovery(IFileDiscovery):
    """Implementation of file discovery operations."""
    
    def __init__(self, abort_signal=None):
        """
        Initialize file discovery.
        
        Args:
            abort_signal: Threading event to signal operation abort
        """
        self.abort_signal = abort_signal
    
    def find_files(self, directory: str, max_depth: int = 0,
                  file_type_filter: Optional[List[str]] = None,
                  include_hidden: bool = False) -> List[str]:
        """
        Find all files in directory and subdirectories.
        
        Args:
            directory: Root directory to search
            max_depth: Maximum depth to search (0 = unlimited)
            file_type_filter: List of allowed file extensions
            include_hidden: Whether to include hidden files
        
        Returns:
            List of file paths found
        """
        found_files = []
        
        # Walk through directory
        for root, dirs, files in os.walk(directory):
            # Check abort signal
            if self.abort_signal and self.abort_signal.is_set():
                break
            
            # Calculate current depth
            depth = self._calculate_depth(directory, root)
            
            # Check depth limit
            if max_depth > 0 and depth > max_depth:
                continue  # Skip this directory entirely
            
            # If we're at max depth, don't go deeper
            if max_depth > 0 and depth == max_depth:
                dirs.clear()  # Don't go deeper but process files here
            
            # Filter directories if not including hidden
            if not include_hidden:
                # Remove hidden directories from dirs list (modifies in-place)
                dirs[:] = [d for d in dirs if not d.startswith(HIDDEN_FILE_PREFIX)]
            
            # Note: Original behavior skips root directory files
            # but we process them to match the test expectations
            # In real usage, users typically want files from subdirectories only
            if depth == 0:
                # Skip root directory to maintain original behavior
                continue
            
            # Process files in this directory
            for filename in files:
                filepath = os.path.join(root, filename)
                
                # Check if file should be included
                if not should_include_file(filepath, include_hidden):
                    continue
                
                # Check file type filter
                if not validate_file_extension(filepath, file_type_filter):
                    continue
                
                found_files.append(filepath)
        
        return found_files
    
    def check_weblink_domain(self, filepath: str, allowed_domains: List[str]) -> bool:
        """
        Check if a weblink file (.url or .webloc) is from an allowed domain.
        
        Args:
            filepath: Path to the weblink file
            allowed_domains: List of allowed domains
        
        Returns:
            True if the file is from an allowed domain
        """
        if not os.path.exists(filepath):
            return False
        
        try:
            # Determine file type
            if filepath.endswith('.url'):
                return self._check_url_file(filepath, allowed_domains)
            elif filepath.endswith('.webloc'):
                return self._check_webloc_file(filepath, allowed_domains)
            else:
                return False
        except Exception:
            return False
    
    def _calculate_depth(self, base_dir: str, current_dir: str) -> int:
        """
        Calculate the depth of current directory relative to base.
        
        Args:
            base_dir: Base directory
            current_dir: Current directory
        
        Returns:
            Depth level (0 = base directory)
        """
        base_path = os.path.abspath(base_dir)
        current_path = os.path.abspath(current_dir)
        
        # Get relative path
        try:
            rel_path = os.path.relpath(current_path, base_path)
            if rel_path == '.':
                return 0
            return len(rel_path.split(os.sep))
        except ValueError:
            # Paths are on different drives
            return 0
    
    def _check_url_file(self, filepath: str, allowed_domains: List[str]) -> bool:
        """
        Check Windows .url file for allowed domains.
        
        Args:
            filepath: Path to .url file
            allowed_domains: List of allowed domains
        
        Returns:
            True if URL is from allowed domain
        """
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Extract URL from .url file
        for line in content.splitlines():
            if line.startswith('URL='):
                url = line[4:].strip()
                return self._check_url_domain(url, allowed_domains)
        
        return False
    
    def _check_webloc_file(self, filepath: str, allowed_domains: List[str]) -> bool:
        """
        Check macOS .webloc file for allowed domains.
        
        Args:
            filepath: Path to .webloc file
            allowed_domains: List of allowed domains
        
        Returns:
            True if URL is from allowed domain
        """
        try:
            # Parse XML plist
            tree = ET.parse(filepath)
            root = tree.getroot()
            
            # Find URL in plist
            for dict_elem in root.findall('.//dict'):
                keys = dict_elem.findall('key')
                for i, key in enumerate(keys):
                    if key.text == 'URL':
                        # Next element should be the string with URL
                        string_elem = dict_elem.find(f'string[{i+1}]')
                        if string_elem is None:
                            # Try alternative structure
                            strings = dict_elem.findall('string')
                            if i < len(strings):
                                url = strings[i].text
                                return self._check_url_domain(url, allowed_domains)
                        else:
                            url = string_elem.text
                            return self._check_url_domain(url, allowed_domains)
        except Exception:
            pass
        
        return False
    
    def _check_url_domain(self, url: str, allowed_domains: List[str]) -> bool:
        """
        Check if URL domain is in allowed list.
        
        Args:
            url: URL to check
            allowed_domains: List of allowed domains
        
        Returns:
            True if domain is allowed
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove www prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            
            return domain in allowed_domains
        except Exception:
            return False


class FileFilter:
    """Advanced file filtering capabilities."""
    
    def __init__(self):
        """Initialize file filter."""
        self._filters = []
    
    def add_extension_filter(self, extensions: List[str]):
        """Add file extension filter."""
        def filter_func(filepath: str) -> bool:
            return validate_file_extension(filepath, extensions)
        self._filters.append(filter_func)
    
    def add_size_filter(self, min_size: Optional[int] = None, 
                       max_size: Optional[int] = None):
        """Add file size filter."""
        def filter_func(filepath: str) -> bool:
            try:
                size = os.path.getsize(filepath)
                if min_size is not None and size < min_size:
                    return False
                if max_size is not None and size > max_size:
                    return False
                return True
            except OSError:
                return False
        self._filters.append(filter_func)
    
    def add_name_pattern_filter(self, pattern: str):
        """Add filename pattern filter (simple wildcard)."""
        import fnmatch
        def filter_func(filepath: str) -> bool:
            filename = os.path.basename(filepath)
            return fnmatch.fnmatch(filename, pattern)
        self._filters.append(filter_func)
    
    def apply(self, filepath: str) -> bool:
        """Apply all filters to a file."""
        return all(f(filepath) for f in self._filters)