# Refactoring Strategy: Global to Dependency Injection

**Date:** 2026-01-05
**Refactoring ID:** settings-di-2026-01

## Strategy Overview

This refactoring uses a combination of the following patterns:

1. **Introduce Parameter** - Add explicit Settings parameter to functions
2. **Rename Method** - Fix parameter order (signature change)
3. **Remove Global** - Eliminate module-level singleton
4. **Inline Method** - Remove duplicate `_get_all_categories()` in SmartSorter
5. **Update References** - Fix all call sites to use new signatures

**Core Pattern:** ✅ **Dependency Injection Pattern**

Transform from:
```python
# Global singleton
settings = Settings()

def configure_from_args(args, settings_instance=None):
    if settings_instance is None:
        settings_instance = settings  # Implicit dependency
    # ...
```

To:
```python
# No global - explicit dependency injection
def configure_from_args(settings: Settings, args) -> None:
    # settings is mandatory parameter
    # ...
```

---

## Refactoring Patterns

### Pattern 1: Introduce Parameter → Remove Optional Default ✅

**Martin Fowler:** "Introduce Parameter Object" + "Remove Parameter"

**What:**
Make optional `settings_instance` parameter mandatory and place it first.

**Why:**
- Makes dependency explicit
- Enforces injection at compile time (via type hints)
- Removes fallback mechanism that defeats DI

**Before:**
```python
def configure_from_args(args, settings_instance: Optional[Settings] = None) -> None:
    if settings_instance is None:
        settings_instance = settings  # Global fallback
```

**After:**
```python
def configure_from_args(settings: Settings, args) -> None:
    # No fallback - settings is required
```

**Applied to:**
- `configure_from_args()`
- `get_all_categories()`

---

### Pattern 2: Rename Method (Fix Parameter Order) ✅

**Martin Fowler:** "Change Function Signature"

**What:**
Swap parameter order to follow convention: dependency injection parameters come first.

**Why:**
- Consistency with Python/DI conventions
- Config objects typically come before data parameters
- Makes dependency explicit at call site

**Before:**
```python
def configure_from_args(args, settings_instance: Optional[Settings] = None)
    # Data parameter (args) comes first ❌
```

**After:**
```python
def configure_from_args(settings: Settings, args) -> None:
    # Dependency (settings) comes first ✅
```

**Convention:**
```python
def function(dependencies, data, flags) -> Result:
    """
    Order: injectable dependencies → data → optional flags
    """
```

---

### Pattern 3: Remove Global Variable ✅

**Martin Fowler:** "Replace Global with Parameter"

**What:**
Delete the module-level `settings = Settings()` instance.

**Why:**
- Eliminates hidden coupling
- Forces explicit dependency management
- Enables parallel configurations
- Improves testability

**Before:**
```python
# settings.py line 134
settings = Settings()

# Hidden dependency - anyone can import this
from folder_extractor.config.settings import settings
```

**After:**
```python
# Line 134 deleted - no global

# Must create own instance
settings = Settings()
configure_from_args(settings, args)
```

---

### Pattern 4: Inline Method ✅

**Martin Fowler:** "Inline Method" / "Remove Duplication"

**What:**
Remove `SmartSorter._get_all_categories()` and use shared `get_all_categories()` function.

**Why:**
- Eliminates code duplication
- Single source of truth
- Easier to maintain

**Before:**
```python
# smart_sorter.py
class SmartSorter:
    def _get_all_categories(self) -> list[str]:
        # Duplicate implementation
        custom: list[str] = self._settings.get("custom_categories", [])
        return custom + [cat for cat in DEFAULT_CATEGORIES if cat not in custom]

    def some_method(self):
        categories = self._get_all_categories()  # Uses duplicate
```

**After:**
```python
# smart_sorter.py
from folder_extractor.config.settings import get_all_categories

class SmartSorter:
    # _get_all_categories() deleted

    def some_method(self):
        categories = get_all_categories(self._settings)  # Uses shared function
```

