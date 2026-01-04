# Refactoring: test_file_operations.py Path Migration

## Overview

This refactoring converts `tests/unit/test_file_operations.py` from using `tempfile.TemporaryDirectory()` (string paths) to pytest's `tmp_path` fixture (Path objects), bringing it in line with project standards.

**Status**: Planning Complete ✅
**Ready to Execute**: Yes
**Estimated Time**: 30-45 minutes
**Risk Level**: Low

---

## Quick Start

### Pre-Flight Check
```bash
# Ensure tests pass
python run_tests.py unit

# Ensure clean pyright
pyright tests/unit/test_file_operations.py
```

### Execute Refactoring

Follow the commits in `atomic-plan.md`:

1. **Commit 1**: TestUniqueNameGeneration (7 tests)
2. **Commit 2**: TestSafePathValidation (str() removals)
3. **Commit 3**: TestEmptyFolderRemoval (5 tests)
4. **Commit 4**: TestWebLinkDomainCheck (6 tests)
5. **Commit 5**: Remove tempfile import

**CRITICAL**: Run tests after EVERY commit!

### Post-Flight Validation
```bash
# All tests pass
python run_tests.py

# Pyright clean
pyright tests/unit/test_file_operations.py

# Metrics achieved
wc -l tests/unit/test_file_operations.py  # ~310 lines
grep -c "tmp_path" tests/unit/test_file_operations.py  # 17
grep "TemporaryDirectory" tests/unit/test_file_operations.py  # None
```

---

## Documentation

### Planning Documents (Read in Order)

1. **pain-points.md** - What problems exist?
2. **current-state.md** - How does the code work now?
3. **success-criteria.md** - How do we measure success?
4. **safety-net.md** - Tests pass before we start
5. **strategy.md** - What refactoring pattern to use?
6. **incremental-steps.md** - Detailed step-by-step changes
7. **atomic-plan.md** - Commit-by-commit execution plan
8. **verification.md** - How to verify after each step
9. **quality-validation.md** - How to measure improvements

### Quick Reference

**Key Metrics**:
- Line reduction: ~26 lines (-7.7%)
- TemporaryDirectory: 20 → 0
- tmp_path: 0 → 17
- str() conversions: 15 → 0

**Key Benefits**:
- Consistent with project standards
- Cleaner code (less boilerplate)
- Better cross-platform support
- More readable tests

---

## Execution Checklist

### Before Starting
- [ ] Read atomic-plan.md
- [ ] Ensure tests pass
- [ ] Ensure pyright clean
- [ ] Git working directory clean
- [ ] Understand rollback procedure

### During Refactoring (Per Commit)
- [ ] Make changes as documented
- [ ] Run: `python run_tests.py unit`
- [ ] Run: `pyright tests/unit/test_file_operations.py`
- [ ] Visual inspection looks correct
- [ ] Commit with descriptive message
- [ ] If anything fails → REVERT

### After Completion
- [ ] All 5 commits made
- [ ] All tests pass
- [ ] Pyright clean
- [ ] Metrics achieved (see success-criteria.md)
- [ ] Fill out quality report (see quality-validation.md)

---

## Success Criteria (Summary)

### Mandatory
- ✅ All 25 tests pass
- ✅ Pyright: 0 errors
- ✅ TemporaryDirectory: 0 usage
- ✅ tmp_path: 17 usage
- ✅ tempfile import: removed
- ✅ Coverage: maintained (≥95%)

### Desirable
- ✅ Line count: ~310 (-7.7%)
- ✅ str() conversions: 0 (in wrapper calls)
- ✅ Code: more readable
- ✅ Consistent: with project standards

---

## Risk Assessment

**Overall Risk**: Low

**Mitigations**:
- Comprehensive test coverage (25 tests)
- Incremental changes (5 atomic commits)
- Tests run after each commit
- Easy rollback (git revert)
- Detailed documentation

**Worst Case**: Revert all commits, ~15 minutes lost

---

## Rollback Procedure

### Rollback Last Commit
```bash
git reset --soft HEAD~1
git checkout tests/unit/test_file_operations.py
python run_tests.py unit  # Verify
```

### Rollback All Commits
```bash
git log --oneline -10  # Find pre-refactoring commit
git reset --hard <commit-hash>
python run_tests.py unit  # Verify
```

---

## Timeline

**Planning**: Complete (9 phases, ~2 hours)
**Execution**: 30-45 minutes
**Validation**: 10-15 minutes
**Total**: ~3 hours including planning

**Actual execution** (once planned): < 1 hour

---

## Contact & Questions

This refactoring was planned using the **refactor-master** workflow, which ensures:
- Safe, incremental changes
- Tests always green
- Clear documentation
- Easy rollback

For questions about the workflow, see:
- `~/.claude/skills/refactor-master/skill.md`

---

## Notes

- This refactoring makes ZERO functional changes
- All 25 tests must pass before, during, and after
- Each commit is atomic and independently reversible
- Follow the plan exactly for best results
- Documentation is verbose but thorough by design

**Remember**: GREEN → GREEN → GREEN (tests must always pass)

---

Generated: 2026-01-04
Workflow: refactor-master (9-phase)
File: tests/unit/test_file_operations.py
Issue: Main-wrapper tests use string paths instead of Path/tmp_path
