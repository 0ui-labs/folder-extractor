"""
Tests für extrem tiefe Verzeichnisstrukturen.

Verifiziert, dass die iterative os.walk()-Implementierung in FileDiscovery
resistent gegen RecursionError ist und bei Tiefen > sys.getrecursionlimit()
korrekt funktioniert.

Teststrategien:
1. Mock-basiert: Simuliert Tiefen > 1000 ohne Filesystem-Overhead
2. Real Filesystem: Testet moderate Tiefen (100-200) mit echten Verzeichnissen
3. Hypothesis: Property-basierte Tests mit zufälligen Tiefen
"""

import sys
import threading
from pathlib import Path
from typing import List, Tuple
from unittest.mock import patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from folder_extractor.core.file_discovery import FileDiscovery


# =============================================================================
# Mock Helper Functions
# =============================================================================


def mock_deep_os_walk(
    base_path: str, depth: int, files_per_level: int = 2
) -> List[Tuple[str, List[str], List[str]]]:
    """
    Generate mock data for os.walk() with configurable depth.

    Creates a simulated deep directory structure without touching the filesystem.

    Args:
        base_path: Base directory path for the mock structure
        depth: Number of nesting levels to generate
        files_per_level: Number of files to simulate per directory level

    Returns:
        List of (root, dirs, files) tuples simulating os.walk() output.
        Each level has a subdirectory (except the last) and files.

    Example:
        For depth=3, generates:
        - (base_path, ['level_0'], ['file_0.txt', 'file_1.txt'])
        - (base_path/level_0, ['level_1'], ['file_0.txt', 'file_1.txt'])
        - (base_path/level_0/level_1, [], ['file_0.txt', 'file_1.txt'])
    """
    result = []
    current_path = Path(base_path)

    for level in range(depth):
        # Generate file names for this level
        files = [f"file_{i}.txt" for i in range(files_per_level)]

        # Last level has no subdirectories
        if level == depth - 1:
            dirs = []
        else:
            dirs = [f"level_{level}"]

        result.append((str(current_path), dirs, files))

        # Build path for next level
        if level < depth - 1:
            current_path = current_path / f"level_{level}"

    return result


def create_simulated_os_walk(base_path: str, depth: int, files_per_level: int = 2):
    """
    Create a generator that simulates os.walk() with topdown=True behavior.

    This correctly handles the in-place modification of dirs[] that os.walk()
    uses for pruning. When the consumer clears dirs[:], subsequent levels
    are not yielded.

    Args:
        base_path: Base directory path for the mock structure
        depth: Maximum depth of the simulated structure
        files_per_level: Number of files per directory level

    Yields:
        Tuples of (root, dirs, files) like os.walk(), respecting dirs pruning.
    """

    def _walk_generator(path, topdown=True):
        """Inner generator that respects dirs modification."""
        current_path = Path(path)
        stack = [(current_path, 0)]

        while stack:
            current, level = stack.pop()

            if level >= depth:
                continue

            # Generate file names for this level
            files = [f"file_{i}.txt" for i in range(files_per_level)]

            # Subdirectory for next level (if not at max depth)
            if level < depth - 1:
                dirs = [f"level_{level}"]
            else:
                dirs = []

            # Yield and let consumer modify dirs
            yield str(current), dirs, files

            # Only descend if dirs wasn't cleared by consumer
            if dirs and level < depth - 1:
                next_path = current / f"level_{level}"
                stack.append((next_path, level + 1))

    return _walk_generator


# =============================================================================
# Test Class: Mock-Based Tests for Extreme Depths
# =============================================================================


