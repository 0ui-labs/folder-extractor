"""
Tests for FileMover._prepare_global_hash_index() method.

This method extracts the hash-index preparation logic from move_files() and
move_files_sorted() to eliminate code duplication while preserving the
critical bugfix for source file filtering.

Test strategy:
- Test the sorting behavior (mtime, name length, alphabetical)
- Test the hash index building and filtering
- Test the callback signaling
- Test error handling
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock

from folder_extractor.core.file_operations import FileMover, FileOperations


class TestPrepareGlobalHashIndexSorting:
    """Test that files are sorted correctly by mtime, name length, and alphabetically."""

    def test_sorts_files_by_modification_time_oldest_first(self):
        """
        Files should be sorted by modification time (oldest first).

        This ensures that original files are processed before copies,
        so duplicates are detected correctly.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)
            subdir = dest / "subdir"
            subdir.mkdir()

            # Create files with different mtimes
            old_file = subdir / "old.txt"
            new_file = subdir / "new.txt"
            old_file.write_text("content")
            new_file.write_text("content")

            # Set modification times
            old_time = 1600000000.0
            new_time = 1700000000.0
            os.utime(old_file, (old_time, old_time))
            os.utime(new_file, (new_time, new_time))

            file_ops = FileOperations()
            file_mover = FileMover(file_ops)

            # Call with files in wrong order (new first)
            sorted_files, _ = file_mover._prepare_global_hash_index(
                files=[new_file, old_file],
                dest_path=dest,
            )

            # Verify sorted order - old file should be first
            sorted_names = [Path(f).name for f in sorted_files]
            assert sorted_names == ["old.txt", "new.txt"], (
                f"Expected oldest file first, got {sorted_names}"
            )

    def test_sorts_by_name_length_when_same_mtime(self):
        """
        When modification times are equal, shorter filenames should come first.

        This handles cases like archive extractions where mtimes are preserved
        and assumes shorter names are likely originals (e.g., "doc.txt" vs "doc kopie.txt").
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)
            subdir = dest / "subdir"
            subdir.mkdir()

            short_name = subdir / "a.txt"
            long_name = subdir / "a_long_name.txt"
            short_name.write_text("content")
            long_name.write_text("content")

            # Set same mtime
            same_time = 1700000000.0
            os.utime(short_name, (same_time, same_time))
            os.utime(long_name, (same_time, same_time))

            file_ops = FileOperations()
            file_mover = FileMover(file_ops)

            sorted_files, _ = file_mover._prepare_global_hash_index(
                files=[long_name, short_name],
                dest_path=dest,
            )

            sorted_names = [Path(f).name for f in sorted_files]
            assert sorted_names == ["a.txt", "a_long_name.txt"], (
                f"Expected shorter name first, got {sorted_names}"
            )

    def test_sorts_alphabetically_when_same_mtime_and_length(self):
        """
        When mtime and name length are equal, sort alphabetically.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)
            subdir = dest / "subdir"
            subdir.mkdir()

            file_b = subdir / "bbb.txt"
            file_a = subdir / "aaa.txt"
            file_b.write_text("content")
            file_a.write_text("content")

            same_time = 1700000000.0
            os.utime(file_a, (same_time, same_time))
            os.utime(file_b, (same_time, same_time))

            file_ops = FileOperations()
            file_mover = FileMover(file_ops)

            sorted_files, _ = file_mover._prepare_global_hash_index(
                files=[file_b, file_a],
                dest_path=dest,
            )

            sorted_names = [Path(f).name for f in sorted_files]
            assert sorted_names == ["aaa.txt", "bbb.txt"], (
                f"Expected alphabetical order, got {sorted_names}"
            )


