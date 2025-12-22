"""
Unit tests for migration module.
"""

from unittest.mock import MagicMock, patch

from folder_extractor.config.settings import settings
from folder_extractor.core.migration import MigrationHelper


class TestMigrationHelper:
    """Tests for MigrationHelper class."""

    def setup_method(self):
        """Reset settings before each test."""
        settings.reset_to_defaults()

    def test_migrate_settings_transfers_deduplicate_to_state_manager(self):
        """Test that deduplicate setting is properly migrated to state manager."""
        # Arrange: Set deduplicate to True in settings
        settings.set("deduplicate", True)

        # Create a mock state manager to capture what values are passed
        mock_state_manager = MagicMock()

        with patch(
            "folder_extractor.core.migration.get_state_manager",
            return_value=mock_state_manager,
        ):
            # Act
            MigrationHelper.migrate_settings()

            # Assert: Check that update_values was called with deduplicate=True
            mock_state_manager.update_values.assert_called_once()
            call_args = mock_state_manager.update_values.call_args[0][0]

            assert "deduplicate" in call_args
            assert call_args["deduplicate"] is True

    def test_migrate_settings_default_deduplicate_is_false(self):
        """Test that deduplicate defaults to False when migrating."""
        # Arrange: Use default settings (deduplicate should be False)
        mock_state_manager = MagicMock()

        with patch(
            "folder_extractor.core.migration.get_state_manager",
            return_value=mock_state_manager,
        ):
            # Act
            MigrationHelper.migrate_settings()

            # Assert
            call_args = mock_state_manager.update_values.call_args[0][0]
            assert call_args["deduplicate"] is False

    def test_migrate_settings_includes_all_operation_settings(self):
        """Test that all operation settings are migrated to state manager."""
        # Arrange: Configure various settings
        settings.set("dry_run", True)
        settings.set("max_depth", 3)
        settings.set("include_hidden", True)
        settings.set("sort_by_type", True)
        settings.set("deduplicate", True)
        settings.set("file_type_filter", [".pdf"])
        settings.set("domain_filter", ["example.com"])

        mock_state_manager = MagicMock()

        with patch(
            "folder_extractor.core.migration.get_state_manager",
            return_value=mock_state_manager,
        ):
            # Act
            MigrationHelper.migrate_settings()

            # Assert: All settings should be present in the migrated values
            call_args = mock_state_manager.update_values.call_args[0][0]

            assert call_args["dry_run"] is True
            assert call_args["max_depth"] == 3
            assert call_args["include_hidden"] is True
            assert call_args["sort_by_type"] is True
            assert call_args["deduplicate"] is True
            assert call_args["file_type_filter"] == [".pdf"]
            assert call_args["domain_filter"] == ["example.com"]
