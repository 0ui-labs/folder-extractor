# Incremental Steps: test_file_operations.py Refactoring

## Overview

This refactoring is broken into 6 atomic steps. Each step MUST keep tests green.

**CRITICAL RULE**: Run tests after EVERY step. If red, REVERT immediately.

---

## Step 1: Remove Tempfile Import

**Goal**: Remove unused import after all TemporaryDirectory usage is eliminated
**Note**: This should be done LAST, but we verify it's removable first

### Pre-Step Verification
```bash
# Ensure tests pass
python run_tests.py unit

# Count TemporaryDirectory usage (should be 20)
grep -c "TemporaryDirectory" tests/unit/test_file_operations.py
```

**Expected**: 20 occurrences

### Change
Actually, SKIP this step for now. We'll do it at the very end after all conversions.

---

## Step 2: Convert TestUniqueNameGeneration (7 tests)

**Goal**: Replace all TemporaryDirectory with tmp_path in this test class
**Lines affected**: ~20-83

### Changes Required

#### Test 1: `test_no_conflict` (lines 20-24)

**Before**:
```python
def test_no_conflict(self):
    """Test when no file exists."""
    with tempfile.TemporaryDirectory() as temp_dir:
        name = generiere_eindeutigen_namen(temp_dir, "test.txt")
        assert name == "test.txt"
```

**After**:
```python
def test_no_conflict(self, tmp_path):
    """Test when no file exists."""
    name = generiere_eindeutigen_namen(tmp_path, "test.txt")
    assert name == "test.txt"
```

**Changes**:
1. Add `tmp_path` parameter to method signature
2. Remove `with tempfile.TemporaryDirectory() as temp_dir:` line
3. Remove indentation from method body
4. Replace `temp_dir` → `tmp_path`

#### Test 2: `test_single_conflict` (lines 26-33)

**Before**:
```python
def test_single_conflict(self):
    """Test with one existing file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create existing file
        Path(temp_dir, "test.txt").touch()

        name = generiere_eindeutigen_namen(temp_dir, "test.txt")
        assert name == "test_1.txt"
```

**After**:
```python
def test_single_conflict(self, tmp_path):
    """Test with one existing file."""
    # Create existing file
    (tmp_path / "test.txt").touch()

    name = generiere_eindeutigen_namen(tmp_path, "test.txt")
    assert name == "test_1.txt"
```

**Changes**:
1. Add `tmp_path` parameter
2. Remove context manager
3. Reduce indentation
4. Replace `Path(temp_dir, "test.txt")` → `(tmp_path / "test.txt")`
5. Replace `temp_dir` → `tmp_path`

#### Test 3: `test_multiple_conflicts` (lines 35-44)

**Before**:
```python
def test_multiple_conflicts(self):
    """Test with multiple existing files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create existing files
        Path(temp_dir, "test.txt").touch()
        Path(temp_dir, "test_1.txt").touch()
        Path(temp_dir, "test_2.txt").touch()

        name = generiere_eindeutigen_namen(temp_dir, "test.txt")
        assert name == "test_3.txt"
```

**After**:
```python
def test_multiple_conflicts(self, tmp_path):
    """Test with multiple existing files."""
    # Create existing files
    (tmp_path / "test.txt").touch()
    (tmp_path / "test_1.txt").touch()
    (tmp_path / "test_2.txt").touch()

    name = generiere_eindeutigen_namen(tmp_path, "test.txt")
    assert name == "test_3.txt"
```

#### Test 4: `test_no_extension` (lines 46-52)

**Before**:
```python
def test_no_extension(self):
    """Test files without extension."""
    with tempfile.TemporaryDirectory() as temp_dir:
        Path(temp_dir, "README").touch()

        name = generiere_eindeutigen_namen(temp_dir, "README")
        assert name == "README_1"
```

**After**:
```python
def test_no_extension(self, tmp_path):
    """Test files without extension."""
    (tmp_path / "README").touch()

    name = generiere_eindeutigen_namen(tmp_path, "README")
    assert name == "README_1"
```

#### Test 5: `test_multiple_dots` (lines 54-60)

