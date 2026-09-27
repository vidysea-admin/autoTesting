# Manifest — at130-genai-dep
**Contract:** qa/contracts/core-invariants.md
**Goal task:** none
**Date:** 2026-09-25
**Fix cycle:** 1 of max 3
**Dual check:** no
**Issues addressed:** AT-130 (medium, open -> fixed)
**Executor:** maker build subagent (worktree D:/autoTesting/.worktrees/at130-genai-dep, branch wave/at130-genai-dep)
**Executor rationale:** small structural addition (one doctor check + tests) plus a one-line dependency declaration; RAM 1.3-1.7 GB, well below the full-suite ceiling

## What changed
- **`google-genai` was already declared** (pyproject.toml, `google-genai>=2.22.0`) — that part of AT-130 landed earlier, under commit dd7ba5d "fix(AT-230 cycle2): ... declare google-genai", before this unit started. AT-130 itself was never flipped to `fixed` in qa/issues.jsonl, and — more importantly — nothing caught the *class* of hazard the checker's evidence described ("an import that resolves only by the accident of another library's pin"). That gap is what this unit closes.
- `src/autotester/doctor.py:1-16` — imports `sys`, `tomllib`, `importlib.metadata.packages_distributions`.
- `src/autotester/doctor.py:134-186` (`_dep_name`, `check_dependencies_declared`) — new check. AST-walks every `Import`/`ImportFrom` node anywhere in each src/ module (`ast.walk`, not just `tree.body` — the real AT-130 imports are lazy, inside `GeminiProvider._config`/`_structured`, not module-level), resolves each third-party top-level import name to its distribution(s) via `importlib.metadata.packages_distributions()`, and flags any import whose distribution set does not intersect `[project].dependencies` (parsed from pyproject.toml via stdlib `tomllib`). Stdlib modules (`sys.stdlib_module_names`) and the package's own `autotester` imports are skipped; imports the current environment cannot resolve at all are left to `import` itself (not this check's job — see test below).
- `src/autotester/doctor.py:264` (`run`) — wired `check_dependencies_declared` into the standing check list, so `uv run autotester doctor` catches this class on every future run, not only in a standalone test.
- `tests/test_doctor.py:27-32` (`write_pyproject`) — new fixture helper.
- `tests/test_doctor.py:150-212` — 8 new tests: undeclared third-party import flagged, declared import passes, a **lazy import inside a function body** is still caught (the actual AT-130 shape), stdlib imports never flagged, own-package imports never flagged, an unresolvable/typo'd import is not this check's job, no-pyproject repo is not this check's job, and a direct regression proof against the **real repo** (`doctor.check_dependencies_declared(doctor.repo_root()) == []`).
- **Second live instance found by the new check, fixed in the same commit:** `pyproject.toml` — added `starlette>=1.6.0`. `src/autotester/ui/routes_crawls.py:17`, `routes_issues.py:9`, `routes_report.py:12` all `from starlette.background import BackgroundTask` directly, undeclared, riding transitively on fastapi/uvicorn's pin — the identical hazard shape AT-130 named. Left unfixed, the new regression test (and `autotester doctor`) would be red on a pre-existing gap unrelated-in-ticket but identical-in-class; fixing it was the one-line mechanical move required to land the class-level test green.
- `uv.lock` — re-locked (`uv lock`) after the `starlette` declaration; `google-genai` was already present in the lock (2 line diff: `{ name = "starlette" }` + `{ name = "starlette", specifier = ">=1.6.0" }`).

## How to verify
- `uv run pytest tests/test_doctor.py tests/test_providers.py` -> all pass (targeted; RAM-gated, see below)
- `uv run ruff check src tests scripts` -> clean
- `uv run autotester doctor` -> clean

## Actual outputs (maker's run, worktree HEAD 5c4ab92)
- `uv run pytest tests/test_doctor.py tests/test_providers.py`: `28 passed in 5.33s`
- `uv run ruff check src tests scripts`: `All checks passed!`
- `uv run autotester doctor`: `doctor: clean`
- **Full suite: NOT RUN.** Free RAM measured via `Get-CimInstance Win32_OperatingSystem FreePhysicalMemory` at 1,722,092 KB (~1.68 GB) before work and 1,393,408 KB (~1.36 GB) after — both well under the 3.5 GB gate. Declared gap; targeted tests above substitute per the RAM rule.

