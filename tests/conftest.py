"""
Pytest configuration and shared fixtures
"""

import hashlib
import shutil
import sys
from pathlib import Path

import pytest
from faker import Faker

# reset_state_manager is deprecated - no longer needed with dependency injection

# Add parent directory to path so we can import folder_extractor
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# Collection-time skip for Python 3.8 (google-generativeai not available)
# =============================================================================


def _can_import_google_generativeai() -> bool:
    """Check if google-generativeai module can be imported (Python 3.9+)."""
    try:
        import google.generativeai  # noqa: F401

        return True
    except ImportError:
        return False


# Conditionally ignore test files that require google-generativeai
# This prevents collection errors on Python 3.8
if not _can_import_google_generativeai():
    collect_ignore = [
        # Unit tests for API and CLI that depend on google-generativeai
        "unit/api/test_server.py",
        "unit/api/test_dependencies.py",
        "unit/api/test_endpoints.py",
        "unit/api/test_watcher_endpoints.py",
        "unit/test_cli_app.py",
        # Integration tests that import CLI
        "integration/test_archive_extraction.py",
        "integration/test_extraction_workflow.py",
        "integration/test_watch.py",
    ]


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing."""
    yield tmp_path
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
    yield desktop
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
    Reset global instances to ensure test isolation.

    With the migration to dependency injection, StateManager instances are now
    created per-component rather than shared globally. This fixture now only
    resets the Settings singleton which is still used for backward compatibility.

    Tests should use the state_manager_fixture for isolated StateManager instances
    rather than relying on global state.
    """
    import folder_extractor.config.settings
    from folder_extractor.config.settings import Settings

    # Reset global Settings instance
    folder_extractor.config.settings.settings = Settings()

    yield


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
    file_path = temp_dir / "test_binary.bin"
    content = b"Test binary content for hashing"
    file_path.write_bytes(content)
    expected_hash = hashlib.sha256(content).hexdigest()
    return file_path, expected_hash


# =============================================================================
# Settings Fixtures
# =============================================================================


@pytest.fixture
def settings_fixture():
    """Provide a fresh Settings instance for each test."""
    from folder_extractor.config.settings import Settings

    return Settings()


@pytest.fixture
def state_manager_fixture():
    """Provide a fresh StateManager instance for each test."""
    from folder_extractor.core.state_manager import StateManager

    return StateManager()
