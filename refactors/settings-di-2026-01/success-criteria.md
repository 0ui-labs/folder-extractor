# Success Criteria: Settings DI Refactoring

**Date:** 2026-01-05
**Refactoring ID:** settings-di-2026-01

## Primary Goals

This refactoring has **ONE clear objective:**

> **Completely remove the global `settings` instance and establish mandatory dependency injection throughout the codebase.**

## Measurable Success Criteria

### 1. Code Structure ✓

#### ✅ Global Instance Removed
**Metric:** Zero global instances of Settings
```bash
# Must return zero results
grep -n "^settings = Settings()" folder_extractor/config/settings.py
```

**Before:**
```python
# Line 134
settings = Settings()
```

**After:**
```python
# Line 134 deleted - no global instance
```

---

#### ✅ Correct Function Signatures
**Metric:** Both functions have mandatory Settings as first parameter

**Before:**
```python
def configure_from_args(args, settings_instance: Optional[Settings] = None) -> None:

def get_all_categories(settings_instance: Optional[Settings] = None) -> list:
```

**After:**
```python
def configure_from_args(settings: Settings, args) -> None:

def get_all_categories(settings: Settings) -> list[str]:
```

**Verification:**
```bash
# Should show correct signatures
grep -A2 "^def configure_from_args" folder_extractor/config/settings.py
grep -A2 "^def get_all_categories" folder_extractor/config/settings.py
```

---

#### ✅ No Fallback Logic
**Metric:** Zero lines containing fallback to global

**Before:**
```python
if settings_instance is None:
    settings_instance = settings  # Fallback
```

**After:**
```python
# No fallback logic - parameter is mandatory
```

**Verification:**
```bash
# Must return zero results
grep -n "settings_instance = settings" folder_extractor/config/settings.py
```

---

### 2. Test Quality ✓

#### ✅ No Global Imports in Tests
**Metric:** Zero test files import global `settings` object

**Before:**
```python
from folder_extractor.config.settings import Settings, configure_from_args, settings
```

**After:**
```python
from folder_extractor.config.settings import Settings, configure_from_args
# No 'settings' import
```

**Verification:**
```bash
# Must return zero results
grep -r "from.*settings import.*\bsettings\b" tests/
```

---

#### ✅ No Monkey-Patching
**Metric:** Zero lines monkey-patching module globals

**Before:**
```python
folder_extractor.config.settings.settings = settings_fixture
```

**After:**
```python
# No monkey-patching - explicit parameter passing
```

**Verification:**
```bash
# Must return zero results
grep -r "folder_extractor.config.settings.settings =" tests/
```

---

#### ✅ All Tests Use Explicit DI
**Metric:** 100% of test calls pass Settings explicitly

**Before (test_settings.py):**
```python
configure_from_args(args)  # Implicit global usage
```

**After:**
```python
configure_from_args(settings_fixture, args)  # Explicit DI
```

**Verification:**
- Inspect all test files manually
- All `configure_from_args()` calls have 2 arguments
- All `get_all_categories()` calls have 1 argument

---

### 3. Code Duplication ✓

#### ✅ No Duplicate Category Logic
**Metric:** Only ONE implementation of category merging

**Before:**
- `settings.py:get_all_categories()` - Implementation #1
- `smart_sorter.py:_get_all_categories()` - Implementation #2 (duplicate)

**After:**
- `settings.py:get_all_categories()` - Single source of truth
- `smart_sorter.py` - Uses shared function

**Verification:**
```bash
# Should show only ONE implementation
grep -r "def.*get_all_categories" folder_extractor/
```

---

### 4. Test Coverage ✓

#### ✅ All Tests Pass
**Metric:** 100% test pass rate

**Verification:**
```bash
python run_tests.py
# Must show: All tests passed
```

**Coverage Requirements:**
- `folder_extractor/config/settings.py`: 90%+ coverage
- All modified files: No decrease in coverage
- Test suite completes in < 60 seconds

---

#### ✅ Type Checking Passes
**Metric:** Zero type errors from pyright

**Verification:**
```bash
pyright folder_extractor/
# Must show: 0 errors
```

---

### 5. API Consistency ✓

#### ✅ Parameter Order Convention
**Metric:** All DI functions follow "instance first" pattern

**Standard Pattern:**
```python
def some_function(settings: Settings, other_args) -> ReturnType:
    """Settings instance comes FIRST, always."""
```

**Verification:**
- Manually review function signatures
- Check that settings/config parameters come before data parameters

---

### 6. Documentation ✓

#### ✅ Docstrings Updated
**Metric:** All modified functions have accurate docstrings

