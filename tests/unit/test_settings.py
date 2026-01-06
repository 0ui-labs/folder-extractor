"""
Unit tests for config/settings.py module.
"""

import json
from unittest.mock import MagicMock

from folder_extractor.config.settings import configure_from_args


class TestSettings:
    """Tests for Settings class."""

    def test_init(self, settings_fixture):
        """Test Settings initialization."""
        s = settings_fixture
        assert s._settings is not None
        assert "dry_run" in s._settings
        assert s._settings["dry_run"] is False

    def test_reset_to_defaults(self, settings_fixture):
        """Test reset_to_defaults method."""
        s = settings_fixture
        s.set("dry_run", True)
        s.set("max_depth", 10)
        s.reset_to_defaults()
        assert s.get("dry_run") is False
        assert s.get("max_depth") == 0

    def test_get(self, settings_fixture):
        """Test get method."""
        s = settings_fixture
        assert s.get("dry_run") is False
        assert s.get("nonexistent") is None
        assert s.get("nonexistent", "default") == "default"

    def test_set(self, settings_fixture):
        """Test set method."""
        s = settings_fixture
        s.set("dry_run", True)
        assert s._settings["dry_run"] is True

    def test_update(self, settings_fixture):
        """Test update method."""
        s = settings_fixture
        s.update({"dry_run": True, "max_depth": 5})
        assert s.get("dry_run") is True
        assert s.get("max_depth") == 5

    def test_to_dict(self, settings_fixture):
        """Test to_dict method."""
        s = settings_fixture
        s.set("dry_run", True)
        result = s.to_dict()
        assert isinstance(result, dict)
        assert result["dry_run"] is True
        # Should be a copy
        result["dry_run"] = False
        assert s.get("dry_run") is True

    def test_from_dict(self, settings_fixture):
        """Test from_dict method."""
        s = settings_fixture
        s.from_dict({"dry_run": True, "max_depth": 10})
        assert s.get("dry_run") is True
        assert s.get("max_depth") == 10

    def test_save_to_file(self, settings_fixture, tmp_path):
        """Test save_to_file method."""
        s = settings_fixture
        s.set("dry_run", True)
        s.set("max_depth", 5)

        filepath = tmp_path / "settings.json"
        s.save_to_file(filepath)

        assert filepath.exists()
        with open(filepath) as f:
            saved = json.load(f)
        assert saved["dry_run"] is True
        assert saved["max_depth"] == 5

    def test_load_from_file(self, settings_fixture, tmp_path):
        """Test load_from_file method."""
        filepath = tmp_path / "settings.json"
        test_settings = {"dry_run": True, "max_depth": 10}
        with open(filepath, "w") as f:
            json.dump(test_settings, f)

        s = settings_fixture
        s.load_from_file(filepath)

        assert s.get("dry_run") is True
        assert s.get("max_depth") == 10

    def test_load_from_file_nonexistent(self, settings_fixture, tmp_path):
        """Test load_from_file with nonexistent file."""
        filepath = tmp_path / "nonexistent.json"
        s = settings_fixture
        original = s.to_dict()
        s.load_from_file(filepath)
        # Should not change settings
        assert s.to_dict() == original

    # Property tests
    def test_dry_run_property(self, settings_fixture):
        """Test dry_run property."""
        s = settings_fixture
        assert s.dry_run is False
        s.set("dry_run", True)
        assert s.dry_run is True

    def test_max_depth_property(self, settings_fixture):
        """Test max_depth property."""
        s = settings_fixture
        assert s.max_depth == 0
        s.set("max_depth", 5)
        assert s.max_depth == 5

    def test_include_hidden_property(self, settings_fixture):
        """Test include_hidden property."""
        s = settings_fixture
        assert s.include_hidden is False
        s.set("include_hidden", True)
        assert s.include_hidden is True

    def test_sort_by_type_property(self, settings_fixture):
        """Test sort_by_type property."""
        s = settings_fixture
        assert s.sort_by_type is False
        s.set("sort_by_type", True)
        assert s.sort_by_type is True

    def test_file_type_filter_property(self, settings_fixture):
        """Test file_type_filter property."""
        s = settings_fixture
        assert s.file_type_filter is None
        s.set("file_type_filter", ["pdf", "txt"])
        assert s.file_type_filter == ["pdf", "txt"]

    def test_domain_filter_property(self, settings_fixture):
        """Test domain_filter property."""
        s = settings_fixture
        assert s.domain_filter is None
        s.set("domain_filter", ["example.com"])
        assert s.domain_filter == ["example.com"]

    def test_deduplicate_property(self, settings_fixture):
        """Test deduplicate property."""
        s = settings_fixture
        assert s.deduplicate is False
        s.set("deduplicate", True)
        assert s.deduplicate is True

    def test_global_dedup_property(self, settings_fixture):
        """Test global_dedup property enables content dedup across entire destination."""
        s = settings_fixture
        assert s.global_dedup is False
        s.set("global_dedup", True)
        assert s.global_dedup is True

    def test_custom_categories_property(self, settings_fixture):
        """Test custom_categories property returns user-defined category list."""
        s = settings_fixture
        assert s.custom_categories == []
        s.set("custom_categories", ["Kategorie1", "Kategorie2"])
        assert s.custom_categories == ["Kategorie1", "Kategorie2"]

    def test_watch_mode_defaults_to_false(self, settings_fixture):
        """Test watch_mode property defaults to False for normal extraction mode."""
        s = settings_fixture
        assert s.watch_mode is False

    def test_watch_mode_can_be_enabled(self, settings_fixture):
        """Test watch_mode property can be enabled for continuous monitoring."""
        s = settings_fixture
        s.set("watch_mode", True)
        assert s.watch_mode is True

    def test_to_dict_includes_custom_categories(self, settings_fixture):
        """Test that to_dict includes custom_categories for serialization."""
        s = settings_fixture
        s.set("custom_categories", ["Cat1", "Cat2"])
        result = s.to_dict()
        assert "custom_categories" in result
        assert result["custom_categories"] == ["Cat1", "Cat2"]

    def test_from_dict_loads_custom_categories(self, settings_fixture):
        """Test that from_dict restores custom_categories from saved state."""
        s = settings_fixture
        s.from_dict({"custom_categories": ["Cat1", "Cat2"], "dry_run": True})
        assert s.custom_categories == ["Cat1", "Cat2"]
        assert s.dry_run is True


