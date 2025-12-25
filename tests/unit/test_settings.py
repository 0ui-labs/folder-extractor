"""
Unit tests for config/settings.py module.
"""

import json
from unittest.mock import MagicMock

from folder_extractor.config.settings import Settings, configure_from_args, settings


class TestSettings:
    """Tests for Settings class."""

    def setup_method(self):
        """Reset settings before each test."""
        settings.reset_to_defaults()

    def test_init(self):
        """Test Settings initialization."""
        s = Settings()
        assert s._settings is not None
        assert "dry_run" in s._settings
        assert s._settings["dry_run"] is False

    def test_reset_to_defaults(self):
        """Test reset_to_defaults method."""
        s = Settings()
        s.set("dry_run", True)
        s.set("max_depth", 10)
        s.reset_to_defaults()
        assert s.get("dry_run") is False
        assert s.get("max_depth") == 0

    def test_get(self):
        """Test get method."""
        s = Settings()
        assert s.get("dry_run") is False
        assert s.get("nonexistent") is None
        assert s.get("nonexistent", "default") == "default"

    def test_set(self):
        """Test set method."""
        s = Settings()
        s.set("dry_run", True)
        assert s._settings["dry_run"] is True

    def test_update(self):
        """Test update method."""
        s = Settings()
        s.update({"dry_run": True, "max_depth": 5})
        assert s.get("dry_run") is True
        assert s.get("max_depth") == 5

    def test_to_dict(self):
        """Test to_dict method."""
        s = Settings()
        s.set("dry_run", True)
        result = s.to_dict()
        assert isinstance(result, dict)
        assert result["dry_run"] is True
        # Should be a copy
        result["dry_run"] = False
        assert s.get("dry_run") is True

    def test_from_dict(self):
        """Test from_dict method."""
        s = Settings()
        s.from_dict({"dry_run": True, "max_depth": 10})
        assert s.get("dry_run") is True
        assert s.get("max_depth") == 10

    def test_save_to_file(self, tmp_path):
        """Test save_to_file method."""
        s = Settings()
        s.set("dry_run", True)
        s.set("max_depth", 5)

        filepath = tmp_path / "settings.json"
        s.save_to_file(filepath)

        assert filepath.exists()
        with open(filepath) as f:
            saved = json.load(f)
        assert saved["dry_run"] is True
        assert saved["max_depth"] == 5

    def test_load_from_file(self, tmp_path):
        """Test load_from_file method."""
        filepath = tmp_path / "settings.json"
        test_settings = {"dry_run": True, "max_depth": 10}
        with open(filepath, "w") as f:
            json.dump(test_settings, f)

        s = Settings()
        s.load_from_file(filepath)

        assert s.get("dry_run") is True
        assert s.get("max_depth") == 10

    def test_load_from_file_nonexistent(self, tmp_path):
        """Test load_from_file with nonexistent file."""
        filepath = tmp_path / "nonexistent.json"
        s = Settings()
        original = s.to_dict()
        s.load_from_file(filepath)
        # Should not change settings
        assert s.to_dict() == original

    # Property tests
    def test_dry_run_property(self):
        """Test dry_run property."""
        s = Settings()
        assert s.dry_run is False
        s.set("dry_run", True)
        assert s.dry_run is True

    def test_max_depth_property(self):
        """Test max_depth property."""
        s = Settings()
        assert s.max_depth == 0
        s.set("max_depth", 5)
        assert s.max_depth == 5

    def test_include_hidden_property(self):
        """Test include_hidden property."""
        s = Settings()
        assert s.include_hidden is False
        s.set("include_hidden", True)
        assert s.include_hidden is True

    def test_sort_by_type_property(self):
        """Test sort_by_type property."""
        s = Settings()
        assert s.sort_by_type is False
        s.set("sort_by_type", True)
        assert s.sort_by_type is True

    def test_file_type_filter_property(self):
        """Test file_type_filter property."""
        s = Settings()
        assert s.file_type_filter is None
        s.set("file_type_filter", ["pdf", "txt"])
        assert s.file_type_filter == ["pdf", "txt"]

    def test_domain_filter_property(self):
        """Test domain_filter property."""
        s = Settings()
        assert s.domain_filter is None
        s.set("domain_filter", ["example.com"])
        assert s.domain_filter == ["example.com"]

    def test_deduplicate_property(self):
        """Test deduplicate property."""
        s = Settings()
        assert s.deduplicate is False
        s.set("deduplicate", True)
        assert s.deduplicate is True

    def test_global_dedup_property(self):
        """Test global_dedup property enables content dedup across entire destination."""
        s = Settings()
        assert s.global_dedup is False
        s.set("global_dedup", True)
        assert s.global_dedup is True