**Before**:
```python
def test_multiple_dots(self):
    """Test files with multiple dots."""
    with tempfile.TemporaryDirectory() as temp_dir:
        Path(temp_dir, "archive.tar.gz").touch()

        name = generiere_eindeutigen_namen(temp_dir, "archive.tar.gz")
        assert name == "archive.tar_1.gz"
```

**After**:
```python
def test_multiple_dots(self, tmp_path):
    """Test files with multiple dots."""
    (tmp_path / "archive.tar.gz").touch()

    name = generiere_eindeutigen_namen(tmp_path, "archive.tar.gz")
    assert name == "archive.tar_1.gz"
```

#### Test 6: `test_gap_in_numbering` (lines 62-71)

**Before**:
```python
def test_gap_in_numbering(self):
    """Test when there's a gap in numbering."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create files with gap
        Path(temp_dir, "test.txt").touch()
        Path(temp_dir, "test_1.txt").touch()
        Path(temp_dir, "test_3.txt").touch()  # Gap at _2

        name = generiere_eindeutigen_namen(temp_dir, "test.txt")
        assert name == "test_2.txt"
```

**After**:
```python
def test_gap_in_numbering(self, tmp_path):
    """Test when there's a gap in numbering."""
    # Create files with gap
    (tmp_path / "test.txt").touch()
    (tmp_path / "test_1.txt").touch()
    (tmp_path / "test_3.txt").touch()  # Gap at _2

    name = generiere_eindeutigen_namen(tmp_path, "test.txt")
    assert name == "test_2.txt"
```

#### Test 7: `test_high_numbers` (lines 73-82)

**Before**:
```python
def test_high_numbers(self):
    """Test with high numbered files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create files up to 99
        Path(temp_dir, "test.txt").touch()
        for i in range(1, 100):
            Path(temp_dir, f"test_{i}.txt").touch()

        name = generiere_eindeutigen_namen(temp_dir, "test.txt")
        assert name == "test_100.txt"
```

**After**:
```python
def test_high_numbers(self, tmp_path):
    """Test with high numbered files."""
    # Create files up to 99
    (tmp_path / "test.txt").touch()
    for i in range(1, 100):
        (tmp_path / f"test_{i}.txt").touch()

    name = generiere_eindeutigen_namen(tmp_path, "test.txt")
    assert name == "test_100.txt"
```

### Post-Step Verification
```bash
# Run tests
python run_tests.py unit

# Check pyright
pyright tests/unit/test_file_operations.py

# Verify change count (should have 7 tmp_path parameters in TestUniqueNameGeneration)
grep -A 2 "class TestUniqueNameGeneration" tests/unit/test_file_operations.py | grep -c "tmp_path"
```

**Expected**: All tests pass, 0 pyright errors

---

## Step 3: Convert TestSafePathValidation (7 tests)

**Goal**: Remove unnecessary `str()` conversions
**Lines affected**: ~85-181

**NOTE**: Most of these tests use REAL filesystem paths, not temporary directories!

### Changes Required

#### Tests using str() explicitly (lines 92-100, 116, 127)

**Before** (line 100):
```python
assert ist_sicherer_pfad(path) is True
```

**No change needed** - `path` is already a string from the list

**Before** (line 116):
```python
assert ist_sicherer_pfad(str(downloads)) is True
```

**After**:
```python
assert ist_sicherer_pfad(downloads) is True
```

**Before** (line 127):
```python
assert ist_sicherer_pfad(str(documents)) is True
```

**After**:
```python
assert ist_sicherer_pfad(documents) is True
```

**Before** (line 149):
```python
assert ist_sicherer_pfad(str(Path.home())) is False
```

**After**:
```python
assert ist_sicherer_pfad(Path.home()) is False
```

### Post-Step Verification
```bash
python run_tests.py unit
pyright tests/unit/test_file_operations.py
```

**Expected**: All tests pass, fewer str() conversions

---

## Step 4: Convert TestEmptyFolderRemoval (5 tests)

**Goal**: Replace all TemporaryDirectory with tmp_path
**Lines affected**: ~183-268

### Changes Required

#### Test 1: `test_remove_single_empty_folder` (lines 186-195)