class TestPrepareGlobalHashIndexFiltering:
    """Test that source files are correctly filtered from the hash index."""

    def test_filters_source_files_from_subdirectories(self):
        """
        Source files in subdirectories must be filtered from the hash index.

        BUGFIX: Without this, identical source files would match each other
        in the hash index, causing both to be detected as duplicates and
        deleted, resulting in data loss.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)
            subdir = dest / "subdir"
            subdir.mkdir()

            # Create identical files in subdirectory
            file1 = subdir / "doc.txt"
            file2 = subdir / "doc_copy.txt"
            content = "identical content for testing"
            file1.write_text(content)
            file2.write_text(content)

            file_ops = FileOperations()
            file_mover = FileMover(file_ops)

            _, hash_index = file_mover._prepare_global_hash_index(
                files=[file1, file2],
                dest_path=dest,
            )

            # The source files should NOT be in the hash index
            # (otherwise they would match each other as duplicates)
            all_indexed_paths = []
            for paths in hash_index.values():
                all_indexed_paths.extend(str(p) for p in paths)

            assert str(file1.resolve()) not in [
                str(Path(p).resolve()) for p in all_indexed_paths
            ], f"Source file {file1} should be filtered from hash index"
            assert str(file2.resolve()) not in [
                str(Path(p).resolve()) for p in all_indexed_paths
            ], f"Source file {file2} should be filtered from hash index"

    def test_does_not_filter_files_in_root_directory(self):
        """
        Files already in the root destination directory should remain in the hash index.
        These are existing files, not source files being moved.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            # Create a file already in root (existing file at destination)
            existing_file = dest / "existing.txt"
            existing_file.write_text("I already exist at destination")

            # Create source file in subdirectory
            subdir = dest / "subdir"
            subdir.mkdir()
            source_file = subdir / "new.txt"
            source_file.write_text("I am being moved")

            file_ops = FileOperations()
            file_mover = FileMover(file_ops)

            _, hash_index = file_mover._prepare_global_hash_index(
                files=[source_file],
                dest_path=dest,
            )

            # The existing file in root should be in the hash index
            all_indexed_paths = set()
            for paths in hash_index.values():
                for p in paths:
                    all_indexed_paths.add(p.resolve())

            assert existing_file.resolve() in all_indexed_paths, (
                f"Existing file {existing_file} should remain in hash index"
            )

    def test_does_not_filter_files_in_type_folders(self):
        """
        Files in type folders (e.g., TEXT/, PDF/) should remain in the hash index.
        These are files already sorted, not source files being moved.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            # Create a file in a type folder (already sorted)
            text_folder = dest / "TEXT"
            text_folder.mkdir()
            sorted_file = text_folder / "sorted.txt"
            sorted_file.write_text("I am already sorted")

            # Create source file in subdirectory
            subdir = dest / "subdir"
            subdir.mkdir()
            source_file = subdir / "new.txt"
            source_file.write_text("I am being moved")

            file_ops = FileOperations()
            file_mover = FileMover(file_ops)

            _, hash_index = file_mover._prepare_global_hash_index(
                files=[source_file],
                dest_path=dest,
            )

            # The sorted file in type folder should remain in hash index
            all_indexed_paths = set()
            for paths in hash_index.values():
                for p in paths:
                    all_indexed_paths.add(p.resolve())

            assert sorted_file.resolve() in all_indexed_paths, (
                f"File in type folder {sorted_file} should remain in hash index"
            )


class TestPrepareGlobalHashIndexCallbacks:
    """Test that indexing callbacks are correctly triggered."""

    def test_calls_indexing_callback_start_and_end(self):
        """
        The indexing_callback should be called with "start" and "end".
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)
            subdir = dest / "subdir"
            subdir.mkdir()
            file1 = subdir / "test.txt"
            file1.write_text("content")

            callback_calls: list[str] = []

            def callback(phase: str) -> None:
                callback_calls.append(phase)

            file_ops = FileOperations()
            file_mover = FileMover(file_ops, indexing_callback=callback)

            file_mover._prepare_global_hash_index(
                files=[file1],
                dest_path=dest,
            )

            assert callback_calls == ["start", "end"], (
                f"Expected ['start', 'end'], got {callback_calls}"
            )

    def test_calls_end_callback_even_on_error(self):
        """
        The "end" callback must be called even if an error occurs during indexing.
        This ensures proper cleanup of UI state (e.g., progress indicators).
        """
        callback_calls: list[str] = []

        def callback(phase: str) -> None:
            callback_calls.append(phase)

        file_ops = Mock(spec=FileOperations)
        # Make build_hash_index raise an error
        from folder_extractor.core.file_operations import FileOperationError

        file_ops.build_hash_index.side_effect = FileOperationError("Test error")

        file_mover = FileMover(file_ops, indexing_callback=callback)

        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)
            subdir = dest / "subdir"
            subdir.mkdir()
            file1 = subdir / "test.txt"
            file1.write_text("content")

            # Should not raise - error is caught internally
            _, hash_index = file_mover._prepare_global_hash_index(
                files=[file1],
                dest_path=dest,
            )

            # Hash index should be empty due to error
            assert hash_index == {}, "Hash index should be empty on error"

            # But both callbacks should have been called
            assert "start" in callback_calls, "'start' callback should be called"
            assert "end" in callback_calls, "'end' callback should be called"


class TestPrepareGlobalHashIndexReturnValue:
    """Test the return value structure of _prepare_global_hash_index()."""

    def test_returns_tuple_of_sorted_files_and_hash_index(self):
        """
        Method should return (sorted_files, hash_index) tuple.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)
            subdir = dest / "subdir"
            subdir.mkdir()
            file1 = subdir / "test.txt"
            file1.write_text("content")

            file_ops = FileOperations()
            file_mover = FileMover(file_ops)

            result = file_mover._prepare_global_hash_index(
                files=[file1],
                dest_path=dest,
            )

            assert isinstance(result, tuple), "Should return a tuple"
            assert len(result) == 2, "Should return 2-tuple (files, hash_index)"

            sorted_files, hash_index = result
            assert hasattr(sorted_files, "__iter__"), (
                "First element should be iterable (files)"
            )
            assert isinstance(hash_index, dict), (
                "Second element should be dict (hash_index)"
            )

    def test_hash_index_maps_hashes_to_path_lists(self):
        """
        The hash_index should map file hashes to lists of Path objects.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            # Create a file in root (so it stays in hash index)
            existing = dest / "existing.txt"
            existing.write_text("unique content")

            file_ops = FileOperations()
            file_mover = FileMover(file_ops)

            _, hash_index = file_mover._prepare_global_hash_index(
                files=[],  # No source files, just index destination
                dest_path=dest,
            )

            # Check structure
            for hash_value, paths in hash_index.items():
                assert isinstance(hash_value, str), "Keys should be hash strings"
                assert isinstance(paths, list), "Values should be lists"
                for path in paths:
                    assert isinstance(path, Path), "List items should be Path objects"
