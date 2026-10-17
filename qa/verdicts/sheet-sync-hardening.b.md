# Verdict - sheet-sync-hardening (coordinator B, blind)

Cycle checked: 0
Bound to: D:/autoTesting/.worktrees/sheet-sync-hardening ; base 69ebfae7 (= git merge-base HEAD master) ; head ea65f9b5 (code b3844a0d)
Policy-Version: proportional-verification/2026-10-15.12

## Check plan
Logic + security: security/write-barrier (sheet_write.py `_assert_writable`) and secret redaction (sheet_plan.py `scrub`). Affected tests re-run; one falsification per criterion in throwaway copies outside the worktree (scratchpad chkb/c1..c4); step 4c diff read; ruff + doctor. No UI, no persona walk, no full suite (6c covers it).

VERDICT: PASS
SCOREBOARD: 4/4 criteria met (AT-981, AT-982, AT-983, AT-984), 0/0 invariants touched
TIER: L (security trigger: src/autotester/stages/sheet_write.py:89 write barrier; src/autotester/stages/sheet_plan.py:108 scrub of sheet text; matches the manifest, not raised or lowered)
FAILURES: none
CAPABILITY-COVERAGE: 5/5 rows reproduced (C1, C2, C3a, C3b, C4), each green in the copy before and red on the named assertion after
LIVE-BROWSER: not-applicable (src/autotester/stages/sheet_plan.py, sheet_write.py, schema/sheet_plan.py, tests only)
ISSUES-WRITTEN: none (dual coordinator; no rows written)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## Evidence I produced
- `uv run pytest tests/test_sheet_sync_hardening.py tests/test_sheet_plan.py tests/test_sheet_sync_tb12_tb14.py` -> 37 passed, 1 warning (8.94 s). Matches the manifest's 37.
- `uv run ruff check src tests scripts` -> All checks passed! ; `uv run autotester doctor` -> doctor: clean.
- Diff `git diff 69ebfae7..HEAD` read in full: 6 files, all listed in the manifest's What changed; nothing deleted or renamed (4c clean; `plan_sync`/`_row_for` signature change is internal, importers sheet_sync.py and tests pass).
- Falsification (copy of HEAD via git archive, copy imports its own src, verified), green before / red after:
  - C1 AT-981 `before=scrub(have)`, `sheet_has=scrub(have)` -> raw: 1 passed -> `assert not True` (secret in plan JSON/render).
  - C2 AT-982 `if new and last != new:` -> `if False:`: 1 passed -> `adopts` empty, `{} == {'bug_...': {'Status': 'fixed'}}`.
  - C3a AT-983 `isinstance(client, tuple(_WRITERS))` check -> `if False:`: 1 passed -> `DID NOT RAISE WriteRefused`.
  - C3b AT-983 post-read and per-row `_assert_writable` removed: 1 passed -> `DID NOT RAISE LiveWriteRefused`.
  - C4 AT-984 `unguard(...)` compares -> raw: 1 passed -> PlanRow(action='conflict') `sheet_has='-5', we_last_wrote="'-5"`.
- Reading: sheet_write.py:89-97 refuses `live` (a client with no flag counts as live) then non-registered class; called at :107 (before read), :110 (after read, before plan), :118 (before each write). `_WRITERS` is empty in production (:51); only tests/sheet_fake.py registers. AT-983 text asks for "a structural check, not a self-declared flag, and the flag re-checked after the read": met. The module-level list is not tamper-proof (any code can call `register_writer`); that is beyond the AT-983 text.
- Hash compatibility: schema/sheet_plan.py:116-118 adds `adopts` to the hash input only when non-empty; existing plan tests still green.

## Non-blocking observations (PROPOSED-ISSUE, low)
PROPOSED-ISSUE: {"feature":"team-bug-loop","severity":"low","type":"security","title":"register_writer is a public mutable allow-list: any importer can register a live-capable class, so the barrier is structural but not tamper-proof; the live slice should replace it with a gate-backed check (qa/gates/t199-first-live-write.md)","evidence":"src/autotester/stages/sheet_write.py:51-58","expected":"a live client is admitted only by the approved first-write record","fix_direction":"tie registration to the gate record when the live slice is built"}

Lane exit: none (tier L, dual check; quick lane not applicable)
EXPLANATION: All four issue texts are met by the code as read at the cited lines and by fresh runs; each criterion has a falsification that goes green in a clean copy and red on the named assertion. The unit adds no live client and makes the refusal stricter, so gate t199-first-live-write stays open. Judged blind: the other coordinator's files were not read.
Metrics: start=2026-10-17T14:40:00Z end=2026-10-17T16:40:32Z wall_min=unavailable agent_min=unavailable blocked_min=unavailable suite_runs=0 repeat_runs=0 mutations=5 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=unavailable defects_unit=0 defects_6c=0
(note: the wall span includes a rate-limit pause; active work was roughly 15 min)
