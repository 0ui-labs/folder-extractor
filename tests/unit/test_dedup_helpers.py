"""
Tests for FileMover deduplication helper methods.

These tests verify the behavior of the private helper methods:
- _check_local_duplicate(): Handles same name + same content deduplication
- _check_global_duplicate(): Handles different name + same content deduplication

Following TDD principles, these tests document the expected behavior
of the helper methods before implementation.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Dict, List
from unittest.mock import Mock

import pytest

from folder_extractor.core.file_operations import (
    FileMover,
    FileOperations,
    FileOperationError,
)


class TestCheckLocalDuplicate:
    """Tests for _check_local_duplicate() helper method."""

    def test_returns_history_entry_when_hashes_match(self):
        """
        When source and destination have identical content (same hash),
        the method should return a history entry dict.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            # Create two files with identical content
            source = dest / "subdir" / "test.txt"
            source.parent.mkdir()
            source.write_text("identical content")

            existing_dest = dest / "test.txt"
            existing_dest.write_text("identical content")

            file_ops = FileOperations()
            file_mover = FileMover(file_ops)

            # Call helper method (dry_run=False)
            result = file_mover._check_local_duplicate(
                source_path=source,
                existing_dest=existing_dest,
                dry_run=False,
            )

            # Should return a history entry
            assert result is not None
            assert result["content_duplicate"] is True
            assert result["original_pfad"] == str(source)
            assert result["neuer_pfad"] == str(existing_dest)
            assert result["original_name"] == "test.txt"
            assert result["neuer_name"] == "test.txt"
            assert result["duplicate_of"] == str(existing_dest)
            assert "zeitstempel" in result

            # Source should be deleted
            assert not source.exists()

    def test_returns_none_when_hashes_differ(self):
        """
        When source and destination have different content,
        the method should return None (no duplicate).
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            source = dest / "subdir" / "test.txt"
            source.parent.mkdir()
            source.write_text("content A")

            existing_dest = dest / "test.txt"
            existing_dest.write_text("content B")

            file_ops = FileOperations()
            file_mover = FileMover(file_ops)

            result = file_mover._check_local_duplicate(
                source_path=source,
                existing_dest=existing_dest,
                dry_run=False,
            )

            # Should return None (not a duplicate)
            assert result is None

            # Source should NOT be deleted
            assert source.exists()

    def test_dry_run_does_not_delete_source(self):
        """
        In dry_run mode, the source file should not be deleted
        even when it's a duplicate.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            source = dest / "subdir" / "test.txt"
            source.parent.mkdir()
            source.write_text("identical content")

            existing_dest = dest / "test.txt"
            existing_dest.write_text("identical content")

            file_ops = FileOperations()
            file_mover = FileMover(file_ops)

            result = file_mover._check_local_duplicate(
                source_path=source,
                existing_dest=existing_dest,
                dry_run=True,
            )

            # Should still return history entry
            assert result is not None
            assert result["content_duplicate"] is True

            # But source should NOT be deleted in dry_run
            assert source.exists()

    def test_returns_none_when_dest_does_not_exist(self):
        """
        When the destination file doesn't exist,
        the method should return None.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            source = dest / "subdir" / "test.txt"
            source.parent.mkdir()
            source.write_text("some content")

            # No destination file exists
            existing_dest = dest / "test.txt"

            file_ops = FileOperations()
            file_mover = FileMover(file_ops)

            result = file_mover._check_local_duplicate(
                source_path=source,
                existing_dest=existing_dest,
                dry_run=False,
            )

            assert result is None
            assert source.exists()

    def test_returns_none_on_hash_error(self):
        """
        When hash calculation fails (e.g., permission error),
        the method should return None to allow fallback behavior.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            source = dest / "test.txt"
            source.write_text("content")

            existing_dest = dest / "existing.txt"
            existing_dest.write_text("content")

            # Mock file_ops to raise error on hash calculation
            mock_file_ops = Mock(spec=FileOperations)
            mock_file_ops.calculate_file_hash.side_effect = FileOperationError(
                "Hash calculation failed"
            )

            file_mover = FileMover(mock_file_ops)

            result = file_mover._check_local_duplicate(
                source_path=source,
                existing_dest=existing_dest,
                dry_run=False,
            )

            # Should return None (fallback to normal behavior)
            assert result is None