**Before**:
```python
def test_remove_single_empty_folder(self):
    """Test removing a single empty folder."""
    with tempfile.TemporaryDirectory() as temp_dir:
        empty_dir = Path(temp_dir) / "empty"
        empty_dir.mkdir()

        removed = entferne_leere_ordner(temp_dir)

        assert removed == 1
        assert not empty_dir.exists()
```

**After**:
```python
def test_remove_single_empty_folder(self, tmp_path):
    """Test removing a single empty folder."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    removed = entferne_leere_ordner(tmp_path)

    assert removed == 1
    assert not empty_dir.exists()
```

#### Test 2: `test_keep_non_empty_folders` (lines 197-208)

**Before**:
```python
def test_keep_non_empty_folders(self):
    """Test that non-empty folders are kept."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create folder with file
        non_empty = Path(temp_dir) / "non_empty"
        non_empty.mkdir()
        (non_empty / "file.txt").touch()

        removed = entferne_leere_ordner(temp_dir)

        assert removed == 0
        assert non_empty.exists()
```

**After**:
```python
def test_keep_non_empty_folders(self, tmp_path):
    """Test that non-empty folders are kept."""
    # Create folder with file
    non_empty = tmp_path / "non_empty"
    non_empty.mkdir()
    (non_empty / "file.txt").touch()

    removed = entferne_leere_ordner(tmp_path)

    assert removed == 0
    assert non_empty.exists()
```

#### Test 3: `test_nested_empty_folders` (lines 210-221)

**Before**:
```python
def test_nested_empty_folders(self):
    """Test removing nested empty folders."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create nested structure
        nested = Path(temp_dir) / "level1" / "level2" / "level3"
        nested.mkdir(parents=True)

        removed = entferne_leere_ordner(temp_dir)

        # Should remove all empty folders
        assert removed >= 3
        assert not (Path(temp_dir) / "level1").exists()
```

**After**:
```python
def test_nested_empty_folders(self, tmp_path):
    """Test removing nested empty folders."""
    # Create nested structure
    nested = tmp_path / "level1" / "level2" / "level3"
    nested.mkdir(parents=True)

    removed = entferne_leere_ordner(tmp_path)

    # Should remove all empty folders
    assert removed >= 3
    assert not (tmp_path / "level1").exists()
```

#### Test 4: `test_mixed_empty_and_full` (lines 223-246)

**Before**:
```python
def test_mixed_empty_and_full(self):
    """Test mixed empty and non-empty folders."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Empty folders
        (Path(temp_dir) / "empty1").mkdir()
        (Path(temp_dir) / "empty2").mkdir()

        # Non-empty folder
        full = Path(temp_dir) / "full"
        full.mkdir()
        (full / "file.txt").touch()

        # Nested with file at bottom
        nested = Path(temp_dir) / "nested" / "deep"
        nested.mkdir(parents=True)
        (nested / "file.txt").touch()

        removed = entferne_leere_ordner(temp_dir)

        assert removed == 2  # empty1 and empty2
        assert not (Path(temp_dir) / "empty1").exists()
        assert not (Path(temp_dir) / "empty2").exists()
        assert full.exists()
        assert nested.exists()
```

**After**:
```python
def test_mixed_empty_and_full(self, tmp_path):
    """Test mixed empty and non-empty folders."""
    # Empty folders
    (tmp_path / "empty1").mkdir()
    (tmp_path / "empty2").mkdir()

    # Non-empty folder
    full = tmp_path / "full"
    full.mkdir()
    (full / "file.txt").touch()

    # Nested with file at bottom
    nested = tmp_path / "nested" / "deep"
    nested.mkdir(parents=True)
    (nested / "file.txt").touch()

    removed = entferne_leere_ordner(tmp_path)

    assert removed == 2  # empty1 and empty2
    assert not (tmp_path / "empty1").exists()
    assert not (tmp_path / "empty2").exists()
    assert full.exists()
    assert nested.exists()
```

#### Test 5: `test_hidden_files_handling` (lines 248-268)

