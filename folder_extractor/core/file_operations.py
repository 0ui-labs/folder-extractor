"""
File operations module.

Handles all file system operations including moving files,
generating unique names, and managing directories.
"""

import base64
import hashlib
import json
import os
import platform
import shutil
import stat
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from folder_extractor.config.constants import (
    FILE_TYPE_FOLDERS,
    HISTORY_FILE_NAME,
    NO_EXTENSION_FOLDER,
)


def get_config_directory() -> Path:
    """Get the application config directory.

    Returns platform-appropriate config directory:
    - macOS/Linux: ~/.config/folder_extractor/
    - Windows: %APPDATA%/folder_extractor/

    Returns:
        Path to config directory (created if doesn't exist)
    """
    if platform.system() == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        # macOS and Linux use ~/.config/
        base = Path.home() / ".config"

    config_dir = base / "folder_extractor" / "history"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_history_filename(directory: Union[str, Path]) -> str:
    """Generate a unique history filename for a directory.

    Uses a hash of the absolute path to create a unique, filesystem-safe filename.

    Args:
        directory: The working directory path

    Returns:
        Unique filename like 'abc123def456.json'
    """
    dir_path = Path(directory).resolve()
    # Create a hash of the absolute path for uniqueness
    path_hash = hashlib.sha256(str(dir_path).encode()).hexdigest()[:16]
    return f"{path_hash}.json"


class FileOperationError(Exception):
    """Base exception for file operation errors."""

    pass


class IFileOperations(ABC):  # pragma: no cover
    """Interface for file operations."""

    @abstractmethod
    def move_file(
        self,
        source: Union[str, Path],
        destination: Union[str, Path],
        dry_run: bool = False,
    ) -> bool:
        """Move a single file."""
        pass

    @abstractmethod
    def generate_unique_name(self, directory: Union[str, Path], filename: str) -> str:
        """Generate a unique filename in the given directory."""
        pass

    @abstractmethod
    def remove_empty_directories(
        self, path: Union[str, Path], include_hidden: bool = False
    ) -> int:
        """Remove empty directories recursively."""
        pass

    @abstractmethod
    def determine_type_folder(self, filename: Union[str, Path]) -> str:
        """Determine the folder name for a file type."""
        pass