**Required Updates:**
```python
def configure_from_args(settings: Settings, args) -> None:
    """Configure settings from command line arguments.

    Args:
        settings: Settings instance to configure (mandatory)
        args: Parsed command line arguments

    Note:
        Requires explicit Settings instance - no global fallback.
    """
```

**Verification:**
- Check docstrings mention mandatory parameters
- No references to "optional" or "defaults to global"

---

## Automated Verification Script

```bash
#!/bin/bash
# verify-di-refactoring.sh

echo "🔍 Verifying Settings DI Refactoring..."
echo ""

# Test 1: No global instance
echo "✓ Test 1: Global instance removed"
if grep -q "^settings = Settings()" folder_extractor/config/settings.py; then
    echo "  ❌ FAILED: Global settings instance still exists"
    exit 1
fi
echo "  ✅ PASSED"

# Test 2: No fallback logic
echo "✓ Test 2: No fallback logic"
if grep -q "settings_instance = settings" folder_extractor/config/settings.py; then
    echo "  ❌ FAILED: Fallback logic still exists"
    exit 1
fi
echo "  ✅ PASSED"

# Test 3: No global imports in tests
echo "✓ Test 3: No global imports in tests"
if grep -r "from.*settings import.*\bsettings\b" tests/ > /dev/null; then
    echo "  ❌ FAILED: Tests still import global settings"
    exit 1
fi
echo "  ✅ PASSED"

# Test 4: No monkey-patching
echo "✓ Test 4: No monkey-patching"
if grep -r "folder_extractor.config.settings.settings =" tests/ > /dev/null; then
    echo "  ❌ FAILED: Tests still monkey-patch globals"
    exit 1
fi
echo "  ✅ PASSED"

# Test 5: All tests pass
echo "✓ Test 5: Test suite"
if ! python run_tests.py > /dev/null 2>&1; then
    echo "  ❌ FAILED: Tests are failing"
    exit 1
fi
echo "  ✅ PASSED"

# Test 6: Type checking
echo "✓ Test 6: Type checking"
if ! pyright folder_extractor/ > /dev/null 2>&1; then
    echo "  ❌ FAILED: Type errors detected"
    exit 1
fi
echo "  ✅ PASSED"

echo ""
echo "🎉 All verification checks passed!"
```

---

## Before/After Comparison

### Complexity Metrics

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Global instances | 1 | 0 | 0 |
| Function with fallback | 2 | 0 | 0 |
| Optional DI parameters | 2 | 0 | 0 |
| Test monkey-patches | 12+ | 0 | 0 |
| Duplicate implementations | 2 | 1 | 1 |
| Files importing global | 1 | 0 | 0 |

### Test Quality Metrics

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Tests using fallback | 12 | 0 | 0 |
| Tests with explicit DI | 8 | 20 | 100% |
| Test pass rate | 100% | 100% | 100% |
| Type errors | 0 | 0 | 0 |

### Code Quality Metrics

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| DI consistency | 60% | 100% | 100% |
| Hidden dependencies | 1 | 0 | 0 |
| Test isolation | Poor | Good | Good |
| Parallel testability | No | Yes | Yes |

---

## Definition of Done

The refactoring is **COMPLETE** when ALL of the following are true:

- [ ] ✅ No global `settings = Settings()` in settings.py
- [ ] ✅ Both functions have mandatory Settings parameter as first argument
- [ ] ✅ No fallback logic (`if settings_instance is None`)
- [ ] ✅ No test files import global `settings` object
- [ ] ✅ No tests use monkey-patching (`folder_extractor.config.settings.settings =`)
- [ ] ✅ All tests pass (100% pass rate)
- [ ] ✅ Pyright shows zero type errors
- [ ] ✅ SmartSorter uses shared `get_all_categories()` function
- [ ] ✅ All docstrings updated to reflect mandatory parameters
- [ ] ✅ Verification script passes all checks
- [ ] ✅ Code review by peer developer (if applicable)
- [ ] ✅ Documentation updated (CLAUDE.md, ARCHITECTURE.md if needed)

---

## Success Indicators

### Immediate Indicators
✅ All tests green after each atomic change
✅ No type errors from pyright
✅ No grep results for prohibited patterns

### Long-Term Indicators
✅ New developers follow DI pattern naturally
✅ Tests are easier to write (no monkey-patching)
✅ Multiple Settings configurations can coexist
✅ No bugs related to shared global state

---

## Failure Conditions

The refactoring is **FAILED** if:

❌ Tests break and can't be fixed
❌ Type errors appear that can't be resolved
❌ Hidden callers break production code
❌ Performance degrades significantly
❌ Code becomes harder to understand

**Mitigation:** Each atomic step is reversible via git - revert and try smaller steps.