class TestConfigureFromArgs:
    """Tests for configure_from_args function."""

    def test_basic_args(self, settings_fixture):
        """Test basic argument configuration."""
        args = MagicMock()
        args.dry_run = True
        args.depth = 5
        args.include_hidden = True
        args.sort_by_type = True
        args.type = None
        args.domain = None

        configure_from_args(settings_fixture, args)

        assert settings_fixture.get("dry_run") is True
        assert settings_fixture.get("max_depth") == 5
        assert settings_fixture.get("include_hidden") is True
        assert settings_fixture.get("sort_by_type") is True

    def test_with_type_filter(self, settings_fixture):
        """Test configuration with type filter."""
        args = MagicMock()
        args.dry_run = False
        args.depth = 0
        args.include_hidden = False
        args.sort_by_type = False
        args.type = "pdf,txt"
        args.domain = None

        configure_from_args(settings_fixture, args)

        # Parser returns extensions with dots
        assert settings_fixture.get("file_type_filter") == [".pdf", ".txt"]

    def test_with_domain_filter(self, settings_fixture):
        """Test configuration with domain filter."""
        args = MagicMock()
        args.dry_run = False
        args.depth = 0
        args.include_hidden = False
        args.sort_by_type = False
        args.type = None
        args.domain = "example.com,test.org"

        configure_from_args(settings_fixture, args)

        assert settings_fixture.get("domain_filter") == ["example.com", "test.org"]

    def test_with_all_filters(self, settings_fixture):
        """Test configuration with all filters."""
        args = MagicMock()
        args.dry_run = True
        args.depth = 3
        args.include_hidden = True
        args.sort_by_type = True
        args.type = "pdf"
        args.domain = "example.com"
        args.deduplicate = False

        configure_from_args(settings_fixture, args)

        assert settings_fixture.get("dry_run") is True
        assert settings_fixture.get("max_depth") == 3
        assert settings_fixture.get("include_hidden") is True
        assert settings_fixture.get("sort_by_type") is True
        # Parser returns extensions with dots
        assert settings_fixture.get("file_type_filter") == [".pdf"]
        assert settings_fixture.get("domain_filter") == ["example.com"]

    def test_with_deduplicate_flag(self, settings_fixture):
        """Test configuration with deduplicate flag enabled."""
        args = MagicMock()
        args.dry_run = False
        args.depth = 0
        args.include_hidden = False
        args.sort_by_type = False
        args.type = None
        args.domain = None
        args.deduplicate = True
        args.global_dedup = False

        configure_from_args(settings_fixture, args)

        assert settings_fixture.get("deduplicate") is True

    def test_with_global_dedup_flag(self, settings_fixture):
        """Test configuration with global_dedup flag enables tree-wide content dedup."""
        args = MagicMock()
        args.dry_run = False
        args.depth = 0
        args.include_hidden = False
        args.sort_by_type = False
        args.type = None
        args.domain = None
        args.deduplicate = False
        args.global_dedup = True

        configure_from_args(settings_fixture, args)

        assert settings_fixture.get("global_dedup") is True

    def test_with_both_dedup_flags(self, settings_fixture):
        """Test configuration with both dedup flags enabled together."""
        args = MagicMock()
        args.dry_run = False
        args.depth = 0
        args.include_hidden = False
        args.sort_by_type = False
        args.type = None
        args.domain = None
        args.deduplicate = True
        args.global_dedup = True

        configure_from_args(settings_fixture, args)

        assert settings_fixture.get("deduplicate") is True
        assert settings_fixture.get("global_dedup") is True

    def test_with_extract_archives_flag(self, settings_fixture):
        """Test configuration with extract_archives flag enabled."""
        args = MagicMock()
        args.dry_run = False
        args.depth = 0
        args.include_hidden = False
        args.sort_by_type = False
        args.type = None
        args.domain = None
        args.deduplicate = False
        args.global_dedup = False
        args.extract_archives = True
        args.delete_archives = False

        configure_from_args(settings_fixture, args)

        assert settings_fixture.get("extract_archives") is True
        assert settings_fixture.get("delete_archives") is False

    def test_delete_archives_ignored_without_extract_archives(self, settings_fixture):
        """Test that delete_archives is ignored when extract_archives is False.

        The --delete-archives flag only makes sense in combination with
        --extract-archives. If a user specifies --delete-archives without
        --extract-archives, delete_archives should be set to False.
        """
        args = MagicMock()
        args.dry_run = False
        args.depth = 0
        args.include_hidden = False
        args.sort_by_type = False
        args.type = None
        args.domain = None
        args.deduplicate = False
        args.global_dedup = False
        args.extract_archives = False  # extract_archives is OFF
        args.delete_archives = True  # but delete_archives is requested

        configure_from_args(settings_fixture, args)

        # delete_archives should be False because extract_archives is False
        assert settings_fixture.get("extract_archives") is False
        assert settings_fixture.get("delete_archives") is False

    def test_with_both_archive_flags(self, settings_fixture):
        """Test configuration with both archive flags enabled together."""
        args = MagicMock()
        args.dry_run = False
        args.depth = 0
        args.include_hidden = False
        args.sort_by_type = False
        args.type = None
        args.domain = None
        args.deduplicate = False
        args.global_dedup = False
        args.extract_archives = True
        args.delete_archives = True

        configure_from_args(settings_fixture, args)

        assert settings_fixture.get("extract_archives") is True
        assert settings_fixture.get("delete_archives") is True

    def test_watch_mode_from_args_when_enabled(self, settings_fixture):
        """Test configure_from_args sets watch_mode True when --watch flag is set."""
        args = MagicMock()
        args.dry_run = False
        args.depth = 0
        args.include_hidden = False
        args.sort_by_type = False
        args.type = None
        args.domain = None
        args.deduplicate = False
        args.global_dedup = False
        args.extract_archives = False
        args.delete_archives = False
        args.watch = True

        configure_from_args(settings_fixture, args)

        assert settings_fixture.get("watch_mode") is True

    def test_watch_mode_from_args_when_disabled(self, settings_fixture):
        """Test configure_from_args sets watch_mode False when --watch flag is not set."""
        args = MagicMock()
        args.dry_run = False
        args.depth = 0
        args.include_hidden = False
        args.sort_by_type = False
        args.type = None
        args.domain = None
        args.deduplicate = False
        args.global_dedup = False
        args.extract_archives = False
        args.delete_archives = False
        args.watch = False

        configure_from_args(settings_fixture, args)

        assert settings_fixture.get("watch_mode") is False

    def test_watch_mode_from_args_defaults_to_false_when_missing(
        self, settings_fixture
    ):
        """Test configure_from_args defaults watch_mode to False when args.watch is missing."""
        args = MagicMock(
            spec=[
                "dry_run",
                "depth",
                "include_hidden",
                "sort_by_type",
                "type",
                "domain",
                "deduplicate",
                "global_dedup",
                "extract_archives",
                "delete_archives",
            ]
        )
        args.dry_run = False
        args.depth = 0
        args.include_hidden = False
        args.sort_by_type = False
        args.type = None
        args.domain = None
        args.deduplicate = False
        args.global_dedup = False
        args.extract_archives = False
        args.delete_archives = False
        # Note: args.watch is NOT set (missing attribute)

        configure_from_args(settings_fixture, args)

        assert settings_fixture.get("watch_mode") is False


