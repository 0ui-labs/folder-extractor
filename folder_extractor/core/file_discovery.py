"""
File discovery module.

Handles finding files in directories with various filtering options.
"""

import os
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Union
from urllib.parse import urlparse

from folder_extractor.config.constants import HIDDEN_FILE_PREFIX
from folder_extractor.utils.file_validators import (
    should_include_file,
    validate_file_extension,
)


class IFileDiscovery(ABC):
    """Interface for file discovery operations."""

    @abstractmethod
    def find_files(
        self,
        directory: Union[str, Path],
        max_depth: int = 0,
        file_type_filter: Optional[List[str]] = None,
        include_hidden: bool = False,
    ) -> List[str]:
        """Find files in directory with given criteria."""
        pass

    @abstractmethod
    def check_weblink_domain(
        self, filepath: Union[str, Path], allowed_domains: List[str]
    ) -> bool:
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

    def find_files(
        self,
        directory: Union[str, Path],
        max_depth: int = 0,
        file_type_filter: Optional[List[str]] = None,
        include_hidden: bool = False,
    ) -> List[str]:
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
        base_path = Path(directory)
        found_files = []

        # Pre-calculate base path parts count for fast depth calculation
        base_parts_count = len(base_path.parts)

        # Walk through directory tree using os.walk()
        try:
            for root, dirs, files in os.walk(str(base_path), topdown=True):
                # Check abort signal
                if self.abort_signal and self.abort_signal.is_set():
                    return found_files

                # Convert root to Path object
                current_path = Path(root)

                # Calculate current depth efficiently (avoid resolve() overhead)
                current_depth = len(current_path.parts) - base_parts_count

                # Handle max_depth: prevent further descent if limit reached
                if max_depth > 0 and current_depth >= max_depth:
                    dirs[:] = []  # Clear in-place to stop os.walk from descending

                # Prune hidden directories if not included
                if not include_hidden:
                    dirs[:] = [d for d in dirs if not d.startswith(HIDDEN_FILE_PREFIX)]

                # Process files in current directory
                for filename in files:
                    # Construct full path
                    filepath = str(current_path / filename)

                    # Check if file should be included
                    if not should_include_file(filepath, include_hidden):
                        continue

                    # Check file type filter
                    if not validate_file_extension(filepath, file_type_filter):
                        continue

                    found_files.append(filepath)
        except OSError:
            # Skip directories we can't read (includes PermissionError)
            pass

        return found_files

    def check_weblink_domain(
        self, filepath: Union[str, Path], allowed_domains: List[str]
    ) -> bool:
        """
        Check if a weblink file (.url or .webloc) is from an allowed domain.

        Args:
            filepath: Path to the weblink file
            allowed_domains: List of allowed domains

        Returns:
            True if the file is from an allowed domain
        """
        file_path = Path(filepath)
        if not file_path.exists():
            return False

        try:
            # Determine file type using Path.suffix
            if file_path.suffix == ".url":
                return self._check_url_file(str(file_path), allowed_domains)
            elif file_path.suffix == ".webloc":
                return self._check_webloc_file(str(file_path), allowed_domains)
            else:
                return False
        except Exception:  # pragma: no cover
            # Inner methods have their own exception handling
            return False

    def _calculate_depth(
        self, base_dir: Union[str, Path], current_dir: Union[str, Path]
    ) -> int:
        """
        Calculate the depth of current directory relative to base.

        Args:
            base_dir: Base directory
            current_dir: Current directory

        Returns:
            Depth level (0 = base directory)
        """
        base_path = Path(base_dir).resolve()
        current_path = Path(current_dir).resolve()

        # Get relative path
        try:
            rel_path = current_path.relative_to(base_path)
            if rel_path == Path("."):
                return 0
            return len(rel_path.parts)
        except ValueError:
            # Paths are on different drives or not relative
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
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Extract URL from .url file
        for line in content.splitlines():
            if line.startswith("URL="):
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
            for dict_elem in root.findall(".//dict"):
                keys = dict_elem.findall("key")
                for i, key in enumerate(keys):
                    if key.text == "URL":
                        # Next element should be the string with URL
                        string_elem = dict_elem.find(f"string[{i + 1}]")
                        if string_elem is None:  # pragma: no cover
                            # Alternative structure for malformed plists
                            # Note: This path is logically unreachable because:
                            # - If string[i+1] is None, there are < (i+1) strings
                            # - Thus i < len(strings) will always be False
                            strings = dict_elem.findall("string")
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
            if domain.startswith("www."):
                domain = domain[4:]

            return domain in allowed_domains
        except Exception:
            return False

    def extract_weblink_domain(self, filepath: Union[str, Path]) -> Optional[str]:
        """
        Extract the domain from a weblink file (.url or .webloc).

        Args:
            filepath: Path to the weblink file

        Returns:
            Domain string (e.g., 'youtube.com') or None if extraction fails
        """
        file_path = Path(filepath)
        if not file_path.exists():
            return None

        try:
            if file_path.suffix == ".url":
                return self._extract_domain_from_url_file(str(file_path))
            elif file_path.suffix == ".webloc":
                return self._extract_domain_from_webloc_file(str(file_path))
            else:
                return None
        except Exception:
            return None

    def _extract_domain_from_url_file(self, filepath: str) -> Optional[str]:
        """Extract domain from Windows .url file."""
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            content = f.read()

        for line in content.splitlines():
            if line.startswith("URL="):
                url = line[4:].strip()
                return self._extract_domain_from_url(url)
        return None

    def _extract_domain_from_webloc_file(self, filepath: str) -> Optional[str]:
        """Extract domain from macOS .webloc file."""
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()

            for dict_elem in root.findall(".//dict"):
                keys = dict_elem.findall("key")
                for i, key in enumerate(keys):
                    if key.text == "URL":
                        string_elem = dict_elem.find(f"string[{i + 1}]")
                        if string_elem is None:
                            strings = dict_elem.findall("string")
                            if i < len(strings):
                                return self._extract_domain_from_url(strings[i].text)
                        else:
                            return self._extract_domain_from_url(string_elem.text)
        except Exception:
            pass
        return None

    def _extract_domain_from_url(self, url: str) -> Optional[str]:
        """Extract domain from URL string."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Remove www prefix
            if domain.startswith("www."):
                domain = domain[4:]

            return domain if domain else None
        except Exception:
            return None


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

    def add_size_filter(
        self, min_size: Optional[int] = None, max_size: Optional[int] = None
    ):
        """Add file size filter."""

        def filter_func(filepath: str) -> bool:
            try:
                size = Path(filepath).stat().st_size
                if min_size is not None and size < min_size:
                    return False
                return not (max_size is not None and size > max_size)
            except OSError:
                return False

        self._filters.append(filter_func)

    def add_name_pattern_filter(self, pattern: str):
        """Add filename pattern filter (simple wildcard)."""
        import fnmatch

        def filter_func(filepath: str) -> bool:
            filename = Path(filepath).name
            return fnmatch.fnmatch(filename, pattern)

        self._filters.append(filter_func)

    def apply(self, filepath: str) -> bool:
        """Apply all filters to a file."""
        return all(f(filepath) for f in self._filters)
