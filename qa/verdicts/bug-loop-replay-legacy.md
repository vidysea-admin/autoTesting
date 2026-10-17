# Verdict - bug-loop-replay-legacy

Cycle checked: 0
Date: 2026-10-17
Bound to: D:/autoTesting/.worktrees/bug-loop-replay-legacy (base 69ebfae7 = git merge-base HEAD master; head c7f92f9e, code afe6d4f5)
Policy-Version: proportional-verification/2026-10-15.12

## Check plan
Logic changed in two existing modules (bug_run.py, bug_store.py), no UI/security/data-write/prod trigger. Tier M. Quick lane: `tick.mjs --lane-check 69ebfae7` -> `LANE: none lane-disabled`, so a normal check. Steps: criteria vs issue text (AT-979, AT-980), affected bug tests, ruff, doctor, step 4c diff read, one falsification per criterion in copies outside the worktree.

VERDICT: PASS
SCOREBOARD: 2/2 criteria met (C1 = AT-979, C2 = AT-980), invariants: none touched (core-invariants, no schema/credential/file-size breach; bug_run.py 174 and bug_store.py 192 lines)
TIER: M (two existing modules, no L trigger)
FAILURES: none
CAPABILITY-COVERAGE: 2/2 rows reproduced
LIVE-BROWSER: not-applicable (src/autotester/stages/bug_run.py, src/autotester/store/bug_store.py, tests only)
ISSUES-WRITTEN: none

## Evidence (all run by the checker)
- Affected set (six bug test files, same list as the manifest): `uv run pytest tests/test_bug_run_replay.py tests/test_bug_store_hardening.py tests/test_bug_store.py tests/test_bug_store_concurrency.py tests/test_bug_run.py tests/test_bug_run_idempotent.py` -> 89 passed, 1 warning, 92 s. No full suite (unit check).
- `uv run ruff check src tests scripts` -> All checks passed! `uv run autotester doctor` -> doctor: clean (advisory D-000/D-005 notes only).
- C1 (AT-979, expected: a replay of an older run never rewrites or retroactively refuses a later FAIL): bug_run.py:`changed_case_events` stamps `max(at, latest stored event of that bug)`; `process_run` passes `snap.events`. tests/test_bug_run_replay.py reproduces FAIL r1, FAIL r2, edit, replay r1, re-see r2: refused == [], count 2, last_seen r2, case_changed at r2's time.
- C2 (AT-980, expected: legacy event files are read, or the store fails loud): bug_store.py:`snapshot()` accepts `file_name(event)` or `legacy_file_name(event)`; a legacy-named file holding another event is still bad (second test, green both sides). New events keep `file_name`. Builder chose read over raise; the issue text admits either.
- Falsification (copies of HEAD src+tests+scripts under the scratchpad, outside the worktree, PYTHONPATH on the copy; the bound tree was never edited):
  - Green in copy with the fix: the two named nodes, `3 passed`.
  - C1: copy with bug_run.py = base -> tests/test_bug_run_replay.py red on `assert (BugStatus.S..., 1, ...) == (..., 2, ...)  At index 1 diff: 1 != 2` (r2 refused) and `datetime(2026,10,1,9,1) != datetime(2026,10,1,9,2)`.
  - C2: copy with bug_store.py = base -> test_at980_an_old_store_of_legacy_named_events_is_read_not_silently_empty red: `BadEventFile(name='bev_4d65b9d7e750.json', why="file name is not this event's name")`, `1 failed`.
- Step 4c: `git diff 69ebfae7..HEAD --stat` = the manifest, bug_run.py, bug_store.py, two test files, all listed in What changed. Removed lines: only the one `events.append(_event(... at, run_id))` call and the old name check, each replaced in place; no def/class/export/test/config key deleted or renamed; qa/contracts and qa/issues.jsonl untouched.

## Notes (non-blocking)
- The edit time is not recorded, so the C1 stamp is the latest stored event of that bug, not the edit time. Replay-stable and ordered after the bug's history; builder disclosed this choice. Not a defect against the issue text.
- Manifest Pre-check lines carry t=42 and t=32 and the Metrics line is the maker's; reuse of them was not needed (checker re-ran everything above).

EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: Both issue texts are met and each is isolated by a named test that goes red when only its own source file is put back to base. Affected tests, ruff and doctor are green and the diff removes nothing the contract needs.
Metrics: start=2026-10-17T10:45:00Z end=2026-10-17T11:20:00Z wall_min=35 agent_min=unavailable blocked_min=18 suite_runs=0 repeat_runs=0 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=2100 mutants=0 defects_unit=0 defects_6c=0
slow: affected-set pytest 92 s plus a rate-limit wait (blocked_min)
