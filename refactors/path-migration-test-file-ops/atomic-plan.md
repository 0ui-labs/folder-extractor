# Atomic Refactor Plan: test_file_operations.py

## Overview

This document maps each incremental step to a git commit. Each commit is atomic, reversible, and keeps tests green.

**Total Commits**: 5
**Estimated Time**: 30-45 minutes
**Test Run Per Commit**: Yes (mandatory)

---

## Commit 1: refactor(tests): Convert TestUniqueNameGeneration to use tmp_path

### Files Changed
- `tests/unit/test_file_operations.py`

### Changes
- Add `tmp_path` parameter to all 7 test methods in `TestUniqueNameGeneration`
- Remove `with tempfile.TemporaryDirectory() as temp_dir:` blocks
- Replace `temp_dir` → `tmp_path` throughout
- Replace `Path(temp_dir, ...)` → `(tmp_path / ...)`
- Reduce indentation from removing context managers

### Lines Affected
Lines 20-83 (~63 lines)

### Specific Methods
1. `test_no_conflict`
2. `test_single_conflict`
3. `test_multiple_conflicts`
4. `test_no_extension`
5. `test_multiple_dots`
6. `test_gap_in_numbering`
7. `test_high_numbers`

### Pre-Commit Verification
```bash
# Ensure starting point is clean
python run_tests.py unit
pyright tests/unit/test_file_operations.py
```

**Expected**: All pass, 0 errors

### Post-Commit Verification
```bash
# Make changes
# ...

# Test
python run_tests.py unit
pyright tests/unit/test_file_operations.py

# Visual inspection
git diff tests/unit/test_file_operations.py

# If all green, commit
git add tests/unit/test_file_operations.py
git commit -m "refactor(tests): Convert TestUniqueNameGeneration to use tmp_path

- Replace tempfile.TemporaryDirectory with pytest's tmp_path fixture
- Remove context manager boilerplate (7 occurrences)
- Use Path objects directly instead of string paths
- Reduce indentation level across all tests in class"
```

### Rollback Plan
```bash
git reset --soft HEAD~1
git checkout tests/unit/test_file_operations.py
```

---

## Commit 2: refactor(tests): Remove str() conversions in TestSafePathValidation

### Files Changed
- `tests/unit/test_file_operations.py`

### Changes
- Remove `str()` wrapper from `ist_sicherer_pfad` calls
- Keep Path objects as-is
- No TemporaryDirectory changes (these tests use real filesystem)

### Lines Affected
Lines 85-181 (~4 specific lines: 116, 127, 149)

### Specific Changes
- Line 116: `str(downloads)` → `downloads`
- Line 127: `str(documents)` → `documents`
- Line 149: `str(Path.home())` → `Path.home()`

### Post-Commit Verification
```bash
python run_tests.py unit
pyright tests/unit/test_file_operations.py

git add tests/unit/test_file_operations.py
git commit -m "refactor(tests): Remove str() conversions in TestSafePathValidation

- Remove unnecessary str() wrappers around Path objects
- ist_sicherer_pfad accepts Path objects via __fspath__ protocol
- No functional changes, cleaner code"
```

---

## Commit 3: refactor(tests): Convert TestEmptyFolderRemoval to use tmp_path

### Files Changed
- `tests/unit/test_file_operations.py`

### Changes
- Add `tmp_path` parameter to all 5 test methods in `TestEmptyFolderRemoval`
- Remove `with tempfile.TemporaryDirectory() as temp_dir:` blocks
- Replace `temp_dir` → `tmp_path` throughout
- Replace `Path(temp_dir)` → `tmp_path`
- Reduce indentation

### Lines Affected
Lines 183-268 (~85 lines)

### Specific Methods
1. `test_remove_single_empty_folder`
2. `test_keep_non_empty_folders`
3. `test_nested_empty_folders`
4. `test_mixed_empty_and_full`
5. `test_hidden_files_handling`

### Post-Commit Verification
```bash
python run_tests.py unit
pyright tests/unit/test_file_operations.py

git add tests/unit/test_file_operations.py
git commit -m "refactor(tests): Convert TestEmptyFolderRemoval to use tmp_path

- Replace tempfile.TemporaryDirectory with pytest's tmp_path fixture
- Remove context manager boilerplate (5 occurrences)
- Use Path objects directly instead of string paths
- Reduce indentation level across all tests in class"
```

---

## Commit 4: refactor(tests): Convert TestWebLinkDomainCheck to use tmp_path

### Files Changed
- `tests/unit/test_file_operations.py`

### Changes
- Add `tmp_path` parameter to 5 test methods (not `test_nonexistent_file`)
- Remove `with tempfile.TemporaryDirectory() as temp_dir:` blocks
- Replace `temp_dir` → `tmp_path` throughout
- Remove `str()` wrapper from `pruefe_weblink_domain` calls
- Fix string literal in `test_nonexistent_file`: `/nonexistent/file.url` → `Path("/nonexistent/file.url")`