class TestSettingsArchiveProperties:
    """Tests for archive-related Settings properties."""

    def test_extract_archives_property_default_is_false(self, settings_fixture):
        """Test extract_archives property defaults to False."""
        s = settings_fixture
        assert s.extract_archives is False

    def test_extract_archives_property_reflects_set_value(self, settings_fixture):
        """Test extract_archives property reflects the set value."""
        s = settings_fixture
        s.set("extract_archives", True)
        assert s.extract_archives is True

    def test_delete_archives_property_default_is_false(self, settings_fixture):
        """Test delete_archives property defaults to False."""
        s = settings_fixture
        assert s.delete_archives is False

    def test_delete_archives_property_reflects_set_value(self, settings_fixture):
        """Test delete_archives property reflects the set value."""
        s = settings_fixture
        s.set("delete_archives", True)
        assert s.delete_archives is True


class TestGetAllCategories:
    """Tests for get_all_categories function."""

    def test_default_categories_only(self, settings_fixture):
        """When no custom categories defined, returns default categories."""
        from folder_extractor.config.constants import DEFAULT_CATEGORIES
        from folder_extractor.config.settings import get_all_categories

        # Workaround: get_all_categories() uses global settings internally
        result = get_all_categories(settings_fixture)
        assert result == DEFAULT_CATEGORIES

    def test_custom_categories_prepended_to_defaults(self, settings_fixture):
        """Custom categories appear first, followed by defaults."""
        from folder_extractor.config.constants import DEFAULT_CATEGORIES
        from folder_extractor.config.settings import get_all_categories

        settings_fixture.set("custom_categories", ["Custom1", "Custom2"])
        result = get_all_categories(settings_fixture)

        assert result[:2] == ["Custom1", "Custom2"]
        assert "Finanzen" in result
        assert len(result) == len(DEFAULT_CATEGORIES) + 2

    def test_custom_category_overrides_duplicate_default(self, settings_fixture):
        """When custom category matches a default, it appears only once (from custom)."""
        from folder_extractor.config.settings import get_all_categories

        settings_fixture.set("custom_categories", ["Finanzen", "Custom1"])
        result = get_all_categories(settings_fixture)

        # "Finanzen" should appear only once (from custom position)
        assert result.count("Finanzen") == 1
        assert result[0] == "Finanzen"
        assert "Custom1" in result

    def test_empty_custom_categories_returns_defaults(self, settings_fixture):
        """Explicitly empty custom categories returns only defaults."""
        from folder_extractor.config.constants import DEFAULT_CATEGORIES
        from folder_extractor.config.settings import get_all_categories

        settings_fixture.set("custom_categories", [])
        result = get_all_categories(settings_fixture)
        assert result == DEFAULT_CATEGORIES

    def test_all_defaults_overridden_preserves_custom_order(self, settings_fixture):
        """When all custom categories match defaults, custom order is preserved."""
        from folder_extractor.config.constants import DEFAULT_CATEGORIES
        from folder_extractor.config.settings import get_all_categories

        # Reverse order of defaults
        reversed_defaults = list(reversed(DEFAULT_CATEGORIES))
        settings_fixture.set("custom_categories", reversed_defaults)
        result = get_all_categories(settings_fixture)

        # Should have same length (no duplicates)
        assert len(result) == len(DEFAULT_CATEGORIES)
        # Should be in reversed order
        assert result == reversed_defaults
