"""
Zone Manager for Dropzone configuration.

This module provides the ZoneManager class for managing dropzone configurations.
Zones are persisted to ~/.config/folder_extractor/zones.json and support
thread-safe CRUD operations.
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, TypedDict

from folder_extractor.core.file_operations import get_config_dir

logger = logging.getLogger(__name__)


class ZoneManagerError(Exception):
    """Exception raised for ZoneManager errors."""

    pass


class ZoneConfig(TypedDict):
    """Configuration for a single dropzone.

    Attributes:
        id: Unique zone identifier (UUID string).
        name: Human-readable zone name.
        path: Absolute path to the watched directory.
        enabled: Whether the zone is active.
        auto_sort: Whether to automatically sort files by type.
        categories: List of allowed file extensions (empty = all).
        created_at: ISO 8601 timestamp when the zone was created.
    """

    id: str
    name: str
    path: str
    enabled: bool
    auto_sort: bool
    categories: list[str]
    created_at: str


class SmartWatchProfile(TypedDict, total=False):
    """Configuration profile for smart watch mode with AI categorization.

    Contains all settings needed for SmartFolderEventHandler to process
    files using the SmartSorter AI categorization.

    Attributes:
        name: Human-readable profile name.
        path: Absolute path to the watched directory.
        folder_structure: Template for target path (e.g., "{category}/{sender}/{year}").
        categories: List of AI categories for sorting.
        file_types: Allowed file extensions (empty = all).
        recursive: Whether to watch subdirectories.
        exclude_subfolders: Subfolder names to exclude when recursive.
        ignore_patterns: Glob patterns for files to ignore.
    """

    name: str
    path: str
    folder_structure: str
    categories: list[str]
    file_types: list[str]
    recursive: bool
    exclude_subfolders: list[str]
    ignore_patterns: list[str]


class ZoneManager:
    """Manages dropzone configurations with persistence.

    Provides thread-safe CRUD operations for dropzone configurations.
    Zones are persisted to ~/.config/folder_extractor/zones.json.

    Example:
        >>> manager = ZoneManager()
        >>> zone_id = manager.add_zone(name="Downloads", path="/Users/user/Downloads")
        >>> zones = manager.list_zones()
        >>> manager.remove_zone(zone_id)
    """

    def __init__(self) -> None:
        """Initialize the ZoneManager.

        Loads existing zones from the config file if it exists.
        """
        self._lock = threading.RLock()
        self._zones: dict[str, ZoneConfig] = {}
        self._config_file = get_config_dir() / "zones.json"
        self._load_zones()

    def _load_zones(self) -> None:
        """Load zones from the config file.

        Creates an empty zone list if the file doesn't exist or is corrupted.
        """
        if not self._config_file.exists():
            logger.debug("No zones config file found, starting with empty zones")
            return

        try:
            content = self._config_file.read_text(encoding="utf-8")
            data = json.loads(content)
            if isinstance(data, dict):
                self._zones = data
                logger.debug(f"Loaded {len(self._zones)} zones from config")
            else:
                logger.warning("Invalid zones config format, starting with empty zones")
                self._zones = {}
        except json.JSONDecodeError as e:
            logger.warning(
                f"Corrupted zones config file: {e}, starting with empty zones"
            )
            self._zones = {}
        except OSError as e:
            logger.warning(
                f"Failed to read zones config: {e}, starting with empty zones"
            )
            self._zones = {}

    def _save_zones(self) -> None:
        """Save zones to the config file.

        Creates the config directory if it doesn't exist.
        """
        try:
            self._config_file.parent.mkdir(parents=True, exist_ok=True)
            content = json.dumps(self._zones, indent=2, ensure_ascii=False)
            self._config_file.write_text(content, encoding="utf-8")
            logger.debug(f"Saved {len(self._zones)} zones to config")
        except OSError as e:
            logger.error(f"Failed to save zones config: {e}")
            raise ZoneManagerError(f"Failed to save zones: {e}") from e

    def _validate_path(self, path: str) -> Path:
        """Validate that a path exists and is a directory.

        Args:
            path: The path to validate.

        Returns:
            The resolved Path object.

        Raises:
            ZoneManagerError: If the path doesn't exist or isn't a directory.
        """
        if not path:
            raise ZoneManagerError("Zone path is required")

        resolved = Path(path).resolve()

        if not resolved.exists():
            raise ZoneManagerError(f"Zone path does not exist: {path}")

        if not resolved.is_dir():
            raise ZoneManagerError(f"Zone path is not a directory: {path}")

        return resolved

    def add_zone(
        self,
        name: str,
        path: str,
        enabled: bool = True,
        auto_sort: bool = False,
        categories: Optional[list[str]] = None,
    ) -> str:
        """Add a new zone.

        Args:
            name: Human-readable zone name.
            path: Absolute path to the watched directory.
            enabled: Whether the zone is active (default: True).
            auto_sort: Whether to auto-sort files (default: False).
            categories: List of allowed file extensions (default: []).

        Returns:
            The unique zone ID (UUID string).

        Raises:
            ZoneManagerError: If name is empty or path is invalid.
        """
        if not name:
            raise ZoneManagerError("Zone name is required")

        resolved_path = self._validate_path(path)

        with self._lock:
            zone_id = str(uuid.uuid4())
            created_at = datetime.now(timezone.utc).isoformat()
            zone: ZoneConfig = {
                "id": zone_id,
                "name": name,
                "path": str(resolved_path),
                "enabled": enabled,
                "auto_sort": auto_sort,
                "categories": categories if categories is not None else [],
                "created_at": created_at,
            }
            self._zones[zone_id] = zone
            self._save_zones()
            logger.info(f"Zone created: {zone_id} ({name})")
            return zone_id

    def remove_zone(self, zone_id: str) -> bool:
        """Remove a zone.

        Args:
            zone_id: The ID of the zone to remove.

        Returns:
            True if the zone was removed, False if it didn't exist.
        """
        with self._lock:
            if zone_id not in self._zones:
                return False

            del self._zones[zone_id]
            self._save_zones()
            logger.info(f"Zone removed: {zone_id}")
            return True

    def get_zone(self, zone_id: str) -> Optional[ZoneConfig]:
        """Get a zone by ID.

        Args:
            zone_id: The ID of the zone to retrieve.

        Returns:
            The zone configuration, or None if not found.
        """
        with self._lock:
            return self._zones.get(zone_id)

    def list_zones(self) -> list[ZoneConfig]:
        """List all configured zones.

        Returns:
            A list of all zone configurations.
        """
        with self._lock:
            return list(self._zones.values())

    def update_zone(self, zone_id: str, **kwargs: Any) -> bool:
        """Update a zone's configuration.

        Args:
            zone_id: The ID of the zone to update.
            **kwargs: Fields to update (name, path, enabled, auto_sort, categories).

        Returns:
            True if the zone was updated, False if it didn't exist.

        Raises:
            ZoneManagerError: If the new path is invalid.
        """
        allowed_fields = {"name", "path", "enabled", "auto_sort", "categories"}

        with self._lock:
            if zone_id not in self._zones:
                return False

            zone = self._zones[zone_id]

            # Validate path if being updated - use resolved path for consistency
            if "path" in kwargs:
                resolved_path = self._validate_path(kwargs["path"])
                kwargs["path"] = resolved_path

            # Validate name if being updated
            if "name" in kwargs and not kwargs["name"]:
                raise ZoneManagerError("Zone name cannot be empty")

            # Update allowed fields
            for key, value in kwargs.items():
                if key in allowed_fields:
                    zone[key] = value  # type: ignore[literal-required]

            self._save_zones()
            logger.info(f"Zone updated: {zone_id}")
            return True

    def get_enabled_zones(self) -> list[ZoneConfig]:
        """Get all enabled zones.

        Returns:
            A list of zone configurations where enabled is True.
        """
        with self._lock:
            return [zone for zone in self._zones.values() if zone["enabled"]]

    def zone_exists(self, zone_id: str) -> bool:
        """Check if a zone exists.

        Args:
            zone_id: The ID of the zone to check.

        Returns:
            True if the zone exists, False otherwise.
        """
        with self._lock:
            return zone_id in self._zones

    def clear_all_zones(self) -> None:
        """Remove all zones.

        Useful for testing or resetting configuration.
        """
        with self._lock:
            self._zones.clear()
            self._save_zones()
            logger.info("All zones cleared")
