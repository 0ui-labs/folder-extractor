# Current State: test_file_operations.py

## File Information
- **Path**: `tests/unit/test_file_operations.py`
- **Lines of Code**: 336
- **Test Classes**: 4
- **Test Methods**: 25
- **Dependencies**: `os`, `tempfile`, `pathlib.Path`

## Architecture Overview

```
test_file_operations.py
├── TestUniqueNameGeneration (7 tests)
│   ├── test_no_conflict
│   ├── test_single_conflict
│   ├── test_multiple_conflicts
│   ├── test_no_extension
│   ├── test_multiple_dots
│   ├── test_gap_in_numbering
│   └── test_high_numbers
├── TestSafePathValidation (7 tests)
│   ├── test_desktop_paths
│   ├── test_downloads_paths
│   ├── test_documents_paths
│   ├── test_unsafe_system_paths
│   ├── test_home_directory_rejected
│   ├── test_unsafe_home_subdirs
│   └── test_case_sensitivity
├── TestEmptyFolderRemoval (5 tests)
│   ├── test_remove_single_empty_folder
│   ├── test_keep_non_empty_folders
│   ├── test_nested_empty_folders
│   ├── test_mixed_empty_and_full
│   └── test_hidden_files_handling
└── TestWebLinkDomainCheck (6 tests)
    ├── test_url_file_parsing
    ├── test_webloc_file_parsing
    ├── test_invalid_file_format
    ├── test_nonexistent_file
    └── test_multiple_domains
```

## Current Implementation Pattern

### Temporary Directory Creation
**Current Pattern** (used in 20 out of 25 tests):
```python
with tempfile.TemporaryDirectory() as temp_dir:  # Returns str
    # Test code
```

**Exceptions**:
- `TestSafePathValidation` tests use actual filesystem paths (Desktop, Downloads, Documents)
- These tests don't need temporary directories

### Path Type Flow

```
┌─────────────────────────────────┐
│ TemporaryDirectory() → str      │
└────────────┬────────────────────┘
             │
             ├→ Path(temp_dir, "file.txt")  # Convert to Path for file creation
             │
             ├→ generiere_eindeutigen_namen(temp_dir, ...)  # Pass as str
             │
             ├→ entferne_leere_ordner(temp_dir, ...)  # Pass as str
             │
             └→ assert checks with Path(temp_dir) / "file"  # Convert back to Path
```

### Function Call Patterns

#### generiere_eindeutigen_namen()
**Occurrences**: 7 calls
**Current signature**: `generiere_eindeutigen_namen(directory: str, filename: str) → str`
**Call pattern**:
```python
name = generiere_eindeutigen_namen(temp_dir, "test.txt")  # temp_dir is str
```

#### entferne_leere_ordner()
**Occurrences**: 6 calls
**Current signature**: `entferne_leere_ordner(directory: str, include_hidden: bool = False) → int`
**Call pattern**:
```python
removed = entferne_leere_ordner(temp_dir)  # temp_dir is str
```

#### ist_sicherer_pfad()
**Occurrences**: 12 calls
**Current signature**: `ist_sicherer_pfad(path: str) → bool`
**Call patterns**:
```python
assert ist_sicherer_pfad(path) is True  # path is already str (from list)
assert ist_sicherer_pfad(str(downloads)) is True  # explicit str() conversion
```

#### pruefe_weblink_domain()
**Occurrences**: 8 calls
**Current signature**: `pruefe_weblink_domain(file_path: str, domains: list) → bool`
**Call patterns**:
```python
assert pruefe_weblink_domain(str(url_file), ["youtube.com"]) is True
result = pruefe_weblink_domain("/nonexistent/file.url", ["any.com"])  # string literal
```

## Complexity Metrics

### String ↔ Path Conversions
- **str → Path conversions**: ~45 occurrences
  - `Path(temp_dir)` or `Path(temp_dir, "file")`
- **Path → str conversions**: ~15 occurrences
  - `str(path)` for function calls
- **String literals**: ~8 occurrences
  - Hardcoded paths like `"/etc"`, `"/nonexistent/file.url"`

### Type Inconsistency Score
**Score**: 7/10 (High)
- Multiple type conversions per test method
- No consistent pattern (sometimes Path, sometimes str)
- Wrapper functions expect str, but test creates Path objects

## Dependencies on Current Implementation

### External Dependencies
- `tempfile.TemporaryDirectory` - provides string paths
- `pathlib.Path` - used for file operations
- Wrapper functions in `folder_extractor.main` - accept string arguments

### Internal Test Structure
- All tests are self-contained (no shared fixtures)
- No inter-test dependencies
- Cleanup handled by context managers

## Migration Considerations

### Safe to Change
✅ All temporary directory creation (20 tests)
✅ Path → str conversions (can be removed if functions accept Path)
✅ String literals for paths (can use Path objects)

### Requires Verification
⚠️ `TestSafePathValidation` - tests actual filesystem paths
⚠️ Cross-platform path handling (line 318: `/nonexistent/file.url`)

### No Changes Needed
✓ Test logic and assertions
✓ File content creation
✓ Cleanup logic

## Current Test Coverage
**All tests passing**: Yes
**Coverage**: Part of unit test suite (95%+ coverage target)

## Notes
- File created during recent standardization effort (commit 67f55fb)
- Other test files already migrated to `tmp_path` fixture
- This file was overlooked during the migration
