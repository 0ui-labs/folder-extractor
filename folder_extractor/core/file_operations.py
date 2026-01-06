"""
File operations module.

Handles all file system operations including moving files,
generating unique names, and managing directories.
"""

import contextlib
import hashlib
import json
import os
import platform
import shutil
import stat
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

from folder_extractor.config.constants import (
    FILE_TYPE_FOLDERS,
    HISTORY_FILE_NAME,
    NO_EXTENSION_FOLDER,
)


def get_config_dir() -> Path:
    """Get the application config root directory.

    Returns platform-appropriate config directory:
    - macOS/Linux: ~/.config/folder_extractor/
    - Windows: %APPDATA%/folder_extractor/

    This is the root config directory for all application settings.
    Use get_config_directory() for history-specific storage.

    Returns:
        Path to config root directory (created if doesn't exist)
    """
    if platform.system() == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        # macOS and Linux use ~/.config/
        base = Path.home() / ".config"

    config_dir = base / "folder_extractor"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_directory() -> Path:
    """Get the application history config directory.

    Returns platform-appropriate config directory for history storage:
    - macOS/Linux: ~/.config/folder_extractor/history/
    - Windows: %APPDATA%/folder_extractor/history/

    This is specifically for history file storage.
    Use get_config_dir() for the config root directory.

    Returns:
        Path to history config directory (created if doesn't exist)
    """
    config_dir = get_config_dir() / "history"
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
        source: Path,
        destination: Path,
        dry_run: bool = False,
    ) -> bool:
        """Move a single file."""
        pass

    @abstractmethod
    def generate_unique_name(self, directory: Path, filename: str) -> str:
        """Generate a unique filename in the given directory."""
        pass

    @abstractmethod
    def remove_empty_directories(
        self, path: Path, include_hidden: bool = False
    ) -> int:
        """Remove empty directories recursively."""
        pass

    @abstractmethod
    def determine_type_folder(self, filename: Path) -> str:
        """Determine the folder name for a file type."""
        pass

    @abstractmethod
    def calculate_file_hash(
        self, filepath: Path, algorithm: str = "sha256"
    ) -> str:
        """Calculate the hash of a file.

        Args:
            filepath: Path object to the file to hash
            algorithm: Hash algorithm to use (default: sha256)

        Returns:
            Hexadecimal hash string
        """
        pass

    @abstractmethod
    def build_hash_index(
        self, directory: Path, include_all: bool = False
    ) -> Dict[str, List[Path]]:
        """Build a hash index of all files in a directory tree.

        Scans the directory recursively and groups files by their content hash.
        Uses size-based pre-filtering to minimize expensive hash calculations
        (unless include_all is True).

        Args:
            directory: Root directory to scan (Path object)
            include_all: If True, hash ALL files (for global deduplication).
                        If False, only hash files with matching sizes (optimization).

        Returns:
            Dictionary mapping hash values to lists of file paths.
            If include_all=False: Only includes hashes with multiple files (duplicates).
            If include_all=True: Includes ALL file hashes.
        """
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
        source: Path,
        destination: Path,
        dry_run: bool = False,
    ) -> bool:
        """
        Move a single file from source to destination.

        Args:
            source: Source file path (Path object)
            destination: Destination file path (Path object)
            dry_run: If True, don't actually move the file

        Returns:
            True if successful, False otherwise

        Raises:
            FileOperationError: If the move operation fails
        """
        if dry_run:
            return True

        try:
            # Try to move using rename (fastest)
            source.rename(destination)
            return True
        except OSError:
            # Fall back to copy and delete (works across filesystems)
            try:
                shutil.copy2(source, destination)
                source.unlink()
                return True
            except Exception as e:
                raise FileOperationError(f"Failed to move file: {str(e)}") from e

    def generate_unique_name(self, directory: Path, filename: str) -> str:
        """
        Generate a unique filename in the given directory.

        If a file with the given name already exists, appends _1, _2, etc.

        Args:
            directory: Directory to check for existing files (Path object)
            filename: Original filename

        Returns:
            Unique filename that doesn't exist in the directory
        """
        if not (directory / filename).exists():
            return filename

        # Use Path for extension handling
        file_path = Path(filename)
        base_name = file_path.stem
        extension = file_path.suffix  # includes the dot, e.g., '.txt'

        # Find unique name
        counter = 1
        while True:
            new_name = f"{base_name}_{counter}{extension}"
            if not (directory / new_name).exists():
                return new_name
            counter += 1

    def remove_empty_directories(
        self, path: Path, include_hidden: bool = False
    ) -> int:
        """
        Remove empty directories recursively.

        Args:
            path: Root path to start from (Path object)
            include_hidden: Whether to consider hidden files

        Returns:
            Number of directories removed
        """
        removed_count = 0

        # Walk directory tree bottom-up using sorted list of all subdirectories
        all_dirs = sorted(
            path.rglob("*"), key=lambda p: len(p.parts), reverse=True
        )

        for dir_path in all_dirs:
            # Skip non-directories (rglob returns files too)
            if not dir_path.is_dir():
                continue

            # Skip root directory itself (defensive, rglob shouldn't return it)
            if dir_path == path:  # pragma: no cover
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

    def determine_type_folder(self, filename: Path) -> str:
        """
        Determine the folder name for a file based on its type.

        Args:
            filename: Name of the file (Path object)

        Returns:
            Folder name for the file type
        """
        ext = filename.suffix.lower()  # suffix includes the dot, e.g., '.pdf'

        # Look up in mapping
        if ext in FILE_TYPE_FOLDERS:
            return FILE_TYPE_FOLDERS[ext]
        elif ext:
            # Unknown extension - use uppercase extension without dot
            return ext[1:].upper()
        else:
            # No extension
            return NO_EXTENSION_FOLDER

    def calculate_file_hash(
        self, filepath: Path, algorithm: str = "sha256"
    ) -> str:
        """
        Calculate the hash of a file using the specified algorithm.

        Reads the file in chunks to minimize memory usage, making it suitable
        for large files (e.g., videos).

        Args:
            filepath: Path to the file to hash (Path object)
            algorithm: Hash algorithm to use (default: "sha256")
                       Supported: "md5", "sha1", "sha256", "sha512", etc.

        Returns:
            Hexadecimal hash string

        Raises:
            FileOperationError: If file doesn't exist, is not readable,
                               or is a directory
            ValueError: If algorithm is not supported

        Example:
            >>> ops = FileOperations()
            >>> hash_value = ops.calculate_file_hash(Path("video.mp4"))
            >>> print(hash_value)
            'a1b2c3d4...'
        """
        # Validate file exists
        if not filepath.exists():
            raise FileOperationError(f"Datei existiert nicht: {filepath}")

        # Validate it's a file, not a directory
        if filepath.is_dir():
            raise FileOperationError(
                f"Pfad ist ein Verzeichnis, keine Datei: {filepath}"
            )

        # Create hash object - ValueError is raised by hashlib for invalid algorithms
        try:
            hash_obj = hashlib.new(algorithm)
        except ValueError as e:
            raise ValueError(f"Ungültiger Hash-Algorithmus: {algorithm}") from e

        # Read file in chunks and update hash
        chunk_size = 8192  # 8KB chunks - optimal for I/O performance

        try:
            with filepath.open("rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    hash_obj.update(chunk)
        except PermissionError as e:
            raise FileOperationError(
                f"Keine Berechtigung zum Lesen der Datei: {filepath}"
            ) from e
        except OSError as e:
            raise FileOperationError(
                f"Fehler beim Lesen der Datei: {filepath} - {e}"
            ) from e

        return hash_obj.hexdigest()

    def build_hash_index(
        self, directory: Path, include_all: bool = False
    ) -> Dict[str, List[Path]]:
        """
        Build a hash index of all files in a directory tree.

        Scans the directory recursively and groups files by their content hash.
        Uses size-based pre-filtering to minimize expensive hash calculations
        (unless include_all is True).

        Args:
            directory: Root directory to scan (Path object)
            include_all: If True, hash ALL files (for global deduplication).
                        If False, only hash files with matching sizes (optimization).

        Returns:
            Dictionary mapping hash values to lists of file paths.
            If include_all=False: Only includes hashes with multiple files (duplicates).
            If include_all=True: Includes ALL file hashes.
            Example: {"abc123...": [Path("/path/file1.txt"), Path("/path/file2.txt")]}

        Raises:
            FileOperationError: If directory doesn't exist, is not readable,
                               or is not a directory

        Example:
            >>> ops = FileOperations()
            >>> index = ops.build_hash_index(Path("/media/photos"))
            >>> # Find all duplicate groups
            >>> duplicates = {h: paths for h, paths in index.items() if len(paths) > 1}
            >>> print(f"Found {len(duplicates)} groups of duplicates")
        """
        from collections import defaultdict

        # Validate directory exists
        if not directory.exists():
            raise FileOperationError(f"Verzeichnis existiert nicht: {directory}")

        # Validate it's a directory, not a file
        if not directory.is_dir():
            raise FileOperationError(
                f"Pfad ist eine Datei, kein Verzeichnis: {directory}"
            )

        # Check if we can read the directory
        try:
            # Try to list the directory to check permissions
            next(directory.iterdir(), None)
        except PermissionError as e:
            raise FileOperationError(
                f"Keine Leseberechtigung für Verzeichnis: {directory}"
            ) from e

        # Phase 1: Group files by size (fast metadata operation)
        size_groups: Dict[int, List[Path]] = defaultdict(list)

        try:
            for path in directory.rglob("*"):
                # Check abort signal
                if self.abort_signal and self.abort_signal.is_set():
                    break

                # Skip directories
                if not path.is_file():
                    continue

                try:
                    size = path.stat().st_size
                    size_groups[size].append(path)
                except OSError:
                    # Skip files we can't access (permissions, deleted, etc.)
                    continue
        except PermissionError as e:
            raise FileOperationError(
                f"Keine Leseberechtigung für Verzeichnis: {directory}"
            ) from e

        # Phase 2: Hash files based on include_all flag
        hash_index: Dict[str, List[Path]] = defaultdict(list)

        for _size, paths in size_groups.items():
            # Skip sizes with only one file if not including all
            # (no duplicates possible for unique sizes)
            if not include_all and len(paths) == 1:
                continue

            # Check abort signal
            if self.abort_signal and self.abort_signal.is_set():
                break

            for path in paths:
                try:
                    hash_value = self.calculate_file_hash(path)
                    hash_index[hash_value].append(path)
                except FileOperationError:
                    # Skip files that became unreadable (deleted, permissions changed)
                    continue

        # Return based on include_all flag
        if include_all:
            # Return ALL hashes (for global deduplication)
            return dict(hash_index)
        else:
            # Filter to only include hashes with multiple files (actual duplicates)
            return {h: paths for h, paths in hash_index.items() if len(paths) > 1}


class HistoryManager:
    """Manages operation history for undo functionality.

    History files are stored in a central config directory:
    - macOS/Linux: ~/.config/folder_extractor/history/
    - Windows: %APPDATA%/folder_extractor/history/

    Each working directory gets a unique history file based on a hash of its path.
    """

    @staticmethod
    def _get_history_file_path(directory: Path) -> Path:
        """Get the path to the history file for a directory.

        Args:
            directory: The working directory (Path object)

        Returns:
            Path to the history file in the central config location
        """
        config_dir = get_config_directory()
        filename = get_history_filename(directory)
        return config_dir / filename

    @staticmethod
    def _get_legacy_history_file(directory: Path) -> Path:
        """Get the path to the legacy (local) history file.

        Args:
            directory: The working directory (Path object)

        Returns:
            Path to the legacy history file in the working directory
        """
        return directory / HISTORY_FILE_NAME

    @staticmethod
    def _migrate_legacy_history(directory: Path) -> bool:
        """Migrate legacy history file from working directory to central location.

        Args:
            directory: The working directory (Path object)

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
        operations: List[Dict[str, Any]], directory: Path
    ) -> str:
        """
        Save operation history to file in central config location.

        Args:
            operations: List of operation records
            directory: Working directory (Path object,
                used to identify the history file)

        Returns:
            Path to the history file (as string)
        """
        history_file = HistoryManager._get_history_file_path(directory)

        # Remove protection before writing
        HistoryManager._set_immutable(history_file, False)

        # Store the working directory path in the history for reference
        dir_path = directory.resolve()
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
    def load_history(directory: Path) -> Optional[Dict[str, Any]]:
        """
        Load operation history from file.

        First checks for legacy history in working directory and migrates if found.
        Then loads from central config location.

        Args:
            directory: Working directory (Path object,
                used to identify the history file)

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
    def delete_history(directory: Path) -> bool:
        """
        Delete history file from central config location.

        Also removes any legacy history file in the working directory.

        Args:
            directory: Working directory (Path object,
                used to identify the history file)

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

    def __init__(
        self,
        file_ops: IFileOperations,
        abort_signal=None,
        indexing_callback=None,
    ):
        """
        Initialize file mover.

        Args:
            file_ops: File operations implementation
            abort_signal: Threading event to signal abort
            indexing_callback: Callback for "start"/"end" during indexing
        """
        self.file_ops = file_ops
        self.abort_signal = abort_signal
        self.indexing_callback = indexing_callback

    def _perform_move(
        self,
        source_path: Path,
        dest_path: Path,
        filename: str,
        dry_run: bool,
        hash_index: Optional[Dict[str, List[Path]]] = None,
    ) -> Tuple[bool, bool, Optional[Dict[str, Any]]]:
        """
        Perform a single file move operation with optional hash index update.

        This is a helper method that encapsulates the common move logic
        used by both move_files() and move_files_sorted().

        Args:
            source_path: Path to the source file
            dest_path: Destination directory path
            filename: Original filename of the file
            dry_run: If True, simulate the operation without moving
            hash_index: Optional hash index to update after move

        Returns:
            Tuple of (success, renamed, history_entry) where:
            - success: True if file was successfully moved
            - renamed: True if file was renamed (unique_name != filename)
            - history_entry: History entry dict or None for dry-run
        """
        # Step 1: Generate unique name
        unique_name = self.file_ops.generate_unique_name(dest_path, filename)

        # Step 2: Check if renamed
        renamed = unique_name != filename

        # Step 3: Create final destination
        final_dest = dest_path / unique_name

        # Step 4: Move file
        success = self.file_ops.move_file(source_path, final_dest, dry_run)

        # Step 5: If not successful, return failure
        if not success:
            return (False, False, None)

        # Step 6: Update hash index (when success AND hash_index given AND not dry_run)
        if hash_index is not None and not dry_run:
            try:
                file_hash = self.file_ops.calculate_file_hash(final_dest)
                hash_index.setdefault(file_hash, []).append(final_dest)
            except FileOperationError:
                # Hash calculation error is caught silently
                pass

        # Step 7: Create history entry (only when success AND not dry_run)
        history_entry: Optional[Dict[str, Any]] = None
        if not dry_run:
            history_entry = {
                "original_pfad": str(source_path),
                "neuer_pfad": str(final_dest),
                "original_name": filename,
                "neuer_name": unique_name,
                "zeitstempel": datetime.now().isoformat(),
            }

        # Step 8: Return results
        return (success, renamed, history_entry)

    def _prepare_global_hash_index(
        self,
        files: Sequence[Path],
        dest_path: Path,
    ) -> Tuple[Sequence[Path], Dict[str, List[Path]]]:
        """
        Prepare hash index for global deduplication.

        Sorts files by modification time (oldest first), builds a hash index
        of all existing files in the destination, and filters out source files
        to prevent false duplicate detection.

        Args:
            files: List of file paths to process
            dest_path: Destination directory path

        Returns:
            Tuple of (sorted_files, hash_index) where:
            - sorted_files: Files sorted by mtime, name length, and name
            - hash_index: Dict mapping file hashes to lists of file paths

        Note:
            BUGFIX: Source files in subdirectories are removed from the hash
            index to prevent data loss when identical source files would
            otherwise match each other and be deleted.
        """
        # Sort files by modification time (oldest first) so that when
        # duplicates are found, the ORIGINAL (older) file is kept and
        # the newer copy is detected as duplicate.
        # Secondary sort by filename length then alphabetically, so that
        # when mtimes are equal, shorter/simpler names (likely originals)
        # are processed first (e.g., "test.md" before "test kopie.md").
        sorted_files: Sequence[Path] = files
        with contextlib.suppress(OSError):
            sorted_files = sorted(
                files,
                key=lambda f: (
                    f.stat().st_mtime,  # Primary: oldest first
                    len(f.name),  # Secondary: shortest name first
                    f.name,  # Tertiary: alphabetically
                ),
            )

        hash_index: Dict[str, List[Path]] = {}

        try:
            # Signal indexing start
            if self.indexing_callback:
                self.indexing_callback("start")
            # Get all existing hashes in destination for dedup
            hash_index = self.file_ops.build_hash_index(dest_path, include_all=True)

            # BUGFIX: Remove source files from the hash index to prevent
            # them from matching each other. Without this, two identical
            # source files would both be detected as "already exists"
            # and deleted, resulting in data loss.
            # IMPORTANT: Only remove files from SUBDIRECTORIES, not from root
            # or from type folders (when using sort-by-type).
            dest_resolved = dest_path.resolve()
            # Get known type folder names for filtering
            known_type_folders = set(FILE_TYPE_FOLDERS.values())
            source_paths = set()
            for f in sorted_files:
                fp = Path(f).resolve()
                parent = fp.parent
                # Skip files in root directory
                if parent == dest_resolved:
                    continue
                # Skip files already in a type folder (e.g., TEXT/doc.txt)
                if parent.parent == dest_resolved and parent.name in known_type_folders:
                    continue
                source_paths.add(fp)
            for hash_value in list(hash_index.keys()):
                hash_index[hash_value] = [
                    p for p in hash_index[hash_value] if p.resolve() not in source_paths
                ]
                # Remove empty entries
                if not hash_index[hash_value]:
                    del hash_index[hash_value]
        except FileOperationError:
            # If we can't build index, continue without global dedup
            hash_index = {}
        finally:
            # Signal indexing end
            if self.indexing_callback:
                self.indexing_callback("end")

        return sorted_files, hash_index

    def _check_local_duplicate(
        self,
        source_path: Path,
        existing_dest: Path,
        dry_run: bool,
    ) -> Optional[Dict[str, Any]]:
        """
        Check if source file is a content duplicate of an existing destination file.

        This handles the case where source and destination have the same name
        AND the same content. The source file is deleted (not moved) and a
        history entry is returned.

        Args:
            source_path: Path to the source file
            existing_dest: Path to the existing destination file
            dry_run: If True, don't actually delete the source file

        Returns:
            History entry dict if duplicate detected, None otherwise.
            Returns None on hash calculation errors to allow fallback behavior.
        """
        if not existing_dest.exists():
            return None

        try:
            source_hash = self.file_ops.calculate_file_hash(source_path)
            dest_hash = self.file_ops.calculate_file_hash(existing_dest)

            if source_hash == dest_hash:
                # Identical content - delete source, return history entry
                if not dry_run:
                    source_path.unlink()

                return {
                    "original_pfad": str(source_path),
                    "neuer_pfad": str(existing_dest),
                    "original_name": source_path.name,
                    "neuer_name": existing_dest.name,
                    "zeitstempel": datetime.now().isoformat(),
                    "content_duplicate": True,
                    "duplicate_of": str(existing_dest),
                }
        except (FileOperationError, OSError):
            # Hash calculation failed - fall back to normal behavior
            pass

        return None

    def _check_global_duplicate(
        self,
        source_path: Path,
        hash_index: Dict[str, List[Path]],
        dry_run: bool,
    ) -> Optional[Dict[str, Any]]:
        """
        Check if source file is a global duplicate (same content, different name).

        This handles the case where the source file's content already exists
        somewhere in the destination tree under a different filename.
        The source file is deleted (not moved) and a history entry is returned.

        Args:
            source_path: Path to the source file
            hash_index: Dict mapping file hashes to lists of file paths
            dry_run: If True, don't actually delete the source file

        Returns:
            History entry dict if duplicate detected, None otherwise.
            Returns None on hash calculation errors to allow fallback behavior.
        """
        try:
            source_hash = self.file_ops.calculate_file_hash(source_path)

            if source_hash in hash_index:
                # Find files that are NOT the source file itself
                matching_files = [
                    p
                    for p in hash_index[source_hash]
                    if p.resolve() != source_path.resolve()
                ]

                if matching_files:
                    # Content exists in another file - delete source
                    if not dry_run:
                        source_path.unlink()

                    return {
                        "original_pfad": str(source_path),
                        "neuer_pfad": str(matching_files[0]),
                        "original_name": source_path.name,
                        "neuer_name": matching_files[0].name,
                        "zeitstempel": datetime.now().isoformat(),
                        "global_duplicate": True,
                        "duplicate_of": str(matching_files[0]),
                    }
        except FileOperationError:
            # Hash calculation failed - fall back to normal behavior
            pass

        return None

    def move_files(
        self,
        files: Sequence[Path],
        destination: Path,
        dry_run: bool = False,
        progress_callback: Optional[Callable[..., None]] = None,
        deduplicate: bool = False,
        global_dedup: bool = False,
    ) -> Tuple[int, int, int, int, int, List[Dict[str, Any]]]:
        """
        Move multiple files to destination.

        Args:
            files: List of file paths to move (str or Path)
            destination: Destination directory (str or Path)
            dry_run: If True, simulate the operation
            progress_callback: Optional callback for progress updates
            deduplicate: If True, skip files with identical content (via hash)
                        when destination has same-named file with identical content
            global_dedup: If True, skip files whose content already exists
                         ANYWHERE in the destination tree (regardless of filename)

        Returns:
            Tuple of counts and history. Contents depend on flags:
            - global_dedup: (moved, errors, name_dups, content_dups,
                            global_dups, history)
            - deduplicate: (moved, errors, duplicates, content_dups, history)
            - default: (moved, errors, duplicates, history)
        """
        # Convert destination to Path
        dest_path = Path(destination)

        moved = 0
        errors = 0
        duplicates = 0
        content_duplicates = 0
        global_duplicates = 0
        history = []

        # Build hash index for global deduplication
        hash_index: Dict[str, List[Path]] = {}
        if global_dedup:
            files, hash_index = self._prepare_global_hash_index(files, dest_path)

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

                # Skip files already at destination level (no move needed)
                source_parent = source_path.parent.resolve()
                source_is_at_destination = source_parent == dest_path.resolve()
                if source_is_at_destination:
                    # File is already where it needs to be, skip processing
                    continue

                existing_dest = dest_path / filename

                # Content duplicate check - BEFORE global dedup when same name
                # Same name + same content = content duplicate (not global)
                # Note: Also runs when global_dedup is True, because identical
                # files with same name should be deduplicated regardless
                if existing_dest.exists() and (deduplicate or global_dedup):
                    history_entry = self._check_local_duplicate(
                        source_path, existing_dest, dry_run
                    )
                    if history_entry:
                        content_duplicates += 1
                        if not dry_run:
                            history.append(history_entry)
                        continue

                # Global dedup check - AFTER content duplicate check
                # Only runs when no file with same name exists
                # Catches files with different names but matching content
                if global_dedup and not existing_dest.exists():
                    history_entry = self._check_global_duplicate(
                        source_path, hash_index, dry_run
                    )
                    if history_entry:
                        global_duplicates += 1
                        if not dry_run:
                            history.append(history_entry)
                        continue

                # Call helper method to perform the move
                success, renamed, history_entry = self._perform_move(
                    source_path,
                    dest_path,
                    filename,
                    dry_run,
                    hash_index if global_dedup else None,
                )

                if success:
                    moved += 1
                    if renamed:
                        duplicates += 1
                    if history_entry:
                        history.append(history_entry)

            except Exception as e:  # pragma: no branch
                errors += 1
                if progress_callback:  # pragma: no branch
                    progress_callback(i + 1, len(files), file_path, error=str(e))

        # Always return consistent tuple structure
        return (
            moved,
            errors,
            duplicates,
            content_duplicates,
            global_duplicates,
            history,
        )

    def move_files_sorted(
        self,
        files: Sequence[Path],
        destination: Path,
        dry_run: bool = False,
        progress_callback: Optional[Callable[..., None]] = None,
        folder_override_callback: Optional[
            Callable[[Path], Optional[str]]
        ] = None,
        deduplicate: bool = False,
        global_dedup: bool = False,
    ) -> Tuple[int, int, int, int, int, List[Dict[str, Any]], List[str]]:
        """
        Move files sorted by type into subdirectories.

        Args:
            files: List of file paths to move (str or Path)
            destination: Destination directory (str or Path)
            dry_run: If True, simulate the operation
            progress_callback: Optional callback for progress updates
            folder_override_callback: Optional callback(filepath) -> folder_name
                                     If provided, can override the default folder name
            deduplicate: If True, skip files with identical content (via hash)
                        when destination has same-named file with identical content
            global_dedup: If True, skip files whose content already exists
                         ANYWHERE in the destination tree (regardless of filename)

        Returns:
            Tuple of counts and history. Contents depend on flags:
            - global_dedup: (moved, errors, name_dups, content_dups,
                            global_dups, history, created_folders)
            - deduplicate: (moved, errors, duplicates, content_dups,
                           history, created_folders)
            - default: (moved, errors, duplicates, history, created_folders)
        """
        # Convert destination to Path
        dest_path = Path(destination)

        moved = 0
        errors = 0
        duplicates = 0
        content_duplicates = 0
        global_duplicates = 0
        history = []
        created_folders = set()

        # Build hash index for global deduplication
        hash_index: Dict[str, List[Path]] = {}
        if global_dedup:
            files, hash_index = self._prepare_global_hash_index(files, dest_path)

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

                # Skip files already in their correct type folder
                # (already sorted, should not be moved or deduped)
                source_parent = source_path.parent.resolve()
                source_is_at_destination = source_parent == dest_path.resolve()

                # Check if file is already in the correct type folder
                source_is_in_correct_type_folder = False
                if not source_is_at_destination:
                    parent_folder_name = source_path.parent.name
                    file_extension = source_path.suffix.lower()
                    type_folder = FILE_TYPE_FOLDERS.get(file_extension, "OTHER")
                    source_grandparent = source_parent.parent.resolve()
                    # File is in correct type folder if:
                    # 1. Parent folder name matches expected type folder
                    # 2. Parent's parent is destination (direct child folder)
                    source_is_in_correct_type_folder = (
                        parent_folder_name == type_folder
                        and source_grandparent == dest_path.resolve()
                    )

                if source_is_at_destination or source_is_in_correct_type_folder:
                    # Already at destination or in correct folder, skip
                    continue

                # Determine type folder first - needed for dedup checks
                type_folder = None
                if folder_override_callback:
                    type_folder = folder_override_callback(source_path)

                # Fall back to default type folder determination
                if not type_folder:
                    type_folder = self.file_ops.determine_type_folder(source_path)

                type_path = dest_path / type_folder

                # Create type folder if needed
                if not type_path.exists() and not dry_run:
                    type_path.mkdir(parents=True, exist_ok=True)
                    created_folders.add(type_folder)

                existing_dest = type_path / filename

                # Check if destination file exists and deduplicate is enabled
                # Note: Also runs when global_dedup is True, because identical
                # files with same name should be deduplicated regardless
                if existing_dest.exists() and (deduplicate or global_dedup):
                    history_entry = self._check_local_duplicate(
                        source_path, existing_dest, dry_run
                    )
                    if history_entry:
                        content_duplicates += 1
                        if not dry_run:
                            history.append(history_entry)
                        continue

                # Global dedup check - AFTER content duplicate check
                # Only runs when no file with same name exists
                # Catches files with different names but matching content
                if global_dedup and not existing_dest.exists():
                    history_entry = self._check_global_duplicate(
                        source_path, hash_index, dry_run
                    )
                    if history_entry:
                        global_duplicates += 1
                        if not dry_run:
                            history.append(history_entry)
                        continue

                # Call helper method to perform the move
                success, renamed, history_entry = self._perform_move(
                    source_path,
                    type_path,  # Note: type_path instead of dest_path
                    filename,
                    dry_run,
                    hash_index if global_dedup else None,
                )

                if success:
                    moved += 1
                    if renamed:
                        duplicates += 1
                    if history_entry:
                        history.append(history_entry)

            except Exception as e:  # pragma: no branch
                errors += 1
                if progress_callback:  # pragma: no branch
                    progress_callback(i + 1, len(files), file_path, error=str(e))

        # Always return consistent tuple structure
        folders = list(created_folders)
        return (
            moved,
            errors,
            duplicates,
            content_duplicates,
            global_duplicates,
            history,
            folders,
        )
