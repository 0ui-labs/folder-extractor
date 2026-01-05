# Pain Points: Global Settings Instance

**Date:** 2026-01-05
**Refactoring ID:** settings-di-2026-01
**Goal:** Complete removal of global settings instance and establish explicit dependency injection

## Executive Summary

The `folder_extractor/config/settings.py` module currently maintains a **global singleton** instance (`settings = Settings()`) that creates hidden coupling throughout the codebase. While partial refactoring has introduced optional DI parameters, the implementation has **incorrect parameter ordering** causing caller-side bugs, and the fallback mechanisms defeat the purpose of dependency injection.

## Critical Issues

### 1. Global Instance Still Exists (settings.py:134)

```python
# Line 134 in settings.py
settings = Settings()
```

**Impact:**
- Creates hidden coupling between modules
- Makes testing difficult (requires monkey-patching)
- Violates explicit dependency principle
- Prevents running multiple configurations in parallel
- Makes it unclear which settings instance a function uses

**Evidence:**
- `tests/unit/test_settings.py:9` - Imports global `settings` object
- `tests/unit/test_settings.py:223` - Uses hack: `folder_extractor.config.settings.settings = settings_fixture`

### 2. Incorrect Parameter Order (CRITICAL BUG)

**Current function signatures (WRONG):**
```python
# settings.py:137
def configure_from_args(args, settings_instance: Optional[Settings] = None) -> None:

# settings.py:179
def get_all_categories(settings_instance: Optional[Settings] = None) -> list:
```

**Callers assume CORRECT order (settings first, args second):**
```python
# cli/app.py:57 - BROKEN
configure_from_args(self.settings, parsed_args)  # settings first, args second

# tests/unit/test_settings_refactored.py:30 - BROKEN
configure_from_args(settings_instance, args)  # settings first, args second
```

**Problem:** Functions expect `args` first but callers pass `settings` first!

**Impact:**
- **Silent bugs** - Python doesn't catch this at call time
- The `args` parameter receives a `Settings` object
- The `settings_instance` parameter receives an `args` object
- Only works due to fallback to global (which defeats DI)
- Tests pass accidentally via global fallback

**Root cause:** Partial refactoring added DI parameter but placed it in wrong position

### 3. Optional Parameters with Fallback Defeat DI

**Current implementation:**
```python
def configure_from_args(args, settings_instance: Optional[Settings] = None) -> None:
    if settings_instance is None:
        settings_instance = settings  # Falls back to global!
```

**Impact:**
- Makes DI optional instead of required
- Hides the dependency from call sites
- Allows code to work without explicit injection
- Makes it impossible to enforce DI via type system
- Tests can pass without proper DI setup

### 4. Test Hacks Required

**Current workaround in tests:**
```python
# tests/unit/test_settings.py:223
def test_basic_args(self, settings_fixture):
    # Workaround: configure_from_args() uses global settings internally
    folder_extractor.config.settings.settings = settings_fixture
    configure_from_args(args)  # No explicit settings passed
```

**Impact:**
- Monkey-patching module-level variables is fragile
- Tests don't reflect production code structure
- Hides the true dependency graph
- Makes tests harder to understand
- Can cause test pollution between test cases

### 5. Inconsistent Usage Patterns

**Good examples (explicit DI):**
```python
# core/extractor.py - Creates local instance
settings = Settings()
extractor = EnhancedFileExtractor(settings=settings)

# cli/app.py:38 - Instance-based
self.settings = Settings()

# tests/integration/test_smart_sorting_integration.py:738
get_all_categories(test_settings)  # Explicit!
```

**Bad examples (implicit global usage):**
```python
# tests/unit/test_settings.py:233 - Uses global via fallback
configure_from_args(args)  # Where does args.settings go?

# Old callers that rely on fallback mechanism
```

**Impact:**
- Codebase has two patterns for same functionality
- New developers don't know which pattern to follow
- Refactoring is incomplete/half-done
- Code review is harder (which pattern is correct?)

### 6. Duplicate Logic in SmartSorter

**settings.py has:**
```python
def get_all_categories(settings_instance: Optional[Settings] = None) -> list:
    # Implementation
```

**smart_sorter.py duplicates it:**
```python
class SmartSorter:
    def _get_all_categories(self) -> list[str]:
        custom: list[str] = self._settings.get("custom_categories", [])
        return custom + [cat for cat in DEFAULT_CATEGORIES if cat not in custom]
```

**Impact:**
- Code duplication violates DRY principle
- Two places to maintain same logic
- Can diverge over time causing bugs
- Unnecessary because `SmartSorter` already has `self._settings`

**Note:** This duplication exists BECAUSE `get_all_categories()` was tied to global - `SmartSorter` couldn't use it safely with its own settings instance.

## Affected Files

**Core module:**
- `folder_extractor/config/settings.py` - Global instance, wrong signatures

**Callers with wrong argument order:**
- `folder_extractor/cli/app.py:57` - Passes settings first (BROKEN)
- `tests/unit/test_settings_refactored.py:30,52,78,103` - Passes settings first (BROKEN)

**Callers using fallback (implicit global):**
- `tests/unit/test_settings.py` - All 12 test methods use fallback
- `tests/unit/test_cli_app.py` - May use fallback

**Good examples (already using DI):**
- `folder_extractor/core/extractor.py` - Creates local `Settings()`
- `folder_extractor/api/server.py` - Creates local `Settings()`
- `tests/integration/test_smart_sorting_integration.py:738` - Explicit DI

**Duplicate logic:**
- `folder_extractor/core/smart_sorter.py:65-76` - Has own `_get_all_categories()`

## Why This Matters

### Testing Impact
- Cannot test multiple configurations in parallel
- Tests require monkey-patching globals
- Test isolation is broken (shared global state)
- Hard to test edge cases (can't create temporary settings)

### Maintenance Impact
- Unclear dependencies make refactoring risky
- Two patterns for same thing confuses developers
- Parameter order bug shows incomplete refactoring
- Fallback mechanism hides missing dependencies

### Architecture Impact
- Violates dependency inversion principle
- Makes dependency graph implicit
- Prevents proper dependency injection framework usage
- Blocks future enhancements (e.g., multi-tenant support)

## Success Will Look Like

✅ Zero global state - no `settings = Settings()` at module level
✅ All functions have explicit, required `Settings` parameter as FIRST argument
✅ No fallback mechanisms - DI is mandatory
✅ All tests create and pass `Settings()` instances explicitly
✅ No more test hacks (`folder_extractor.config.settings.settings = ...`)
✅ Consistent DI pattern across entire codebase
✅ `SmartSorter` uses shared `get_all_categories()` function
✅ All tests pass with proper DI

## Risk Assessment

**Risk Level:** Medium-High

**Risks:**
1. **Widespread changes** - 20+ files need updates
2. **Parameter order fix** - Easy to miss a caller
3. **Test updates** - All test files need refactoring
4. **Hidden callers** - Dynamic imports might break

**Mitigation:**
1. Run full test suite after each atomic change
2. Use grep to find ALL callers before changing signatures
3. Change function signatures LAST (after fixing all callers)
4. Run pyright to catch type errors
5. Test coverage ensures behavioral correctness
