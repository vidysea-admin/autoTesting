# Verdict — at130-genai-dep

**Date:** 2026-09-26 · **Head checked:** 088ff74 (fix 5c4ab92, base bb4be39) · **Cycle checked: 1** (manifest Fix cycle: 1) · **Issues addressed (claimed):** AT-130

```
VERDICT: PASS
SCOREBOARD: AT-130 expected clause met (a class-level guard: doctor's check_dependencies_declared AST-walks every import in src, lazy ones included, and flags any whose distribution is not declared; the second live instance, starlette, is declared); core invariants hold
FAILURES: none
CAPABILITY-COVERAGE: 2/2 rows reproduced in an own-venv copy: starlette removed from pyproject -> 3 undeclared-dependency violations (routes_crawls.py:17, routes_issues.py:9, routes_report.py:12); ast.walk -> tree.body -> test_a_lazy_import_inside_a_function_body_is_still_caught red; both restored green
LIVE-BROWSER: not-applicable (changed paths: pyproject.toml, uv.lock, src/autotester/doctor.py, tests/test_doctor.py)
ISSUES-WRITTEN: AT-590 (medium, not blocking)
EXECUTOR: claude-sonnet-subagent (checker: claude-opus-session orchestrating a claude-sonnet checker subagent)
EXPLANATION: The guard works on the real repo and catches the transitive-accident class AT-130 describes. The lockfile change adds exactly starlette, nothing else. It is blind to TYPE_CHECKING-only and try/except-optional imports (filed as AT-590), and it adds an enforced rule with no core-invariants criterion yet; the checker folds that at merge.
```

## What was re-run

- Worktree: `tests/test_doctor.py` + `tests/test_providers.py` -> 28 passed · `ruff` clean · `doctor` clean. doctor.py is 269 lines; `check_dependencies_declared` is 43 lines.
- Environment probes, in the own-venv copy c130-1:
  - a mismatched distribution name (`yaml` -> PyYAML) is flagged when undeclared and clears when declared;
  - stdlib and the project's own package are never flagged;
  - a package missing from the venv is silently skipped (documented and tested: `test_an_import_the_environment_cannot_resolve_is_not_this_checks_job`);
  - an installed-but-undeclared package under `if TYPE_CHECKING:`, or inside `try/except ImportError`, IS flagged like a hard import -> AT-590.
- Lockfile: `git diff bb4be39..HEAD -- uv.lock` touches only the two `starlette` entries.
- Diff scope: M pyproject.toml, M src/autotester/doctor.py, M tests/test_doctor.py, M uv.lock, A manifest. No deletions or renames; matches "What changed".
- The full suite runs once for the whole wave, on a combined tree, in the orchestrating session.

## Contract gap (checker action, not a failure)

`qa/contracts/core-invariants.md` has no criterion for "every third-party import is declared in [project].dependencies". The checker folds one, with a D-entry, once this unit merges.

## Status: PASS
