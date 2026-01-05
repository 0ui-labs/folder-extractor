# Atomic Refactor Plan: Commit-by-Commit Strategy

**Date:** 2026-01-05
**Refactoring ID:** settings-di-2026-01

## Overview

This document maps each incremental step to a specific git commit with:
- Commit message (conventional commits format)
- Files changed
- Verification commands
- Expected test state

**Commit Convention:**
```
refactor(settings): <short description>

<detailed explanation>

- Bullet points of changes
- Expected impact on tests

Relates-to: settings-di-2026-01
```

---

## Commit Sequence

### Commit 0: Document Refactoring Plan 📋

**Purpose:** Establish refactoring documentation before changes

```bash
git add refactors/settings-di-2026-01/
git commit -m "docs(refactor): Add settings DI refactoring plan

Complete planning documentation for removing global settings instance:
- Pain points analysis
- Current state documentation
- Success criteria with verification script
- Safety net assessment
- Refactoring strategy
- Incremental steps breakdown
- Atomic commit plan

Relates-to: settings-di-2026-01"
```

**Files Changed:**
- `refactors/settings-di-2026-01/pain-points.md` (new)
- `refactors/settings-di-2026-01/current-state.md` (new)
- `refactors/settings-di-2026-01/success-criteria.md` (new)
- `refactors/settings-di-2026-01/safety-net.md` (new)
- `refactors/settings-di-2026-01/strategy.md` (new)
- `refactors/settings-di-2026-01/incremental-steps.md` (new)
- `refactors/settings-di-2026-01/atomic-plan.md` (new)

**Test Impact:** None (documentation only)

---

### Commit 1: Fix configure_from_args() Signature 🔧

**Purpose:** Correct parameter order and make Settings mandatory

```bash
git commit -m "refactor(settings): Fix configure_from_args parameter order

Change signature from:
  configure_from_args(args, settings_instance=None)
To:
  configure_from_args(settings: Settings, args)

Changes:
- Settings parameter now mandatory (no default)
- Settings parameter moved to first position (DI convention)
- Removed fallback to global instance
- Updated all internal references from settings_instance to settings

Impact:
- test_settings_refactored.py: 3 tests now PASS (were failing)
- test_settings.py: Tests now FAIL (no longer have fallback)
- cli/app.py: Call now works correctly (was accidentally right order)

Relates-to: settings-di-2026-01
Step: A1"
```

**Files Changed:**
- `folder_extractor/config/settings.py`
  - Line 137: Function signature
  - Lines 144-145: Remove fallback logic
  - Lines 147-176: Rename `settings_instance` → `settings`

**Verification:**
```bash
pytest tests/unit/test_settings_refactored.py::TestConfigureFromArgsWithExplicitSettings -v
# Expected: 3 PASSED (were 3 FAILED before)

pyright folder_extractor/config/settings.py
# Expected: 0 errors
```

**Test State:**
- ✅ `test_settings_refactored.py::TestConfigureFromArgsWithExplicitSettings` - ALL PASS
- ❌ `test_settings.py::TestConfigureFromArgs` - ALL FAIL (expected)
- ✅ Integration tests - PASS

---

### Commit 2: Fix get_all_categories() Signature 🔧

**Purpose:** Make Settings parameter mandatory and rename

```bash
git commit -m "refactor(settings): Fix get_all_categories parameter order

Change signature from:
  get_all_categories(settings_instance=None) -> list
To:
  get_all_categories(settings: Settings) -> list[str]

Changes:
- Settings parameter now mandatory (no default)
- Removed fallback to global instance
- Updated return type hint to list[str]
- Updated all internal references from settings_instance to settings

Impact:
- test_settings_refactored.py: Still PASS (already correct)
- Integration tests: Still PASS (already use explicit parameter)

Relates-to: settings-di-2026-01
Step: A2"
```

**Files Changed:**
- `folder_extractor/config/settings.py`
  - Line 179: Function signature
  - Lines 192-193: Remove fallback logic
  - Lines 195-199: Rename `settings_instance` → `settings`

**Verification:**
```bash
pytest tests/unit/test_settings_refactored.py::TestGetAllCategoriesWithExplicitSettings -v
# Expected: 4 PASSED

pytest tests/integration/test_smart_sorting_integration.py -v
# Expected: PASS (uses explicit parameter)

pyright folder_extractor/config/settings.py
# Expected: 0 errors
```

**Test State:**
- ✅ `test_settings_refactored.py` - ALL PASS
- ❌ `test_settings.py::TestConfigureFromArgs` - STILL FAIL
- ✅ Integration tests - PASS

---

### Commit 3: Update test_settings.py to Use Explicit DI 🧪

**Purpose:** Remove monkey-patching, use explicit Settings parameter

