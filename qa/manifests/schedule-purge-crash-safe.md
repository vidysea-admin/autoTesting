# Manifest - schedule-purge-crash-safe
**Contract:** qa/contracts/team-schedule.md
**Goal task:** none
**Date:** 2026-10-17
**Fix cycle:** 0 of max 2
**Persona walk:** skip (api-only: no human screen; storage helper)
**Issues addressed:** AT-943
**Executor:** claude-sonnet-subagent
**Executor rationale:** single-file storage fix sized for one build agent

## What changed
- `src/autotester/stages/schedule_store.py:150-232` - `purge_project` now runs under the project's records lock; rolls back on `BaseException` (SystemExit, Ctrl-C), not only OSError; writes a manifest (`manifest.json`, tmp then `os.rename`) into the stage dir before the first move and deletes it as the commit point; the rollback (`_restore_stage`) tries every file, never overwrites an existing file, and keeps the stage if one restore fails. New `_stage_prefix`, `_restore_stage`, `_recover_stages`, `recover_stale_purges`, `_purge_locked`. Stage dirs are named `.purge-<sha256(project)[:16]>-<uuid>` so a purge only adopts its own project's leftovers. The next purge (or `recover_stale_purges`) adopts a stranded stage: manifest present = put the files back, manifest absent = committed or never started = delete.
- `tests/test_schedule_purge_crash.py` (new, 7 test functions, 8 cases): SystemExit and KeyboardInterrupt at the 2nd move, a failed restore not stopping later restores, hard kill (`os._exit`) after 1 and after 3 moves, hard kill after commit before the stage delete, no overwrite on adoption, another project's stage left alone.
- File sizes: schedule_store.py 257 lines, test file 193. No new src module.

## Verification scope
Policy-Version: proportional-verification/2026-10-15.12
Tier: M (storage write path, one file, no security gate)
Base / checked state: 69ebfae7 / d3c2e5f5
Gate answers: none (no gate applies; no new module)
Affected tests / full-suite trigger: tests/test_schedule_purge_crash.py tests/test_schedule_marker.py; no full-suite trigger. The builder ran no full suite. Another caller of `purge_project`: ui/routes_schedule.py:138 (unchanged signature).
Pre-check[C1]: d3c2e5f5 uv run pytest tests/test_schedule_purge_crash.py tests/test_schedule_marker.py -> 18 passed in 136.00s t=136 blobs=tests/test_schedule_purge_crash.py:7697d3a,tests/test_schedule_marker.py:9c0a3bc
Metrics: start=2026-10-17T13:55:00Z end=2026-10-17T14:38:00Z wall_min=43 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=1 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=136 mutants=1 defects_unit=0 defects_6c=0

## How to verify (commands + expected)
- `uv run pytest tests/test_schedule_purge_crash.py tests/test_schedule_marker.py` -> expected: 18 passed
- `uv run ruff check src tests scripts` -> expected: All checks passed!
- `uv run autotester doctor` -> expected: doctor: clean

## Actual outputs (from maker's own run)
- pytest (both files): `18 passed, 1 warning in 136.00s (0:02:15)` (spawned child processes make the run slow on this machine)
- ruff: `All checks passed!`
- doctor: `doctor: clean`
- AT-943 C1 (expected: "A purge interrupted at any point leaves either all files or none, and a later purge adopts or removes stale .purge-* dirs"): covered by the SystemExit / KeyboardInterrupt cases (all files back, no stage dir) and the hard-kill cases (stage adopted by the next purge: put back if uncommitted, removed if committed).

## Capability coverage (each new claim -> its isolating falsification)

| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| C1 | an interrupted or killed purge leaves all files or none, and the next purge adopts a stranded `.purge-*` stage | tests/test_schedule_purge_crash.py::test_a_purge_interrupted_by_systemexit_or_ctrl_c_leaves_every_file_and_no_stage_dir | revert schedule_store.py to base 69ebfae7 (OSError-only rollback, no manifest), in a throwaway copy outside the worktree | green@d3c2e5f5: `1 passed, 8 deselected` (-k system_exit) ; red@69ebfae7: `AssertionError: assert (['.purge-e3a5...rds\p.jsonl'] == ['claims\p%3...rds\p.jsonl']` / `At index 0 diff: '.purge-e3a5f2f3815f493f85e90caa22a9dd81\0' != 'claims\p%3Afixed%3A2026-10-08T09%3A00Z.claim'` / `2 failed, 6 deselected` (system_exit and keyboard_interrupt cases both fail on the assertion, not on import) |

The hard-kill cases call `recover_stale_purges`, which does not exist on the base, so on the reverted copy they fail with AttributeError after their first assertion (a stage dir was stranded) passes; the SystemExit case above is the assertion-level falsification.

## Live browser evidence
Not UI-touching - no surface changed: src/autotester/stages/schedule_store.py and tests/test_schedule_purge_crash.py only.

## Status: checked-PASS (qa/verdicts/schedule-purge-crash-safe.md, cycle 0)