class TestDeepStructuresWithMock:
    """Tests for extreme directory depths using mocked os.walk()."""

    def test_extreme_depth_no_recursion_error(self, tmp_path):
        """
        FileDiscovery handles depths exceeding Python's recursion limit.

        Purpose:
            Verify that find_files() does not raise RecursionError when
            processing directory structures deeper than sys.getrecursionlimit().

        Rationale:
            The implementation uses iterative os.walk() instead of recursive
            traversal. This test documents and verifies this robustness.

        Setup:
            Mock os.walk() to simulate a depth of recursion_limit + 500 levels.

        Expected:
            All files are found without RecursionError.
        """
        recursion_limit = sys.getrecursionlimit()
        test_depth = recursion_limit + 500
        files_per_level = 2

        mock_data = mock_deep_os_walk(str(tmp_path), test_depth, files_per_level)

        with patch("folder_extractor.core.file_discovery.os.walk") as mock_walk:
            mock_walk.return_value = iter(mock_data)

            discovery = FileDiscovery()
            found_files = discovery.find_files(tmp_path)

        expected_file_count = test_depth * files_per_level
        assert len(found_files) == expected_file_count, (
            f"Expected {expected_file_count} files for depth {test_depth}, "
            f"got {len(found_files)}"
        )

    def test_max_depth_at_extreme_levels(self, tmp_path):
        """
        max_depth correctly limits file discovery at extreme depths.

        Purpose:
            Verify that max_depth parameter stops traversal at specified
            depth even when total structure is much deeper.

        Rationale:
            When users specify max_depth, they expect consistent behavior
            regardless of actual directory depth. This ensures the depth
            limiting logic works at scale.

        Setup:
            Mock os.walk() for 2000 levels, request max_depth=100.

        Expected:
            Files from levels 0 through max_depth are returned (inclusive).
            The implementation stops descending when current_depth >= max_depth,
            so files at depth=max_depth are still processed, but no deeper.
        """
        total_depth = 2000
        max_depth_limit = 100
        files_per_level = 2

        # Use the simulated os.walk that respects dirs[:] = [] pruning
        simulated_walk = create_simulated_os_walk(
            str(tmp_path), total_depth, files_per_level
        )

        with patch("folder_extractor.core.file_discovery.os.walk") as mock_walk:
            mock_walk.side_effect = simulated_walk

            discovery = FileDiscovery()
            found_files = discovery.find_files(tmp_path, max_depth=max_depth_limit)

        # Files from levels 0 through max_depth (inclusive)
        # Level 0 = base dir, level max_depth = last level processed
        # Total levels = max_depth + 1 (depth 0, 1, ..., max_depth)
        expected_file_count = (max_depth_limit + 1) * files_per_level
        assert len(found_files) == expected_file_count, (
            f"Expected {expected_file_count} files for max_depth={max_depth_limit}, "
            f"got {len(found_files)}"
        )

    def test_abort_signal_in_deep_structure(self, tmp_path):
        """
        abort_signal terminates traversal in deep structures.

        Purpose:
            Verify that setting abort_signal stops file discovery mid-traversal
            in a deep directory structure.

        Rationale:
            Users should be able to cancel long-running operations with ESC key.
            This must work correctly in deeply nested structures.

        Setup:
            Mock os.walk() for 1000 levels, trigger abort after 50 iterations.

        Expected:
            Function returns early with partial results, fewer than full count.
        """
        total_depth = 1000
        abort_after_iterations = 50
        files_per_level = 2

        mock_data = mock_deep_os_walk(str(tmp_path), total_depth, files_per_level)

        abort_signal = threading.Event()
        iteration_count = [0]

        def mock_walk_with_abort(path, topdown=True):
            """Wrap mock data to trigger abort after N iterations."""
            for root, dirs, files in mock_data:
                iteration_count[0] += 1
                if iteration_count[0] >= abort_after_iterations:
                    abort_signal.set()
                yield root, dirs.copy(), files

        with patch("folder_extractor.core.file_discovery.os.walk") as mock_walk:
            mock_walk.side_effect = mock_walk_with_abort

            discovery = FileDiscovery(abort_signal=abort_signal)
            found_files = discovery.find_files(tmp_path)

        full_file_count = total_depth * files_per_level
        assert len(found_files) < full_file_count, (
            f"Expected fewer than {full_file_count} files due to abort, "
            f"got {len(found_files)}"
        )
        # Should have files from approximately abort_after_iterations levels
        # (might be slightly more due to timing)
        assert len(found_files) <= (abort_after_iterations + 1) * files_per_level


# =============================================================================
# Test Class: Real Filesystem Tests for Deep Structures
# =============================================================================


