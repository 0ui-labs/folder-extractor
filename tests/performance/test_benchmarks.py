"""
Performance benchmarks for critical operations.
"""

import shutil
import statistics
import sys
import tempfile
import time
from pathlib import Path

import pytest

from folder_extractor.main import (
    entferne_leere_ordner,
    finde_dateien,
    generiere_eindeutigen_namen,
    verschiebe_dateien,
)


class BenchmarkTimer:
    """Context manager for timing operations."""

    def __init__(self, name):
        self.name = name
        self.start_time = None
        self.end_time = None
        self.duration = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.duration = self.end_time - self.start_time
        print(f"\n{self.name}: {self.duration:.4f} seconds")


def create_file_tree(base_path, num_files, depth, files_per_dir=10):
    """Create a file tree for testing."""
    created_files = []

    def create_level(path, current_depth):
        if current_depth > depth:
            return

        # Create files at this level
        for i in range(files_per_dir):
            file_path = path / f"file_{current_depth}_{i}.txt"
            file_path.write_text(f"Content at depth {current_depth}, file {i}")
            created_files.append(str(file_path))

        # Create subdirectories and recurse
        if current_depth < depth:
            for i in range(3):  # 3 subdirs per level
                subdir = path / f"subdir_{current_depth}_{i}"
                subdir.mkdir(exist_ok=True)
                create_level(subdir, current_depth + 1)

    create_level(Path(base_path), 0)
    return created_files


def create_deep_linear_structure(base_path, depth, files_per_level=5):
    """Create a deep linear directory structure efficiently without recursion.

    Creates a single chain of nested directories: d0/d1/.../dN with short names
    to avoid hitting filesystem PATH_MAX limits (typically 1024 bytes on macOS).
    Uses iterative approach to avoid RecursionError even for depths exceeding
    Python's recursion limit.

    Args:
        base_path: Base directory for the structure
        depth: Number of nested levels to create
        files_per_level: Number of files to create at each level (default: 5)

    Returns:
        List of created file paths
    """
    created_files = []
    current_path = Path(base_path)

    for level in range(depth):
        # Use short names to maximize depth before hitting PATH_MAX
        level_dir = current_path / f"d{level}"
        level_dir.mkdir(exist_ok=True)

        # Create files at this level with short names
        for file_idx in range(files_per_level):
            file_path = level_dir / f"f{file_idx}.txt"
            file_path.write_text(f"{level}_{file_idx}")
            created_files.append(str(file_path))

        # Move to next level
        current_path = level_dir

    return created_files


