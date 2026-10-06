# Manifest — t171-goal-pin (repoint the T-171 done_check pin at the real test file)

Contract: qa/contracts/core-invariants.md (C7/C12: a done_check must be able to run and fail; enforced by tests/test_goal_done_checks.py::test_no_done_task_has_a_done_check_naming_a_file_that_does_not_exist) and qa/contracts/coverage.md V9 for T-171 itself; T-171's PASS record qa/manifests/t171-permission-surface-coverage.md (checked-PASS, names tests/test_permission_coverage.py)
Goal task: T-171 (bookkeeping only, no behavior change; already checked-PASS)
Policy-Version: proportional-verification/2026-10-06.6
Fix cycle: 0 of 2
Phase: READY
Tier: L — protected test change (tests/test_goal_contract_registration.py is an oracle: its pinned expectation changes)
Dual check: no — single checker. Not security/auth/tenancy and not a production data write; the Tier L trigger is the protected-test edit only.
Persona walk: skip (test and goal bookkeeping, no UI)
Executor: claude-sonnet-subagent (branch assembly)
Base: bd2fe8f4d9a9fa87552e8a3999eb27cb52f8addf
Branch: wave/t171-goal-pin, commit 8e1b1dc5 plus this manifest

## What changed

- tests/test_goal_contract_registration.py:42 — the pinned T-171 done_check spec `tests/test_permission_surface.py` becomes `tests/test_permission_coverage.py`. PROTECTED test change: the oracle's expected value changes, so it needs this checker. Reason: the old file never existed; the real test is tests/test_permission_coverage.py (T-171's checked-PASS manifest).
- .goal/goal.json — only these hunks of the main tree's dirty diff: T-171 `done_check.cmd` (same repoint); `progress` block (total 81->82, done 57->59, pending 24->23, percent 70->72); T-185 `status` pending->done, its `note` and `completed` (the done count 59 cannot be consistent with the 82 tasks without that flip). Every other dirty goal.json hunk (updated/tick timestamps, notes of other tasks, T-196 criticality and alert, velocity) is deliberately left in the main tree.
- .goal/dashboard.html — the main tree's one-line regenerated diff, verbatim (the test also asserts the dashboard shows 59/82 tasks, 72%, Remaining (23)).

Why progress and T-185 had to come along: at the base the progress block (81/57/24) disagrees with the 82 tasks (58 done/24 pending) on its own, so `assert progress["total"] == len(data["tasks"])` fails independent of the pin. Only the main tree's own numbers were used, no new values invented. REVIEW POINT FOR THE CHECKER: the T-185 flip is another unit's bookkeeping (qa/manifests/at408-416-scroll-reach.md in the main tree); this branch carries it only so the file is self-consistent. If the checker would rather keep it out, the alternative is progress 82/58/24/71 plus a hand-regenerated dashboard, which invents numbers present nowhere in the main tree.

## Verification scope

Policy-Version: proportional-verification/2026-10-06.6
Tier: L (protected test change), single checker.
Base / checked state: bd2fe8f4 + 8e1b1dc5 (+ this manifest).
Affected tests / full-suite trigger: tests/test_goal_contract_registration.py, tests/test_goal_done_checks.py, tests/test_goal_done_check_shapes.py, tests/test_permission_coverage.py. The builder ran no full suite.
Metrics: start=2026-10-07 end=2026-10-07 wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.6

## How to verify (commands + expected)

- `uv run pytest tests/test_goal_contract_registration.py tests/test_goal_done_checks.py tests/test_goal_done_check_shapes.py` -> 10 passed
- `uv run pytest tests/test_permission_coverage.py` -> 15 passed (the real T-171 test, so the new done_check is runnable)
- `uv run ruff check src tests scripts` -> All checks passed
- `uv run autotester doctor` -> 7 violations, all present at the base (see below)

## Actual outputs (maker's own run, 2026-10-07)

- At the base before the edit: `2 failed, 8 passed in 0.85s`; FAILED test_goal_contract_registration.py::test_revised_goal_contract_is_registered and FAILED test_goal_done_checks.py::test_no_done_task_has_a_done_check_naming_a_file_that_does_not_exist.
- After the pin edit only (test + cmd, no progress change): `1 failed, 9 passed`, the remaining failure `assert 81 == 82` (progress.total vs task count), which is why the progress block came along.
- At the tip: `10 passed in 0.21s`; `15 passed, 1 warning in 18.80s` for test_permission_coverage.py; ruff `All checks passed!`.
- doctor at the tip: 7 violations: ledger-row-missing T-171; stale-generated docs/SNAPSHOT.md; 5 decision-citation-dangling (all D-061: at733-entry-cleanup.md x2, at113-crawl-completion.b.md x2, docs/SNAPSHOT.md). All exist at the base. The T-171 ledger row and the D-061 entry are uncommitted in the main tree (FEATURES.jsonl, DECISIONS.md). Root-clutter (at113-fixture-*, pytest-of-unknown) is a main-tree-only pre-existing condition and does not appear in a fresh worktree.

## Capability coverage (each new claim -> its isolating falsification)

Throwaway `git archive` copy outside the tree; original restored byte-identical, runner re-run before/after/restored.

| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| pin | the pinned T-171 done_check is the real file | tests/test_goal_contract_registration.py::test_revised_goal_contract_is_registered | tests/test_goal_contract_registration.py:42 back to `test_permission_surface.py` | before `1 passed in 0.16s`; after `FAILED ...test_revised_goal_contract_is_registered`, `1 failed in 0.26s`; restored `1 passed in 0.08s` |
| goal.json cmd | goal.json T-171 done_check names an existing file | tests/test_goal_done_checks.py::test_no_done_task_has_a_done_check_naming_a_file_that_does_not_exist and the pin test | .goal/goal.json T-171 `cmd` back to `tests/test_permission_surface.py` | before `8 passed in 0.14s`; after `FAILED ...test_revised_goal_contract_is_registered`, `FAILED ...test_no_done_task_has_a_done_check_naming_a_file_that_does_not_exist`, `2 failed, 6 passed in 0.28s`; restored `8 passed in 0.14s` |

## Live browser evidence

Not UI-touching — no surface changed: the changed paths are tests/test_goal_contract_registration.py, .goal/goal.json and the generated .goal/dashboard.html (a status report, no behavior).

## Status: checked-PASS — qa/verdicts/t171-goal-pin.md (cycle 0)
