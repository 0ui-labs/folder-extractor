"""
Pytest configuration and shared fixtures
"""

import shutil
import sys
from pathlib import Path

import pytest

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