class TestFileDiscoveryPerformance:
    """Benchmark file discovery operations."""

    @pytest.mark.benchmark
    def test_find_files_flat_structure(self):
        """Benchmark finding files in flat structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create 1000 files in a subdirectory (finde_dateien skips root dir)
            print("\nCreating 1000 files in flat structure...")
            subdir = Path(temp_dir) / "subdir"
            subdir.mkdir()
            for i in range(1000):
                (subdir / f"file_{i:04d}.txt").touch()

            # Benchmark finding files
            with BenchmarkTimer("Find 1000 files (flat)"):
                files = finde_dateien(temp_dir)

            assert len(files) == 1000

    @pytest.mark.benchmark
    def test_find_files_deep_structure(self):
        """Benchmark finding files in deep structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create deep structure
            print("\nCreating deep file structure...")
            created = create_file_tree(temp_dir, 1000, depth=5)

            # Benchmark finding files
            with BenchmarkTimer("Find files (deep structure)"):
                files = finde_dateien(temp_dir, max_tiefe=0)

            # Note: finde_dateien skips files in root directory (depth 0),
            # so we expect slightly fewer files than created (minus 10 root files)
            assert len(files) >= len(created) - 10

    @pytest.mark.benchmark
    def test_find_files_with_filtering(self):
        """Benchmark finding files with type filtering."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mixed file types in a subdirectory (finde_dateien skips root dir)
            print("\nCreating mixed file types...")
            subdir = Path(temp_dir) / "subdir"
            subdir.mkdir()
            extensions = [".txt", ".pdf", ".jpg", ".doc", ".mp3"]
            for i in range(1000):
                ext = extensions[i % len(extensions)]
                (subdir / f"file_{i:04d}{ext}").touch()

            # Benchmark finding only txt and pdf files
            with BenchmarkTimer("Find files with type filter"):
                files = finde_dateien(temp_dir, dateityp_filter=[".txt", ".pdf"])

            assert len(files) == 400  # 200 txt + 200 pdf

    @pytest.mark.benchmark
    def test_find_files_extreme_depth_100(self):
        """Benchmark finding files in 100-level deep structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            print("\nCreating 100-level deep structure...")
            create_deep_linear_structure(temp_dir, depth=100, files_per_level=5)

            with BenchmarkTimer("Find files (100 levels deep)"):
                files = finde_dateien(temp_dir, max_tiefe=0)

            assert len(files) == 100 * 5, f"Expected 500 files, got {len(files)}"
            print(f"✓ Found {len(files)} files across 100 levels")

    @pytest.mark.benchmark
    def test_find_files_extreme_depth_200(self):
        """Benchmark finding files in 200-level deep structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            print("\nCreating 200-level deep structure...")
            create_deep_linear_structure(temp_dir, depth=200, files_per_level=5)

            with BenchmarkTimer("Find files (200 levels deep)"):
                files = finde_dateien(temp_dir, max_tiefe=0)

            assert len(files) == 200 * 5, f"Expected 1000 files, got {len(files)}"
            print(f"✓ Found {len(files)} files across 200 levels")

    @pytest.mark.benchmark
    def test_find_files_deep_iterative_no_recursion_error(self):
        """Verify iterative os.walk() approach works without RecursionError.

        Note: Filesystem PATH_MAX limits (~1024 bytes on macOS) restrict actual
        depth more than Python's recursion limit. This test verifies the iterative
        approach handles deep structures correctly.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Use 150 levels - safe for PATH_MAX while demonstrating iterative approach
            depth = 150
            print(f"\nCreating {depth}-level deep structure...")
            print(
                f"(Python recursion limit: {sys.getrecursionlimit()}, but PATH_MAX is the real limit)"
            )
            create_deep_linear_structure(temp_dir, depth=depth, files_per_level=5)

            with BenchmarkTimer(f"Find files ({depth} levels deep - iterative)"):
                files = finde_dateien(temp_dir, max_tiefe=0)

            assert len(files) == depth * 5, (
                f"Expected {depth * 5} files, got {len(files)}"
            )
            print(f"✓ Iterative os.walk() successfully handled {depth} levels")
            print(f"✓ Found {len(files)} files without RecursionError")

    @pytest.mark.benchmark
    def test_find_files_max_depth_on_deep_structure(self):
        """Benchmark max_depth parameter efficiency on deep structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            structure_depth = 150
            print(
                f"\nBenchmarking max_depth parameter on {structure_depth}-level structure..."
            )
            create_deep_linear_structure(
                temp_dir, depth=structure_depth, files_per_level=5
            )

            # Test various max_depth values
            depth_values = [10, 50, 100, 0]  # 0 = unlimited
            results = []

            for depth in depth_values:
                depth_label = "unlimited" if depth == 0 else str(depth)
                with BenchmarkTimer(f"Find files (max_depth={depth_label})"):
                    files = finde_dateien(temp_dir, max_tiefe=depth)

                expected = structure_depth * 5 if depth == 0 else depth * 5
                assert len(files) == expected, (
                    f"max_depth={depth}: expected {expected}, got {len(files)}"
                )
                print(f"  max_depth={depth_label}: {len(files)} files found")
                results.append((depth_label, len(files)))

            print("\n📊 max_depth efficiency summary:")
            for label, count in results:
                print(f"  {label}: {count} files")

    @pytest.mark.benchmark
    def test_compare_flat_vs_deep_structures(self):
        """Compare performance between flat and deep structures with same file count."""
        print("\nComparing flat vs. deep structure performance...")

        # Test with 500 files total (100 levels × 5 files = 100 folders × 5 files)
        levels = 100
        files_per_level = 5
        total_files = levels * files_per_level

        # Flat structure: 100 subdirectories with 5 files each (depth 1)
        with tempfile.TemporaryDirectory() as temp_dir:
            print(
                f"Creating flat structure ({levels} folders × {files_per_level} files, depth 1)..."
            )
            for folder_idx in range(levels):
                folder = Path(temp_dir) / f"f{folder_idx}"
                folder.mkdir()
                for file_idx in range(files_per_level):
                    (folder / f"f{file_idx}.txt").write_text(f"{folder_idx}_{file_idx}")

            with BenchmarkTimer("Find files (flat structure)") as flat_timer:
                flat_files = finde_dateien(temp_dir, max_tiefe=0)

            assert len(flat_files) == total_files, (
                f"Flat: expected {total_files}, got {len(flat_files)}"
            )
            flat_time = flat_timer.duration

        # Deep structure: 100 levels with 5 files each
        with tempfile.TemporaryDirectory() as temp_dir:
            print(
                f"Creating deep structure ({levels} levels × {files_per_level} files)..."
            )
            create_deep_linear_structure(
                temp_dir, depth=levels, files_per_level=files_per_level
            )

            with BenchmarkTimer("Find files (deep structure)") as deep_timer:
                deep_files = finde_dateien(temp_dir, max_tiefe=0)

            assert len(deep_files) == total_files, (
                f"Deep: expected {total_files}, got {len(deep_files)}"
            )
            deep_time = deep_timer.duration

        # Print comparison
        ratio = deep_time / flat_time if flat_time > 0 else float("inf")
        print(f"\n📊 Performance Comparison ({total_files} files):")
        print(f"  Flat: {flat_time:.4f}s vs Deep: {deep_time:.4f}s")
        print(f"  Deep/Flat ratio: {ratio:.2f}x")


class TestFileMovePerformance:
    """Benchmark file moving operations."""

    @pytest.mark.benchmark
    def test_move_many_small_files(self, safe_test_dir):
        """Benchmark moving many small files."""
        source_dir = Path(safe_test_dir) / "source"
        source_dir.mkdir(exist_ok=True)

        # Create 500 small files
        print("\nCreating 500 small files...")
        files = []
        for i in range(500):
            file_path = source_dir / f"file_{i:04d}.txt"
            file_path.write_text(f"Small content {i}")
            files.append(str(file_path))

        # Benchmark moving
        with BenchmarkTimer("Move 500 small files"):
            moved, _errors, _duplicates, _history = verschiebe_dateien(
                files, safe_test_dir, dry_run=False
            )

        assert moved == 500

    @pytest.mark.benchmark
    def test_move_large_files(self, safe_test_dir):
        """Benchmark moving large files."""
        source_dir = Path(safe_test_dir) / "source"
        source_dir.mkdir(exist_ok=True)

        # Create 10 large files (1MB each)
        print("\nCreating 10 large files (1MB each)...")
        files = []
        large_content = "x" * (1024 * 1024)  # 1MB
        for i in range(10):
            file_path = source_dir / f"large_{i}.dat"
            file_path.write_text(large_content)
            files.append(str(file_path))

        # Benchmark moving
        with BenchmarkTimer("Move 10 large files (1MB each)"):
            moved, _errors, _duplicates, _history = verschiebe_dateien(
                files, safe_test_dir, dry_run=False
            )

        assert moved == 10

    @pytest.mark.benchmark
    def test_move_with_many_duplicates(self, safe_test_dir):
        """Benchmark moving files with many duplicates."""
        source_dir = Path(safe_test_dir) / "source"
        source_dir.mkdir(exist_ok=True)

        # Create existing files in destination (10 files)
        print("\nCreating existing files for duplicate testing...")
        for i in range(10):
            Path(safe_test_dir, f"duplicate_{i}.txt").touch()

        # Create 100 unique source files that will conflict with the 10 existing names
        # Each of the 10 names will have 10 source files trying to use it
        files = []
        for i in range(100):
            # Use unique subdirectories to have unique source paths
            subdir = source_dir / f"batch_{i}"
            subdir.mkdir(exist_ok=True)
            file_path = subdir / f"duplicate_{i % 10}.txt"
            file_path.write_text(f"New content {i}")
            files.append(str(file_path))

        # Benchmark moving with duplicate handling
        with BenchmarkTimer("Move 100 files with duplicates"):
            moved, errors, duplicates, history = verschiebe_dateien(
                files, safe_test_dir, dry_run=False
            )

        assert moved == 100
        assert duplicates == 100


class TestUniqueNamePerformance:
    """Benchmark unique name generation."""

    @pytest.mark.benchmark
    def test_unique_name_no_conflicts(self):
        """Benchmark unique name generation with no conflicts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            times = []

            print("\nBenchmarking unique name generation (no conflicts)...")
            for i in range(1000):
                start = time.perf_counter()
                generiere_eindeutigen_namen(temp_dir, f"test_{i}.txt")
                end = time.perf_counter()
                times.append(end - start)

            avg_time = statistics.mean(times)
            print(f"Average time per generation: {avg_time * 1000:.4f} ms")
            print(f"Total time for 1000 generations: {sum(times):.4f} seconds")

    @pytest.mark.benchmark
    def test_unique_name_many_conflicts(self):
        """Benchmark unique name generation with many conflicts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create many conflicting files
            print("\nCreating 100 conflicting files...")
            base_name = "conflict.txt"
            Path(temp_dir, base_name).touch()
            for i in range(1, 100):
                Path(temp_dir, f"conflict_{i}.txt").touch()

            # Benchmark finding next available name
            with BenchmarkTimer("Generate unique name with 100 conflicts"):
                name = generiere_eindeutigen_namen(temp_dir, base_name)

            assert name == "conflict_100.txt"


class TestEmptyFolderCleanupPerformance:
    """Benchmark empty folder cleanup."""

    @pytest.mark.benchmark
    def test_cleanup_many_empty_folders(self):
        """Benchmark cleaning up many empty folders."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create deep structure of empty folders
            print("\nCreating 1000 empty folders...")
            for i in range(100):
                for j in range(10):
                    path = Path(temp_dir) / f"level1_{i}" / f"level2_{j}"
                    path.mkdir(parents=True, exist_ok=True)

            # Benchmark cleanup
            with BenchmarkTimer("Clean up 1000 empty folders"):
                removed = entferne_leere_ordner(temp_dir)

            assert removed >= 1000

    @pytest.mark.benchmark
    def test_cleanup_mixed_folders(self):
        """Benchmark cleanup with mixed empty/non-empty folders."""
        with tempfile.TemporaryDirectory() as temp_dir:
            print("\nCreating mixed folder structure...")

            # Create some empty folders
            for i in range(500):
                Path(temp_dir, f"empty_{i}").mkdir()

            # Create some non-empty folders
            for i in range(500):
                folder = Path(temp_dir, f"full_{i}")
                folder.mkdir()
                (folder / "file.txt").touch()

            # Benchmark cleanup
            with BenchmarkTimer("Clean up mixed structure (500 empty, 500 full)"):
                removed = entferne_leere_ordner(temp_dir)

            assert removed == 500


