# Pain Points: test_file_operations.py Path Migration

## Overview
The test file `tests/unit/test_file_operations.py` uses `tempfile.TemporaryDirectory()` which returns string paths, while the project has standardized on using `pathlib.Path` objects. This creates inconsistency and violates the coding standard established for the test suite.

## Specific Pain Points

### 1. TemporaryDirectory Returns Strings
**Location**: Throughout all test classes (lines 22, 28, 37, etc.)

**Current State**:
```python
with tempfile.TemporaryDirectory() as temp_dir:
    name = generiere_eindeutigen_namen(temp_dir, "test.txt")  # temp_dir is str
```

**Problem**:
- `TemporaryDirectory()` context manager yields a string path
- Inconsistent with pytest's `tmp_path` fixture which yields Path objects
- Other test files in the project use `tmp_path` per standardization effort

**Impact**: Medium
- Code works but violates coding standards
- Inconsistent with rest of test suite
- Makes tests harder to maintain

### 2. Explicit str() Conversions
**Location**: Lines 92, 100, 116, 127, 284, 303, etc.

**Current State**:
```python
desktop_paths = [
    str(home / "Desktop"),  # Explicit conversion
    str(home / "Desktop" / "subfolder"),
]
assert ist_sicherer_pfad(str(downloads)) is True  # Line 116
assert pruefe_weblink_domain(str(url_file), ["youtube.com"]) is True  # Line 284
```

**Problem**:
- Functions are being called with string arguments when they could accept Path objects
- Creates unnecessary type conversions
- Makes code more verbose

**Impact**: Medium
- Code smell indicating API could be improved
- Harder to read

### 3. String Literal for Non-Existent Path
**Location**: Line 318

**Current State**:
```python
result = pruefe_weblink_domain("/nonexistent/file.url", ["any.com"])
```

**Problem**:
- Uses hardcoded string literal instead of Path object
- Inconsistent with Path-based approach
- Breaks on Windows (uses Unix-style path separator)

**Impact**: Low
- Functional issue on Windows
- Inconsistent style

### 4. Mixed Path/String Usage
**Location**: Throughout all tests

**Current State**:
```python
with tempfile.TemporaryDirectory() as temp_dir:  # str
    Path(temp_dir, "test.txt").touch()  # Converts to Path
    name = generiere_eindeutigen_namen(temp_dir, "test.txt")  # Back to str
```

**Problem**:
- Constant back-and-forth between str and Path
- Mental overhead tracking types
- Violates "use one type consistently" principle

**Impact**: High
- Reduces code clarity
- Makes refactoring harder
- Inconsistent with project standards

## Evidence from Codebase

**Other test files using tmp_path**:
- `tests/unit/test_core_functionality.py` - Uses `tmp_path` fixture
- `tests/integration/test_end_to_end.py` - Uses `tmp_path` fixture

**Project standard** (from review comment):
> "Wandle z.B. Aufrufe wie `generiere_eindeutigen_namen(temp_dir, ...)`, `entferne_leere_ordner(temp_dir)`, `ist_sicherer_pfad(str(downloads))` und `pruefe_weblink_domain(str(url_file), ...)` auf Path-Eingaben um"

## Priority
**Medium-High**: This refactoring is required to bring the test file in line with project standards established in recent commits.

## Risk Assessment
**Low Risk**:
- Pure test code refactoring
- No production code changes
- Tests should continue to pass if done incrementally
- Easy to verify (run tests after each step)
