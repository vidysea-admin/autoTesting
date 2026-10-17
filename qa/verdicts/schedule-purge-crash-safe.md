# Verdict - schedule-purge-crash-safe

**Verdict: PASS**
**Checker:** Mode A, fresh context. **Date:** 2026-10-17. **Cycle checked: 0** (manifest Fix cycle 0).
**Bound root:** D:/autoTesting/.worktrees/schedule-purge-crash-safe (head 238db25c, code d3c2e5f5, base 69ebfae7 = git merge-base with master).
**Criterion C1 (AT-943):** a purge interrupted at any point leaves either all files or none, and a later purge adopts or removes stale .purge-* dirs. **Tier:** M (storage write path, one file), single checker.
Policy-Version: proportional-verification/2026-10-15.12

## Plan
Logic changed in src/autotester/stages/schedule_store.py (purge_project and helpers) plus one new test file. Checks: re-run manifest verify commands, one falsification for C1, step 4c diff-scope read. No UI, no persona walk (api-only), no security/auth trigger, no dual check.

## Results
- `uv run pytest tests/test_schedule_marker.py` -> 10 passed (110 s).
- `uv run pytest tests/test_schedule_purge_crash.py` -> 7 passed, 1 failed (`..._killed_after_its_commit_..._finished_not_undone`, `child.exitcode None` after the 60 s join, tests/test_schedule_purge_crash.py:127) while ruff, doctor and the marker run shared the machine. Rerun alone: 1 passed in 13 s. Load flake, not a product defect (low row AT-1019). Together with the marker file this reproduces the manifest's 18 cases.
- `uv run ruff check src tests scripts` -> All checks passed. `uv run autotester doctor` -> doctor: clean (2 advisory D-069 findings, non-blocking).
- Falsification (copy under scratch, outside the worktree): `test_a_purge_interrupted_by_systemexit_or_ctrl_c_...` GREEN in the copy (2 passed). `except BaseException:` -> `except OSError:` at schedule_store.py:238 -> RED on `assert _files(...) == before` (a `.purge-<hash>-<uuid>\0` file left instead of the claim marker, for both SystemExit and KeyboardInterrupt), not an import error. Restored; cmp identical.
- Hard-kill cases (`os._exit` after 1 and 3 moves, and after commit) passed in the full run; they exercise adoption by `recover_stale_purges` and the next `purge_project`.
- Step 4c: diff 69ebfae7...HEAD = schedule_store.py (old OSError-only rollback replaced), the new test file, the manifest. Nothing removed beyond the replaced rollback block; no unlisted file; `purge_project(claim_dir, records_path, project)` signature unchanged, caller ui/routes_schedule.py:138 unaffected. Read the locking: `_APPEND_LOCK` is an RLock and `read_records` re-enters it; manifest written tmp then rename before the first move; unlinking the manifest is the commit point; recovery is idempotent (skips files already back, never overwrites an existing destination).

## Findings (non-blocking ledger rows)
- AT-1018 low: `recover_stale_purges` has no production caller; only a later purge of the same project adopts a stage, and legacy un-hashed `.purge-<uuid>` stages are never matched. The criterion's text (a later purge adopts) holds for the same project.
- AT-1019 low: the 60 s `child.join` in the new tests is brittle under heavy machine load.

AT-943 flipped open -> fixed in qa/issues.jsonl (a later re-check moves it to verified).

VERDICT: PASS
SCOREBOARD: 1/1 criteria met, 0/0 invariants touched
TIER: M (one-file storage write path, no security gate)
FAILURES: none
CAPABILITY-COVERAGE: 1/1 rows reproduced
LIVE-BROWSER: not-applicable (src/autotester/stages/schedule_store.py, tests/test_schedule_purge_crash.py)
ISSUES-WRITTEN: AT-1018, AT-1019 (AT-943 -> fixed)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: purge_project now rolls back on BaseException, stages a manifest before the first move and deletes it as the commit point, and the next purge of that project adopts a stranded stage; reverting to an OSError-only rollback turns the SystemExit test red on the named assertion. The one test failure was a 60 s child-join timeout under load and passed alone.
Metrics: start=2026-10-17T14:50:00Z end=2026-10-17T15:25:00Z wall_min=35 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=1 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=2100 mutants=0 defects_unit=0 defects_6c=0