class TestDeepStructuresRealFilesystem:
    """
    Tests for deep directory structures using real filesystem operations.

    These tests create actual nested directories on disk to verify behavior
    with real I/O operations, symlinks, permissions, and edge cases that
    mocking cannot reliably simulate.
    """

    @staticmethod
    def create_deep_directory_structure(
        base_path: Path,
        depth: int,
        files_per_level: int = 1,
        hidden_at_levels: List[int] = None,
    ) -> int:
        """
        Create a real nested directory structure on disk.

        Args:
            base_path: Root directory for the structure
            depth: Number of nesting levels to create
            files_per_level: Number of files to create at each level
            hidden_at_levels: List of levels where hidden directories should be created

        Returns:
            Total number of files created
        """
        if hidden_at_levels is None:
            hidden_at_levels = []

        current_path = base_path
        total_files = 0

        for level in range(depth):
            # Create files at this level
            for i in range(files_per_level):
                file_path = current_path / f"file_{level}_{i}.txt"
                file_path.write_text(f"Content at level {level}, file {i}")
                total_files += 1

            # Create next level directory (not at last level)
            if level < depth - 1:
                if level in hidden_at_levels:
                    # Create hidden directory
                    next_dir = current_path / f".hidden_level_{level}"
                else:
                    next_dir = current_path / f"level_{level}"
                next_dir.mkdir(parents=True, exist_ok=True)
                current_path = next_dir

        return total_files

    def test_real_filesystem_100_levels_no_max_depth(self, tmp_path):
        """
        FileDiscovery finds all files in a 100-level deep real directory.

        Purpose:
            Verify that find_files() correctly traverses a moderately deep
            real directory structure without any depth limit.

        Rationale:
            Real filesystem tests catch edge cases that mocking misses:
            OS-specific path length limits, actual I/O behavior, symlink handling.

        Setup:
            Create a 100-level deep directory structure with 1 file per level.

        Expected:
            All 100 files are found, one from each level.
        """
        depth = 100
        files_per_level = 1

        total_files = self.create_deep_directory_structure(
            tmp_path, depth, files_per_level
        )

        discovery = FileDiscovery()
        found_files = discovery.find_files(tmp_path)

        assert len(found_files) == total_files, (
            f"Expected {total_files} files in {depth}-level structure, "
            f"got {len(found_files)}"
        )

    def test_real_filesystem_100_levels_with_max_depth(self, tmp_path):
        """
        max_depth limits file discovery in real 100-level directory.

        Purpose:
            Verify that max_depth correctly limits traversal depth in a
            real filesystem structure.

        Rationale:
            Users rely on max_depth to limit operations to specific levels.
            This must work identically on real filesystems as with mocks.

        Setup:
            Create 100-level deep structure, set max_depth=50.

        Expected:
            Only files from levels 0-49 are returned (50 files total).
        """
        depth = 100
        max_depth_limit = 50
        files_per_level = 1

        self.create_deep_directory_structure(tmp_path, depth, files_per_level)

        discovery = FileDiscovery()
        found_files = discovery.find_files(tmp_path, max_depth=max_depth_limit)

        # max_depth limits descent, but files at depth=max_depth are still processed.
        # With max_depth=50, files at depths 0-50 are found (51 files).
        # The condition `current_depth >= max_depth` stops descent but processes
        # current directory first.
        expected_files = (max_depth_limit + 1) * files_per_level
        assert len(found_files) == expected_files, (
            f"Expected {expected_files} files with max_depth={max_depth_limit}, "
            f"got {len(found_files)}"
        )

    def test_real_filesystem_multiple_files_per_level(self, tmp_path):
        """
        FileDiscovery finds multiple files at each level of deep structure.

        Purpose:
            Verify that find_files() correctly handles multiple files per
            directory level in deep structures.

        Rationale:
            Real-world directories often contain many files at each level.
            This tests the combination of depth and breadth.

        Setup:
            Create 50-level structure with 3 files per level.

        Expected:
            All 150 files are found (50 levels × 3 files).
        """
        depth = 50
        files_per_level = 3

        total_files = self.create_deep_directory_structure(
            tmp_path, depth, files_per_level
        )

        discovery = FileDiscovery()
        found_files = discovery.find_files(tmp_path)

        assert len(found_files) == total_files, (
            f"Expected {total_files} files, got {len(found_files)}"
        )

    def test_real_filesystem_hidden_directories_skipped(self, tmp_path):
        """
        Hidden directories are skipped with include_hidden=False in deep structures.

        Purpose:
            Verify that find_files() correctly skips hidden directories
            (prefixed with '.') at various depths when include_hidden=False.

        Rationale:
            Users expect hidden directories to be excluded by default.
            This behavior must work correctly at any depth level.

        Setup:
            Create 20-level structure with hidden directories at levels 5, 10, 15.
            Files exist after these hidden directories but should not be found.

        Expected:
            Only files from levels 0-4 are found (before first hidden dir).
        """
        depth = 20
        files_per_level = 1
        # Hidden directories at levels 5, 10, 15 block traversal
        hidden_levels = [5, 10, 15]

        self.create_deep_directory_structure(
            tmp_path, depth, files_per_level, hidden_at_levels=hidden_levels
        )

        discovery = FileDiscovery()
        # Default: include_hidden=False
        found_files = discovery.find_files(tmp_path, include_hidden=False)

        # Files at levels 0-5 are visible (6 files)
        # The file at level 5 is created BEFORE the hidden directory
        # Level 5 creates .hidden_level_5 which blocks further descent
        expected_files = 6  # Levels 0, 1, 2, 3, 4, 5
        assert len(found_files) == expected_files, (
            f"Expected {expected_files} files (before hidden dir at level 5), "
            f"got {len(found_files)}"
        )

    def test_real_filesystem_hidden_directories_included(self, tmp_path):
        """
        Hidden directories are traversed with include_hidden=True.

        Purpose:
            Verify that include_hidden=True allows traversal through
            hidden directories in deep structures.

        Rationale:
            When users explicitly request hidden files, all hidden
            directories must be traversed regardless of depth.

        Setup:
            Create 20-level structure with hidden directories at levels 5, 10, 15.

        Expected:
            All 20 files are found, including those after hidden directories.
        """
        depth = 20
        files_per_level = 1
        hidden_levels = [5, 10, 15]

        total_files = self.create_deep_directory_structure(
            tmp_path, depth, files_per_level, hidden_at_levels=hidden_levels
        )

        discovery = FileDiscovery()
        found_files = discovery.find_files(tmp_path, include_hidden=True)

        assert len(found_files) == total_files, (
            f"Expected {total_files} files with include_hidden=True, "
            f"got {len(found_files)}"
        )

    def test_real_filesystem_max_depth_zero_means_unlimited(self, tmp_path):
        """
        max_depth=0 means unlimited depth in real filesystem.

        Purpose:
            Verify that max_depth=0 (default) means no depth limit.

        Rationale:
            The API contract specifies 0 = unlimited. This must work
            correctly in deep real structures.

        Setup:
            Create 75-level structure, call find_files with max_depth=0.

        Expected:
            All 75 files are found.
        """
        depth = 75
        files_per_level = 1

        total_files = self.create_deep_directory_structure(
            tmp_path, depth, files_per_level
        )

        discovery = FileDiscovery()
        # Explicitly pass max_depth=0
        found_files = discovery.find_files(tmp_path, max_depth=0)

        assert len(found_files) == total_files, (
            f"Expected {total_files} files with max_depth=0, got {len(found_files)}"
        )


