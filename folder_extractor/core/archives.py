"""
Archive handling module with Zip Slip protection.

Provides handlers for extracting ZIP and TAR archives safely,
with protection against path traversal attacks (Zip Slip).

Security Features:
- All extracted paths are validated to stay within target directory
- Absolute paths in archives are rejected
- Path traversal attempts (../) are blocked
"""

from __future__ import annotations

import sys
import tarfile
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from folder_extractor.core.file_operations import FileOperationError


class SecurityError(Exception):
    """Raised when security validation fails (e.g., Zip Slip attack detected)."""

    pass


class IArchiveHandler(ABC):
    """
    Interface for archive handlers.

    Implementations must provide safe extraction with path traversal protection.
    """

    @abstractmethod
    def extract(self, archive_path: Path, target_dir: Path) -> None:
        """
        Extract archive contents to target directory.

        Args:
            archive_path: Path to the archive file
            target_dir: Directory to extract contents into

        Raises:
            SecurityError: If path traversal attack is detected
            FileOperationError: If extraction fails due to I/O error
        """
        pass

    @abstractmethod
    def is_supported(self, file_path: Path) -> bool:
        """
        Check if this handler supports the given file type.

        Args:
            file_path: Path to check (only extension is evaluated)

        Returns:
            True if this handler can process the file type
        """
        pass


def _validate_extraction_path(target_dir: Path, member_name: str) -> Path:
    """
    Validate that a member path stays within the target directory.

    This is the core security function that prevents Zip Slip attacks.

    Args:
        target_dir: The authorized extraction directory
        member_name: The path from the archive entry

    Returns:
        The resolved, validated target path

    Raises:
        SecurityError: If the path would escape the target directory
    """
    # Resolve target directory to absolute path
    target_dir_resolved = target_dir.resolve()

    # Construct and resolve the target path
    target_path = (target_dir / member_name).resolve()

    # Check if path stays within target directory
    # Python 3.9+ has is_relative_to(), for older versions we compare paths
    if sys.version_info >= (3, 9):
        is_safe = target_path.is_relative_to(target_dir_resolved)
    else:
        # Fallback for Python 3.7/3.8
        try:
            target_path.relative_to(target_dir_resolved)
            is_safe = True
        except ValueError:
            is_safe = False

    if not is_safe:
        raise SecurityError(
            f"Zip Slip attack detected: '{member_name}' would escape target directory"
        )

    return target_path


class ZipHandler(IArchiveHandler):
    """
    Handler for ZIP archives with Zip Slip protection.

    Supports: .zip files (case-insensitive)
    """

    SUPPORTED_EXTENSIONS: list[str] = [".zip"]

    def is_supported(self, file_path: Path) -> bool:
        """Check if file is a ZIP archive based on extension."""
        suffix = file_path.suffix.lower()
        return suffix in self.SUPPORTED_EXTENSIONS

    def extract(self, archive_path: Path, target_dir: Path) -> None:
        """
        Extract ZIP archive contents safely.

        Validates each entry's path before extraction to prevent
        path traversal attacks.
        """
        try:
            # Ensure target directory exists
            target_dir.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(archive_path, "r") as zf:
                for member_name in zf.namelist():
                    # Skip directory entries (they end with /)
                    if member_name.endswith("/"):
                        # Create the directory
                        dir_path = _validate_extraction_path(target_dir, member_name)
                        dir_path.mkdir(parents=True, exist_ok=True)
                        continue

                    # Validate path is safe before extraction
                    target_path = _validate_extraction_path(target_dir, member_name)

                    # Create parent directories if needed
                    target_path.parent.mkdir(parents=True, exist_ok=True)

                    # Extract the file
                    with zf.open(member_name) as source:
                        target_path.write_bytes(source.read())
        except SecurityError:
            # Re-raise security errors unchanged
            raise
        except zipfile.BadZipFile as e:
            raise FileOperationError(
                f"Invalid or corrupted ZIP archive: {archive_path}"
            ) from e
        except (OSError, PermissionError) as e:
            raise FileOperationError(
                f"Failed to extract ZIP archive '{archive_path}': {e}"
            ) from e


class TarHandler(IArchiveHandler):
    """
    Handler for TAR archives (compressed variants) with path traversal protection.

    Supports: .tar, .tar.gz, .tgz, .tar.bz2 (case-insensitive)
    """

    SUPPORTED_EXTENSIONS: list[str] = [".tar"]
    SUPPORTED_COMPOUND_EXTENSIONS: list[str] = [".tar.gz", ".tar.bz2"]
    SUPPORTED_ALIASES: list[str] = [".tgz"]

    def is_supported(self, file_path: Path) -> bool:
        """Check if file is a TAR archive based on extension."""
        name_lower = file_path.name.lower()

        # Check compound extensions first (e.g., .tar.gz)
        for ext in self.SUPPORTED_COMPOUND_EXTENSIONS:
            if name_lower.endswith(ext):
                return True

        # Check aliases
        suffix = file_path.suffix.lower()
        if suffix in self.SUPPORTED_ALIASES:
            return True

        # Check simple extension
        return suffix in self.SUPPORTED_EXTENSIONS

    def extract(self, archive_path: Path, target_dir: Path) -> None:
        """
        Extract TAR archive contents safely.

        Validates each entry's path before extraction to prevent
        path traversal attacks. Supports auto-detection of compression.
        """
        try:
            # Ensure target directory exists
            target_dir.mkdir(parents=True, exist_ok=True)

            # Open with auto-detection of compression format
            with tarfile.open(archive_path, "r:*") as tf:
                for member in tf.getmembers():
                    # Validate path is safe before extraction
                    target_path = _validate_extraction_path(target_dir, member.name)

                    if member.isdir():
                        target_path.mkdir(parents=True, exist_ok=True)
                    elif member.isfile():
                        # Create parent directories if needed
                        target_path.parent.mkdir(parents=True, exist_ok=True)

                        # Extract file content
                        source = tf.extractfile(member)
                        if source is not None:
                            target_path.write_bytes(source.read())
        except SecurityError:
            # Re-raise security errors unchanged
            raise
        except tarfile.TarError as e:
            raise FileOperationError(
                f"Invalid or corrupted TAR archive: {archive_path}"
            ) from e
        except (OSError, PermissionError) as e:
            raise FileOperationError(
                f"Failed to extract TAR archive '{archive_path}': {e}"
            ) from e


def get_archive_handler(file_path: Path) -> Optional[IArchiveHandler]:
    """
    Factory function to get the appropriate handler for an archive file.

    Args:
        file_path: Path to the archive file

    Returns:
        An IArchiveHandler instance if the file type is supported, None otherwise

    Example:
        handler = get_archive_handler(Path("backup.tar.gz"))
        if handler:
            handler.extract(archive_path, target_dir)
    """
    handlers: list[IArchiveHandler] = [
        ZipHandler(),
        TarHandler(),
    ]

    for handler in handlers:
        if handler.is_supported(file_path):
            return handler

    return None
