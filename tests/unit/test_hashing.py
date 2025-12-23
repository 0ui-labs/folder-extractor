"""
Unit tests for file hashing functionality.

Tests for the calculate_file_hash method of FileOperations class.
Uses property-based testing with Hypothesis for comprehensive coverage.
"""

import hashlib
import platform
import stat
from pathlib import Path

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from folder_extractor.core.file_operations import FileOperationError, FileOperations

# =============================================================================
# Test-Klasse: Grundlegende Funktionalität
# =============================================================================


class TestCalculateFileHashBasic:
    """Basic functionality tests for calculate_file_hash."""

    def test_hash_empty_file(self, temp_dir):
        """Empty file produces the known SHA256 empty hash.

        The SHA256 hash of zero bytes is a well-known constant that serves
        as a regression test to verify the algorithm is correctly applied.
        """
        file_ops = FileOperations()
        file_path = Path(temp_dir) / "empty.bin"
        file_path.touch()  # Create empty file

        result = file_ops.calculate_file_hash(file_path)

        # Known SHA256 hash of empty content
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert result == expected

    def test_hash_small_file(self, temp_dir):
        """Small file (< 8KB) is hashed correctly.

        Verifies that files smaller than the internal chunk size are
        processed correctly in a single read operation.
        """
        file_ops = FileOperations()
        file_path = Path(temp_dir) / "small.txt"
        content = b"Hello, World!"
        file_path.write_bytes(content)

        result = file_ops.calculate_file_hash(file_path)

        expected = hashlib.sha256(content).hexdigest()
        assert result == expected

    def test_hash_large_file(self, temp_dir):
        """Large file (> 100KB) is hashed correctly using chunked reading.

        Verifies that files larger than the chunk size are processed
        correctly across multiple read operations.
        """
        file_ops = FileOperations()
        file_path = Path(temp_dir) / "large.bin"

        # Create file larger than typical chunk size (8KB)
        content = b"x" * 150_000  # 150KB
        file_path.write_bytes(content)

        result = file_ops.calculate_file_hash(file_path)

        expected = hashlib.sha256(content).hexdigest()
        assert result == expected

    def test_hash_binary_file(self, temp_dir):
        """Binary file with arbitrary bytes is hashed correctly.

        Ensures binary mode reading works for non-text content.
        """
        file_ops = FileOperations()
        file_path = Path(temp_dir) / "binary.bin"

        # Binary content with all byte values 0-255
        content = bytes(range(256)) * 10
        file_path.write_bytes(content)

        result = file_ops.calculate_file_hash(file_path)

        expected = hashlib.sha256(content).hexdigest()
        assert result == expected

    def test_default_algorithm_is_sha256(self, temp_dir):
        """SHA256 is used when no algorithm is specified.

        The default algorithm should be SHA256 for security and
        compatibility reasons.
        """
        file_ops = FileOperations()
        file_path = Path(temp_dir) / "test.txt"
        content = b"Test content"
        file_path.write_bytes(content)

        # Call without algorithm parameter
        result = file_ops.calculate_file_hash(file_path)

        # Verify it's SHA256 (64 hex characters)
        assert len(result) == 64
        assert result == hashlib.sha256(content).hexdigest()

    @pytest.mark.parametrize(
        "algorithm,expected_length",
        [
            ("md5", 32),
            ("sha1", 40),
            ("sha256", 64),
            ("sha512", 128),
        ],
    )
    def test_different_algorithms(self, temp_dir, algorithm, expected_length):
        """Different hash algorithms produce correct output lengths.

        Users may need different algorithms for compatibility or
        performance reasons.
        """
        file_ops = FileOperations()
        file_path = Path(temp_dir) / "test.txt"
        content = b"Test content for different algorithms"
        file_path.write_bytes(content)

        result = file_ops.calculate_file_hash(file_path, algorithm=algorithm)

        assert len(result) == expected_length
        expected = hashlib.new(algorithm, content).hexdigest()
        assert result == expected


# =============================================================================
# Test-Klasse: Property-Based Tests mit Hypothesis
# =============================================================================


