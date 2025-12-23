"""
Pytest configuration and shared fixtures
"""

import hashlib
import shutil
import sys
from pathlib import Path

import pytest
from faker import Faker

from folder_extractor.core.state_manager import reset_state_manager

# Add parent directory to path so we can import folder_extractor
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing."""
    yield str(tmp_path)
    # Cleanup handled automatically by pytest


@pytest.fixture
def test_file_structure(temp_dir):
    """Create a standard test file structure."""
    base_path = Path(temp_dir)

    # Create directories
    (base_path / "subdir1").mkdir(parents=True)
    (base_path / "subdir2" / "nested").mkdir(parents=True)
    (base_path / ".hidden").mkdir(parents=True)
    (base_path / ".git" / "objects").mkdir(parents=True)

    # Create files
    files = {
        "file1.txt": "Content 1",
        "file2.pdf": "PDF content",
        "subdir1/file3.txt": "Content 3",
        "subdir1/file4.jpg": "Image content",
        "subdir2/file5.doc": "Doc content",
        "subdir2/nested/file6.txt": "Nested content",
        ".hidden/secret.txt": "Secret content",
        ".git/config": "Git config",
        ".git/HEAD": "ref: refs/heads/main",
        ".DS_Store": "System file",
    }

    created_files = []
    for file_path, content in files.items():
        full_path = str(base_path / file_path)
        with open(full_path, "w") as f:
            f.write(content)
        created_files.append(full_path)

    return temp_dir, created_files


@pytest.fixture
def safe_test_dir():
    """Create a test directory in a safe location (Desktop)."""
    desktop = Path.home() / "Desktop" / "folder_extractor_test"
    desktop.mkdir(exist_ok=True)
    yield str(desktop)
    # Cleanup
    if desktop.exists():
        shutil.rmtree(desktop)


@pytest.fixture
def mock_user_input(monkeypatch):
    """Helper to mock user input."""

    def _mock_input(inputs):
        input_iterator = iter(inputs)
        monkeypatch.setattr("builtins.input", lambda _: next(input_iterator))

    return _mock_input


# =============================================================================
# Faker Fixtures for Reproducible Test Data
# =============================================================================


@pytest.fixture(scope="session")
def faker_seed():
    """
    Provide a Faker instance with a fixed seed for reproducible test data.

    Session-scoped to maintain consistent sequences across all tests in a run.
    The fixed seed (42) ensures that generated data is deterministic.
    """
    fake = Faker()
    Faker.seed(42)
    return fake


@pytest.fixture
def random_filename(faker_seed):
    """
    Generate realistic random filenames for testing.

    Returns a callable that produces filenames with configurable extensions.
    Uses the seeded Faker instance for reproducibility.

    Usage:
        filename = random_filename()  # Returns e.g. "approach.txt"
        pdf_name = random_filename(extension=".pdf")  # Returns e.g. "market.pdf"
    """

    def _generate(extension: str = ".txt") -> str:
        # Use word() to get a simple, filesystem-safe name
        word = faker_seed.word()
        return f"{word}{extension}"

    return _generate


# =============================================================================
# Thread-Safety Fixtures for Parallel Test Execution
# =============================================================================


@pytest.fixture(autouse=True)
def reset_global_state():
    """
    Reset the global StateManager before each test.

    This autouse fixture ensures that each test starts with a clean state,
    preventing state leakage between tests during parallel execution with
    pytest-xdist (-n auto).
    """
    reset_state_manager()
    yield
    # Also reset after the test to clean up any modifications
    reset_state_manager()


# =============================================================================
# Hashing Fixtures
# =============================================================================


@pytest.fixture
def binary_test_file(temp_dir):
    """
    Create a binary test file with known content and pre-computed hash.

    Returns a tuple of (file_path, expected_sha256_hash) for use in
    hash verification tests.

    Usage:
        def test_hash(binary_test_file):
            file_path, expected_hash = binary_test_file
            result = calculate_hash(file_path)
            assert result == expected_hash
    """
    file_path = Path(temp_dir) / "test_binary.bin"
    content = b"Test binary content for hashing"
    file_path.write_bytes(content)
    expected_hash = hashlib.sha256(content).hexdigest()
    return str(file_path), expected_hash
