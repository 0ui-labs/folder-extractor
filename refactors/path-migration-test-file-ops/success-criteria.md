# Success Criteria: test_file_operations.py Path Migration

## Primary Goals

### 1. Complete Elimination of TemporaryDirectory
**Metric**: Zero usages of `tempfile.TemporaryDirectory()`

**Before**:
```python
import tempfile

with tempfile.TemporaryDirectory() as temp_dir:  # 20 occurrences
```

**After**:
```python
def test_example(tmp_path):  # pytest fixture, 0 TemporaryDirectory usages
```

**How to Measure**:
```bash
grep -c "TemporaryDirectory" tests/unit/test_file_operations.py
```
- **Current**: 20
- **Target**: 0

### 2. Path Objects Throughout
**Metric**: All wrapper function calls use Path objects, not strings

**Before**:
```python
generiere_eindeutigen_namen(temp_dir, "test.txt")  # temp_dir is str
ist_sicherer_pfad(str(downloads))  # explicit conversion
pruefe_weblink_domain(str(url_file), domains)  # explicit conversion
```

**After**:
```python
generiere_eindeutigen_namen(tmp_path, "test.txt")  # tmp_path is Path
ist_sicherer_pfad(downloads)  # no conversion needed
pruefe_weblink_domain(url_file, domains)  # no conversion needed
```

**How to Measure**:
```bash
# Count str() conversions in function calls
grep -c "str(" tests/unit/test_file_operations.py
```
- **Current**: ~15 str() calls
- **Target**: 0 str() calls to wrapper functions (some may remain for str paths in lists)

### 3. No String Path Literals
**Metric**: All path literals converted to Path objects

**Before**:
```python
result = pruefe_weblink_domain("/nonexistent/file.url", ["any.com"])
```

**After**:
```python
result = pruefe_weblink_domain(Path("/nonexistent/file.url"), ["any.com"])
```

**How to Measure**: Manual inspection of hardcoded paths
- **Current**: ~8 string literals
- **Target**: 0 string path literals (converted to Path)

### 4. Consistent tmp_path Usage
**Metric**: All test methods requiring temporary directories use `tmp_path` fixture

**Before**:
- 7/7 methods in `TestUniqueNameGeneration` use TemporaryDirectory
- 0/7 methods in `TestSafePathValidation` use TemporaryDirectory (use real paths)
- 5/5 methods in `TestEmptyFolderRemoval` use TemporaryDirectory
- 5/6 methods in `TestWebLinkDomainCheck` use TemporaryDirectory

**After**:
- 7/7 methods in `TestUniqueNameGeneration` use `tmp_path` fixture
- 0/7 methods in `TestSafePathValidation` use `tmp_path` (still use real paths - no change needed)
- 5/5 methods in `TestEmptyFolderRemoval` use `tmp_path` fixture
- 5/6 methods in `TestWebLinkDomainCheck` use `tmp_path` fixture

**How to Measure**: Count `tmp_path` parameters vs TemporaryDirectory context managers
- **Current**: 0 methods with `tmp_path` parameter
- **Target**: 17 methods with `tmp_path` parameter

## Secondary Goals

### 5. Reduced Type Conversions
**Metric**: Fewer str ↔ Path conversions

**Before**: ~60 type conversions (45 str→Path + 15 Path→str)
**After**: ~30 type conversions (only for Path→str where necessary)

**How to Measure**: Count `Path()` and `str()` calls
```bash
grep -o "Path(" tests/unit/test_file_operations.py | wc -l
grep -o "str(" tests/unit/test_file_operations.py | wc -l
```

### 6. Improved Readability
**Metric**: Subjective but measurable by reduced line complexity

**Before**:
```python
with tempfile.TemporaryDirectory() as temp_dir:
    empty_dir = Path(temp_dir) / "empty"
    removed = entferne_leere_ordner(temp_dir)
```

**After**:
```python
def test_example(tmp_path):
    empty_dir = tmp_path / "empty"
    removed = entferne_leere_ordner(tmp_path)
```

**How to Measure**: Lines of code reduction
- **Current**: 336 lines
- **Target**: ~310 lines (removing context manager boilerplate)

## Code Quality Metrics

### Type Safety
**Before**: Mixed str/Path types throughout
**After**: Consistent Path usage

### Cross-Platform Compatibility
**Before**: Hardcoded Unix paths (`"/nonexistent/file.url"`)
**After**: Platform-agnostic Path objects

### Compliance with Project Standards
**Before**: Inconsistent with other test files
**After**: Matches pattern in `test_core_functionality.py` and `test_end_to_end.py`

## Verification Checklist

After refactoring, the following must be true:

- [ ] All 25 tests still pass
- [ ] No `import tempfile` statement
- [ ] No `TemporaryDirectory()` usage
- [ ] All test methods use `tmp_path` parameter (where applicable)
- [ ] No `str()` conversions when calling wrapper functions
- [ ] No string path literals (except in domain lists and path content)
- [ ] Pyright passes with no new errors
- [ ] Coverage remains at 95%+
- [ ] Tests run in same or less time

## Success Definition

**The refactoring is successful when:**

1. ✅ All tests pass (pytest runs green)
2. ✅ Zero TemporaryDirectory usages
3. ✅ All wrapper function calls use Path objects
4. ✅ No platform-specific string paths
5. ✅ Code matches project conventions
6. ✅ Pyright type checking passes
7. ✅ Line count reduced by ~5-10%

## Measurement Commands

```bash
# Run tests
python run_tests.py

# Check for TemporaryDirectory
grep "TemporaryDirectory" tests/unit/test_file_operations.py

# Check for str() conversions
grep "str(" tests/unit/test_file_operations.py

# Type check
pyright tests/unit/test_file_operations.py

# Line count
wc -l tests/unit/test_file_operations.py
```

## Acceptance Criteria

**MUST HAVE** (blocking):
- All tests pass
- Zero TemporaryDirectory usages
- All tmp_path conversions complete

**SHOULD HAVE** (desirable):
- Reduced str() conversions
- Shorter file length
- Better readability

**NICE TO HAVE** (optional):
- Improved test organization
- Better comments