**Before**:
```python
def test_hidden_files_handling(self):
    """Test handling of hidden files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Folder with only hidden file
        hidden_only = Path(temp_dir) / "hidden_only"
        hidden_only.mkdir()
        (hidden_only / ".hidden").touch()

        # Test without include_hidden - should remove
        removed = entferne_leere_ordner(temp_dir, include_hidden=False)
        assert removed == 1
        assert not hidden_only.exists()

        # Recreate for second test
        hidden_only.mkdir()
        (hidden_only / ".hidden").touch()

        # Test with include_hidden - should keep
        removed = entferne_leere_ordner(temp_dir, include_hidden=True)
        assert removed == 0
        assert hidden_only.exists()
```

**After**:
```python
def test_hidden_files_handling(self, tmp_path):
    """Test handling of hidden files."""
    # Folder with only hidden file
    hidden_only = tmp_path / "hidden_only"
    hidden_only.mkdir()
    (hidden_only / ".hidden").touch()

    # Test without include_hidden - should remove
    removed = entferne_leere_ordner(tmp_path, include_hidden=False)
    assert removed == 1
    assert not hidden_only.exists()

    # Recreate for second test
    hidden_only.mkdir()
    (hidden_only / ".hidden").touch()

    # Test with include_hidden - should keep
    removed = entferne_leere_ordner(tmp_path, include_hidden=True)
    assert removed == 0
    assert hidden_only.exists()
```

### Post-Step Verification
```bash
python run_tests.py unit
pyright tests/unit/test_file_operations.py
```

---

## Step 5: Convert TestWebLinkDomainCheck (6 tests)

**Goal**: Replace TemporaryDirectory with tmp_path, fix string literals
**Lines affected**: ~271-336

### Changes Required

#### Test 1: `test_url_file_parsing` (lines 274-285)

**Before**:
```python
def test_url_file_parsing(self):
    """Test parsing of .url files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create .url file
        url_file = Path(temp_dir) / "test.url"
        url_file.write_text(
            "[InternetShortcut]\nURL=https://www.youtube.com/watch?v=123\n"
        )

        # Test matching domain
        assert pruefe_weblink_domain(str(url_file), ["youtube.com"]) is True
        assert pruefe_weblink_domain(str(url_file), ["github.com"]) is False
```

**After**:
```python
def test_url_file_parsing(self, tmp_path):
    """Test parsing of .url files."""
    # Create .url file
    url_file = tmp_path / "test.url"
    url_file.write_text(
        "[InternetShortcut]\nURL=https://www.youtube.com/watch?v=123\n"
    )

    # Test matching domain
    assert pruefe_weblink_domain(url_file, ["youtube.com"]) is True
    assert pruefe_weblink_domain(url_file, ["github.com"]) is False
```

#### Test 2: `test_webloc_file_parsing` (lines 287-304)

**Before**:
```python
def test_webloc_file_parsing(self):
    """Test parsing of .webloc files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create .webloc file
        webloc_file = Path(temp_dir) / "test.webloc"
        webloc_file.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<plist version="1.0">\n'
            "<dict>\n"
            "    <key>URL</key>\n"
            "    <string>https://github.com/user/repo</string>\n"
            "</dict>\n"
            "</plist>\n"
        )

        # Test matching domain
        assert pruefe_weblink_domain(str(webloc_file), ["github.com"]) is True
        assert pruefe_weblink_domain(str(webloc_file), ["youtube.com"]) is False
```

**After**:
```python
def test_webloc_file_parsing(self, tmp_path):
    """Test parsing of .webloc files."""
    # Create .webloc file
    webloc_file = tmp_path / "test.webloc"
    webloc_file.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<plist version="1.0">\n'
        "<dict>\n"
        "    <key>URL</key>\n"
        "    <string>https://github.com/user/repo</string>\n"
        "</dict>\n"
        "</plist>\n"
    )

    # Test matching domain
    assert pruefe_weblink_domain(webloc_file, ["github.com"]) is True
    assert pruefe_weblink_domain(webloc_file, ["youtube.com"]) is False
```

#### Test 3: `test_invalid_file_format` (lines 306-314)

**Before**:
```python
def test_invalid_file_format(self):
    """Test handling of invalid file formats."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create invalid file
        invalid_file = Path(temp_dir) / "test.url"
        invalid_file.write_text("This is not a valid URL file")

        # Should return False for invalid format
        assert pruefe_weblink_domain(str(invalid_file), ["any.com"]) is False
```