class TestCheckGlobalDuplicate:
    """Tests for _check_global_duplicate() helper method."""

    def test_returns_history_entry_when_hash_in_index(self):
        """
        When source file's hash exists in the index (pointing to a different file),
        the method should return a history entry dict.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            # Source file to check
            source = dest / "subdir" / "new_file.txt"
            source.parent.mkdir()
            source.write_text("shared content")

            # Existing file in destination with same content
            existing = dest / "original.txt"
            existing.write_text("shared content")

            file_ops = FileOperations()
            file_mover = FileMover(file_ops)

            # Build hash index
            file_hash = file_ops.calculate_file_hash(existing)
            hash_index: Dict[str, List[Path]] = {
                file_hash: [existing]
            }

            result = file_mover._check_global_duplicate(
                source_path=source,
                hash_index=hash_index,
                dry_run=False,
            )

            # Should return a history entry
            assert result is not None
            assert result["global_duplicate"] is True
            assert result["original_pfad"] == str(source)
            assert result["neuer_pfad"] == str(existing)
            assert result["original_name"] == "new_file.txt"
            assert result["neuer_name"] == "original.txt"
            assert result["duplicate_of"] == str(existing)
            assert "zeitstempel" in result

            # Source should be deleted
            assert not source.exists()

    def test_returns_none_when_hash_not_in_index(self):
        """
        When source file's hash is not in the index,
        the method should return None (no duplicate).
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            source = dest / "unique_file.txt"
            source.write_text("unique content")

            file_ops = FileOperations()
            file_mover = FileMover(file_ops)

            # Empty hash index
            hash_index: Dict[str, List[Path]] = {}

            result = file_mover._check_global_duplicate(
                source_path=source,
                hash_index=hash_index,
                dry_run=False,
            )

            assert result is None
            assert source.exists()

    def test_ignores_self_in_hash_index(self):
        """
        The method should not consider the source file itself as a duplicate,
        even if it's in the hash index.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            source = dest / "test.txt"
            source.write_text("some content")

            file_ops = FileOperations()
            file_mover = FileMover(file_ops)

            # Hash index contains only the source file itself
            file_hash = file_ops.calculate_file_hash(source)
            hash_index: Dict[str, List[Path]] = {
                file_hash: [source]
            }

            result = file_mover._check_global_duplicate(
                source_path=source,
                hash_index=hash_index,
                dry_run=False,
            )

            # Should return None (can't be duplicate of itself)
            assert result is None
            assert source.exists()

    def test_dry_run_does_not_delete_source(self):
        """
        In dry_run mode, the source file should not be deleted
        even when it's a global duplicate.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            source = dest / "subdir" / "copy.txt"
            source.parent.mkdir()
            source.write_text("shared content")

            existing = dest / "original.txt"
            existing.write_text("shared content")

            file_ops = FileOperations()
            file_mover = FileMover(file_ops)

            file_hash = file_ops.calculate_file_hash(existing)
            hash_index: Dict[str, List[Path]] = {
                file_hash: [existing]
            }

            result = file_mover._check_global_duplicate(
                source_path=source,
                hash_index=hash_index,
                dry_run=True,
            )

            # Should still return history entry
            assert result is not None
            assert result["global_duplicate"] is True

            # But source should NOT be deleted in dry_run
            assert source.exists()

    def test_returns_none_on_hash_error(self):
        """
        When hash calculation fails, the method should return None
        to allow fallback to normal move behavior.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            source = dest / "test.txt"
            source.write_text("content")

            # Mock file_ops to raise error
            mock_file_ops = Mock(spec=FileOperations)
            mock_file_ops.calculate_file_hash.side_effect = FileOperationError(
                "Hash error"
            )

            file_mover = FileMover(mock_file_ops)

            hash_index: Dict[str, List[Path]] = {"somehash": [Path("/some/file")]}

            result = file_mover._check_global_duplicate(
                source_path=source,
                hash_index=hash_index,
                dry_run=False,
            )

            assert result is None

    def test_uses_first_matching_file_from_index(self):
        """
        When multiple files match the hash, the first one in the list
        should be used as the duplicate reference.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            source = dest / "subdir" / "new.txt"
            source.parent.mkdir()
            source.write_text("shared content")

            # Multiple existing files with same content
            existing1 = dest / "first.txt"
            existing2 = dest / "second.txt"
            existing1.write_text("shared content")
            existing2.write_text("shared content")

            file_ops = FileOperations()
            file_mover = FileMover(file_ops)

            file_hash = file_ops.calculate_file_hash(existing1)
            hash_index: Dict[str, List[Path]] = {
                file_hash: [existing1, existing2]
            }

            result = file_mover._check_global_duplicate(
                source_path=source,
                hash_index=hash_index,
                dry_run=False,
            )

            assert result is not None
            # Should reference the first file in the list
            assert result["duplicate_of"] == str(existing1)
            assert result["neuer_name"] == "first.txt"
