"""
File validation utilities.

Provides functions to validate files, paths, and check
for temporary or system files.
"""

from pathlib import Path
from typing import Optional, Union

from folder_extractor.config.constants import (
    EDITOR_TEMP_FILES,
    GIT_DIRECTORY,
    GIT_TEMP_FILES,
    HIDDEN_FILE_PREFIX,
    SYSTEM_FILES,
    TEMP_EXTENSIONS,
)


def get_temp_files_list() -> list:
    """
    Get list of temporary and system file names to ignore.

    Returns:
        List of temporary/system file names

    Examples:
        >>> temp_files = get_temp_files_list()
        >>> ".DS_Store" in temp_files
        True
    """
    temp_list = list(SYSTEM_FILES) + list(GIT_TEMP_FILES)
    # Add patterns from editor temp files that are exact names (not wildcards)
    for pattern in EDITOR_TEMP_FILES:
        if (
            not pattern.startswith("*")
            and not pattern.startswith(".#")
            and not pattern.startswith("#")
        ):
            temp_list.append(pattern)
    return temp_list


def is_temp_or_system_file(filename: Union[str, Path]) -> bool:
    """
    Check if a file is a temporary or system file.

    Args:
        filename: Name or Path of the file to check

    Returns:
        True if the file is temporary or system file

    Examples:
        >>> is_temp_or_system_file(".DS_Store")
        True
        >>> is_temp_or_system_file("document.pdf")
        False
        >>> is_temp_or_system_file(Path("document.pdf"))
        False
    """
    path = Path(filename)
    basename = path.name
    name_lower = basename.lower()

    # Check exact matches first
    if basename in SYSTEM_FILES or basename in GIT_TEMP_FILES:
        return True

    # Check lowercase matches for case-insensitive systems
    if name_lower in {f.lower() for f in SYSTEM_FILES}:
        return True

    # Check extensions
    ext = path.suffix.lower()
    if ext in TEMP_EXTENSIONS:
        return True

    # Check editor temp files patterns
    for pattern in EDITOR_TEMP_FILES:
        if pattern.endswith("*"):
            if basename.startswith(pattern[:-1]):
                return True
        elif pattern.startswith("*"):  # pragma: no cover
            # Currently no patterns in EDITOR_TEMP_FILES start with *
            if basename.endswith(pattern[1:]):
                return True
        elif basename == pattern:
            return True

    # Check for various temp file patterns
    if basename.startswith(("~$", ".~")):
        return True

    if basename.startswith(".#") or (
        basename.startswith("#") and basename.endswith("#")
    ):
        return True

    if basename.endswith("~"):
        return True

    # Check for hidden macOS resource forks
    return bool(basename.startswith("._"))


def is_git_path(path: Union[str, Path]) -> bool:
    """
    Check if a path is within a git directory.

    Args:
        path: str or Path to check

    Returns:
        True if the path is within .git directory

    Examples:
        >>> is_git_path("/project/.git/config")
        True
        >>> is_git_path("/project/src/main.py")
        False
        >>> is_git_path(Path("/project/.git/config"))
        True
    """
    path_parts = Path(path).parts
    return GIT_DIRECTORY in path_parts


def is_hidden_file(path: Union[str, Path]) -> bool:
    """
    Check if a file or directory is hidden.

    Args:
        path: str or Path to check

    Returns:
        True if the file/directory is hidden

    Examples:
        >>> is_hidden_file(".hidden")
        True
        >>> is_hidden_file("visible.txt")
        False
        >>> is_hidden_file(Path(".hidden"))
        True
    """
    path_obj = Path(path)
    basename = path_obj.name
    # Exclude current (.) and parent (..) directories
    return basename.startswith(HIDDEN_FILE_PREFIX) and basename not in [".", ".."]


def should_include_file(
    filepath: Union[str, Path], include_hidden: bool = False
) -> bool:
    """
    Determine if a file should be included based on various criteria.

    Args:
        filepath: str or Path to the file
        include_hidden: Whether to include hidden files

    Returns:
        True if the file should be included

    Examples:
        >>> should_include_file("document.pdf")
        True
        >>> should_include_file(".DS_Store")
        False
        >>> should_include_file(Path("document.pdf"))
        True
        >>> should_include_file(".hidden", include_hidden=True)
        True
    """
    # Skip temp and system files
    if is_temp_or_system_file(filepath):
        return False

    # Skip git files
    if is_git_path(filepath):
        return False

    # Skip hidden files if not included
    # Equivalent to: include_hidden OR file is not hidden
    return include_hidden or not is_hidden_file(filepath)


def validate_file_extension(
    filepath: Union[str, Path], allowed_extensions: Optional[list] = None
) -> bool:
    """
    Check if a file has an allowed extension.

    Args:
        filepath: str or Path to the file
        allowed_extensions: List of allowed extensions (with dots)

    Returns:
        True if the file extension is allowed or no filter is set

    Examples:
        >>> validate_file_extension("document.pdf", [".pdf", ".txt"])
        True
        >>> validate_file_extension("image.jpg", [".pdf", ".txt"])
        False
        >>> validate_file_extension(Path("document.pdf"), [".pdf"])
        True
        >>> validate_file_extension("any_file.xyz")
        True
    """
    if not allowed_extensions:
        return True

    path = Path(filepath)
    ext = path.suffix.lower()
    return ext in allowed_extensions