## Capability coverage
| capability | check | falsifying edit | observed |
|---|---|---|---|
| an import declared only via someone else's transitive dependency is flagged as `undeclared-dependency`, even for the guaranteed-installed-but-undeclared `pytest` fixture | `tests/test_doctor.py::test_undeclared_third_party_import_is_flagged` | remove the intersection check (`if not normalized & declared:` -> `if False:`) in `check_dependencies_declared` | in-repo assertion: with the guard disabled, `doctor.run(root)` on the fixture returns `[]`; test fails without the guard, passes with it |
| a **lazy** (function-body) import is caught, not just module-level ones — the actual shape of the original AT-130 bug (`GeminiProvider._structured`/`_config` import `google.genai` inside the method, not at module top) | `tests/test_doctor.py::test_a_lazy_import_inside_a_function_body_is_still_caught` | change `ast.walk(tree)` to `tree.body` in `check_dependencies_declared`'s loop | throwaway copy (below) reproduces this exact bug shape; the module-level-only variant would have missed gemini.py:80/130 entirely, which is precisely why AT-130 shipped undetected |
| the real repo's declared dependencies cover every third-party import it actually makes (direct regression proof, not a fixture) | `tests/test_doctor.py::test_the_real_repo_declares_every_third_party_import_it_makes` | in pyproject.toml, delete the `"google-genai>=2.22.0"` line (reproducing the original AT-130 state) | **throwaway copy of `master`** (outside this worktree, own `uv sync`'d venv, deleted after): with the new check + tests but master's original pyproject (no `starlette` declared), `1 failed` — red on `routes_crawls.py:17` (`starlette.background`). After copying this unit's pyproject.toml fix in: `20 passed in 3.25s`. Then, in the same copy, deleting the `google-genai` line reproduces the original bug: `1 failed`, `Violation(...'google.genai' resolves via ['google-auth', 'google-genai']..., location='src\\autotester\\providers\\gemini.py:80')` — the exact line the AT-130 checker evidence cited. |
| stdlib and own-package imports are never flagged (no false positives) | `test_stdlib_imports_are_never_flagged`, `test_own_package_imports_are_never_flagged` | remove the `top in stdlib` / `top == "autotester"` skip conditions | with the skips removed, both tests fail (stdlib/own-package imports get flagged); with them present, both pass |
| an import the environment cannot resolve at all (typo, genuinely missing) is left to `import` itself, not this check | `test_an_import_the_environment_cannot_resolve_is_not_this_checks_job` | remove the `if not candidates: continue` guard | without the guard, `packages_distributions().get(top)` returns `None`, `None.lower()` raises `AttributeError` inside the check — test fails with an error instead of a clean pass |

## Live browser evidence
Not applicable — no UI/browser code touched. Changed paths: `src/autotester/doctor.py`, `tests/test_doctor.py`, `pyproject.toml`, `uv.lock`.

## Gaps
- Full non-browser pytest suite not run (RAM below the 3.5 GB gate both before and after work — see Actual outputs). Targeted `tests/test_doctor.py` + `tests/test_providers.py` (28 tests) substitute; a checker sweep with more free RAM should run the full suite once available.
- `check_dependencies_declared` resolves distributions via the **currently installed** environment (`importlib.metadata.packages_distributions()`), not a static parse of `uv.lock`. If a dependency is declared in pyproject but the venv is stale (not `uv sync`'d), the check could pass or fail incorrectly for reasons unrelated to the real declaration state. This matches the existing pattern of every other AST-based doctor check (all read the live tree, not a lockfile), so it is consistent with the codebase's existing tradeoffs rather than a new one.
- This check does not (and by design should not) flag `dependency-groups.dev` tools imported under `tests/` or `scripts/` — scope is `src/` only, per the brief ("every third-party top-level import under src/").

## Status: checked-PASS (cycle 1, 42b918c)
