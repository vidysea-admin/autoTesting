# Manifest - at672-tmp-root

**Contract:** qa/contracts/core-invariants.md (no feature contract; AT-672 criterion C1 below)
**Goal task:** none
**Date:** 2026-10-17
**Status:** ready-for-check
**Fix cycle:** 0 of max 2
**Hold fix cycles:** 0 of 2
**Hold-reopens:** 0
**Resume-reset:** unused
**Capability-redispatch:** 0
**Dual check:** no
**Persona walk:** skip (test-infrastructure change, no user-facing surface)
**Issues addressed:** AT-672
**Executor:** claude-sonnet-subagent
**Executor rationale:** one conftest hook plus one test; no external executor worthy.

## What changed
- tests/conftest.py:12-14,21-52 - new `pytest_configure` sets `config.option.basetemp` to a run-unique dir `<repo>/.work/pytest-tmp/r<pid>-<ts>` (creates the parent, since pytest mkdirs basetemp without parents), prunes sibling runs older than 24 h best-effort. Skipped when the caller passed `--basetemp` or on an xdist worker. Always redirects (one rule on every OS and CI) rather than only when TEMP is on the system drive: no drive-letter heuristic, and the repo already says scratch goes to `.work/`. Added imports `shutil`, `time`. File is 263 lines (cap 300).
- tests/test_core.py:173-187 - new `test_tmp_root_not_on_system_volume` (docstring names the C: 0.34 GB free scenario); skips only when the caller gave an explicit `--basetemp`.
- Nothing existing deleted or renamed. `.gitignore` untouched (`.work/` already ignored, .gitignore:11).
- Not done (human, per facts-c2.md): freeing C:, UV_CACHE_DIR, the "ENOSPC = instrument failure" checker rule.

## Verification scope
Policy-Version: proportional-verification/2026-10-15.12
Tier: L (tests/conftest.py edit is never test-only; config trigger), single checker, no dual check (no security/auth/tenancy/prod-write trigger)
Base / checked state: base fcedc9f4, code at 6899f3df, clean tree
Gate answers: none; no gate applies.
Affected tests / full-suite trigger: tests/test_core.py (all 15), tests/test_ids.py (conftest still loads). conftest is session-wide so the checker may run the full suite once; the builder ran none.
Pre-check[C1]: 6899f3df uv run pytest tests/test_core.py::test_tmp_root_not_on_system_volume -> 1 passed, 1 warning t=16 blobs=tests/test_core.py:2728ae1,tests/conftest.py:88ec869
Metrics: start=2026-10-17T09:30:00Z end=2026-10-17T09:42:00Z wall_min=12 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=1 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=16 mutants=1 defects_unit=0 defects_6c=0

## How to verify (commands + expected)
- `uv run pytest tests/test_core.py` -> expected: 15 passed
- `uv run pytest tests/test_ids.py` -> expected: 3 passed (conftest loads)
- `ls .work/pytest-tmp` -> expected: `r<pid>-<ts>` dirs exist after a run
- `uv run ruff check src tests scripts` -> expected: All checks passed!
- `uv run autotester doctor` -> expected: doctor: clean

## Actual outputs (from maker's own run)
- tests/test_core.py: `15 passed, 1 warning in 5.97s`
- tests/test_ids.py: `3 passed, 1 warning in 0.53s`
- `.work/pytest-tmp`: `r36920-1792229760/  r44444-1792229747/`
- ruff: `All checks passed!`; doctor: `doctor: clean`

## Capability coverage (each new claim -> its isolating falsification)
| Criterion | capability | check | falsifying edit | observed |
|---|---|---|---|---|
| C1 | tmp_path roots under `<repo>/.work/pytest-tmp`, off the OS temp (C:) dir | tests/test_core.py::test_tmp_root_not_on_system_volume | revert the conftest `pytest_configure` hunk (throwaway copy outside the worktree using the base conftest, `git show fcedc9f4:tests/conftest.py`) | before (red, base conftest, assertion): `E AssertionError: C:\Users\Lenovo\AppData\Local\Temp\pytest-of-Lenovo\pytest-36790\test_tmp_root_not_on_system_vo0 is not under ...\scratchpad\fals672\.work\pytest-tmp`; after (green, 6899f3df): `1 passed, 1 warning in 0.67s` |

Also red-first on the worktree before the edit: `FAILED tests/test_core.py::test_tmp_root_not_on_system_volume - AssertionErro...  1 failed, 14 passed`. The first conftest attempt without `mkdir(parents)` errored with FileNotFoundError on all tests; fixed and re-run green.

## Live browser
Not UI-touching.
