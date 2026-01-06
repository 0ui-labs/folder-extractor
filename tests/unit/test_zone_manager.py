"""
Tests for ZoneManager - Dropzone configuration management.

These tests define the expected behavior of the ZoneManager before
implementation (TDD approach).
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    from folder_extractor.core.zone_manager import ZoneManager


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """Create a temporary config directory."""
    config = tmp_path / "config"
    config.mkdir()
    return config


@pytest.fixture
def zone_path(tmp_path: Path) -> Path:
    """Create a temporary directory for zone path."""
    zone = tmp_path / "dropzone"
    zone.mkdir()
    return zone


@pytest.fixture
def zone_manager(config_dir: Path) -> ZoneManager:
    """Create a ZoneManager with temporary config directory."""
    from folder_extractor.core.zone_manager import ZoneManager

    with patch(
        "folder_extractor.core.zone_manager.get_config_dir",
        return_value=config_dir,
    ):
        return ZoneManager()


@pytest.fixture
def sample_zone_data(zone_path: Path) -> dict:
    """Return sample zone data for tests."""
    return {
        "name": "Downloads",
        "path": str(zone_path),
        "enabled": True,
        "auto_sort": False,
        "categories": [],
    }


# =============================================================================
# Test ZoneManager Initialization
# =============================================================================


class TestZoneManagerInit:
    """Tests for ZoneManager initialization."""

    def test_initializes_with_empty_zones(self, zone_manager: ZoneManager) -> None:
        """ZoneManager starts with no zones configured."""
        zones = zone_manager.list_zones()

        assert zones == []

    def test_creates_config_file_on_first_save(
        self, config_dir: Path, zone_path: Path
    ) -> None:
        """Config file is created when first zone is added."""
        from folder_extractor.core.zone_manager import ZoneManager

        with patch(
            "folder_extractor.core.zone_manager.get_config_dir",
            return_value=config_dir,
        ):
            manager = ZoneManager()
            manager.add_zone(name="Test", path=str(zone_path))

        config_file = config_dir / "zones.json"
        assert config_file.exists()


# =============================================================================
# Test CRUD Operations
# =============================================================================


class TestAddZone:
    """Tests for adding zones."""

    def test_add_zone_returns_uuid(
        self, zone_manager: ZoneManager, zone_path: Path
    ) -> None:
        """Adding a zone returns a valid UUID string."""
        zone_id = zone_manager.add_zone(name="Downloads", path=str(zone_path))

        assert zone_id is not None
        assert isinstance(zone_id, str)
        assert len(zone_id) == 36  # UUID format: 8-4-4-4-12

    def test_add_zone_stores_configuration(
        self, zone_manager: ZoneManager, zone_path: Path
    ) -> None:
        """Added zone can be retrieved with correct configuration."""
        zone_id = zone_manager.add_zone(
            name="Downloads",
            path=str(zone_path),
            enabled=True,
            auto_sort=True,
            categories=["pdf", "docx"],
        )

        zone = zone_manager.get_zone(zone_id)

        assert zone is not None
        assert zone["name"] == "Downloads"
        assert zone["path"] == str(zone_path)
        assert zone["enabled"] is True
        assert zone["auto_sort"] is True
        assert zone["categories"] == ["pdf", "docx"]

    def test_add_zone_with_defaults(
        self, zone_manager: ZoneManager, zone_path: Path
    ) -> None:
        """Zone uses default values when not specified."""
        zone_id = zone_manager.add_zone(name="Test", path=str(zone_path))

        zone = zone_manager.get_zone(zone_id)
        assert zone is not None

        assert zone["enabled"] is True
        assert zone["auto_sort"] is False
        assert zone["categories"] == []

    def test_add_zone_sets_created_at_timestamp(
        self, zone_manager: ZoneManager, zone_path: Path
    ) -> None:
        """Adding a zone sets the created_at timestamp in ISO 8601 format."""
        from datetime import datetime

        zone_id = zone_manager.add_zone(name="Test", path=str(zone_path))

        zone = zone_manager.get_zone(zone_id)

        assert zone is not None
        assert "created_at" in zone
        # Verify it's a valid ISO 8601 timestamp
        created_at = datetime.fromisoformat(zone["created_at"])
        assert created_at is not None

    def test_add_zone_invalid_path_raises_error(
        self, zone_manager: ZoneManager
    ) -> None:
        """Adding a zone with non-existent path raises error."""
        from folder_extractor.core.zone_manager import ZoneManagerError

        with pytest.raises(ZoneManagerError, match="path"):
            zone_manager.add_zone(name="Test", path="/nonexistent/path/12345")


class TestRemoveZone:
    """Tests for removing zones."""

    def test_remove_existing_zone_returns_true(
        self, zone_manager: ZoneManager, zone_path: Path
    ) -> None:
        """Removing an existing zone returns True."""
        zone_id = zone_manager.add_zone(name="Test", path=str(zone_path))

        result = zone_manager.remove_zone(zone_id)

        assert result is True

    def test_remove_zone_deletes_from_storage(
        self, zone_manager: ZoneManager, zone_path: Path
    ) -> None:
        """Removed zone is no longer retrievable."""
        zone_id = zone_manager.add_zone(name="Test", path=str(zone_path))

        zone_manager.remove_zone(zone_id)

        assert zone_manager.get_zone(zone_id) is None
        assert zone_manager.zone_exists(zone_id) is False

    def test_remove_nonexistent_zone_returns_false(
        self, zone_manager: ZoneManager
    ) -> None:
        """Removing a non-existent zone returns False."""
        result = zone_manager.remove_zone("nonexistent-id")

        assert result is False


class TestGetZone:
    """Tests for retrieving zones."""

    def test_get_existing_zone(
        self, zone_manager: ZoneManager, zone_path: Path
    ) -> None:
        """Getting an existing zone returns its configuration."""
        zone_id = zone_manager.add_zone(name="Downloads", path=str(zone_path))

        zone = zone_manager.get_zone(zone_id)

        assert zone is not None
        assert zone["id"] == zone_id
        assert zone["name"] == "Downloads"

    def test_get_nonexistent_zone_returns_none(self, zone_manager: ZoneManager) -> None:
        """Getting a non-existent zone returns None."""
        zone = zone_manager.get_zone("nonexistent-id")

        assert zone is None


class TestListZones:
    """Tests for listing zones."""

    def test_list_zones_empty(self, zone_manager: ZoneManager) -> None:
        """Listing zones returns empty list when no zones exist."""
        zones = zone_manager.list_zones()

        assert zones == []

    def test_list_zones_returns_all(
        self, zone_manager: ZoneManager, tmp_path: Path
    ) -> None:
        """Listing zones returns all configured zones."""
        # Create two zone directories
        zone1 = tmp_path / "zone1"
        zone2 = tmp_path / "zone2"
        zone1.mkdir()
        zone2.mkdir()

        zone_manager.add_zone(name="Zone1", path=str(zone1))
        zone_manager.add_zone(name="Zone2", path=str(zone2))

        zones = zone_manager.list_zones()

        assert len(zones) == 2
        names = {z["name"] for z in zones}
        assert names == {"Zone1", "Zone2"}


class TestUpdateZone:
    """Tests for updating zones."""

    def test_update_zone_changes_fields(
        self, zone_manager: ZoneManager, zone_path: Path
    ) -> None:
        """Updating a zone changes the specified fields."""
        zone_id = zone_manager.add_zone(name="Original", path=str(zone_path))

        result = zone_manager.update_zone(zone_id, name="Updated", auto_sort=True)

        assert result is True
        zone = zone_manager.get_zone(zone_id)
        assert zone is not None

        assert zone["name"] == "Updated"
        assert zone["auto_sort"] is True

    def test_update_zone_preserves_unchanged_fields(
        self, zone_manager: ZoneManager, zone_path: Path
    ) -> None:
        """Updating a zone preserves fields not specified."""
        zone_id = zone_manager.add_zone(
            name="Test",
            path=str(zone_path),
            enabled=True,
            categories=["pdf"],
        )

        zone_manager.update_zone(zone_id, name="Updated")

        zone = zone_manager.get_zone(zone_id)
        assert zone is not None

        assert zone["enabled"] is True
        assert zone["categories"] == ["pdf"]

    def test_update_nonexistent_zone_returns_false(
        self, zone_manager: ZoneManager
    ) -> None:
        """Updating a non-existent zone returns False."""
        result = zone_manager.update_zone("nonexistent-id", name="Test")

        assert result is False

    def test_update_zone_with_invalid_path_raises_error(
        self, zone_manager: ZoneManager, zone_path: Path
    ) -> None:
        """Updating zone with non-existent path raises error."""
        from folder_extractor.core.zone_manager import ZoneManagerError

        zone_id = zone_manager.add_zone(name="Test", path=str(zone_path))

        with pytest.raises(ZoneManagerError, match="path"):
            zone_manager.update_zone(zone_id, path="/nonexistent/path/12345")


# =============================================================================
# Test Helper Methods
# =============================================================================


class TestHelperMethods:
    """Tests for helper methods."""

    def test_get_enabled_zones_filters_correctly(
        self, zone_manager: ZoneManager, tmp_path: Path
    ) -> None:
        """get_enabled_zones returns only enabled zones."""
        zone1 = tmp_path / "zone1"
        zone2 = tmp_path / "zone2"
        zone1.mkdir()
        zone2.mkdir()

        zone_manager.add_zone(name="Enabled", path=str(zone1), enabled=True)
        zone_manager.add_zone(name="Disabled", path=str(zone2), enabled=False)

        enabled = zone_manager.get_enabled_zones()

        assert len(enabled) == 1
        assert enabled[0]["name"] == "Enabled"

    def test_zone_exists_returns_true_for_existing(
        self, zone_manager: ZoneManager, zone_path: Path
    ) -> None:
        """zone_exists returns True for existing zones."""
        zone_id = zone_manager.add_zone(name="Test", path=str(zone_path))

        assert zone_manager.zone_exists(zone_id) is True

    def test_zone_exists_returns_false_for_nonexistent(
        self, zone_manager: ZoneManager
    ) -> None:
        """zone_exists returns False for non-existent zones."""
        assert zone_manager.zone_exists("nonexistent-id") is False

    def test_clear_all_zones_removes_all(
        self, zone_manager: ZoneManager, tmp_path: Path
    ) -> None:
        """clear_all_zones removes all configured zones."""
        zone1 = tmp_path / "zone1"
        zone2 = tmp_path / "zone2"
        zone1.mkdir()
        zone2.mkdir()

        zone_manager.add_zone(name="Zone1", path=str(zone1))
        zone_manager.add_zone(name="Zone2", path=str(zone2))

        zone_manager.clear_all_zones()

        assert zone_manager.list_zones() == []


# =============================================================================
# Test Persistence
# =============================================================================


class TestPersistence:
    """Tests for zone persistence."""

    def test_zones_persist_across_instances(
        self, config_dir: Path, zone_path: Path
    ) -> None:
        """Zones are loaded from file when new instance is created."""
        from folder_extractor.core.zone_manager import ZoneManager

        with patch(
            "folder_extractor.core.zone_manager.get_config_dir",
            return_value=config_dir,
        ):
            # Create zone with first instance
            manager1 = ZoneManager()
            zone_id = manager1.add_zone(name="Persistent", path=str(zone_path))

            # Create new instance
            manager2 = ZoneManager()
            zone = manager2.get_zone(zone_id)

        assert zone is not None
        assert zone["name"] == "Persistent"

    def test_zones_saved_as_valid_json(self, config_dir: Path, zone_path: Path) -> None:
        """Zones are saved as valid, readable JSON."""
        from folder_extractor.core.zone_manager import ZoneManager

        with patch(
            "folder_extractor.core.zone_manager.get_config_dir",
            return_value=config_dir,
        ):
            manager = ZoneManager()
            manager.add_zone(name="Test", path=str(zone_path))

        config_file = config_dir / "zones.json"
        content = json.loads(config_file.read_text(encoding="utf-8"))

        assert isinstance(content, dict)
        assert len(content) == 1

    def test_handles_corrupted_config_file(self, config_dir: Path) -> None:
        """ZoneManager handles corrupted config file gracefully."""
        from folder_extractor.core.zone_manager import ZoneManager

        # Create corrupted config file
        config_file = config_dir / "zones.json"
        config_file.write_text("{ invalid json }", encoding="utf-8")

        with patch(
            "folder_extractor.core.zone_manager.get_config_dir",
            return_value=config_dir,
        ):
            manager = ZoneManager()

        # Should start with empty zones after corrupted file
        assert manager.list_zones() == []

    def test_handles_missing_config_file(self, config_dir: Path) -> None:
        """ZoneManager handles missing config file gracefully."""
        from folder_extractor.core.zone_manager import ZoneManager

        with patch(
            "folder_extractor.core.zone_manager.get_config_dir",
            return_value=config_dir,
        ):
            manager = ZoneManager()

        assert manager.list_zones() == []


# =============================================================================
# Test Thread Safety
# =============================================================================


class TestThreadSafety:
    """Tests for thread-safe operations."""

    def test_concurrent_add_zone_is_safe(
        self, zone_manager: ZoneManager, tmp_path: Path
    ) -> None:
        """Multiple threads can add zones concurrently without data loss."""
        num_threads = 10
        results: list[str] = []
        errors: list[Exception] = []

        def add_zone(index: int) -> None:
            try:
                zone_dir = tmp_path / f"zone_{index}"
                zone_dir.mkdir(exist_ok=True)
                zone_id = zone_manager.add_zone(name=f"Zone{index}", path=str(zone_dir))
                results.append(zone_id)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=add_zone, args=(i,)) for i in range(num_threads)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == num_threads
        assert len(zone_manager.list_zones()) == num_threads


# =============================================================================
# Test Validation
# =============================================================================


class TestValidation:
    """Tests for input validation."""

    def test_validates_name_required(self, zone_manager: ZoneManager) -> None:
        """Zone name is required."""
        from folder_extractor.core.zone_manager import ZoneManagerError

        with pytest.raises((ZoneManagerError, TypeError)):
            zone_manager.add_zone(name="", path="/some/path")  # type: ignore

    def test_validates_path_required(self, zone_manager: ZoneManager) -> None:
        """Zone path is required."""
        from folder_extractor.core.zone_manager import ZoneManagerError

        with pytest.raises((ZoneManagerError, TypeError)):
            zone_manager.add_zone(name="Test", path="")  # type: ignore
