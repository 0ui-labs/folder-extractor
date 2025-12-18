"""
Migration utilities for transitioning to new architecture.

Provides utilities to ensure settings are properly migrated to the
new state management system.
"""

from folder_extractor.core.state_manager import (
    get_state_manager
)


class MigrationHelper:
    """Helper class for migrating to new architecture."""

    @staticmethod
    def migrate_settings() -> None:
        """Migrate settings to new state manager."""
        state_manager = get_state_manager()

        # Copy relevant settings to state manager
        from folder_extractor.config.settings import settings

        state_values = {
            "dry_run": settings.get("dry_run", False),
            "max_depth": settings.get("max_depth", 0),
            "include_hidden": settings.get("include_hidden", False),
            "sort_by_type": settings.get("sort_by_type", False),
            "file_type_filter": settings.get("file_type_filter"),
            "domain_filter": settings.get("domain_filter"),
        }

        state_manager.update_values(state_values)