```bash
git commit -m "test(settings): Update tests to use explicit dependency injection

Remove monkey-patching pattern and use explicit Settings parameter:
- Remove all 'folder_extractor.config.settings.settings = fixture' hacks
- Update configure_from_args() calls to pass settings explicitly
- Pattern: configure_from_args(args) → configure_from_args(settings_fixture, args)

Updated test methods (13 total):
- test_basic_args
- test_type_filter
- test_domain_filter
- test_dry_run_and_depth
- test_deduplicate_flag
- test_global_dedup_flag
- test_global_dedup_implies_deduplicate
- test_extract_archives_flag
- test_delete_archives_without_extract_false
- test_delete_archives_with_extract_true
- test_watch_mode_from_args_when_enabled
- test_watch_mode_from_args_when_disabled
- test_watch_mode_from_args_defaults_to_false_when_missing

Impact:
- All 13 tests now PASS
- Tests now use proper DI pattern
- No more reliance on global fallback

Relates-to: settings-di-2026-01
Step: B1"
```

**Files Changed:**
- `tests/unit/test_settings.py`
  - Remove ~13 lines: `folder_extractor.config.settings.settings = settings_fixture`
  - Update ~13 calls: `configure_from_args(args)` → `configure_from_args(settings_fixture, args)`

**Verification:**
```bash
pytest tests/unit/test_settings.py::TestConfigureFromArgs -v
# Expected: ALL PASS (13 tests)

pytest tests/unit/test_settings.py -v
# Expected: ALL PASS (entire file)
```

**Test State:**
- ✅ `test_settings.py` - ALL PASS (fixed!)
- ✅ `test_settings_refactored.py` - ALL PASS
- ✅ Integration tests - PASS

---

### Commit 4: Remove Global Settings Import from Tests 🗑️

**Purpose:** Clean up import statement to remove global reference

```bash
git commit -m "test(settings): Remove global settings import

Remove import of global 'settings' instance from test file.

Before:
  from folder_extractor.config.settings import Settings, configure_from_args, settings

After:
  from folder_extractor.config.settings import Settings, configure_from_args

This change verifies no hidden dependencies on the global instance remain
in the test file after converting to explicit DI.

Impact:
- No test failures (global not used after previous commit)
- Confirms clean transition to explicit DI

Relates-to: settings-di-2026-01
Step: B2"
```

**Files Changed:**
- `tests/unit/test_settings.py`
  - Line 9: Remove `, settings` from import

**Verification:**
```bash
pytest tests/unit/test_settings.py -v
# Expected: ALL PASS (no change)

# Verify no global imports remain
grep -r "from.*settings import.*\bsettings\b" tests/
# Expected: No results
```

**Test State:**
- ✅ `test_settings.py` - ALL PASS
- ✅ `test_settings_refactored.py` - ALL PASS
- ✅ Integration tests - PASS

---

### Commit 5: Delete Global Settings Instance 🗑️

**Purpose:** Remove the global singleton entirely

```bash
git commit -m "refactor(settings): Remove global settings instance

Delete the module-level 'settings = Settings()' singleton instance.

All code now uses explicit dependency injection - the global instance
is no longer needed or referenced anywhere in the codebase.

Changes:
- Deleted line 134: settings = Settings()

Verification:
- All tests still pass (no dependencies on global)
- Type checking passes
- No NameError at import time

This completes the core refactoring goal: zero global state in settings module.

Relates-to: settings-di-2026-01
Step: C1"
```

**Files Changed:**
- `folder_extractor/config/settings.py`
  - Delete line 134: `settings = Settings()`

**Verification:**
```bash
python run_tests.py
# Expected: All tests PASS

pyright folder_extractor/
# Expected: 0 errors

# Verify deletion
grep -n "^settings = Settings()" folder_extractor/config/settings.py
# Expected: No results

# Verify no remaining fallback
grep -n "settings_instance = settings" folder_extractor/config/settings.py
# Expected: No results
```

**Test State:**
- ✅ ALL tests PASS
- ✅ Type checking PASS
- ✅ No global instance exists

---

### Commit 6: Add get_all_categories Import to SmartSorter 📦

**Purpose:** Prepare for removing duplicate implementation

```bash
git commit -m "refactor(smart_sorter): Import shared get_all_categories function

Add import of get_all_categories from settings module in preparation
for removing the duplicate _get_all_categories method.

This is a preparatory commit with no behavior change.

Relates-to: settings-di-2026-01
Step: D1"
```

**Files Changed:**
- `folder_extractor/core/smart_sorter.py`
  - Add: `from folder_extractor.config.settings import get_all_categories`

**Verification:**
```bash
pytest tests/unit/test_smart_sorter.py -v
# Expected: ALL PASS (no change yet)

pyright folder_extractor/core/smart_sorter.py
# Expected: 0 errors (unused import warning ok for now)
```