---

### Pattern 5: Update References ✅

**Martin Fowler:** "Move Method" / "Change Method Signature"

**What:**
Fix all call sites to match new signatures.

**Why:**
- Required for refactoring to work
- Opportunity to improve code clarity
- Makes dependencies visible

**Before:**
```python
# cli/app.py - WRONG ORDER
configure_from_args(self.settings, parsed_args)  # Settings first, args second

# tests/unit/test_settings.py - IMPLICIT GLOBAL
folder_extractor.config.settings.settings = settings_fixture  # Monkey-patch
configure_from_args(args)  # No settings passed
```

**After:**
```python
# cli/app.py - CORRECT ORDER
configure_from_args(self.settings, parsed_args)  # Same call - signature changed

# tests/unit/test_settings.py - EXPLICIT DI
configure_from_args(settings_fixture, args)  # Explicit injection
```

---

## Strategy Justification

### Why This Order?

**1. Fix Callers First**
- Safer to change call sites before signatures
- If signature changes first, ALL callers break immediately
- Changing callers first makes signature change safer

**2. Then Change Signatures**
- After callers fixed, signature change is mechanical
- Type checker will catch any missed callers
- Tests verify behavior unchanged

**3. Remove Global Last**
- Global removal is final irreversible step
- Only safe after all explicit injection working
- Final verification that no hidden dependencies exist

**4. Clean Up Duplication**
- Can be done independently
- Low risk change
- Improves maintainability

---

## Alternative Strategies (Rejected)

### ❌ Strategy A: Big Bang (Change Everything At Once)

```python
# Change settings.py, all callers, and all tests in one step
```

**Rejected because:**
- High risk of missing callers
- Hard to debug if something breaks
- Not reversible atomically
- Violates "tests always green" principle

---

### ❌ Strategy B: Signature First (Change Function, Then Callers)

```python
# 1. Change configure_from_args(settings, args) signature
# 2. Fix all callers that now break
```

**Rejected because:**
- Breaks ALL callers immediately
- Tests go red until all callers fixed
- Hard to verify each change works
- Violates incremental refactoring principle

---

### ❌ Strategy C: Gradual Migration (Keep Both Signatures)

```python
# Keep old signature, add new function
def configure_from_args_v2(settings: Settings, args) -> None:
    ...

# Gradually migrate callers
```

**Rejected because:**
- Leaves codebase in inconsistent state longer
- Two ways to do same thing (confusion)
- Still need to remove old function eventually
- Doesn't solve parameter order issue

---

## Selected Strategy: Incremental Dependency Injection ✅

**Approach:** Fix in reverse dependency order

```
Tests (consumers) → Functions (providers) → Global (deprecated)
```

**Why This Works:**
1. **Caller First:** Changes are compatible with current fallback mechanism
2. **Signature Change:** Safe because callers already use correct pattern
3. **Global Removal:** Safe because no code depends on it anymore
4. **Tests Stay Green:** Each step is verified independently

---

## Dependency Order Analysis

### Dependency Graph

```
Global settings instance (line 134)
        ↓
    (fallback)
        ↓
configure_from_args() / get_all_categories()
        ↓
    Callers:
    ├── cli/app.py
    ├── tests/unit/test_settings.py
    ├── tests/unit/test_settings_refactored.py
    ├── smart_sorter.py (_get_all_categories)
    └── (others)
```

**Refactoring Order (Bottom-Up):**

```
1. Fix leaf nodes (callers) first
2. Then fix intermediate nodes (functions)
3. Finally remove root node (global)
```

---

## Change Impact Matrix

| Component | Risk | Change Type | Impact |
|-----------|------|-------------|---------|
| settings.py:134 (global) | High | Delete | Breaking if any imports remain |
| settings.py:137 (configure) | Medium | Signature | Breaking for all callers |
| settings.py:179 (get_categories) | Medium | Signature | Breaking for all callers |
| cli/app.py | Low | Fix order | Compatible (signatures update later) |
| test_settings.py | Medium | Remove hacks | Requires rewrite of 12 tests |
| test_settings_refactored.py | Low | Already correct | Will pass after signature fix |
| smart_sorter.py | Low | Inline method | Local change only |