class TestCalculateFileHashProperties:
    """Property-based tests for calculate_file_hash using Hypothesis."""

    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[
            HealthCheck.too_slow,
            HealthCheck.function_scoped_fixture,
        ],
    )
    @given(binary_content=st.binary(min_size=0, max_size=50000))
    def test_hash_deterministic(self, binary_content, tmp_path):
        """Hashing the same content twice produces identical results.

        This is a fundamental property: hash functions must be deterministic.
        """
        file_ops = FileOperations()
        # Use unique filename per hypothesis example to avoid conflicts
        file_path = tmp_path / f"deterministic_{hash(binary_content) % 10000}.bin"
        file_path.write_bytes(binary_content)

        hash1 = file_ops.calculate_file_hash(file_path)
        hash2 = file_ops.calculate_file_hash(file_path)

        assert hash1 == hash2

    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[
            HealthCheck.too_slow,
            HealthCheck.function_scoped_fixture,
        ],
    )
    @given(
        content1=st.binary(min_size=1, max_size=1000),
        content2=st.binary(min_size=1, max_size=1000),
    )
    def test_different_content_different_hash(self, content1, content2, tmp_path):
        """Different file contents produce different hashes.

        While hash collisions are theoretically possible, they should be
        extremely rare for SHA256.
        """
        assume(content1 != content2)

        file_ops = FileOperations()
        # Use unique filenames per hypothesis example
        suffix = hash((content1, content2)) % 10000
        file1 = tmp_path / f"file1_{suffix}.bin"
        file2 = tmp_path / f"file2_{suffix}.bin"
        file1.write_bytes(content1)
        file2.write_bytes(content2)

        hash1 = file_ops.calculate_file_hash(file1)
        hash2 = file_ops.calculate_file_hash(file2)

        assert hash1 != hash2

    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[
            HealthCheck.too_slow,
            HealthCheck.function_scoped_fixture,
        ],
    )
    @given(binary_content=st.binary(min_size=0, max_size=100000))
    def test_hash_format_valid(self, binary_content, tmp_path):
        """Hash output is a valid hexadecimal string of correct length.

        SHA256 produces 256 bits = 32 bytes = 64 hex characters.
        """
        file_ops = FileOperations()
        file_path = tmp_path / f"format_{hash(binary_content) % 10000}.bin"
        file_path.write_bytes(binary_content)

        result = file_ops.calculate_file_hash(file_path)

        # SHA256 = 64 hex characters
        assert len(result) == 64
        # All characters must be valid hex
        assert all(c in "0123456789abcdef" for c in result)

    @settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[
            HealthCheck.too_slow,
            HealthCheck.function_scoped_fixture,
        ],
    )
    @given(binary_content=st.binary(min_size=0, max_size=10000))
    def test_hash_matches_direct_hashlib(self, binary_content, tmp_path):
        """Hash matches direct hashlib computation on content.

        Verifies our chunked reading produces the same result as
        hashing the entire content at once.
        """
        file_ops = FileOperations()
        file_path = tmp_path / f"compare_{hash(binary_content) % 10000}.bin"
        file_path.write_bytes(binary_content)

        result = file_ops.calculate_file_hash(file_path)
        expected = hashlib.sha256(binary_content).hexdigest()

        assert result == expected


# =============================================================================
# Test-Klasse: Fehlerbehandlung
# =============================================================================


class TestCalculateFileHashErrors:
    """Error handling tests for calculate_file_hash."""

    def test_nonexistent_file_raises_error(self, temp_dir):
        """Non-existent file raises FileOperationError.

        Users need clear feedback when attempting to hash missing files.
        """
        file_ops = FileOperations()
        nonexistent = Path(temp_dir) / "does_not_exist.txt"

        with pytest.raises(FileOperationError) as exc_info:
            file_ops.calculate_file_hash(nonexistent)

        assert (
            "existiert nicht" in str(exc_info.value).lower()
            or "not exist" in str(exc_info.value).lower()
            or "nicht gefunden" in str(exc_info.value).lower()
        )

    def test_directory_raises_error(self, temp_dir):
        """Passing a directory instead of file raises FileOperationError.

        Directories cannot be hashed - only files.
        """
        file_ops = FileOperations()
        dir_path = Path(temp_dir) / "subdir"
        dir_path.mkdir()

        with pytest.raises(FileOperationError) as exc_info:
            file_ops.calculate_file_hash(dir_path)

        error_msg = str(exc_info.value).lower()
        assert (
            "verzeichnis" in error_msg
            or "directory" in error_msg
            or "keine datei" in error_msg
            or "not a file" in error_msg
        )

    def test_invalid_algorithm_raises_error(self, temp_dir):
        """Invalid hash algorithm raises ValueError.

        Users need feedback when specifying unsupported algorithms.
        """
        file_ops = FileOperations()
        file_path = Path(temp_dir) / "test.txt"
        file_path.write_bytes(b"test")

        with pytest.raises(ValueError):
            file_ops.calculate_file_hash(file_path, algorithm="invalid_algo")

    @pytest.mark.skipif(
        platform.system() == "Windows", reason="Permission handling differs on Windows"
    )
    def test_permission_denied_raises_error(self, temp_dir):
        """File without read permission raises FileOperationError.

        Permission errors should be caught and wrapped appropriately.
        """
        file_ops = FileOperations()
        file_path = Path(temp_dir) / "no_read.txt"
        file_path.write_bytes(b"secret content")

        # Remove read permission
        file_path.chmod(0o000)

        try:
            with pytest.raises(FileOperationError) as exc_info:
                file_ops.calculate_file_hash(file_path)

            error_msg = str(exc_info.value).lower()
            assert (
                "berechtigung" in error_msg
                or "permission" in error_msg
                or "zugriff" in error_msg
                or "access" in error_msg
            )
        finally:
            # Restore permissions for cleanup
            file_path.chmod(stat.S_IRUSR | stat.S_IWUSR)


