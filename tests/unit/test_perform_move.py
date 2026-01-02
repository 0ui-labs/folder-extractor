"""
Unit tests for FileMover._perform_move() method.

TDD tests written FIRST before implementation.
Tests the new private helper method that extracts common move logic
from move_files() and move_files_sorted().
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from folder_extractor.core.file_operations import (
    FileMover,
    FileOperationError,
    FileOperations,
)


class TestPerformMove:
    """Test FileMover._perform_move() method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.file_ops = FileOperations()
        self.file_mover = FileMover(self.file_ops)

    def test_perform_move_success_creates_history_entry(self, monkeypatch):
        """Successful move creates proper history entry with all required fields.

        When a file is successfully moved, _perform_move should return:
        - success=True
        - renamed=False (when name unchanged)
        - history_entry with original_pfad, neuer_pfad, original_name, neuer_name, zeitstempel
        """
        # Freeze time for deterministic test
        fixed_time = "2024-06-15T10:30:00"
        monkeypatch.setattr(
            "folder_extractor.core.file_operations.datetime",
            MagicMock(
                now=MagicMock(
                    return_value=MagicMock(isoformat=MagicMock(return_value=fixed_time))
                )
            ),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            # Create source file
            source_file = source_dir / "document.txt"
            source_file.write_text("file content")

            # Execute the method
            success, renamed, history_entry = self.file_mover._perform_move(
                source_path=source_file,
                dest_path=dest_dir,
                filename="document.txt",
                dry_run=False,
                hash_index=None,
            )

            # Verify results
            assert success is True
            assert renamed is False
            assert history_entry is not None

            # Verify history entry structure
            assert history_entry["original_pfad"] == str(source_file)
            assert history_entry["neuer_pfad"] == str(dest_dir / "document.txt")
            assert history_entry["original_name"] == "document.txt"
            assert history_entry["neuer_name"] == "document.txt"
            assert history_entry["zeitstempel"] == fixed_time

            # Verify file was actually moved
            assert not source_file.exists()
            assert (dest_dir / "document.txt").exists()

    def test_perform_move_dry_run_returns_none_history(self):
        """Dry run returns success but no history entry.

        When dry_run=True, the method should:
        - Return success=True (simulated)
        - Return renamed appropriately
        - Return history_entry=None (nothing to record)
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            # Create source file
            source_file = source_dir / "document.txt"
            source_file.write_text("file content")

            # Execute the method with dry_run=True
            success, renamed, history_entry = self.file_mover._perform_move(
                source_path=source_file,
                dest_path=dest_dir,
                filename="document.txt",
                dry_run=True,
                hash_index=None,
            )

            # Verify results
            assert success is True
            assert renamed is False
            assert history_entry is None

            # Verify file was NOT moved (dry run)
            assert source_file.exists()
            assert not (dest_dir / "document.txt").exists()

    def test_perform_move_renamed_returns_true_when_name_changed(self):
        """Renamed flag is True when unique_name differs from original filename.

        When a file with the same name already exists at destination,
        generate_unique_name returns a different name, and renamed should be True.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            # Create existing file at destination (triggers rename)
            (dest_dir / "conflict.txt").write_text("existing content")

            # Create source file with same name
            source_file = source_dir / "conflict.txt"
            source_file.write_text("new content")

            # Execute the method
            success, renamed, history_entry = self.file_mover._perform_move(
                source_path=source_file,
                dest_path=dest_dir,
                filename="conflict.txt",
                dry_run=False,
                hash_index=None,
            )

            # Verify results
            assert success is True
            assert renamed is True  # Name was changed due to conflict
            assert history_entry is not None

            # Verify the new name
            assert history_entry["original_name"] == "conflict.txt"
            assert history_entry["neuer_name"] == "conflict_1.txt"
            assert (dest_dir / "conflict_1.txt").exists()

    def test_perform_move_failure_returns_false(self):
        """When move_file fails, returns (False, False, None).

        If the underlying move operation fails (e.g., permission error),
        the method should return failure indicators.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            source_file = source_dir / "document.txt"
            source_file.write_text("content")

            # Mock move_file to fail
            with patch.object(self.file_ops, "move_file", return_value=False):
                success, renamed, history_entry = self.file_mover._perform_move(
                    source_path=source_file,
                    dest_path=dest_dir,
                    filename="document.txt",
                    dry_run=False,
                    hash_index=None,
                )

            # Verify failure results
            assert success is False
            assert renamed is False
            assert history_entry is None

    def test_perform_move_updates_hash_index_when_provided(self):
        """Hash index is updated after successful move when provided.

        When hash_index is not None and dry_run is False, the method should:
        1. Calculate the hash of the moved file
        2. Add the file path to the hash_index under its hash key
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            # Create source file with known content
            source_file = source_dir / "hashable.txt"
            file_content = "content for hashing"
            source_file.write_text(file_content)

            # Start with empty hash index
            hash_index = {}

            # Execute the method
            success, renamed, history_entry = self.file_mover._perform_move(
                source_path=source_file,
                dest_path=dest_dir,
                filename="hashable.txt",
                dry_run=False,
                hash_index=hash_index,
            )

            # Verify results
            assert success is True

            # Verify hash index was updated
            assert len(hash_index) == 1

            # Get the hash that was added
            added_hash = list(hash_index.keys())[0]
            assert len(added_hash) == 64  # SHA256 hex digest length

            # Verify the path was added correctly
            added_paths = hash_index[added_hash]
            assert len(added_paths) == 1
            assert added_paths[0] == dest_dir / "hashable.txt"

    def test_perform_move_handles_hash_calculation_error_gracefully(self):
        """FileOperationError during hash calculation is caught silently.

        If hash calculation fails after a successful move, the operation
        should still succeed - the hash index just won't be updated.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            source_file = source_dir / "document.txt"
            source_file.write_text("content")

            hash_index = {}

            # Mock calculate_file_hash to raise FileOperationError
            with patch.object(
                self.file_ops,
                "calculate_file_hash",
                side_effect=FileOperationError("Hash calculation failed"),
            ):
                success, renamed, history_entry = self.file_mover._perform_move(
                    source_path=source_file,
                    dest_path=dest_dir,
                    filename="document.txt",
                    dry_run=False,
                    hash_index=hash_index,
                )

            # Verify the move still succeeded
            assert success is True
            assert renamed is False
            assert history_entry is not None

            # Hash index should remain empty (error was caught)
            assert len(hash_index) == 0

            # File should still be moved
            assert (dest_dir / "document.txt").exists()

    def test_perform_move_does_not_update_hash_index_on_dry_run(self):
        """Hash index is not updated during dry run even if provided.

        When dry_run=True, no hash calculation should occur.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            source_file = source_dir / "document.txt"
            source_file.write_text("content")

            hash_index = {}

            # Execute with dry_run=True
            success, renamed, history_entry = self.file_mover._perform_move(
                source_path=source_file,
                dest_path=dest_dir,
                filename="document.txt",
                dry_run=True,
                hash_index=hash_index,
            )

            # Verify hash index was NOT updated
            assert len(hash_index) == 0

    def test_perform_move_appends_to_existing_hash_index_entry(self):
        """When hash already exists in index, path is appended to list.

        If another file with the same hash is already in the index,
        the new path should be appended to the existing list.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            dest_dir = temp_path / "dest"
            dest_dir.mkdir()

            # Create source file
            source_file = source_dir / "new_file.txt"
            file_content = "identical content"
            source_file.write_text(file_content)

            # Pre-populate hash index with existing entry
            existing_file = dest_dir / "existing_file.txt"
            existing_file.write_text(file_content)
            existing_hash = self.file_ops.calculate_file_hash(existing_file)
            hash_index = {existing_hash: [existing_file]}

            # Execute the method
            success, renamed, history_entry = self.file_mover._perform_move(
                source_path=source_file,
                dest_path=dest_dir,
                filename="new_file.txt",
                dry_run=False,
                hash_index=hash_index,
            )

            # Verify results
            assert success is True

            # Verify the path was appended (not replaced)
            assert len(hash_index) == 1
            assert len(hash_index[existing_hash]) == 2
            assert existing_file in hash_index[existing_hash]
            assert (dest_dir / "new_file.txt") in hash_index[existing_hash]
