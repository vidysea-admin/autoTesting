# Manifest — bidi-override-ordering-test
**Contract:** qa/contracts/ui.md (U8/U9 bidi override refusal)
**Goal task:** none
**Date:** 2026-10-17
**Fix cycle:** 0 of max 2
**Dual check:** no
**Persona walk:** skip (test-only; no screen or flow changed)
**Issues addressed:** AT-360
**Executor:** claude-sonnet-subagent
**Executor rationale:** single-file test addition sized for one agent

## What changed
- tests/test_ui_credential_bidi.py:168-194 — new `test_a_declared_placeholder_combined_with_an_override_is_still_refused`: a declared `{{SECRET:DEMO_PASSWORD}}` plus U+202E in the case title, step value and step expected must be 400 with the "direction" message and save no case. This is the input that only the real ordering (override check at src/autotester/ui/credential_guard.py:144, before the placeholder early return at :145-155) refuses.
- falsified (unchanged): src/autotester/ui/credential_guard.py — throwaway copy outside the worktree only; the worktree copy is untouched.
- Not edited: qa/evidence/at355-refuse-bidi-overrides/mutations.json (the checker's file; its M5 still deletes the call, and that is left for the checker to relabel).

## Verification scope
Policy-Version: proportional-verification/2026-10-15.12
Tier: S (test only); security-adjacent because it covers the credential guard, but no product code changes
Base / checked state: base 69ebfae7; test commit 910524a8; clean tree
Gate answers: none; no gate touched
Affected tests / full-suite trigger: tests/test_ui_credential_bidi.py only (10 tests). none. The builder runs no full suite.
Pre-check[C1]: 910524a8 uv run pytest tests/test_ui_credential_bidi.py -> 10 passed in 4.83s t=28 blobs=tests/test_ui_credential_bidi.py:1fb7fdb2
Metrics: start=2026-10-17T19:20:00 end=2026-10-17T19:50:00 wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=1 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12

## How to verify (commands + expected)
- `uv run pytest tests/test_ui_credential_bidi.py` -> expected: 10 passed
- `uv run ruff check src tests scripts` -> expected: All checks passed!
- `uv run autotester doctor` -> expected: doctor: clean

## Actual outputs (from maker's own run)
- pytest: `10 passed, 1 warning in 4.83s` (before the new test: 9 collected; the new one is the 10th)
- ruff: `All checks passed!`
- doctor: `doctor: clean` (2 non-blocking known-disputed advisories D-069, unrelated)

## Capability coverage (each new claim -> its isolating falsification)
| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| C1 | A value with a declared placeholder plus a bidi override is refused, so the override check runs BEFORE the placeholder early return | tests/test_ui_credential_bidi.py::test_a_declared_placeholder_combined_with_an_override_is_still_refused | in a throwaway copy outside the worktree, remove `_refuse_direction_override(value, field)` at credential_guard.py:144 and re-insert it immediately before `redactor = secrets.redactor()` (past both the placeholder and AT-078 exempt early returns), the mutation AT-360 names | green before: `10 passed, 1 warning` (copy baseline, same run command with PYTHONPATH on the copy). red after: `FAILED tests/test_ui_credential_bidi.py::test_a_declared_placeholder_combined_with_an_override_is_still_refused` / `AssertionError: placeholder + override via title was accepted` / `assert 303 == 400` / `1 failed, 9 passed`. The other 9 tests stay green, so the test isolates the ordering; restored copy: `10 passed` again |

Method: copy of src, scripts, pyproject and the tests helpers in the scratchpad (`.../scratchpad/at360`), run with the worktree venv python and `PYTHONPATH=<copy>/src:<copy>/scripts:<copy>/tests`, and `autotester.__file__` confirmed to resolve inside the copy. The mutation was applied by exact-once string replace (asserted), diffed, then the file was copied back from the worktree and diffed identical.

## Live browser evidence
Not UI-touching — no surface changed. Changed path: tests/test_ui_credential_bidi.py only (the test drives the app through TestClient).

## Status: ready-for-check
