# Refactoring Strategy: test_file_operations.py

## Refactoring Pattern Choice

**Selected Pattern**: **Parameter Object + Import Cleanup**

### Why This Pattern?

1. **Parameter Object** (pytest `tmp_path` fixture)
   - Replaces context manager boilerplate with cleaner fixture injection
   - Provides Path objects natively (no conversion needed)
   - Standard pytest pattern (matches other test files)

2. **Import Cleanup**
   - Remove `import tempfile` (no longer needed)
   - Keep `from pathlib import Path` (still needed for assertions)

### Alternative Patterns Considered

❌ **Wrapper Functions**: Create helper functions to convert Path ↔ str
- **Rejected**: Adds complexity, doesn't solve root problem

❌ **Monkey Patching**: Patch TemporaryDirectory to return Path
- **Rejected**: Too clever, breaks expectations

❌ **Keep TemporaryDirectory + Convert**: Wrap in Path() everywhere
- **Rejected**: Doesn't reduce type conversions

✅ **Parameter Object + Direct Usage**: Use tmp_path fixture, pass Path directly
- **Selected**: Cleanest, follows pytest conventions, reduces conversions

## Refactoring Strategy Details

### Core Strategy: Systematic Replacement

**Pattern to Follow**:

```python
# BEFORE
def test_something(self):
    with tempfile.TemporaryDirectory() as temp_dir:  # str
        file_path = Path(temp_dir) / "test.txt"  # convert to Path
        file_path.touch()
        result = some_function(temp_dir, ...)  # pass as str

# AFTER
def test_something(self, tmp_path):  # Path object from fixture
    file_path = tmp_path / "test.txt"  # already Path
    file_path.touch()
    result = some_function(tmp_path, ...)  # pass as Path
```

### Strategy Components

#### 1. Fixture Injection
**Change**: Add `tmp_path` parameter to test methods

```python
# Before
def test_no_conflict(self):

# After
def test_no_conflict(self, tmp_path):
```

**Rationale**: pytest's `tmp_path` fixture provides Path objects automatically

#### 2. Remove Context Managers
**Change**: Eliminate `with tempfile.TemporaryDirectory()` blocks

```python
# Before (4 lines + indentation)
def test_something(self):
    with tempfile.TemporaryDirectory() as temp_dir:
        empty_dir = Path(temp_dir) / "empty"
        removed = entferne_leere_ordner(temp_dir)

# After (3 lines, less indentation)
def test_something(self, tmp_path):
    empty_dir = tmp_path / "empty"
    removed = entferne_leere_ordner(tmp_path)
```

**Rationale**: Reduces boilerplate, simplifies code structure

#### 3. Direct Path Usage
**Change**: Use `tmp_path` directly instead of `Path(temp_dir)`

```python
# Before
Path(temp_dir) / "file.txt"
Path(temp_dir, "file.txt")

# After
tmp_path / "file.txt"
```

**Rationale**: `tmp_path` is already a Path object

#### 4. Remove str() Conversions
**Change**: Pass Path objects to wrapper functions

```python
# Before
ist_sicherer_pfad(str(downloads))
pruefe_weblink_domain(str(url_file), domains)

# After
ist_sicherer_pfad(downloads)
pruefe_weblink_domain(url_file, domains)
```

**Rationale**: Wrapper functions should accept Path objects (they already do via `__fspath__`)

#### 5. Path Literal Conversion
**Change**: Convert string literals to Path objects

```python
# Before
pruefe_weblink_domain("/nonexistent/file.url", domains)

# After
pruefe_weblink_domain(Path("/nonexistent/file.url"), domains)
```

**Rationale**: Cross-platform compatibility, type consistency

#### 6. Import Cleanup
**Change**: Remove unused tempfile import

```python
# Before
import os
import tempfile
from pathlib import Path

# After
import os
from pathlib import Path
```

**Rationale**: Clean up unused imports

## Test Class Strategy