class FileOperations(IFileOperations):
    """Implementation of file operations."""

    def __init__(self, abort_signal=None):
        """Initialize file operations.

        Args:
            abort_signal: Threading event to signal operation abort
        """
        self.abort_signal = abort_signal

    def move_file(
        self,
        source: Union[str, Path],
        destination: Union[str, Path],
        dry_run: bool = False,
    ) -> bool:
        """
        Move a single file from source to destination.

        Args:
            source: Source file path (str or Path)
            destination: Destination file path (str or Path)
            dry_run: If True, don't actually move the file

        Returns:
            True if successful, False otherwise

        Raises:
            FileOperationError: If the move operation fails
        """
        if dry_run:
            return True

        # Convert to Path objects
        source_path = Path(source)
        dest_path = Path(destination)

        try:
            # Try to move using rename (fastest)
            source_path.rename(dest_path)
            return True
        except OSError:
            # Fall back to copy and delete (works across filesystems)
            try:
                shutil.copy2(source_path, dest_path)
                source_path.unlink()
                return True
            except Exception as e:
                raise FileOperationError(f"Failed to move file: {str(e)}") from e

    def generate_unique_name(self, directory: Union[str, Path], filename: str) -> str:
        """
        Generate a unique filename in the given directory.

        If a file with the given name already exists, appends _1, _2, etc.

        Args:
            directory: Directory to check for existing files (str or Path)
            filename: Original filename

        Returns:
            Unique filename that doesn't exist in the directory
        """
        # Convert to Path object
        dir_path = Path(directory)

        if not (dir_path / filename).exists():
            return filename

        # Use Path for extension handling
        file_path = Path(filename)
        base_name = file_path.stem
        extension = file_path.suffix  # includes the dot, e.g., '.txt'

        # Find unique name
        counter = 1
        while True:
            new_name = f"{base_name}_{counter}{extension}"
            if not (dir_path / new_name).exists():
                return new_name
            counter += 1

    def remove_empty_directories(
        self, path: Union[str, Path], include_hidden: bool = False
    ) -> int:
        """
        Remove empty directories recursively.

        Args:
            path: Root path to start from (str or Path)
            include_hidden: Whether to consider hidden files

        Returns:
            Number of directories removed
        """
        # Convert to Path object
        root_path = Path(path)
        removed_count = 0

        # Walk directory tree bottom-up using sorted list of all subdirectories
        all_dirs = sorted(
            root_path.rglob("*"), key=lambda p: len(p.parts), reverse=True
        )

        for dir_path in all_dirs:
            # Skip non-directories (rglob returns files too)
            if not dir_path.is_dir():
                continue

            # Skip root directory itself (defensive, rglob shouldn't return it)
            if dir_path == root_path:  # pragma: no cover
                continue

            # Check if directory is empty
            try:
                dir_content = list(dir_path.iterdir())

                # If not including hidden files, filter them out
                if not include_hidden:
                    visible_content = [
                        item for item in dir_content if not item.name.startswith(".")
                    ]
                else:
                    visible_content = dir_content

                # If directory is empty (or only has hidden files), remove it
                if not visible_content:
                    # Remove hidden files if not including them
                    # But protect the history file!
                    if not include_hidden:
                        for item in dir_content:  # pragma: no branch
                            # All items here are hidden (visible_content is empty)
                            if item.name.startswith("."):  # pragma: no branch
                                # Never delete the history file
                                if item.name == HISTORY_FILE_NAME:
                                    continue
                                if item.is_file():
                                    item.unlink()
                                elif item.is_dir():  # pragma: no branch
                                    shutil.rmtree(item)

                    dir_path.rmdir()
                    removed_count += 1
            except (OSError, PermissionError):
                # Skip directories we can't access
                pass

        return removed_count

    def determine_type_folder(self, filename: Union[str, Path]) -> str:
        """
        Determine the folder name for a file based on its type.

        Args:
            filename: Name of the file (str or Path)

        Returns:
            Folder name for the file type
        """
        # Convert to Path object and get extension
        file_path = Path(filename)
        ext = file_path.suffix.lower()  # suffix includes the dot, e.g., '.pdf'

        # Look up in mapping
        if ext in FILE_TYPE_FOLDERS:
            return FILE_TYPE_FOLDERS[ext]
        elif ext:
            # Unknown extension - use uppercase extension without dot
            return ext[1:].upper()
        else:
            # No extension
            return NO_EXTENSION_FOLDER


