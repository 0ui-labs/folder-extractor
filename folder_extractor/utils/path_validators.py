"""
Path validation and security utilities.

Ensures operations only occur in safe directories.
"""
import os
from pathlib import Path
from typing import Tuple

from folder_extractor.config.constants import SAFE_FOLDER_NAMES


def is_safe_path(path: str) -> bool:
    """
    Check if a path is in a safe location.
    
    Only allows operations in Desktop, Downloads, or Documents folders.
    
    Args:
        path: Path to validate
    
    Returns:
        True if the path is in a safe location
    
    Examples:
        >>> is_safe_path("/Users/user/Desktop/test")
        True
        >>> is_safe_path("/etc/passwd")
        False
    """
    try:
        # Resolve to absolute path
        abs_path = os.path.abspath(path)
        
        # Get user home directory
        home = str(Path.home())
        
        # Path must be within home directory
        if not abs_path.startswith(home):
            return False
        
        # Get relative path from home
        rel_path = os.path.relpath(abs_path, home)
        path_parts = rel_path.split(os.sep)
        
        # Check if first part is a safe folder
        if path_parts and path_parts[0] in SAFE_FOLDER_NAMES:
            return True
        
        return False
    
    except Exception:
        # Any error in path resolution means it's not safe
        return False


def get_safe_path_info(path: str) -> Tuple[bool, str]:
    """
    Get detailed information about path safety.
    
    Args:
        path: Path to check
    
    Returns:
        Tuple of (is_safe, reason)
    """
    try:
        abs_path = os.path.abspath(path)
        home = str(Path.home())
        
        if not abs_path.startswith(home):
            return False, "Path is outside home directory"
        
        rel_path = os.path.relpath(abs_path, home)
        path_parts = rel_path.split(os.sep)
        
        if not path_parts:
            return False, "Invalid path structure"
        
        if path_parts[0] in SAFE_FOLDER_NAMES:
            return True, f"Path is in safe folder: {path_parts[0]}"
        
        return False, f"Path is not in allowed folders: {', '.join(SAFE_FOLDER_NAMES)}"
    
    except Exception as e:
        return False, f"Error validating path: {str(e)}"


def normalize_path(path: str) -> str:
    """
    Normalize a path for consistent handling.
    
    Args:
        path: Path to normalize
    
    Returns:
        Normalized absolute path
    """
    return os.path.abspath(os.path.expanduser(path))


def is_subdirectory(parent: str, child: str) -> bool:
    """
    Check if one path is a subdirectory of another.
    
    Args:
        parent: Parent directory path
        child: Potential child directory path
    
    Returns:
        True if child is a subdirectory of parent
    """
    parent = normalize_path(parent)
    child = normalize_path(child)
    
    try:
        # Get relative path - will raise if not related
        rel = os.path.relpath(child, parent)
        # If it starts with .., it's not a subdirectory
        return not rel.startswith('..')
    except ValueError:
        # Paths are on different drives (Windows)
        return False