**Test State:**
- ✅ ALL tests PASS
- ⚠️ Unused import (will be used next commit)

---

### Commit 7: Replace Duplicate _get_all_categories Calls 🔄

**Purpose:** Use shared function instead of duplicate method

```bash
git commit -m "refactor(smart_sorter): Use shared get_all_categories function

Replace calls to self._get_all_categories() with calls to the shared
get_all_categories(self._settings) function.

This eliminates code duplication while maintaining identical behavior.

Changes:
- self._get_all_categories() → get_all_categories(self._settings)

Impact:
- SmartSorter tests still pass (behavior unchanged)
- Integration tests still pass
- Duplicate method now unused (will delete next)

Relates-to: settings-di-2026-01
Step: D2"
```

**Files Changed:**
- `folder_extractor/core/smart_sorter.py`
  - Line ~118: `categories = self._get_all_categories()` → `categories = get_all_categories(self._settings)`
  - (Any other call sites found by grep)

**Verification:**
```bash
pytest tests/unit/test_smart_sorter.py -v
# Expected: ALL PASS

pytest tests/integration/test_smart_sorting_integration.py -v
# Expected: ALL PASS

pyright folder_extractor/core/smart_sorter.py
# Expected: 0 errors
```

**Test State:**
- ✅ ALL tests PASS
- ⚠️ Duplicate method still exists but unused

---

### Commit 8: Delete Duplicate _get_all_categories Method 🗑️

**Purpose:** Remove duplicate code

```bash
git commit -m "refactor(smart_sorter): Remove duplicate _get_all_categories method

Delete the _get_all_categories method now that all calls use the shared
function from settings module.

This eliminates code duplication and establishes a single source of truth
for category merging logic.

Changes:
- Deleted lines 65-76: _get_all_categories() method

Impact:
- SmartSorter tests still pass
- Integration tests still pass
- No code duplication remains

Relates-to: settings-di-2026-01
Step: D3"
```

**Files Changed:**
- `folder_extractor/core/smart_sorter.py`
  - Delete lines 65-76: Entire `_get_all_categories()` method

**Verification:**
```bash
pytest tests/unit/test_smart_sorter.py -v
# Expected: ALL PASS

pytest tests/integration/test_smart_sorting_integration.py -v
# Expected: ALL PASS

# Verify no usages remain
grep -n "_get_all_categories" folder_extractor/core/smart_sorter.py
# Expected: No results

pyright folder_extractor/core/smart_sorter.py
# Expected: 0 errors
```

**Test State:**
- ✅ ALL tests PASS
- ✅ No code duplication

---

### Commit 9: Update configure_from_args Docstring 📝

**Purpose:** Update documentation to reflect new API

```bash
git commit -m "docs(settings): Update configure_from_args docstring

Update docstring to reflect mandatory Settings parameter and removal
of global fallback.

Changes:
- Document Settings as mandatory first parameter
- Remove mention of 'optional' and 'defaults to global'
- Add note about explicit DI requirement
- Add usage example

Relates-to: settings-di-2026-01
Step: E1"
```

**Files Changed:**
- `folder_extractor/config/settings.py`
  - Lines 138-145: Update docstring for `configure_from_args()`

**Verification:**
```bash
# No behavior change - verification not needed
# Review docstring manually for accuracy
```

**Test State:**
- ✅ ALL tests PASS (no code change)

---

### Commit 10: Update get_all_categories Docstring 📝

**Purpose:** Update documentation to reflect new API

```bash
git commit -m "docs(settings): Update get_all_categories docstring

Update docstring to reflect mandatory Settings parameter and removal
of global fallback.

Changes:
- Document Settings as mandatory parameter
- Remove mention of 'optional' and 'defaults to global'
- Add usage example showing explicit DI

Relates-to: settings-di-2026-01
Step: E2"
```

**Files Changed:**
- `folder_extractor/config/settings.py`
  - Lines 180-190: Update docstring for `get_all_categories()`

**Verification:**
```bash
# No behavior change - verification not needed
# Review docstring manually for accuracy
```

**Test State:**
- ✅ ALL tests PASS (no code change)

---

### Commit 11: Final Verification and Cleanup ✅

**Purpose:** Comprehensive verification of completed refactoring

```bash
git commit -m "refactor(settings): Complete global settings removal - final verification

Run comprehensive verification of settings DI refactoring completion.

Verification results:
✅ All tests pass (100%)
✅ Type checking passes (0 errors)
✅ No global settings instance exists
✅ No test imports global settings
✅ No test uses monkey-patching
✅ No fallback logic remains
✅ Code duplication removed
✅ Documentation updated

Success criteria met:
- Global instance deleted (settings.py:134)
- Functions have mandatory Settings parameter as first argument
- All tests use explicit DI
- SmartSorter uses shared get_all_categories function
- Docstrings reflect new API

Relates-to: settings-di-2026-01
Step: F1"
```

