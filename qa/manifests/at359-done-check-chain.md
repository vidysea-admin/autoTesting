# Manifest — at359-done-check-chain
**Contract:** qa/contracts/core-invariants.md (C9 — a declared control value is honoured or rejected, never silently ignored)
**Goal task:** none (guard-machinery fix, follows AT-161)
**Date:** 2026-09-26
**Fix cycle:** 2 of max 3
**Dual check:** no
**Issues addressed:** AT-359 (medium, open -> fixed)
**Executor:** claude-sonnet-5 (maker build subagent, worktree wave/at359-done-check-chain)

## What changed
- `tests/test_goal_done_checks.py` (cycle 1; lines shifted by cycle 2, see below) — `is_capable_of_failing` rewritten. Old code: `command.replace("&&", ";").split(";")` flattened both separators into one list and scored with `any(_is_task_specific(seg) for seg in segments)`, rejecting outright only if some segment was one of the three literal `ALWAYS_TRUE` tokens (`"true"`, `":"`, `"exit 0"`). New code: split on `;` first into top-level groups (a `;` chain's exit status is the **last** group's alone — earlier groups run but their exit codes are discarded); take the **last** group; split *that* group on `&&` into sub-segments (an `&&` chain short-circuits on the first failure and propagates that segment's exit code, so **any** sub-segment being task-specific is enough regardless of what follows it). `||` anywhere still disqualifies the whole command outright, unchanged.
- `tests/test_goal_done_check_shapes.py:41-50` — added the two literal AT-359 evidence commands to the rejected list: `"uv run pytest tests/test_x.py; echo done"`, `"uv run pytest tests/test_x.py; ls"` (both `;`-terminated by a non-literal always-succeeding command, the exact gap AT-359 reports).
- `tests/test_goal_done_check_shapes.py:63-70` — moved `"uv run pytest tests/test_x.py && true"` and `"uv run pytest tests/test_x.py && exit 0"` from the rejected list to the accepted list. Under real `&&` semantics these were never actually unfailable — if `pytest` fails, `&&` short-circuits and the failure propagates untouched; AT-161's own evidence text asserted "the shell returns the LAST segment's exit code" for `&&`, which is true for `;` but not for `&&`, and that mistaken generalization is exactly the flattening bug AT-359's `expected` field calls out ("Today both separators are flattened into one split before scoring").

## Cycle 2 changes (checker FAIL, cycle 1: commit 4bc6fc8, qa/verdicts/at359-done-check-chain.md)

**Finding (high, C9/AT-161 regression):** the cycle-1 rewrite scored a `;`/`&&` chain by which group is positionally last/leftmost, but never modelled that a bare `exit` mid-chain unconditionally terminates the shell. `exit 0 && uv run pytest ...` and `exit 0; uv run pytest ...` were both wrongly ACCEPTED — `exit` runs first and terminates immediately, so the task-specific segment behind it never executes and the command always exits 0 (AT-100's shape wearing `exit` instead of `true`). origin/master correctly rejected both; the branch did not.

**Fix — `tests/test_goal_done_checks.py`:**
- `_is_bare_exit(segment)` (new) — `shlex.split(segment)` and check it is exactly `exit` or `exit N` (a control-flow statement, not a program).
- `_truncate_after_first_exit(command)` (new) — walks segments left to right across BOTH `;` and `&&` via `re.split(r"(;|&&)", command)` (the real left-to-right execution order, independent of which separator connects them), and cuts the command string right after the first bare-exit segment found. Everything after that point is provably unreachable. A *trailing* exit (already the last segment, e.g. `pytest x.py && exit 0`, authorized by AT-359's own expected clause — kept) is untouched since there is nothing after it to cut.
- `is_capable_of_failing` now calls `command = _truncate_after_first_exit(command)` immediately after the `||` check and before the existing `;`-group / `&&`-group scoring — so the pre-existing (already-correct) logic runs on the reachable prefix, not the raw string.
- `tests/test_goal_done_check_shapes.py:41-50` — added the checker's two exact strings to the `rejected` list: `"exit 0 && uv run pytest tests/test_x.py"`, `"exit 0; uv run pytest tests/test_x.py"`.
- Trimmed the new docstrings (and nothing pre-existing) to keep the file at 297 lines — `uv run autotester doctor` flagged 315 after the first draft of this cycle's change (cap is 300).

**Both checker questions from the verdict, answered:**
1. The `&& true` / `&& exit 0` → accepted move stays; it is authorized by AT-359's own expected clause and is a *trailing*-exit case, unaffected by this fix (only a bare exit with something reachable AFTER it is truncated).
2. `||` is still rejected outright, unchanged — checked before truncation ever runs.

## How real .goal/goal.json done_checks were affected
For `;`, the new rule is *stricter* than the old one (a task-specific segment earlier in a `;` chain no longer saves it if the last `;`-segment isn't task-specific) — this is the actual bug fix. For `&&`, the new rule is *looser* (a trailing ALWAYS_TRUE segment no longer disqualifies an otherwise task-specific `&&` chain) — this can only turn a false rejection into a correct acceptance, never the reverse.
- Read-only scan of `.goal/goal.json` (67 tasks, 62 with a `done_check.cmd`): **zero** contain `;` anywhere — only 6 contain `&&` (T-000, T-005, T-135, T-143, T-126, T-150), all task-specific in a leading segment, and **zero** contain the token `exit` anywhere. So the stricter `;` direction and the cycle-2 `exit`-truncation direction both have no live instance to regress, and the looser `&&` direction cannot regress anything.
- Ran `offenders_in(tasks())` (the exact rule `test_no_pending_task_has_a_done_check_that_cannot_fail` asserts) against the new (cycle 2) implementation: **`[]`** — no offenders, both cycles. `.goal/goal.json` was not edited.

## Verify (worktree D:/autoTesting/.worktrees/at359-done-check-chain, commit 27b859a, cycle 2)
```
$ uv run pytest tests/test_goal_done_checks.py tests/test_goal_done_check_shapes.py -v
tests\test_goal_done_checks.py .......                                   [ 77%]
tests\test_goal_done_check_shapes.py ..                                  [100%]
9 passed in 0.27s

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```
Full suite: NOT RUN — RAM 0.33 GB free at cycle-2 check time (0.62 GB at cycle 1), well under the 3.5 GB ceiling for a full run. Declared gap; targeted tests above cover both changed files completely (`is_capable_of_failing` has no other callers besides `offenders_in`/`waiver_of` composition, also exercised by the same two files).

## Capability coverage
| claim | falsifying edit (throwaway scratch copy, outside worktree) | check that goes red |
|---|---|---|
| a `;`-chain is scored by its LAST group only (a trailing non-literal always-succeeding segment like `echo`/`ls` can no longer mask an earlier failing segment) | revert `is_capable_of_failing`'s body to AT-161's flatten-`;`-and-`&&`-then-`any()` shape (single hunk) | `test_the_guard_recognises_the_shapes_it_exists_to_catch` → `AssertionError: accepted an unfailable check: 'uv run pytest tests/test_x.py; echo done'` |
| an `&&`-chain is scored by ANY segment being task-specific (a trailing ALWAYS_TRUE segment can never mask an earlier failure under real `&&` short-circuit semantics) | change the `&&`-group scoring from `any(_is_task_specific(seg) for seg in last_group_segments)` to `_is_task_specific(last_group_segments[-1])` (single hunk — last-segment-only, the old over-rejecting behavior) | same test → `AssertionError: rejected a legitimate check: 'uv run python scripts/check_deliverable.py --exists qa/contracts/ai-target.md && uv run autotester doctor'` (T-126/T-150's own on-disk shape) |
| a bare `exit` mid-chain (across `;` or `&&`) makes everything after it unreachable, so a leading `exit 0` can no longer hide a task-specific segment behind it (cycle 2) | drop the `command = _truncate_after_first_exit(command)` call from `is_capable_of_failing` (single hunk — reintroduces the checker's exact cycle-1 regression) | same test → `AssertionError: accepted an unfailable check: 'exit 0 && uv run pytest tests/test_x.py'` |

All three sabotages were applied to copies of the *fixed* test files in the scratchpad temp directory (outside the worktree, no tracked file touched), run with the worktree's own `.venv` python directly, then deleted. Cycle-2 red-first probe against the *cycle-1* (pre-this-fix) code independently reproduced the checker's exact finding before any tracked edit: `is_capable_of_failing('exit 0 && uv run pytest tests/test_x.py')` and the `;`-form both returned `True` (bug), while `'uv run pytest tests/test_x.py && exit 0'` correctly stayed `True` and `'...; exit 0'` correctly stayed `False` (confirming the trailing-exit cases were never broken).

## LIVE-BROWSER: not-applicable
Pure predicate logic in a test-support module; no UI, no browser surface.

## Gaps
- Full `uv run pytest` (whole suite) not run in either cycle — RAM was 0.62 GB (cycle 1) / 0.33 GB (cycle 2) free, well below the 3.5 GB declared ceiling. Only the two directly-affected test files were run, plus ruff and doctor.
- No live `;`-chain, mixed `;`+`&&` shape, or `exit` token exists in `.goal/goal.json` today, so the stricter `;` direction and the cycle-2 exit-truncation direction of this fix are verified only against the shape tests, not against a real on-disk task. If one is ever added, `offenders_in` (already asserted by `test_no_pending_task_has_a_done_check_that_cannot_fail`) will catch a wrongly-accepted one automatically.
- This heuristic still does not model a *bare* `exit` with no argument (uses the prior command's `$?` in real bash) any differently from `exit N` — both are treated identically as unconditional terminators. Not raised by the checker and no on-disk case exercises it; noted as a known simplification, not a new gap this cycle introduced.

Status: checked-PASS (cycle 2, 48f89e8)
