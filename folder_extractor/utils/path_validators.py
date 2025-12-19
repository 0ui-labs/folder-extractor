"""
Path validation and security utilities.

Ensures operations only occur in safe directories.
"""

from pathlib import Path
from typing import Tuple, Union

from folder_extractor.config.constants import SAFE_FOLDER_NAMES


def is_safe_path(path: Union[str, Path]) -> bool:
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
        path = Path(path).resolve()
        home = Path.home()
        try:
            rel_path = path.relative_to(home)
            return bool(rel_path.parts and rel_path.parts[0] in SAFE_FOLDER_NAMES)
        except ValueError:
            return False
    except Exception:
        return False


def get_safe_path_info(path: Union[str, Path]) -> Tuple[bool, str]:
    """
    Get detailed information about path safety.

    Args:
        path: Path to check

    Returns:
        Tuple of (is_safe, reason)
    """
    try:
        path = Path(path).resolve()
        home = Path.home()

        try:
            rel_path = path.relative_to(home)
        except ValueError:
            return False, "Path is outside home directory"

        if not rel_path.parts:
            return False, "Invalid path structure"

        if rel_path.parts[0] in SAFE_FOLDER_NAMES:
            return True, f"Path is in safe folder: {rel_path.parts[0]}"

        return False, f"Path is not in allowed folders: {', '.join(SAFE_FOLDER_NAMES)}"

    except Exception as e:
        return False, f"Error validating path: {str(e)}"


def normalize_path(path: Union[str, Path]) -> str:
    """
    Normalize a path for consistent handling.

    Args:
        path: Path to normalize

    Returns:
        Normalized absolute path
    """
    return str(Path(path).expanduser().resolve())


def is_subdirectory(parent: Union[str, Path], child: Union[str, Path]) -> bool:
    """
    Check if one path is a subdirectory of another.

    Args:
        parent: Parent directory path
        child: Potential child directory path

    Returns:
        True if child is a subdirectory of parent
    """
    parent_path = Path(normalize_path(parent))
    child_path = Path(normalize_path(child))

    try:
        child_path.relative_to(parent_path)
        return True
    except ValueError:
        return False
