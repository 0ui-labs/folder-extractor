"""
Runtime settings and configuration management.

This module handles runtime configuration that can be modified
during execution, unlike constants which are fixed.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional


class Settings:
    """Runtime settings manager."""

    def __init__(self):
        """Initialize default settings."""
        self.reset_to_defaults()

    def reset_to_defaults(self):
        """Reset all settings to default values."""
        self._settings = {
            # Operation settings
            "dry_run": False,
            "max_depth": 0,
            "include_hidden": False,
            "sort_by_type": False,
            "deduplicate": False,
            "global_dedup": False,
            # Archive settings
            "extract_archives": False,
            "delete_archives": False,
            # Filtering
            "file_type_filter": None,
            "domain_filter": None,
            # Performance
            "batch_size": 100,
            "show_progress": True,
            "progress_update_interval": 0.1,
            # Safety
            "confirm_operations": True,
            "safe_mode": True,
            # Output
            "verbose": False,
            "quiet": False,
            "color_output": True,
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self._settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a setting value."""
        self._settings[key] = value

    def update(self, settings: Dict[str, Any]) -> None:
        """Update multiple settings at once."""
        self._settings.update(settings)

    def to_dict(self) -> Dict[str, Any]:
        """Export settings as dictionary."""
        return self._settings.copy()

    def from_dict(self, settings: Dict[str, Any]) -> None:
        """Import settings from dictionary."""
        self._settings = settings.copy()

    def save_to_file(self, filepath: Path) -> None:
        """Save settings to JSON file."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self._settings, f, indent=2)

    def load_from_file(self, filepath: Path) -> None:
        """Load settings from JSON file."""
        if filepath.exists():
            with open(filepath, encoding="utf-8") as f:
                self._settings = json.load(f)

    @property
    def dry_run(self) -> bool:
        return self._settings["dry_run"]

    @property
    def max_depth(self) -> int:
        return self._settings["max_depth"]

    @property
    def include_hidden(self) -> bool:
        return self._settings["include_hidden"]

    @property
    def sort_by_type(self) -> bool:
        return self._settings["sort_by_type"]

    @property
    def deduplicate(self) -> bool:
        return self._settings["deduplicate"]

    @property
    def global_dedup(self) -> bool:
        return self._settings["global_dedup"]

    @property
    def file_type_filter(self) -> Optional[list]:
        return self._settings["file_type_filter"]

    @property
    def domain_filter(self) -> Optional[list]:
        return self._settings["domain_filter"]

    @property
    def extract_archives(self) -> bool:
        return self._settings["extract_archives"]

    @property
    def delete_archives(self) -> bool:
        return self._settings["delete_archives"]


# Global settings instance
settings = Settings()


def configure_from_args(args) -> None:
    """Configure settings from command line arguments."""
    settings.set("dry_run", args.dry_run)
    settings.set("max_depth", args.depth)
    settings.set("include_hidden", args.include_hidden)
    settings.set("sort_by_type", args.sort_by_type)
    settings.set("deduplicate", args.deduplicate)
    settings.set("global_dedup", getattr(args, "global_dedup", False))

    # Parse filters
    if args.type:
        from folder_extractor.utils.parsers import parse_file_types

        settings.set("file_type_filter", parse_file_types(args.type))
        # Type filter implies sort-by-type (files go into type folders)
        settings.set("sort_by_type", True)

    if args.domain:
        from folder_extractor.utils.parsers import parse_domains

        settings.set("domain_filter", parse_domains(args.domain))

    # Archive settings
    extract_archives = getattr(args, "extract_archives", False)
    delete_archives = getattr(args, "delete_archives", False)

    settings.set("extract_archives", extract_archives)
    # delete_archives only makes sense with extract_archives enabled
    settings.set("delete_archives", delete_archives and extract_archives)