**After**:
```python
def test_invalid_file_format(self, tmp_path):
    """Test handling of invalid file formats."""
    # Create invalid file
    invalid_file = tmp_path / "test.url"
    invalid_file.write_text("This is not a valid URL file")

    # Should return False for invalid format
    assert pruefe_weblink_domain(invalid_file, ["any.com"]) is False
```

#### Test 4: `test_nonexistent_file` (lines 316-319)

**Before**:
```python
def test_nonexistent_file(self):
    """Test handling of nonexistent files."""
    result = pruefe_weblink_domain("/nonexistent/file.url", ["any.com"])
    assert result is False
```

**After**:
```python
def test_nonexistent_file(self):
    """Test handling of nonexistent files."""
    result = pruefe_weblink_domain(Path("/nonexistent/file.url"), ["any.com"])
    assert result is False
```

**Note**: No `tmp_path` parameter needed here!

#### Test 5: `test_multiple_domains` (lines 321-335)

**Before**:
```python
def test_multiple_domains(self):
    """Test checking against multiple domains."""
    with tempfile.TemporaryDirectory() as temp_dir:
        url_file = Path(temp_dir) / "test.url"
        url_file.write_text(
            "[InternetShortcut]\nURL=https://stackoverflow.com/questions/123\n"
        )

        # Test with multiple allowed domains
        domains = ["github.com", "youtube.com", "stackoverflow.com"]
        assert pruefe_weblink_domain(str(url_file), domains) is True

        # Test with non-matching domains
        domains = ["github.com", "youtube.com"]
        assert pruefe_weblink_domain(str(url_file), domains) is False
```

**After**:
```python
def test_multiple_domains(self, tmp_path):
    """Test checking against multiple domains."""
    url_file = tmp_path / "test.url"
    url_file.write_text(
        "[InternetShortcut]\nURL=https://stackoverflow.com/questions/123\n"
    )

    # Test with multiple allowed domains
    domains = ["github.com", "youtube.com", "stackoverflow.com"]
    assert pruefe_weblink_domain(url_file, domains) is True

    # Test with non-matching domains
    domains = ["github.com", "youtube.com"]
    assert pruefe_weblink_domain(url_file, domains) is False
```

### Post-Step Verification
```bash
python run_tests.py unit
pyright tests/unit/test_file_operations.py
```

---

## Step 6: Remove Tempfile Import

**Goal**: Clean up unused import
**Lines affected**: ~6

### Change

**Before**:
```python
import os
import tempfile
from pathlib import Path
```

**After**:
```python
import os
from pathlib import Path
```

### Post-Step Verification
```bash
python run_tests.py unit
pyright tests/unit/test_file_operations.py

# Verify no TemporaryDirectory usage
grep "TemporaryDirectory" tests/unit/test_file_operations.py
```

**Expected**: No matches, all tests pass

---

## Final Verification

After all steps:

```bash
# Run full test suite
python run_tests.py

# Run just this file
pytest tests/unit/test_file_operations.py -v

# Type check
pyright tests/unit/test_file_operations.py

# Check line count (should be ~310, down from 336)
wc -l tests/unit/test_file_operations.py

# Verify no TemporaryDirectory
grep "TemporaryDirectory" tests/unit/test_file_operations.py

# Verify no tempfile import
grep "import tempfile" tests/unit/test_file_operations.py

# Count tmp_path usage (should be 17)
grep -c "def test.*tmp_path" tests/unit/test_file_operations.py
```

**Success Criteria**:
- ✅ All tests pass
- ✅ 0 pyright errors
- ✅ ~310 lines (26 line reduction)
- ✅ 0 TemporaryDirectory usage
- ✅ 0 tempfile imports
- ✅ 17 tmp_path parameters

---

## Emergency Rollback

If anything goes wrong during any step:

```bash
# See what changed
git diff tests/unit/test_file_operations.py

# Revert all changes
git checkout tests/unit/test_file_operations.py

# Verify tests pass again
python run_tests.py unit
```

Then restart from the last successful step.