class HistoryManager:
    """Manages operation history for undo functionality.

    History files are stored in a central config directory:
    - macOS/Linux: ~/.config/folder_extractor/history/
    - Windows: %APPDATA%/folder_extractor/history/

    Each working directory gets a unique history file based on a hash of its path.
    """

    @staticmethod
    def _get_history_file_path(directory: Union[str, Path]) -> Path:
        """Get the path to the history file for a directory.

        Args:
            directory: The working directory

        Returns:
            Path to the history file in the central config location
        """
        config_dir = get_config_directory()
        filename = get_history_filename(directory)
        return config_dir / filename

    @staticmethod
    def _get_legacy_history_file(directory: Union[str, Path]) -> Path:
        """Get the path to the legacy (local) history file.

        Args:
            directory: The working directory

        Returns:
            Path to the legacy history file in the working directory
        """
        return Path(directory) / HISTORY_FILE_NAME

    @staticmethod
    def _migrate_legacy_history(directory: Union[str, Path]) -> bool:
        """Migrate legacy history file from working directory to central location.

        Args:
            directory: The working directory

        Returns:
            True if migration occurred, False otherwise
        """
        legacy_file = HistoryManager._get_legacy_history_file(directory)
        if not legacy_file.exists():
            return False

        # Read legacy history
        try:
            # Remove immutable flag if set
            HistoryManager._set_immutable(legacy_file, False)

            with legacy_file.open("r", encoding="utf-8") as f:
                history_data = json.load(f)

            # Save to new location
            new_file = HistoryManager._get_history_file_path(directory)
            with new_file.open("w", encoding="utf-8") as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)

            # Protect new file
            HistoryManager._set_immutable(new_file, True)

            # Delete legacy file
            legacy_file.unlink()
            return True
        except (OSError, json.JSONDecodeError):
            return False

    @staticmethod
    def _set_immutable(file_path: Path, immutable: bool) -> None:
        """Set or remove the immutable flag on a file (macOS only).

        Args:
            file_path: Path to the file
            immutable: True to protect, False to unprotect
        """
        if platform.system() != "Darwin":
            return  # Only works on macOS

        if not file_path.exists():
            return

        try:
            current_flags = os.stat(file_path).st_flags
            if immutable:
                # Set user immutable flag
                os.chflags(file_path, current_flags | stat.UF_IMMUTABLE)
            else:
                # Remove user immutable flag
                os.chflags(file_path, current_flags & ~stat.UF_IMMUTABLE)
        except (OSError, AttributeError):
            pass  # Ignore errors (e.g., permission denied, not supported)

    @staticmethod
    def save_history(
        operations: List[Dict[str, Any]], directory: Union[str, Path]
    ) -> str:
        """
        Save operation history to file in central config location.

        Args:
            operations: List of operation records
            directory: Working directory (used to identify the history file)

        Returns:
            Path to the history file (as string)
        """
        history_file = HistoryManager._get_history_file_path(directory)

        # Remove protection before writing
        HistoryManager._set_immutable(history_file, False)

        # Store the working directory path in the history for reference
        dir_path = Path(directory).resolve()
        history_data = {
            "zeitstempel": datetime.now().isoformat(),
            "version": "2.0",
            "arbeitsverzeichnis": str(dir_path),
            "operationen": operations,
        }

        with history_file.open("w", encoding="utf-8") as f:
            json.dump(history_data, f, indent=2, ensure_ascii=False)

        # Protect the file after writing
        HistoryManager._set_immutable(history_file, True)

        return str(history_file)

    @staticmethod
    def load_history(directory: Union[str, Path]) -> Optional[Dict[str, Any]]:
        """
        Load operation history from file.

        First checks for legacy history in working directory and migrates if found.
        Then loads from central config location.

        Args:
            directory: Working directory (used to identify the history file)

        Returns:
            History data or None if not found
        """
        # Try to migrate legacy history first
        HistoryManager._migrate_legacy_history(directory)

        # Load from central location
        history_file = HistoryManager._get_history_file_path(directory)

        if not history_file.exists():
            return None

        try:
            with history_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

    @staticmethod
    def delete_history(directory: Union[str, Path]) -> bool:
        """
        Delete history file from central config location.

        Also removes any legacy history file in the working directory.

        Args:
            directory: Working directory (used to identify the history file)

        Returns:
            True if deleted, False if not found
        """
        deleted = False

        # Delete from central location
        history_file = HistoryManager._get_history_file_path(directory)
        if history_file.exists():
            # Remove protection before deleting
            HistoryManager._set_immutable(history_file, False)
            history_file.unlink()
            deleted = True

        # Also clean up any legacy file
        legacy_file = HistoryManager._get_legacy_history_file(directory)
        if legacy_file.exists():
            HistoryManager._set_immutable(legacy_file, False)
            legacy_file.unlink()
            deleted = True

        return deleted