# =============================================================================
# Test-Klasse: Spezialfälle (Edge Cases)
# =============================================================================


class TestCalculateFileHashEdgeCases:
    """Edge case tests for calculate_file_hash."""

    def test_hash_file_with_unicode_name(self, temp_dir):
        """File with Unicode characters (umlauts) in name is hashed correctly.

        German umlauts and other Unicode characters in filenames must work.
        """
        file_ops = FileOperations()
        file_path = Path(temp_dir) / "Übungsaufgabe_äöü.txt"
        content = b"Unicode filename test"
        file_path.write_bytes(content)

        result = file_ops.calculate_file_hash(file_path)

        expected = hashlib.sha256(content).hexdigest()
        assert result == expected

    def test_hash_file_with_spaces_in_name(self, temp_dir):
        """File with spaces in name is hashed correctly.

        Filenames with spaces are common and must be handled properly.
        """
        file_ops = FileOperations()
        file_path = Path(temp_dir) / "my document file.txt"
        content = b"Spaces in filename test"
        file_path.write_bytes(content)

        result = file_ops.calculate_file_hash(file_path)

        expected = hashlib.sha256(content).hexdigest()
        assert result == expected

    @pytest.mark.skipif(
        platform.system() == "Windows",
        reason="Symlinks require special permissions on Windows",
    )
    def test_hash_symlink(self, temp_dir):
        """Symbolic link is resolved and target file content is hashed.

        Symlinks should be followed to hash the actual file content.
        """
        file_ops = FileOperations()
        target_path = Path(temp_dir) / "target.txt"
        symlink_path = Path(temp_dir) / "link.txt"

        content = b"Symlink target content"
        target_path.write_bytes(content)
        symlink_path.symlink_to(target_path)

        result = file_ops.calculate_file_hash(symlink_path)

        expected = hashlib.sha256(content).hexdigest()
        assert result == expected

    def test_hash_file_accepts_string_path(self, temp_dir):
        """Method accepts both str and Path objects for filepath.

        API should be flexible in accepting path types.
        """
        file_ops = FileOperations()
        file_path = Path(temp_dir) / "string_path.txt"
        content = b"String path test"
        file_path.write_bytes(content)

        # Call with string instead of Path
        result = file_ops.calculate_file_hash(str(file_path))

        expected = hashlib.sha256(content).hexdigest()
        assert result == expected

    def test_hash_exactly_chunk_size(self, temp_dir):
        """File with exactly chunk size (8192 bytes) is hashed correctly.

        Boundary condition: file size equals internal buffer size.
        """
        file_ops = FileOperations()
        file_path = Path(temp_dir) / "exact_chunk.bin"

        # Exactly 8192 bytes (typical chunk size)
        content = b"A" * 8192
        file_path.write_bytes(content)

        result = file_ops.calculate_file_hash(file_path)

        expected = hashlib.sha256(content).hexdigest()
        assert result == expected

    def test_hash_chunk_size_plus_one(self, temp_dir):
        """File with chunk size + 1 byte is hashed correctly.

        Boundary condition: requires exactly 2 chunks.
        """
        file_ops = FileOperations()
        file_path = Path(temp_dir) / "chunk_plus_one.bin"

        # 8193 bytes - one more than chunk size
        content = b"B" * 8193
        file_path.write_bytes(content)

        result = file_ops.calculate_file_hash(file_path)

        expected = hashlib.sha256(content).hexdigest()
        assert result == expected
