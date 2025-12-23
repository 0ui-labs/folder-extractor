"""
Tests for global hash index deduplication functionality.

Tests the build_hash_index() method in FileOperations which creates
a hash index for detecting duplicate files across a directory tree.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from folder_extractor.core.file_operations import FileOperationError, FileOperations

# =============================================================================
# TestBuildHashIndexBasic - Grundlegende Funktionalität
# =============================================================================


class TestBuildHashIndexBasic:
    """Test basic build_hash_index functionality."""

    def test_empty_directory_returns_empty_index(self, temp_dir):
        """An empty directory produces an empty hash index.

        This verifies the base case - no files means no hashes to compute.
        """
        ops = FileOperations()
        result = ops.build_hash_index(temp_dir)

        assert result == {}
        assert isinstance(result, dict)

    def test_single_file_not_in_index(self, temp_dir):
        """A single file without duplicates is not included in the index.

        The optimization skips hashing files with unique sizes since they
        cannot have duplicates. This saves expensive I/O operations.
        """
        # Create a single file
        file_path = Path(temp_dir) / "unique.txt"
        file_path.write_text("unique content")

        ops = FileOperations()
        result = ops.build_hash_index(temp_dir)

        # Single file should not be in index (no potential duplicates)
        assert result == {}

    def test_two_identical_files_grouped(self, temp_dir):
        """Two files with identical content are grouped under the same hash.

        This is the core duplicate detection - files with same content
        produce same hash and are grouped together.
        """
        content = "identical content"
        file1 = Path(temp_dir) / "file1.txt"
        file2 = Path(temp_dir) / "file2.txt"
        file1.write_text(content)
        file2.write_text(content)

        ops = FileOperations()
        result = ops.build_hash_index(temp_dir)

        # Should have exactly one hash entry with both files
        assert len(result) == 1
        hash_value = list(result.keys())[0]
        assert len(result[hash_value]) == 2
        assert file1 in result[hash_value]
        assert file2 in result[hash_value]

    def test_three_identical_files_grouped(self, temp_dir):
        """Three identical files are all grouped under the same hash.

        Verifies that grouping works for more than two duplicates.
        """
        content = "triplicate content"
        files = [Path(temp_dir) / f"file{i}.txt" for i in range(3)]
        for f in files:
            f.write_text(content)

        ops = FileOperations()
        result = ops.build_hash_index(temp_dir)

        assert len(result) == 1
        hash_value = list(result.keys())[0]
        assert len(result[hash_value]) == 3
        for f in files:
            assert f in result[hash_value]

    def test_different_files_different_hashes(self, temp_dir):
        """Files with different content produce no duplicate entries.

        Different content means different hashes, but since sizes also
        differ, they won't even be hashed (optimization).
        """
        file1 = Path(temp_dir) / "file1.txt"
        file2 = Path(temp_dir) / "file2.txt"
        file1.write_text("content one")
        file2.write_text("different content two")  # Different size

        ops = FileOperations()
        result = ops.build_hash_index(temp_dir)

        # Different sizes = no hashing = empty result
        assert result == {}

    def test_mixed_identical_and_different(self, temp_dir):
        """Mixed files: only identical ones are grouped.

        When some files are duplicates and others are unique,
        only the duplicates appear in the index.
        """
        # Two identical files
        content = "duplicate content"
        dup1 = Path(temp_dir) / "dup1.txt"
        dup2 = Path(temp_dir) / "dup2.txt"
        dup1.write_text(content)
        dup2.write_text(content)

        # One unique file (different size)
        unique = Path(temp_dir) / "unique.txt"
        unique.write_text("something completely different length")

        ops = FileOperations()
        result = ops.build_hash_index(temp_dir)

        assert len(result) == 1
        hash_value = list(result.keys())[0]
        assert len(result[hash_value]) == 2
        assert dup1 in result[hash_value]
        assert dup2 in result[hash_value]


# =============================================================================
# TestBuildHashIndexSizeOptimization - Größen-basierte Optimierung
# =============================================================================


class TestBuildHashIndexSizeOptimization:
    """Test the size-based pre-filtering optimization."""

    def test_different_sizes_not_hashed(self, temp_dir):
        """Files with different sizes skip hash calculation entirely.

        This is a key performance optimization: if file sizes differ,
        they cannot be duplicates, so we skip the expensive hash.
        """
        file1 = Path(temp_dir) / "small.txt"
        file2 = Path(temp_dir) / "large.txt"
        file1.write_text("a")
        file2.write_text("a" * 100)

        ops = FileOperations()

        # Mock calculate_file_hash to track calls
        with patch.object(ops, "calculate_file_hash") as mock_hash:
            result = ops.build_hash_index(temp_dir)

            # Hash should never be called for files with unique sizes
            mock_hash.assert_not_called()
            assert result == {}

    def test_same_size_different_content(self, temp_dir):
        """Files with same size but different content get different hashes.

        Size match triggers hash calculation, but different content
        means no duplicates are found.
        """
        file1 = Path(temp_dir) / "file1.txt"
        file2 = Path(temp_dir) / "file2.txt"
        file1.write_text("content_A")  # Same length
        file2.write_text("content_B")  # Same length

        ops = FileOperations()
        result = ops.build_hash_index(temp_dir)

        # Same size, different content = different hashes = no groups
        assert result == {}

    def test_same_size_same_content(self, temp_dir):
        """Files with same size and content are properly grouped.

        Size match triggers hash, same content means same hash,
        so files are grouped as duplicates.
        """
        content = "exact match"
        file1 = Path(temp_dir) / "file1.txt"
        file2 = Path(temp_dir) / "file2.txt"
        file1.write_text(content)
        file2.write_text(content)

        ops = FileOperations()
        result = ops.build_hash_index(temp_dir)

        assert len(result) == 1
        hash_value = list(result.keys())[0]
        assert len(result[hash_value]) == 2

    def test_size_optimization_performance(self, temp_dir):
        """Only files with matching sizes are hashed.

        With 100 files of unique sizes and 2 duplicates, only the
        2 duplicates should trigger hash calculations.
        """
        base_path = Path(temp_dir)

        # Create 100 files with different sizes
        for i in range(100):
            (base_path / f"unique_{i}.txt").write_text("x" * (i + 1))

        # Create 2 identical files
        dup_content = "y" * 200  # Size 200, different from others
        (base_path / "dup1.txt").write_text(dup_content)
        (base_path / "dup2.txt").write_text(dup_content)

        ops = FileOperations()

        with patch.object(
            ops, "calculate_file_hash", wraps=ops.calculate_file_hash
        ) as mock_hash:
            result = ops.build_hash_index(temp_dir)

            # Only the 2 files with matching sizes should be hashed
            assert mock_hash.call_count == 2
            assert len(result) == 1


# =============================================================================
# TestBuildHashIndexRecursive - Rekursives Scannen
# =============================================================================


class TestBuildHashIndexRecursive:
    """Test recursive directory scanning."""

    def test_finds_files_in_subdirectories(self, temp_dir):
        """Duplicate files in subdirectories are detected.

        The scan must be recursive to find duplicates anywhere
        in the directory tree.
        """
        base = Path(temp_dir)
        subdir = base / "subdir"
        subdir.mkdir()

        content = "found in subdir"
        file1 = base / "root.txt"
        file2 = subdir / "nested.txt"
        file1.write_text(content)
        file2.write_text(content)

        ops = FileOperations()
        result = ops.build_hash_index(temp_dir)

        assert len(result) == 1
        hash_value = list(result.keys())[0]
        assert file1 in result[hash_value]
        assert file2 in result[hash_value]

    def test_deep_nesting_handled(self, temp_dir):
        """Deeply nested directories (5+ levels) are scanned correctly.

        Verifies that the recursive scan has no artificial depth limits.
        """
        base = Path(temp_dir)
        content = "deep content"

        # Create deep structure: level1/level2/level3/level4/level5
        deep_path = base / "l1" / "l2" / "l3" / "l4" / "l5"
        deep_path.mkdir(parents=True)

        file1 = base / "root.txt"
        file2 = deep_path / "deep.txt"
        file1.write_text(content)
        file2.write_text(content)

        ops = FileOperations()
        result = ops.build_hash_index(temp_dir)

        assert len(result) == 1
        hash_value = list(result.keys())[0]
        assert file1 in result[hash_value]
        assert file2 in result[hash_value]

    def test_multiple_subdirs_with_duplicates(self, temp_dir):
        """Duplicates across multiple separate subdirectories are found.

        Verifies that the scan covers all branches of the directory tree.
        """
        base = Path(temp_dir)
        dir1 = base / "dir1"
        dir2 = base / "dir2"
        dir3 = base / "dir3"
        dir1.mkdir()
        dir2.mkdir()
        dir3.mkdir()

        content = "scattered duplicate"
        file1 = dir1 / "file.txt"
        file2 = dir2 / "copy.txt"
        file3 = dir3 / "another.txt"
        file1.write_text(content)
        file2.write_text(content)
        file3.write_text(content)

        ops = FileOperations()
        result = ops.build_hash_index(temp_dir)

        assert len(result) == 1
        hash_value = list(result.keys())[0]
        assert len(result[hash_value]) == 3

    def test_ignores_directories(self, temp_dir):
        """Directories themselves are not indexed, only files.

        The hash index should contain only file paths, not directories.
        """
        base = Path(temp_dir)

        # Create some directories
        (base / "subdir1").mkdir()
        (base / "subdir2").mkdir()

        # Create identical files
        content = "file content"
        file1 = base / "subdir1" / "file.txt"
        file2 = base / "subdir2" / "file.txt"
        file1.write_text(content)
        file2.write_text(content)

        ops = FileOperations()
        result = ops.build_hash_index(temp_dir)

        # Only files in the index
        for _hash_value, paths in result.items():
            for path in paths:
                assert path.is_file()
                assert not path.is_dir()


# =============================================================================
# TestBuildHashIndexErrors - Fehlerbehandlung
# =============================================================================


class TestBuildHashIndexErrors:
    """Test error handling scenarios."""

    def test_nonexistent_directory_raises_error(self, temp_dir):
        """Non-existent directory raises FileOperationError.

        The method should fail fast with a clear error message
        when given an invalid directory path.
        """
        ops = FileOperations()
        nonexistent = Path(temp_dir) / "does_not_exist"

        with pytest.raises(FileOperationError) as exc_info:
            ops.build_hash_index(nonexistent)

        assert (
            "existiert nicht" in str(exc_info.value).lower()
            or "not exist" in str(exc_info.value).lower()
        )

    def test_file_instead_of_directory_raises_error(self, temp_dir):
        """Passing a file path instead of directory raises error.

        The method expects a directory, not a file.
        """
        ops = FileOperations()
        file_path = Path(temp_dir) / "not_a_dir.txt"
        file_path.write_text("I am a file")

        with pytest.raises(FileOperationError) as exc_info:
            ops.build_hash_index(file_path)

        # Error message should indicate the path is not a directory
        error_msg = str(exc_info.value).lower()
        assert (
            "verzeichnis" in error_msg
            or "directory" in error_msg
            or "datei" in error_msg
        )

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-only permission test")
    def test_permission_denied_raises_error(self, temp_dir):
        """Directory without read permission raises FileOperationError.

        On Unix systems, attempting to read a directory without
        permission should raise a clear error.
        """
        base = Path(temp_dir)
        no_access = base / "no_access"
        no_access.mkdir()

        try:
            # Remove read permission
            os.chmod(no_access, 0o000)

            ops = FileOperations()

            with pytest.raises(FileOperationError) as exc_info:
                ops.build_hash_index(no_access)

            error_msg = str(exc_info.value).lower()
            assert "berechtigung" in error_msg or "permission" in error_msg
        finally:
            # Restore permissions for cleanup
            os.chmod(no_access, 0o755)

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-only permission test")
    def test_unreadable_file_skipped(self, temp_dir):
        """Unreadable files are skipped, other files are still processed.

        The scan should be resilient to individual file access errors,
        continuing with remaining files rather than failing entirely.
        """
        base = Path(temp_dir)

        # Create two readable identical files
        content = "readable content"
        file1 = base / "readable1.txt"
        file2 = base / "readable2.txt"
        file1.write_text(content)
        file2.write_text(content)

        # Create an unreadable file with same size
        unreadable = base / "unreadable.txt"
        unreadable.write_text(content)
        os.chmod(unreadable, 0o000)

        try:
            ops = FileOperations()
            result = ops.build_hash_index(temp_dir)

            # The two readable files should still be grouped
            assert len(result) == 1
            hash_value = list(result.keys())[0]
            # Could be 2 (unreadable skipped) or 3 (if somehow readable)
            assert len(result[hash_value]) >= 2
        finally:
            os.chmod(unreadable, 0o644)

    def test_deleted_file_during_scan_handled(self, temp_dir):
        """Files deleted during scan are handled gracefully.

        Race conditions where files disappear between discovery
        and hashing should not crash the scan.
        """
        base = Path(temp_dir)

        # Create files
        content = "will be deleted"
        file1 = base / "file1.txt"
        file2 = base / "file2.txt"
        file3 = base / "file3.txt"
        file1.write_text(content)
        file2.write_text(content)
        file3.write_text(content)

        ops = FileOperations()

        # Track original method
        original_hash = ops.calculate_file_hash
        call_count = [0]

        def hash_with_delete(path, *args, **kwargs):
            """Delete file2 after first hash calculation."""
            call_count[0] += 1
            if call_count[0] == 1 and file2.exists():
                file2.unlink()
            if not Path(path).exists():
                raise FileOperationError(f"Datei existiert nicht: {path}")
            return original_hash(path, *args, **kwargs)

        with patch.object(ops, "calculate_file_hash", side_effect=hash_with_delete):
            # Should not raise, just skip the deleted file
            ops.build_hash_index(temp_dir)

        # At least some files should be processed
        # The exact count depends on order, but no exception should occur


# =============================================================================
# TestBuildHashIndexEdgeCases - Spezialfälle
# =============================================================================


class TestBuildHashIndexEdgeCases:
    """Test edge cases and special file types."""

    def test_empty_files_grouped_correctly(self, temp_dir):
        """Multiple empty files are grouped together.

        Empty files have identical content (nothing) and thus
        identical hashes. They should be detected as duplicates.
        """
        base = Path(temp_dir)

        empty1 = base / "empty1.txt"
        empty2 = base / "empty2.txt"
        empty3 = base / "empty3.txt"
        empty1.write_text("")
        empty2.write_text("")
        empty3.write_text("")

        ops = FileOperations()
        result = ops.build_hash_index(temp_dir)

        assert len(result) == 1
        hash_value = list(result.keys())[0]
        assert len(result[hash_value]) == 3

    def test_binary_files_handled(self, temp_dir):
        """Binary files (simulated images) are correctly hashed.

        The hash function should work with any file content,
        not just text files.
        """
        base = Path(temp_dir)

        # Simulated binary content
        binary_content = bytes(range(256)) * 10

        file1 = base / "image1.bin"
        file2 = base / "image2.bin"
        file1.write_bytes(binary_content)
        file2.write_bytes(binary_content)

        ops = FileOperations()
        result = ops.build_hash_index(temp_dir)

        assert len(result) == 1
        hash_value = list(result.keys())[0]
        assert len(result[hash_value]) == 2

    def test_large_files_handled(self, temp_dir):
        """Large files (>10MB) are correctly processed.

        The chunked reading approach should handle large files
        without memory issues.
        """
        base = Path(temp_dir)

        # Create 11MB files
        large_content = b"X" * (11 * 1024 * 1024)

        file1 = base / "large1.bin"
        file2 = base / "large2.bin"
        file1.write_bytes(large_content)
        file2.write_bytes(large_content)

        ops = FileOperations()
        result = ops.build_hash_index(temp_dir)

        assert len(result) == 1
        hash_value = list(result.keys())[0]
        assert len(result[hash_value]) == 2

    def test_unicode_filenames(self, temp_dir):
        """Files with Unicode characters in names are handled.

        International filenames (umlauts, emojis, etc.) should
        work correctly.
        """
        base = Path(temp_dir)
        content = "unicode test"

        file1 = base / "datei_mit_ümläuten.txt"
        file2 = base / "Ñoño.txt"
        file1.write_text(content)
        file2.write_text(content)

        ops = FileOperations()
        result = ops.build_hash_index(temp_dir)

        assert len(result) == 1
        hash_value = list(result.keys())[0]
        assert len(result[hash_value]) == 2

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-only symlink test")
    def test_symlinks_followed(self, temp_dir):
        """Symbolic links are resolved and files are hashed.

        Symlinks should be followed to get the actual file content
        for hashing. A symlink and a regular copy of the same content
        should be grouped together as duplicates.
        """
        base = Path(temp_dir)
        content = "linked content"

        # Real file (original)
        real_file = base / "real.txt"
        real_file.write_text(content)

        # Create a symlink pointing to the real file
        symlink_file = base / "symlink.txt"
        symlink_file.symlink_to(real_file)

        # Create a regular copy with same content
        copy_file = base / "copy.txt"
        copy_file.write_text(content)

        ops = FileOperations()
        result = ops.build_hash_index(temp_dir)

        # All three should be found as duplicates (same hash)
        assert len(result) == 1
        hash_value = list(result.keys())[0]
        paths = result[hash_value]
        assert len(paths) == 3
        path_names = [p.name for p in paths]
        assert "real.txt" in path_names
        assert "symlink.txt" in path_names
        assert "copy.txt" in path_names

    def test_hidden_files_included(self, temp_dir):
        """Hidden files (starting with .) are included in the index.

        Hidden files should be scanned and included in duplicate
        detection.
        """
        base = Path(temp_dir)
        content = "hidden content"

        hidden = base / ".hidden"
        visible = base / "visible.txt"
        hidden.write_text(content)
        visible.write_text(content)

        ops = FileOperations()
        result = ops.build_hash_index(temp_dir)

        assert len(result) == 1
        hash_value = list(result.keys())[0]
        assert len(result[hash_value]) == 2


# =============================================================================
# TestBuildHashIndexProperties - Property-Based Tests mit Hypothesis
# =============================================================================


class TestBuildHashIndexProperties:
    """Property-based tests using Hypothesis."""

    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[
            HealthCheck.too_slow,
            HealthCheck.function_scoped_fixture,
        ],
    )
    @given(
        num_files=st.integers(min_value=2, max_value=20),
        content=st.binary(min_size=1, max_size=1000),
    )
    def test_all_identical_files_single_hash(self, num_files, content):
        """N identical files produce exactly one hash group with N paths.

        Property: For any N identical files, the hash index should
        contain exactly one entry with exactly N file paths.
        """

        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)

            # Create N identical files
            files = []
            for i in range(num_files):
                file_path = base / f"file_{i}.bin"
                file_path.write_bytes(content)
                files.append(file_path)

            ops = FileOperations()
            result = ops.build_hash_index(temp_dir)

            assert len(result) == 1
            hash_value = list(result.keys())[0]
            assert len(result[hash_value]) == num_files

    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[
            HealthCheck.too_slow,
            HealthCheck.function_scoped_fixture,
        ],
    )
    @given(
        num_groups=st.integers(min_value=2, max_value=5),
        group_size=st.integers(min_value=2, max_value=4),
    )
    def test_multiple_duplicate_groups(self, num_groups, group_size):
        """Multiple groups of duplicates produce multiple hash entries.

        Property: K groups of M identical files each should produce
        K hash entries, each with M file paths.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)

            # Create groups of identical files with different content per group
            for g in range(num_groups):
                content = f"group_{g}_content".encode() * 10
                for i in range(group_size):
                    file_path = base / f"group{g}_file{i}.bin"
                    file_path.write_bytes(content)

            ops = FileOperations()
            result = ops.build_hash_index(temp_dir)

            assert len(result) == num_groups
            for _hash_value, paths in result.items():
                assert len(paths) == group_size

    @settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[
            HealthCheck.too_slow,
            HealthCheck.function_scoped_fixture,
        ],
    )
    @given(content=st.binary(min_size=0, max_size=5000))
    def test_index_deterministic(self, content):
        """Scanning the same directory twice produces identical results.

        Property: The hash index should be deterministic - same input
        always produces same output (though path ordering may vary).
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)

            # Need at least 2 files to test grouping
            file1 = base / "file1.bin"
            file2 = base / "file2.bin"
            file1.write_bytes(content)
            file2.write_bytes(content)

            ops = FileOperations()

            result1 = ops.build_hash_index(temp_dir)
            result2 = ops.build_hash_index(temp_dir)

            # Same keys
            assert set(result1.keys()) == set(result2.keys())

            # Same paths for each key (order may vary)
            for key in result1:
                assert set(result1[key]) == set(result2[key])