### TestUniqueNameGeneration (7 tests)
**Approach**: Systematic replacement, all tests follow same pattern
- Add `tmp_path` parameter
- Remove `with tempfile.TemporaryDirectory()` block
- Reduce indentation level
- Replace `temp_dir` → `tmp_path`

**Risk**: Low (simple pattern repetition)

### TestSafePathValidation (7 tests)
**Approach**: Careful review - these don't use TemporaryDirectory!
- Only remove `str()` conversions where applicable
- Keep real filesystem path creation (Desktop, Downloads, Documents)
- Most tests don't need changes

**Risk**: Very Low (minimal changes)

### TestEmptyFolderRemoval (5 tests)
**Approach**: Same as TestUniqueNameGeneration
- Systematic replacement
- Remove context managers
- Pass Path objects

**Risk**: Low (consistent pattern)

### TestWebLinkDomainCheck (6 tests)
**Approach**: Mix of changes
- 5 tests: Replace TemporaryDirectory with tmp_path
- 1 test (`test_nonexistent_file`): Only fix string literal
- Remove `str()` conversions from file path arguments

**Risk**: Low-Medium (one test is different)

## Incremental Steps Ordering

### Phase 1: Import and Setup (1 commit)
- Remove `import tempfile`
- Verify tests still pass (should pass if imports unused)

### Phase 2: TestUniqueNameGeneration (1 commit)
- Convert all 7 tests to use `tmp_path`
- Verify tests pass

### Phase 3: TestSafePathValidation (1 commit)
- Remove `str()` conversions
- Keep real path usage
- Verify tests pass

### Phase 4: TestEmptyFolderRemoval (1 commit)
- Convert all 5 tests to use `tmp_path`
- Verify tests pass

### Phase 5: TestWebLinkDomainCheck (1 commit)
- Convert 5 tests to use `tmp_path`
- Fix string literal in `test_nonexistent_file`
- Verify tests pass

### Phase 6: Final Cleanup (1 commit)
- Any remaining str() conversions
- Any remaining style improvements
- Verify tests pass

## Risk Mitigation

### High-Risk Areas
**None identified** - All changes are straightforward

### Medium-Risk Areas
1. **TestSafePathValidation** - Uses real filesystem
   - **Mitigation**: Only remove explicit str() calls, don't change path construction

2. **test_nonexistent_file** - Uses hardcoded path
   - **Mitigation**: Simple string → Path() wrapper

### Low-Risk Areas
Everything else - pure TemporaryDirectory → tmp_path replacements

## Verification Strategy (Per Step)

After each phase:
1. Run tests: `python run_tests.py unit`
2. Check pyright: `pyright tests/unit/test_file_operations.py`
3. Visual inspection: code looks cleaner
4. If any fail → REVERT IMMEDIATELY

## Success Indicators

### During Refactoring
- ✅ Tests stay green after each commit
- ✅ Pyright stays clean (0 errors)
- ✅ Code gets progressively simpler
- ✅ Indentation levels decrease

### After Refactoring
- ✅ All success criteria met (see success-criteria.md)
- ✅ File is shorter (~10% reduction)
- ✅ No TemporaryDirectory usage
- ✅ No unnecessary str() conversions

## Justification

This strategy is chosen because:

1. **Proven Pattern**: tmp_path is standard pytest fixture
2. **Minimal Risk**: Each step is small and verifiable
3. **Incremental**: Can stop at any point if issues arise
4. **Reversible**: Each commit is atomic and can be reverted
5. **Measurable**: Clear before/after metrics
6. **Aligned with Project**: Matches other test files

## Alternative Approaches NOT Taken

### Big Bang Refactoring
**Rejected**: Too risky, hard to debug if something breaks

### Manual Testing Only
**Rejected**: Automated tests are our safety net

### Mixed Approach (Some tmp_path, some TemporaryDirectory)
**Rejected**: Inconsistent, defeats purpose

## Notes

- Wrapper functions (`generiere_eindeutigen_namen`, etc.) accept both str and Path via `os.fspath` protocol
- No changes to wrapper function implementations needed
- This is pure test refactoring, zero production code changes