# =============================================================================
# Test Class: Hypothesis Property-Based Tests
# =============================================================================


class TestDeepStructuresHypothesis:
    """
    Property-based tests for deep directory structures using Hypothesis.

    These tests use random generation to explore edge cases and verify
    that invariants hold across a wide range of inputs.
    """

    @given(depth=st.integers(min_value=1, max_value=80))
    @settings(max_examples=20, deadline=30000)
    def test_hypothesis_no_recursion_error_random_depth(self, tmp_path_factory, depth):
        """
        No RecursionError occurs for any random depth up to 80.

        Purpose:
            Property test ensuring the iterative implementation never
            raises RecursionError regardless of depth.

        Property:
            For any depth d in [1, 80]: find_files() completes without
            RecursionError and returns exactly d files.

        Note:
            Max depth limited to 80 to stay within macOS path length limit (1024 chars).
            Extreme depths (1000+) are tested via mocking in TestDeepStructuresWithMock.
        """
        tmp_path = tmp_path_factory.mktemp(f"depth_{depth}")

        # Create structure
        current_path = tmp_path
        for level in range(depth):
            file_path = current_path / f"file_{level}.txt"
            file_path.write_text(f"Level {level}")

            if level < depth - 1:
                next_dir = current_path / f"level_{level}"
                next_dir.mkdir()
                current_path = next_dir

        discovery = FileDiscovery()

        # This should never raise RecursionError
        try:
            found_files = discovery.find_files(tmp_path)
            assert len(found_files) == depth
        except RecursionError:
            pytest.fail(f"RecursionError raised at depth {depth}")

    @given(
        total_depth=st.integers(min_value=10, max_value=60),
        max_depth=st.integers(min_value=1, max_value=30),
    )
    @settings(max_examples=15, deadline=30000)
    def test_hypothesis_max_depth_limits_results(
        self, tmp_path_factory, total_depth, max_depth
    ):
        """
        max_depth always limits results to at most (max_depth + 1) files.

        Purpose:
            Property test ensuring max_depth correctly bounds the result
            set regardless of actual structure depth.

        Property:
            For any structure with depth D and max_depth M where M < D:
            len(find_files()) <= M + 1 (with 1 file per level).
            Files at depths 0 through M are found (M + 1 files total).

        Note:
            Max values reduced to stay within macOS path length limits.
        """
        # Ensure max_depth is less than total_depth for meaningful test
        if max_depth >= total_depth:
            max_depth = total_depth - 1 if total_depth > 1 else 1

        tmp_path = tmp_path_factory.mktemp(f"depth_{total_depth}_max_{max_depth}")

        # Create structure
        current_path = tmp_path
        for level in range(total_depth):
            file_path = current_path / f"file_{level}.txt"
            file_path.write_text(f"Level {level}")

            if level < total_depth - 1:
                next_dir = current_path / f"level_{level}"
                next_dir.mkdir()
                current_path = next_dir

        discovery = FileDiscovery()
        found_files = discovery.find_files(tmp_path, max_depth=max_depth)

        # max_depth limits files: depths 0 through max_depth are found (max_depth + 1 files)
        expected_max_files = max_depth + 1
        assert len(found_files) <= expected_max_files, (
            f"max_depth={max_depth} should limit results to at most {expected_max_files} "
            f"files, got {len(found_files)}"
        )

    @given(depth=st.integers(min_value=5, max_value=40))
    @settings(max_examples=10, deadline=30000)
    def test_hypothesis_include_hidden_false_skips_hidden(
        self, tmp_path_factory, depth
    ):
        """
        include_hidden=False always skips hidden directories at any depth.

        Purpose:
            Property test ensuring hidden directories are consistently
            skipped regardless of their position in the structure.

        Property:
            For any structure with a hidden directory at level L:
            find_files(include_hidden=False) returns no files from level > L.
        """
        tmp_path = tmp_path_factory.mktemp(f"hidden_depth_{depth}")

        # Place hidden directory at approximately half depth
        hidden_level = depth // 2

        current_path = tmp_path
        for level in range(depth):
            file_path = current_path / f"file_{level}.txt"
            file_path.write_text(f"Level {level}")

            if level < depth - 1:
                if level == hidden_level:
                    next_dir = current_path / f".hidden_level_{level}"
                else:
                    next_dir = current_path / f"level_{level}"
                next_dir.mkdir()
                current_path = next_dir

        discovery = FileDiscovery()
        found_files = discovery.find_files(tmp_path, include_hidden=False)

        # Should only find files before the hidden directory
        expected_max_files = hidden_level + 1  # Levels 0 through hidden_level
        assert len(found_files) <= expected_max_files, (
            f"Expected at most {expected_max_files} files (before hidden at level "
            f"{hidden_level}), got {len(found_files)}"
        )

    @given(
        depth=st.integers(min_value=2, max_value=30),
        files_per_level=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=10, deadline=30000)
    def test_hypothesis_file_count_matches_structure(
        self, tmp_path_factory, depth, files_per_level
    ):
        """
        Total file count always matches depth × files_per_level.

        Purpose:
            Property test ensuring file discovery is complete and accurate.

        Property:
            For any structure with depth D and F files per level:
            len(find_files()) == D × F
        """
        tmp_path = tmp_path_factory.mktemp(f"depth_{depth}_files_{files_per_level}")

        # Create structure with multiple files per level
        current_path = tmp_path
        for level in range(depth):
            for i in range(files_per_level):
                file_path = current_path / f"file_{level}_{i}.txt"
                file_path.write_text(f"Level {level}, file {i}")

            if level < depth - 1:
                next_dir = current_path / f"level_{level}"
                next_dir.mkdir()
                current_path = next_dir

        discovery = FileDiscovery()
        found_files = discovery.find_files(tmp_path)

        expected_count = depth * files_per_level
        assert len(found_files) == expected_count, (
            f"Expected {expected_count} files ({depth} levels × {files_per_level} "
            f"files), got {len(found_files)}"
        )