def run_all_benchmarks():
    """Run all benchmarks and print summary."""
    print("\n" + "=" * 60)
    print("Running Folder Extractor Performance Benchmarks")
    print("=" * 60)

    print("\n📊 Deep Structure Benchmarks:")
    print("Testing resistance to RecursionError and performance at extreme depths")
    print(f"Python recursion limit: {sys.getrecursionlimit()}")

    # Run each benchmark class
    benchmark_classes = [
        TestFileDiscoveryPerformance,
        TestFileMovePerformance,
        TestUniqueNamePerformance,
        TestEmptyFolderCleanupPerformance,
    ]

    for cls in benchmark_classes:
        print(f"\n\n{cls.__name__}:")
        print("-" * 40)

        instance = cls()
        for method_name in dir(instance):
            if method_name.startswith("test_") and callable(
                getattr(instance, method_name)
            ):
                method = getattr(instance, method_name)
                try:
                    method()
                except TypeError:
                    # Method needs safe_test_dir
                    desktop = Path.home() / "Desktop" / "benchmark_test"
                    desktop.mkdir(exist_ok=True)
                    try:
                        method(str(desktop))
                    finally:
                        if desktop.exists():
                            shutil.rmtree(desktop)

    print("\n\n📈 Performance Insights:")
    print("- Iterative os.walk() handles deep structures without RecursionError")
    print("- Filesystem PATH_MAX (~1024 bytes) limits depth more than Python recursion")
    print("- max_depth parameter efficiently prunes traversal")
    print("- Deep structures show linear performance scaling")

    print("\n" + "=" * 60)
    print("Benchmark Summary Complete")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_all_benchmarks()
