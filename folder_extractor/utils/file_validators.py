"""
File validation utilities.

Provides functions to validate files, paths, and check
for temporary or system files.
"""
import os
from pathlib import Path
from typing import Optional

from folder_extractor.config.constants import (
    TEMP_EXTENSIONS,
    SYSTEM_FILES,
    EDITOR_TEMP_FILES,
    GIT_TEMP_FILES,
    GIT_DIRECTORY,
    HIDDEN_FILE_PREFIX
)


def is_temp_or_system_file(filename: str) -> bool:
    """
    Check if a file is a temporary or system file.
    
    Args:
        filename: Name of the file to check
    
    Returns:
        True if the file is temporary or system file
    
    Examples:
        >>> is_temp_or_system_file(".DS_Store")
        True
        >>> is_temp_or_system_file("document.pdf")
        False
    """
    basename = os.path.basename(filename)
    name_lower = basename.lower()
    
    # Check exact matches first
    if basename in SYSTEM_FILES or basename in GIT_TEMP_FILES:
        return True
    
    # Check lowercase matches for case-insensitive systems
    if name_lower in {f.lower() for f in SYSTEM_FILES}:
        return True
    
    # Check extensions
    _, ext = os.path.splitext(name_lower)
    if ext in TEMP_EXTENSIONS:
        return True
    
    # Check editor temp files patterns
    for pattern in EDITOR_TEMP_FILES:
        if pattern.endswith('*'):
            if basename.startswith(pattern[:-1]):
                return True
        elif pattern.startswith('*'):
            if basename.endswith(pattern[1:]):
                return True
        elif basename == pattern:
            return True
    
    # Check for various temp file patterns
    if basename.startswith('~$') or basename.startswith('.~'):
        return True
    
    if basename.startswith('.#') or (basename.startswith('#') and basename.endswith('#')):
        return True
    
    if basename.endswith('~'):
        return True
    
    # Check for hidden macOS resource forks
    if basename.startswith('._'):
        return True
    
    return False


def is_git_path(path: str) -> bool:
    """
    Check if a path is within a git directory.
    
    Args:
        path: Path to check
    
    Returns:
        True if the path is within .git directory
    
    Examples:
        >>> is_git_path("/project/.git/config")
        True
        >>> is_git_path("/project/src/main.py")
        False
    """
    path_parts = Path(path).parts
    return GIT_DIRECTORY in path_parts


def is_hidden_file(path: str) -> bool:
    """
    Check if a file or directory is hidden.
    
    Args:
        path: Path to check
    
    Returns:
        True if the file/directory is hidden
    """
    basename = os.path.basename(path)
    # Exclude current (.) and parent (..) directories
    return basename.startswith(HIDDEN_FILE_PREFIX) and basename not in ['.', '..']


def should_include_file(filepath: str, include_hidden: bool = False) -> bool:
    """
    Determine if a file should be included based on various criteria.
    
    Args:
        filepath: Path to the file
        include_hidden: Whether to include hidden files
    
    Returns:
        True if the file should be included
    """
    # Skip temp and system files
    if is_temp_or_system_file(filepath):
        return False
    
    # Skip git files
    if is_git_path(filepath):
        return False
    
    # Skip hidden files if not included
    if not include_hidden and is_hidden_file(filepath):
        return False
    
    return True


def validate_file_extension(filepath: str, allowed_extensions: Optional[list] = None) -> bool:
    """
    Check if a file has an allowed extension.
    
    Args:
        filepath: Path to the file
        allowed_extensions: List of allowed extensions (with dots)
    
    Returns:
        True if the file extension is allowed or no filter is set
    """
    if not allowed_extensions:
        return True
    
    _, ext = os.path.splitext(filepath.lower())
    return ext in allowed_extensions