class TestGlobalSettings:
    """Tests for global settings instance."""

    def setup_method(self):
        """Reset settings before each test."""
        settings.reset_to_defaults()

    def test_global_instance_exists(self):
        """Test global settings instance exists."""
        assert settings is not None
        assert isinstance(settings, Settings)

    def test_global_instance_persistence(self):
        """Test global instance persists changes."""
        settings.set("dry_run", True)
        from folder_extractor.config.settings import settings as settings2

        assert settings2.get("dry_run") is True


class TestConfigureFromArgs:
    """Tests for configure_from_args function."""

    def setup_method(self):
        """Reset settings before each test."""
        settings.reset_to_defaults()

    def test_basic_args(self):
        """Test basic argument configuration."""
        args = MagicMock()
        args.dry_run = True
        args.depth = 5
        args.include_hidden = True
        args.sort_by_type = True
        args.type = None
        args.domain = None

        configure_from_args(args)

        assert settings.get("dry_run") is True
        assert settings.get("max_depth") == 5
        assert settings.get("include_hidden") is True
        assert settings.get("sort_by_type") is True

    def test_with_type_filter(self):
        """Test configuration with type filter."""
        args = MagicMock()
        args.dry_run = False
        args.depth = 0
        args.include_hidden = False
        args.sort_by_type = False
        args.type = "pdf,txt"
        args.domain = None

        configure_from_args(args)

        # Parser returns extensions with dots
        assert settings.get("file_type_filter") == [".pdf", ".txt"]

    def test_with_domain_filter(self):
        """Test configuration with domain filter."""
        args = MagicMock()
        args.dry_run = False
        args.depth = 0
        args.include_hidden = False
        args.sort_by_type = False
        args.type = None
        args.domain = "example.com,test.org"

        configure_from_args(args)

        assert settings.get("domain_filter") == ["example.com", "test.org"]

    def test_with_all_filters(self):
        """Test configuration with all filters."""
        args = MagicMock()
        args.dry_run = True
        args.depth = 3
        args.include_hidden = True
        args.sort_by_type = True
        args.type = "pdf"
        args.domain = "example.com"
        args.deduplicate = False

        configure_from_args(args)

        assert settings.get("dry_run") is True
        assert settings.get("max_depth") == 3
        assert settings.get("include_hidden") is True
        assert settings.get("sort_by_type") is True
        # Parser returns extensions with dots
        assert settings.get("file_type_filter") == [".pdf"]
        assert settings.get("domain_filter") == ["example.com"]

    def test_with_deduplicate_flag(self):
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

        configure_from_args(args)

        assert settings.get("deduplicate") is True

    def test_with_global_dedup_flag(self):
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

        configure_from_args(args)

        assert settings.get("global_dedup") is True

    def test_with_both_dedup_flags(self):
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

        configure_from_args(args)

        assert settings.get("deduplicate") is True
        assert settings.get("global_dedup") is True

    def test_with_extract_archives_flag(self):
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

        configure_from_args(args)

        assert settings.get("extract_archives") is True
        assert settings.get("delete_archives") is False

    def test_delete_archives_ignored_without_extract_archives(self):
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

        configure_from_args(args)

        # delete_archives should be False because extract_archives is False
        assert settings.get("extract_archives") is False
        assert settings.get("delete_archives") is False

    def test_with_both_archive_flags(self):
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

        configure_from_args(args)

        assert settings.get("extract_archives") is True
        assert settings.get("delete_archives") is True


class TestSettingsArchiveProperties:
    """Tests for archive-related Settings properties."""

    def setup_method(self):
        """Reset settings before each test."""
        settings.reset_to_defaults()

    def test_extract_archives_property_default_is_false(self):
        """Test extract_archives property defaults to False."""
        s = Settings()
        assert s.extract_archives is False

    def test_extract_archives_property_reflects_set_value(self):
        """Test extract_archives property reflects the set value."""
        s = Settings()
        s.set("extract_archives", True)
        assert s.extract_archives is True

    def test_delete_archives_property_default_is_false(self):
        """Test delete_archives property defaults to False."""
        s = Settings()
        assert s.delete_archives is False

    def test_delete_archives_property_reflects_set_value(self):
        """Test delete_archives property reflects the set value."""
        s = Settings()
        s.set("delete_archives", True)
        assert s.delete_archives is True