---

## Risk Mitigation Strategy

### High-Risk Changes

**1. Function Signature Changes**

Risk: Missing a caller causes AttributeError at runtime

Mitigation:
- Use grep to find ALL callers before change
- Use pyright to verify after change
- Run full test suite to catch dynamic calls
- Change signatures LAST (after callers fixed)

**2. Global Removal**

Risk: Hidden import causes NameError

Mitigation:
- Grep for all imports of global
- Remove imports BEFORE deleting global
- Run tests to verify no dynamic access
- Make deletion LAST step

**3. Test Rewrites**

Risk: Tests break and can't be fixed

Mitigation:
- Understand current test patterns first
- Fix one test file at a time
- Keep test_settings_refactored.py as reference
- Verify behavior unchanged with temporary assertions

### Low-Risk Changes

**1. SmartSorter Cleanup**

- Local to one class
- Private method (no external callers)
- Easy to revert
- Can be done independently

**2. Type Hint Additions**

- Non-breaking change
- Improves tooling support
- Safe to do incrementally

---

## Verification Strategy

### After Each Change

```bash
# 1. Type checking
pyright folder_extractor/config/settings.py

# 2. Unit tests
pytest tests/unit/test_settings.py tests/unit/test_settings_refactored.py -v

# 3. Integration tests
pytest tests/integration/ -v

# 4. Full suite (if major change)
python run_tests.py
```

### Green-to-Green Guarantee

**Rule:** Every commit must have passing tests (or identified expected failures)

**Exceptions:**
- `test_settings_refactored.py` failures are expected initially (parameter order)
- These should be FIXED not ignored
- After fix, no failures allowed

---

## Success Indicators

### During Refactoring

✅ Each step compiles (no syntax errors)
✅ Type checker passes (or errors decrease)
✅ Tests pass (or known failures don't increase)
✅ Git commits are atomic and reversible

### After Completion

✅ No global `settings` instance exists
✅ All functions have mandatory Settings parameter
✅ All tests pass (100%)
✅ No monkey-patching in tests
✅ Type checker shows zero errors
✅ Code duplication removed

---

## Rollback Strategy

### If Something Goes Wrong

**1. Immediate Rollback (Git Revert)**
```bash
git revert HEAD  # Undo last commit
```

**2. Partial Rollback (Reset to Previous State)**
```bash
git reset --hard <commit-hash>  # Go back to known good state
```

**3. Re-approach with Smaller Steps**
- Break failing step into smaller changes
- Add intermediate verification
- Use feature flags if needed

---

## Timeline Estimate

### Optimistic: 2-3 hours
- All changes work first try
- No unexpected dependencies
- Tests update cleanly

### Realistic: 4-6 hours
- Some hidden callers found
- Test updates need iteration
- Type errors require fixes

### Pessimistic: 8-12 hours
- Many hidden dependencies
- Integration tests fail
- Need to refactor additional code

---

## Final Strategy Statement

**We will use the Introduce Parameter + Remove Global pattern, applied incrementally in reverse dependency order:**

1. ✅ **Document & Plan** (Current phase)
2. ✅ **Fix Callers** - Update to correct parameter order/explicit DI
3. ✅ **Change Signatures** - Update function definitions
4. ✅ **Remove Fallback Logic** - Make parameters mandatory
5. ✅ **Delete Global** - Remove module-level instance
6. ✅ **Clean Up Duplication** - Inline SmartSorter method
7. ✅ **Verify & Document** - Full test suite + update docs

**Each step is:**
- Atomic (single logical change)
- Reversible (git commit)
- Verifiable (tests run after)
- Documented (commit message explains why)

This strategy minimizes risk while maximizing the likelihood of successful completion.
