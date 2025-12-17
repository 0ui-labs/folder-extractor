"""
Compatibility module for legacy function names.

This module provides the old German function names that wrap the new
modular implementation. This ensures backwards compatibility with
existing tests and code that imports from folder_extractor.main.
"""
from typing import List, Optional, Dict, Tuple, Any

from folder_extractor.utils.path_validators import is_safe_path
from folder_extractor.core.file_operations import FileOperations, FileMover
from folder_extractor.core.file_discovery import FileDiscovery


# Module-level instances for compatibility functions
_file_ops = FileOperations()
_file_discovery = FileDiscovery()
_file_mover = FileMover(_file_ops)


def generiere_eindeutigen_namen(directory: str, filename: str) -> str:
    """
    Generate a unique filename in the given directory.

    Legacy wrapper for FileOperations.generate_unique_name().

    Args:
        directory: Directory to check for existing files
        filename: Original filename

    Returns:
        Unique filename that doesn't exist in the directory
    """
    return _file_ops.generate_unique_name(directory, filename)


def ist_sicherer_pfad(path: str) -> bool:
    """
    Check if a path is safe for file operations.

    Legacy wrapper for is_safe_path().

    Args:
        path: Path to check

    Returns:
        True if path is in a safe location (Desktop, Downloads, Documents)
    """
    return is_safe_path(path)


def entferne_leere_ordner(path: str, include_hidden: bool = False) -> int:
    """
    Remove empty directories recursively.

    Legacy wrapper for FileOperations.remove_empty_directories().

    Args:
        path: Root path to start from
        include_hidden: Whether to consider hidden files

    Returns:
        Number of directories removed
    """
    return _file_ops.remove_empty_directories(path, include_hidden)


def pruefe_weblink_domain(filepath: str, allowed_domains: List[str]) -> bool:
    """
    Check if a weblink file (.url or .webloc) is from an allowed domain.

    Legacy wrapper for FileDiscovery.check_weblink_domain().

    Args:
        filepath: Path to the weblink file
        allowed_domains: List of allowed domains

    Returns:
        True if the file is from an allowed domain
    """
    return _file_discovery.check_weblink_domain(filepath, allowed_domains)


def finde_dateien(directory: str, max_tiefe: int = 0,
                  dateityp_filter: Optional[List[str]] = None,
                  include_hidden: bool = False) -> List[str]:
    """
    Find all files in directory and subdirectories.

    Legacy wrapper for FileDiscovery.find_files().

    Args:
        directory: Root directory to search
        max_tiefe: Maximum depth to search (0 = unlimited)
        dateityp_filter: List of allowed file extensions
        include_hidden: Whether to include hidden files

    Returns:
        List of file paths found
    """
    return _file_discovery.find_files(
        directory,
        max_depth=max_tiefe,
        file_type_filter=dateityp_filter,
        include_hidden=include_hidden
    )


def verschiebe_dateien(files: List[str], destination: str,
                       dry_run: bool = False,
                       progress_callback=None) -> Tuple[int, int, int, List[Dict]]:
    """
    Move multiple files to destination.

    Legacy wrapper for FileMover.move_files().

    Args:
        files: List of file paths to move
        destination: Destination directory
        dry_run: If True, simulate the operation
        progress_callback: Optional callback for progress updates

    Returns:
        Tuple of (moved_count, error_count, duplicate_count, history)
    """
    return _file_mover.move_files(files, destination, dry_run, progress_callback)


# Legacy parsers compatibility - delegate to new parsers
def parse_dateitypen(type_string: Optional[str]) -> Optional[List[str]]:
    """
    Parse file type filter string.

    Legacy wrapper - delegates to utils.parsers.parse_file_types().

    Args:
        type_string: Comma-separated file extensions (e.g., "pdf,jpg,png")

    Returns:
        List of file extensions with dots (e.g., [".pdf", ".jpg", ".png"])
        or None if input is empty
    """
    from folder_extractor.utils.parsers import parse_file_types
    return parse_file_types(type_string)


def parse_domains(domain_string: Optional[str]) -> Optional[List[str]]:
    """
    Parse domain filter string.

    Legacy wrapper - delegates to utils.parsers.parse_domains().

    Args:
        domain_string: Comma-separated domains (e.g., "youtube.com,github.com")

    Returns:
        List of domain strings without www prefix, or None if input is empty
    """
    from folder_extractor.utils.parsers import parse_domains as new_parse_domains
    return new_parse_domains(domain_string)


# Main entry point
def main():
    """Main entry point for Folder Extractor."""
    from folder_extractor.cli.app import main as cli_main
    return cli_main()


if __name__ == "__main__":
    import sys
    sys.exit(main())