class FileMover:
    """High-level file moving operations."""

    def __init__(self, file_ops: IFileOperations, abort_signal=None):
        """
        Initialize file mover.

        Args:
            file_ops: File operations implementation
            abort_signal: Threading event to signal abort
        """
        self.file_ops = file_ops
        self.abort_signal = abort_signal

    def move_files(
        self,
        files: List[Union[str, Path]],
        destination: Union[str, Path],
        dry_run: bool = False,
        progress_callback=None,
    ) -> Tuple[int, int, int, List[Dict]]:
        """
        Move multiple files to destination.

        Args:
            files: List of file paths to move (str or Path)
            destination: Destination directory (str or Path)
            dry_run: If True, simulate the operation
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple of (moved_count, error_count, duplicate_count, history)
        """
        # Convert destination to Path
        dest_path = Path(destination)

        moved = 0
        errors = 0
        duplicates = 0
        history = []

        for i, file_path in enumerate(files):  # pragma: no branch
            # Check abort signal
            if self.abort_signal and self.abort_signal.is_set():
                break

            # Convert to Path object
            source_path = Path(file_path)

            # Progress callback
            if progress_callback:
                progress_callback(i + 1, len(files), file_path)

            try:
                filename = source_path.name

                # Generate unique name if needed
                unique_name = self.file_ops.generate_unique_name(dest_path, filename)
                if unique_name != filename:
                    duplicates += 1

                final_dest = dest_path / unique_name

                # Move file
                if self.file_ops.move_file(
                    source_path, final_dest, dry_run
                ):  # pragma: no branch
                    moved += 1

                    # Record in history (use strings for JSON serialization)
                    if not dry_run:
                        history.append(
                            {
                                "original_pfad": str(source_path),
                                "neuer_pfad": str(final_dest),
                                "original_name": filename,
                                "neuer_name": unique_name,
                                "zeitstempel": datetime.now().isoformat(),
                            }
                        )

            except Exception as e:  # pragma: no branch
                errors += 1
                if progress_callback:  # pragma: no branch
                    progress_callback(i + 1, len(files), file_path, error=str(e))

        return moved, errors, duplicates, history

    def move_files_sorted(
        self,
        files: List[Union[str, Path]],
        destination: Union[str, Path],
        dry_run: bool = False,
        progress_callback=None,
        folder_override_callback=None,
    ) -> Tuple[int, int, int, List[Dict], List[str]]:
        """
        Move files sorted by type into subdirectories.

        Args:
            files: List of file paths to move (str or Path)
            destination: Destination directory (str or Path)
            dry_run: If True, simulate the operation
            progress_callback: Optional callback for progress updates
            folder_override_callback: Optional callback(filepath) -> folder_name
                                     If provided, can override the default folder name

        Returns:
            Tuple of (moved, errors, duplicates, history, created_folders)
        """
        # Convert destination to Path
        dest_path = Path(destination)

        moved = 0
        errors = 0
        duplicates = 0
        history = []
        created_folders = set()

        for i, file_path in enumerate(files):  # pragma: no branch
            # Check abort signal
            if self.abort_signal and self.abort_signal.is_set():
                break

            # Convert to Path object
            source_path = Path(file_path)

            # Progress callback
            if progress_callback:
                progress_callback(i + 1, len(files), file_path)

            try:
                filename = source_path.name

                # Determine type folder - check override callback first
                type_folder = None
                if folder_override_callback:
                    type_folder = folder_override_callback(source_path)

                # Fall back to default type folder determination
                if not type_folder:
                    type_folder = self.file_ops.determine_type_folder(filename)

                type_path = dest_path / type_folder

                # Create type folder if needed
                if not type_path.exists() and not dry_run:
                    type_path.mkdir(parents=True, exist_ok=True)
                    created_folders.add(type_folder)

                # Generate unique name
                unique_name = self.file_ops.generate_unique_name(type_path, filename)
                if unique_name != filename:
                    duplicates += 1

                final_dest = type_path / unique_name

                # Move file
                if self.file_ops.move_file(
                    source_path, final_dest, dry_run
                ):  # pragma: no branch
                    moved += 1

                    # Record in history (use strings for JSON serialization)
                    if not dry_run:
                        history.append(
                            {
                                "original_pfad": str(source_path),
                                "neuer_pfad": str(final_dest),
                                "original_name": filename,
                                "neuer_name": unique_name,
                                "zeitstempel": datetime.now().isoformat(),
                            }
                        )

            except Exception as e:  # pragma: no branch
                errors += 1
                if progress_callback:  # pragma: no branch
                    progress_callback(i + 1, len(files), file_path, error=str(e))

        return moved, errors, duplicates, history, list(created_folders)
