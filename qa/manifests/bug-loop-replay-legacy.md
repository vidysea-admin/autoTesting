# Manifest - bug-loop-replay-legacy

**Contract:** qa/contracts/team-bug-loop.md (TB4, TB6); AT-979 = C1, AT-980 = C2 (qa/issues.jsonl last row per id)
**Goal task:** none
**Date:** 2026-10-17
**Status:** checked-PASS (qa/verdicts/bug-loop-replay-legacy.md, cycle 0)
**Fix cycle:** 0 of max 2
**Hold fix cycles:** 0 of 2
**Hold-reopens:** 0
**Resume-reset:** unused
**Capability-redispatch:** 0
**Dual check:** no
**Persona walk:** skip (store and stage internals, no user-facing surface)
**Issues addressed:** AT-979, AT-980
**Executor:** claude-sonnet-subagent
**Executor rationale:** two small in-place edits to existing modules; no external executor worthy.

## What changed
- src/autotester/stages/bug_run.py:`changed_case_events` (new `history` arg, `latest` per bug_key) and `process_run` (passes `snap.events`): a `case_changed` is stamped `max(run time, latest stored event of that bug)`, so an older run replayed after a criterion edit can no longer put the change before a later FAIL/PASS and refuse it (AT-979, C1). Module docstring updated. File 174 lines.
- src/autotester/store/bug_store.py:`legacy_file_name` (new, 3 lines) and `snapshot()` name check: a T-199a `bev_<id>.json` file is read as a valid event (still bad if its name belongs to another event); new events keep `file_name` (AT-980, C2). Docstring updated. File 192 lines.
- tests/test_bug_run_replay.py (new, 51 lines): two AT-979 tests. tests/test_bug_store_hardening.py:+24 lines (227): two AT-980 tests, import `write_json`.
- No new src module; nothing existing deleted or renamed. qa/issues.jsonl and qa/contracts untouched.
- Choice made (C1): the edit time is not recorded anywhere, so the stamp is the latest history the store already holds for that bug, not wall-clock `now`. It is replay-stable (same snapshot, same time), keeps ordering FAIL < case_changed at one instant (bug_loop.order_key), and leaves a normal in-order run unchanged (run time wins).
- Choice made (C2): read legacy names rather than raise; no real legacy data exists (issue evidence), so either was admissible; reading cannot lose history.

## Verification scope
Policy-Version: proportional-verification/2026-10-15.12
Tier: M (two existing modules, no gate trigger)
Base / checked state: base 69ebfae7, code at afe6d4f5 (branch wave/bug-loop-replay-legacy), clean tree before this manifest commit
Gate answers: none; no gate applies.
Affected tests / full-suite trigger: tests/test_bug_store.py, test_bug_store_concurrency.py, test_bug_store_hardening.py, test_bug_run.py, test_bug_run_idempotent.py, test_bug_run_replay.py (89 passed on the code before two comment-only/unused-variable lint edits; the two changed test files re-run 30 passed after). No full suite; the builder ran none.
Pre-check[C1]: afe6d4f5 uv run pytest tests/test_bug_run_replay.py -> 2 passed, 1 warning t=42 blobs=tests/test_bug_run_replay.py:29c4473
Pre-check[C2]: afe6d4f5 uv run pytest tests/test_bug_store_hardening.py -k at980 -> 2 passed, 26 deselected, 1 warning t=32 blobs=tests/test_bug_store_hardening.py:9227530
Metrics: start=2026-10-17T10:00:00Z end=2026-10-17T10:40:00Z wall_min=40 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=74 mutants=2 defects_unit=0 defects_6c=0

## How to verify (commands + expected)
- `uv run pytest tests/test_bug_run_replay.py tests/test_bug_store_hardening.py` -> expected: 30 passed
- `uv run pytest tests/test_bug_store.py tests/test_bug_store_concurrency.py tests/test_bug_run.py tests/test_bug_run_idempotent.py` -> expected: all pass (59 with the two files above = 89)
- `uv run ruff check src tests scripts` -> expected: All checks passed!
- `uv run autotester doctor` -> expected: doctor: clean

## Actual outputs (from maker's own run)
- six bug test files: `89 passed, 1 warning in 198.64s`; two changed files after lint edits: `30 passed, 1 warning in 58.92s`
- ruff: `All checks passed!`; doctor: `doctor: clean` (two non-blocking known-disputed D-000/D-005 notes)

## Capability coverage (each new claim -> its isolating falsification)
Falsification run in a throwaway copy OUTSIDE the worktree (`<scratchpad>/fals`, PYTHONPATH pointing at its src), with both src files reverted to base via `git show HEAD~1:<path>`; the same nodes then green with the fixed files copied back.

| Criterion | capability | check | falsifying edit | observed |
|---|---|---|---|---|
| C1 | replaying an old run after an edit neither refuses the later FAIL nor stamps case_changed before the bug's own history | tests/test_bug_run_replay.py::test_at979_replaying_an_old_run_after_an_edit_does_not_refuse_the_later_fail and ::test_at979_the_case_changed_event_is_never_earlier_than_the_bugs_own_history | revert bug_run.py to base (stamp at the replayed run's time) | red (base): `assert (<BugStatus.S...) == (<BugStatus.S...)  At index 1 diff: 1 != 2` (count 1, r2 refused) and `datetime(2026, 10, 1, 9, 1) != datetime(2026, 10, 1, 9, 2)`; green (fix): `4 passed, 26 deselected` for -k "at979 or at980" |
| C2 | a store of T-199a `bev_<id>.json` files reads as its events, not as empty with bad=N | tests/test_bug_store_hardening.py::test_at980_an_old_store_of_legacy_named_events_is_read_not_silently_empty (and ::test_at980_a_legacy_file_under_another_events_name_is_still_bad, green both sides) | revert bug_store.py to base (name check accepts `file_name` only) | red (base): `assert ([BadEventFile...vent's name")] == []  Left contains 3 more items, first extra item: BadEventFile(name='bev_4d65b9d7e750.json', why="file name is not this event's name")`; green (fix): same `4 passed, 26 deselected` line |

Red-first on the worktree before any src edit: `3 failed, 27 passed` (the three tests above), then `1 failed` after the fix until the test's own key lookup was corrected (fixture `KEY` is for another case id), then green.

## Live browser evidence
Not UI-touching - no surface changed (changed paths: src/autotester/stages/bug_run.py, src/autotester/store/bug_store.py, tests only).