### Lines Affected
Lines 271-336 (~65 lines)

### Specific Methods
1. `test_url_file_parsing` - add tmp_path
2. `test_webloc_file_parsing` - add tmp_path
3. `test_invalid_file_format` - add tmp_path
4. `test_nonexistent_file` - fix string literal (NO tmp_path)
5. `test_multiple_domains` - add tmp_path

### Post-Commit Verification
```bash
python run_tests.py unit
pyright tests/unit/test_file_operations.py

git add tests/unit/test_file_operations.py
git commit -m "refactor(tests): Convert TestWebLinkDomainCheck to use tmp_path

- Replace tempfile.TemporaryDirectory with pytest's tmp_path fixture (5 tests)
- Remove str() wrappers from pruefe_weblink_domain calls
- Fix hardcoded string path to Path object for cross-platform compatibility
- Remove context manager boilerplate"
```

---

## Commit 5: refactor(tests): Remove unused tempfile import

### Files Changed
- `tests/unit/test_file_operations.py`

### Changes
- Remove `import tempfile` line (line 6)
- Keep `import os` and `from pathlib import Path`

### Lines Affected
Line 6

### Post-Commit Verification
```bash
# Ensure no TemporaryDirectory usage
grep "TemporaryDirectory" tests/unit/test_file_operations.py
# Should return nothing

python run_tests.py unit
pyright tests/unit/test_file_operations.py

git add tests/unit/test_file_operations.py
git commit -m "refactor(tests): Remove unused tempfile import

- tempfile module no longer needed after tmp_path migration
- All tests now use pytest's tmp_path fixture
- Cleanup unused import"
```

---

## Final Verification Checklist

After all 5 commits:

### Functionality
- [ ] All 25 tests pass
- [ ] pyright shows 0 errors, 0 warnings
- [ ] Coverage unchanged (still 95%+)

### Code Quality
- [ ] No `import tempfile`
- [ ] No `TemporaryDirectory` usage
- [ ] No unnecessary `str()` conversions
- [ ] 17 methods using `tmp_path` parameter
- [ ] File reduced to ~310 lines (from 336)

### Git History
- [ ] 5 clean commits
- [ ] Each commit message follows convention
- [ ] Each commit is atomic and reversible

### Commands
```bash
# Full verification
python run_tests.py
pyright tests/unit/test_file_operations.py
wc -l tests/unit/test_file_operations.py

# Check imports
grep "import tempfile" tests/unit/test_file_operations.py  # Should be empty
grep "from pathlib import Path" tests/unit/test_file_operations.py  # Should exist

# Check tmp_path usage
grep -c "tmp_path" tests/unit/test_file_operations.py  # Should be 17

# Check TemporaryDirectory removal
grep "TemporaryDirectory" tests/unit/test_file_operations.py  # Should be empty
```

---

## Commit Message Template

All commits follow this structure:

```
refactor(tests): <Short summary>

- <Detailed change 1>
- <Detailed change 2>
- <Detailed change 3>
```

**Type**: `refactor` (not `test` - refactor emphasizes code improvement)
**Scope**: `tests` (affects test code)
**Body**: Bulleted list of specific changes

---

## Timeline

**Estimated Duration**: 30-45 minutes

- Commit 1: 10 minutes (7 tests)
- Commit 2: 5 minutes (3 simple changes)
- Commit 3: 10 minutes (5 tests)
- Commit 4: 10 minutes (6 tests)
- Commit 5: 2 minutes (1 line)
- Final verification: 8 minutes

**Buffer**: Add 50% for unexpected issues = 45-67 minutes total

---

## Success Metrics

### Before Refactoring
- Lines of code: 336
- TemporaryDirectory usage: 20
- tmp_path usage: 0
- str() conversions: ~15
- Tempfile import: Yes

### After Refactoring
- Lines of code: ~310 (7.7% reduction)
- TemporaryDirectory usage: 0
- tmp_path usage: 17
- str() conversions: 0 (in wrapper calls)
- Tempfile import: No

**Improvement**: Cleaner, more consistent, follows project conventions

---

## Notes

- **GREEN → GREEN → GREEN**: Every commit must keep tests passing
- **Pyright clean**: 0 errors after every commit
- **Atomic**: Each commit is one logical change
- **Reversible**: Can revert any commit independently
- **Documented**: Each commit has detailed message

If any commit fails verification:
1. **STOP** immediately
2. **REVERT** the commit: `git reset --soft HEAD~1 && git checkout tests/unit/test_file_operations.py`
3. **RE-PLAN** the step into smaller pieces
4. **TRY AGAIN** with smaller scope