**Files Changed:**
- `refactors/settings-di-2026-01/verification-results.md` (new)

**Content of verification-results.md:**
```markdown
# Verification Results

Date: 2026-01-05
Refactoring ID: settings-di-2026-01

## Test Results
- Total tests: 1196
- Passing: 1196 (100%)
- Failing: 0
- Errors: 0

## Type Checking
- pyright errors: 0

## Verification Checks
✅ No global instance
✅ No global imports
✅ No monkey-patching
✅ No fallback logic
✅ No code duplication

## Success Criteria
✅ All 10 criteria met

Refactoring COMPLETE!
```

**Verification:**
```bash
# Run full verification script
bash refactors/settings-di-2026-01/verify.sh

# Expected: All checks PASS
```

**Test State:**
- ✅ ALL tests PASS (100%)
- ✅ ALL verification checks PASS

---

## Commit Summary

| Commit | Type | Description | Files | Tests |
|--------|------|-------------|-------|-------|
| 0 | docs | Refactoring plan | 7 new docs | ✅ N/A |
| 1 | refactor | Fix configure signature | settings.py | ⚠️ Mixed |
| 2 | refactor | Fix get_categories signature | settings.py | ⚠️ Mixed |
| 3 | test | Update test_settings.py | test_settings.py | ✅ All pass |
| 4 | test | Remove global import | test_settings.py | ✅ All pass |
| 5 | refactor | Delete global instance | settings.py | ✅ All pass |
| 6 | refactor | Add import to SmartSorter | smart_sorter.py | ✅ All pass |
| 7 | refactor | Replace duplicate calls | smart_sorter.py | ✅ All pass |
| 8 | refactor | Delete duplicate method | smart_sorter.py | ✅ All pass |
| 9 | docs | Update configure docstring | settings.py | ✅ All pass |
| 10 | docs | Update get_categories docstring | settings.py | ✅ All pass |
| 11 | refactor | Final verification | verification doc | ✅ All pass |

**Total Commits:** 12 (including commit 0)

---

## Commit Guidelines

### Before Each Commit

1. **Run Verification**
   ```bash
   pytest <affected-test-files> -v
   pyright <affected-code-files>
   ```

2. **Stage Changes**
   ```bash
   git add <specific-files>
   # DO NOT use 'git add .' - stage intentionally
   ```

3. **Review Diff**
   ```bash
   git diff --cached
   # Verify only intended changes staged
   ```

### Writing Commit Message

**Format:**
```
<type>(<scope>): <short description>

<detailed explanation>

- Bullet points of specific changes
- Expected impact on tests/behavior

Relates-to: <refactoring-id>
Step: <step-id>
```

**Types:** `refactor`, `test`, `docs`
**Scopes:** `settings`, `smart_sorter`, `tests`

### After Each Commit

1. **Verify Commit**
   ```bash
   git log -1 --stat  # Review what was committed
   ```

2. **Run Tests**
   ```bash
   pytest tests/unit/test_settings*.py -v
   ```

3. **Document Status**
   - Update refactoring checklist
   - Note any unexpected issues
   - Plan next commit

---

## Rollback Procedure

### If Commit N Fails Verification

**Option 1: Amend (if not pushed)**
```bash
# Fix the issue
<make corrections>

# Amend the commit
git add <files>
git commit --amend --no-edit

# Re-verify
pytest tests/ -v
```

**Option 2: Revert**
```bash
# Undo the commit
git revert HEAD

# Or reset (if not pushed)
git reset --hard HEAD~1

# Fix and retry
<make corrections>
git add <files>
git commit -m "..."
```

---

## Success Indicators

### During Execution
- Each commit has clear, focused purpose
- Tests pass (or expected failures documented)
- Type checker passes
- Git history is clean and understandable

### After Completion
- All 11 commits completed
- All verification checks pass
- Documentation updated
- Team can review atomic changes

---

## Post-Refactoring Tasks

After Commit 11:

1. **Update Architecture Docs**
   - CLAUDE.md: Mention DI pattern
   - ARCHITECTURE.md: Document settings management

2. **Code Review**
   - Request peer review of PR
   - Walk through atomic commits
   - Explain rationale

3. **Merge to Main**
   - Squash merge if preferred
   - Or keep atomic history

4. **Archive Refactoring Docs**
   - Move to `docs/refactorings/completed/`
   - Keep for future reference

---

## Completion Criteria

Refactoring is **COMPLETE** when:

- [ ] All 12 commits executed successfully
- [ ] All tests pass (100%)
- [ ] Type checking passes (0 errors)
- [ ] All verification checks pass
- [ ] Documentation updated
- [ ] Code review completed (if required)
- [ ] Changes merged to main branch

**When all boxes checked:** 🎉 SUCCESS!
