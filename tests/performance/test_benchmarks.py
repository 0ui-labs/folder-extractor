"""
Performance benchmarks for critical operations.
"""
import os
import time
import pytest
from pathlib import Path
import tempfile
import shutil
import statistics

from folder_extractor.main import (
    finde_dateien,
    verschiebe_dateien,
    generiere_eindeutigen_namen,
    entferne_leere_ordner
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


class TestFileDiscoveryPerformance:
    """Benchmark file discovery operations."""
    
    @pytest.mark.benchmark
    def test_find_files_flat_structure(self):
        """Benchmark finding files in flat structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create 1000 files in single directory
            print("\nCreating 1000 files in flat structure...")
            for i in range(1000):
                Path(temp_dir, f"file_{i:04d}.txt").touch()
            
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
            
            assert len(files) >= len(created)
    
    @pytest.mark.benchmark
    def test_find_files_with_filtering(self):
        """Benchmark finding files with type filtering."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mixed file types
            print("\nCreating mixed file types...")
            extensions = [".txt", ".pdf", ".jpg", ".doc", ".mp3"]
            for i in range(1000):
                ext = extensions[i % len(extensions)]
                Path(temp_dir, f"file_{i:04d}{ext}").touch()
            
            # Benchmark finding only txt and pdf files
            with BenchmarkTimer("Find files with type filter"):
                files = finde_dateien(temp_dir, dateityp_filter=[".txt", ".pdf"])
            
            assert len(files) == 400  # 200 txt + 200 pdf


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
            moved, errors, duplicates, history = verschiebe_dateien(
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
            moved, errors, duplicates, history = verschiebe_dateien(
                files, safe_test_dir, dry_run=False
            )
        
        assert moved == 10
    
    @pytest.mark.benchmark
    def test_move_with_many_duplicates(self, safe_test_dir):
        """Benchmark moving files with many duplicates."""
        source_dir = Path(safe_test_dir) / "source"
        source_dir.mkdir(exist_ok=True)
        
        # Create existing files
        print("\nCreating existing files for duplicate testing...")
        for i in range(100):
            Path(safe_test_dir, f"duplicate_{i % 10}.txt").touch()
        
        # Create source files that will conflict
        files = []
        for i in range(100):
            file_path = source_dir / f"duplicate_{i % 10}.txt"
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
                name = generiere_eindeutigen_namen(temp_dir, f"test_{i}.txt")
                end = time.perf_counter()
                times.append(end - start)
            
            avg_time = statistics.mean(times)
            print(f"Average time per generation: {avg_time*1000:.4f} ms")
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
    print("\n" + "="*60)
    print("Running Folder Extractor Performance Benchmarks")
    print("="*60)
    
    # Run each benchmark class
    benchmark_classes = [
        TestFileDiscoveryPerformance,
        TestFileMovePerformance,
        TestUniqueNamePerformance,
        TestEmptyFolderCleanupPerformance
    ]
    
    for cls in benchmark_classes:
        print(f"\n\n{cls.__name__}:")
        print("-" * 40)
        
        instance = cls()
        for method_name in dir(instance):
            if method_name.startswith('test_') and hasattr(getattr(instance, method_name), '__call__'):
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
    
    print("\n\n" + "="*60)
    print("Benchmark Summary Complete")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_all_benchmarks()