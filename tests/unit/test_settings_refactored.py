"""
Tests for refactored settings.py with explicit dependency injection.

These tests verify the new API where configure_from_args() and
get_all_categories() accept a Settings instance as parameter instead
of using a global singleton.
"""

from unittest.mock import MagicMock

from folder_extractor.config.settings import Settings, configure_from_args, get_all_categories


class TestConfigureFromArgsWithExplicitSettings:
    """Tests for configure_from_args with explicit Settings parameter."""

    def test_configure_from_args_accepts_settings_instance(self):
        """configure_from_args accepts Settings instance as first parameter."""
        settings_instance = Settings()
        args = MagicMock()
        args.dry_run = True
        args.depth = 5
        args.include_hidden = True
        args.sort_by_type = True
        args.deduplicate = False
        args.type = None
        args.domain = None

        # Should accept settings as first parameter
        configure_from_args(settings_instance, args)

        # Verify the passed instance was configured
        assert settings_instance.get("dry_run") is True
        assert settings_instance.get("max_depth") == 5
        assert settings_instance.get("include_hidden") is True

    def test_configure_from_args_does_not_affect_other_instances(self):
        """Configuring one Settings instance does not affect another."""
        settings1 = Settings()
        settings2 = Settings()

        args = MagicMock()
        args.dry_run = True
        args.depth = 10
        args.include_hidden = True
        args.sort_by_type = True
        args.deduplicate = False
        args.type = None
        args.domain = None

        # Configure only settings1
        configure_from_args(settings1, args)

        # settings1 should be configured
        assert settings1.get("dry_run") is True
        assert settings1.get("max_depth") == 10

        # settings2 should remain at defaults
        assert settings2.get("dry_run") is False
        assert settings2.get("max_depth") == 0

    def test_configure_from_args_with_all_options(self):
        """configure_from_args handles all argument types correctly."""
        settings_instance = Settings()
        args = MagicMock()
        args.dry_run = True
        args.depth = 3
        args.include_hidden = True
        args.sort_by_type = True
        args.deduplicate = True
        args.global_dedup = True
        args.type = "pdf,txt"
        args.domain = "example.com"
        args.extract_archives = True
        args.delete_archives = True
        args.watch = True

        configure_from_args(settings_instance, args)

        assert settings_instance.get("dry_run") is True
        assert settings_instance.get("max_depth") == 3
        assert settings_instance.get("include_hidden") is True
        assert settings_instance.get("sort_by_type") is True
        assert settings_instance.get("deduplicate") is True
        assert settings_instance.get("global_dedup") is True
        assert settings_instance.get("file_type_filter") == [".pdf", ".txt"]
        assert settings_instance.get("domain_filter") == ["example.com"]
        assert settings_instance.get("extract_archives") is True
        assert settings_instance.get("delete_archives") is True
        assert settings_instance.get("watch_mode") is True


class TestGetAllCategoriesWithExplicitSettings:
    """Tests for get_all_categories with explicit Settings parameter."""

    def test_get_all_categories_accepts_settings_instance(self):
        """get_all_categories accepts Settings instance as parameter."""
        from folder_extractor.config.constants import DEFAULT_CATEGORIES

        settings_instance = Settings()

        # Should accept settings as parameter
        result = get_all_categories(settings_instance)

        # Should return default categories when no custom ones defined
        assert result == DEFAULT_CATEGORIES

    def test_get_all_categories_uses_provided_instance_custom_categories(self):
        """get_all_categories uses custom categories from provided Settings instance."""
        settings_instance = Settings()
        settings_instance.set("custom_categories", ["Custom1", "Custom2"])

        result = get_all_categories(settings_instance)

        # Custom categories should be first
        assert result[:2] == ["Custom1", "Custom2"]
        assert "Finanzen" in result

    def test_get_all_categories_does_not_mix_instances(self):
        """get_all_categories reads from correct Settings instance."""
        settings1 = Settings()
        settings1.set("custom_categories", ["Settings1Category"])

        settings2 = Settings()
        settings2.set("custom_categories", ["Settings2Category"])

        result1 = get_all_categories(settings1)
        result2 = get_all_categories(settings2)

        # Each call should return categories from the correct instance
        assert result1[0] == "Settings1Category"
        assert "Settings2Category" not in result1

        assert result2[0] == "Settings2Category"
        assert "Settings1Category" not in result2

    def test_get_all_categories_handles_empty_custom_categories(self):
        """get_all_categories returns defaults when custom categories are empty."""
        from folder_extractor.config.constants import DEFAULT_CATEGORIES

        settings_instance = Settings()
        settings_instance.set("custom_categories", [])

        result = get_all_categories(settings_instance)

        assert result == DEFAULT_CATEGORIES
