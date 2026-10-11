# Verdict - t200b-scheduled-test (T-200 phase B, buildable part)

Cycle checked: 0
Head checked: 0d9a3b56 (product sha e4e1b3a9; base 09828f2d), worktree .worktrees/t200b-scheduled-test, bound to D:/autoTesting
Policy: proportional-verification/2026-10-10.9. Evidence: qa/evidence/t200b-scheduled-test/checker-evidence.md. Checkpoint: qa/checkpoints/t200b-scheduled-test.md
Date: 2026-10-11. Coordinator A with 7 read-only Sonnet sub-checkers (tests/lint, TS5 mutants, TS7 mutants, purge+guard mutants, credential probes, purge race, HELD+scope). Lane check not applicable (L, contract says dual).

## Check plan
Logic and concurrency (affected tests plus falsification), security probe of the credential gate, diff read (step 4c), HELD audit against master 09828f2d. No UI surface (no browser walk). No data artifact, no prompt change.

VERDICT: FAIL
SCOREBOARD: 2/4 built criteria met (TS5 gate, TS7 tick side); 0 of the HELD parts claimed. TS6 AST guard and TS1 purge clause not met.
TIER: L (credential-derived run approval, TS5, the contract's CRITICAL criterion; the diff touches schedule_gate.py:68 and scheduler.py `_fire`)

## DUAL-CHECK RULING (first, as asked): a dual check IS required; the manifest's `Dual check: no` is wrong
- Contract: `qa/contracts/team-schedule.md:5-6` says "Tier L (concurrency/timing, auth, outward-facing run), so a dual check applies to TS2-TS6", with TS5 and TS6 CRITICAL. The unit builds TS5, TS6 and the tick side of TS7.
- Diff: `src/autotester/stages/schedule_gate.py:68` calls `covering_approval(... kind=LIVE_CASE ...)` for a provisioned project. That call decides whether a run that uses credentials may start, and it MINTS a signed `RunApproval` row (`explore_consent.py` `_credential_approval` -> `store.add_approval`). On first mint it also calls `ensure_approval_key`, which writes `AUTOTESTER_APPROVAL_KEY` into the repo-root `.env` and leaves a `.env.lock` (probe, evidence file). That is an auth/consent decision with a write to a secrets file, so the manifest's claim that the gate "only reads which declared keys have a value" and "writes nothing" is false for the provisioned path.
- Required action for the maker: add `dual-trigger: security src/autotester/stages/schedule_gate.py:68` and set `Dual check: required`; dispatch the repair as two blind coordinators (policy .8-3). This is not a silent downgrade: this single verdict is FAIL on its own evidence, and it does not stand in for the second coordinator.

## Criteria
- [TS5] credential gate, `blocked_no_credentials`, no trace: MET for the built part. `pytest tests/test_schedule_gate.py` 8 passed (re-run on 0d9a3b56). Falsifications killed: credential_state, approval-after-enqueue (the contract mutation the builder skipped: 6 reds on `len(q)==0`), refusal ignored, domain check dropped, fail-open on a raising gate. Owner inbox/project-page surfaces HELD.
- [TS7 tick side] `run_tick`, heartbeat at tick end, dry run, exit codes 0/2/3, a crashing project does not stop the rest: MET. 32 passed. 7 mutants killed, including the exit-3 branch and the `would_block` preview that the builder did not falsify. The CLI shell is HELD.
- [TS1 purge clause] `purge_project`: NOT MET. Own-project removal works (13 passed, 3 mutants killed), but the rewrite of the shared records file loses another project's records. See F2.
- [TS6 AST guard] NOT MET. The guard passes on a forbidden pipeline import. See F1. The one-launcher half is HELD.
- Gates: `ruff check src tests scripts` clean; `autotester doctor` clean; wide schedule set 133 passed; env readers 64 passed.

FAILURES:
- F1 [TS6] sev: medium (CRITICAL criterion) · the guard `tests/test_schedule_tick.py:167-180` compares `node.module` to a fixed list of dotted names and `node.names` to three names, so adding `from autotester.stages import explore` to `stages/scheduler.py` leaves `test_the_tick_modules_import_no_browser_or_pipeline_code` green; the contract forbids "the pipeline modules". Reproduced by me: unchanged copy `1 passed`, copy with that one line at scheduler.py:18 `1 passed` (command in the evidence file). Also survive: `from autotester.browser import session`, a transitive import (`stages.agent_loop` imports BrowserSession), and `schedule_gate.py` is not scanned (R12). Fix direction: normalise `from pkg import mod` to `pkg.mod`, resolve relative imports, add `schedule_gate.py`, walk the in-repo import closure of the scanned files. · issue: P1
- F2 [TS1 purge] sev: medium (data loss in changed code) · `schedule_store.py:97-108` rewrites the one shared records file; an append by another project landing between its read and `os.replace` is lost. Reproduced by me (probe_race.py): `after purge(A): ['B:...']`, "B's concurrently appended record LOST: True". Two-process stress: 92/100 of B's acknowledged appends survive, 4 appends crash with PermissionError (Windows), 81/100 purges fail; a failed purge leaves A's markers deleted and A's records kept, plus a leaked `.records.jsonl.<pid>.tmp`. Ruling on design choice 6: NOT acceptable, because the file is shared by every project, B keeps ticking, and TS1/TS2/HO23 promise B no loss; the contract has no text excusing a purge racing a live tick. Fix direction: per-project record files (purge = unlink), or a tombstone/filter-on-read, or a lock that appends and the rewrite both take; delete records before markers; clean the tmp file. · issue: P2

## Rulings on the other design choices
1. `TickDeps.gate` required, no default allow: accepted. But `scrub` is a defaulted identity beside it (P3).
2. Gate before the overlap check and before any enqueue; a raising gate ends `failed`, nothing enqueued: accepted, pinned by mutants R2 and R5. Side effect: an approval row is minted for a slot that is then `skipped_overlap` (P4).
3. `blocked_no_credentials` for all refusals with the state as the first word of `detail`: accepted.
4. `--dry-run` skips the gate, uses the read-only `refusal_for`, writes no heartbeat: accepted; before/after file listings show nothing written. One divergence (P5).
5. Default `CrawlBounds()` for the covering approval: accepted for now, wiring slice must pass the real bounds (minted row: max_actions 200, wall_clock_s 600, 10 min expiry).
6. `purge_project`: defect, F2.
7. Heartbeat written on exit 2/3 ticks: accepted, pinned by R6.

## Credential handling
`credential_state`/`refusal_for` return a state only and write nothing. Over 9 scenarios with fake sentinels (four states, malformed, missing, unreadable and invalid-UTF-8 .env) no value reached a record, TickReport, log line, exception text or approval row. Residual: P3 (identity scrub) and the `.env` write above.

## HELD audit on master 09828f2d
Dependencies confirmed missing: `Project.schedule` (only on unmerged `wave/t205-g10-headroom`), `cli_schedule.py`, `auth/` and `schedule.manage` (only on unmerged `wave/t204-team-login`), `stages/run_launcher.py` and `Run.slot_key`/`QueueEntry.slot_key` (T-205 / not on master), any inbox/email sender, any project-delete path. `run_tick`, the gate and `purge_project` have no callers in src or scripts, and the manifest claims nothing built for any HELD part. Soft findings: P6.

## Scope and new modules (human gate)
Diff 09828f2d..0d9a3b56: 11 files, every path listed in the manifest, nothing deleted or renamed (3 removed lines: a comment, a docstring sentence, a signature line), no file over 300 (scheduler.py 289).
- `src/autotester/stages/schedule_gate.py` (73, NEW): could fold into `explore_consent.py` (133, about 200 after) within the cap, but that file's docstring is "may this crawl start" and it would import `stages.scheduler.Slot`; keep separate unless the owner prefers one consent file.
- `src/autotester/stages/schedule_tick.py` (72, NEW): cannot fold into `scheduler.py` (289 + 72 > 300); into `schedule_store.py` it fits by size but breaks that file's one job and creates a circular import.
- `.env.example`: the new `AUTOTESTER_TIMEZONE` comment matches D-078 (UTC or IST, +05:30 fixed, blank = UTC) and `default_timezone` (`schema/schedule.py:88-90`); the grace (1..1440, 60) and tick (1..86400, 60) comments match `scheduler.py`. Wording gap only (P7).

## PROPOSED-ISSUE lines (no ledger rows written)
PROPOSED-ISSUE: {"id":"P1","severity":"medium","feature":"team-schedule","title":"TS6 AST import guard accepts `from autotester.stages import <pipeline module>`, is not transitive, and does not scan schedule_gate.py","evidence":"tests/test_schedule_tick.py:167-180; copy with one added line at scheduler.py:18 stays green (qa/evidence/t200b-scheduled-test/checker-evidence.md)","status":"open","found_by":"checker-unit"}
PROPOSED-ISSUE: {"id":"P2","severity":"medium","feature":"team-schedule","title":"purge_project rewrites the shared records file: another project's concurrent append is lost, ticks crash with PermissionError on Windows, a failed purge leaves markers deleted and records kept","evidence":"src/autotester/stages/schedule_store.py:97-108; probe_race.py output in the evidence file","status":"open","found_by":"checker-unit"}
PROPOSED-ISSUE: {"id":"P3","severity":"medium","feature":"team-schedule","title":"TickDeps.scrub defaults to identity, so a gate exception message containing a value reaches SlotRecord.detail and the TickReport; make scrub required like gate or default it to a redactor, and have the wiring slice pass SecretStore.redactor().scrub","evidence":"src/autotester/stages/scheduler.py:101-102,167-169; probe with RuntimeError from add_approval; no realistic raiser found, so non-blocking","status":"open","found_by":"checker-unit"}
PROPOSED-ISSUE: {"id":"P4","severity":"low","feature":"team-schedule","title":"The gate has write side effects the manifest denies: a signing key written to the repo .env with a leftover .env.lock on first mint, and an approval row minted for slots then skipped as overlap","evidence":"src/autotester/stages/schedule_gate.py:68, explore_consent.py _credential_approval; probe in the evidence file","status":"open","found_by":"checker-unit"}
PROPOSED-ISSUE: {"id":"P5","severity":"low","feature":"team-schedule","title":"--dry-run preview says would_fire when the approval signing key is lost but the real tick blocks (preview is state-only)","evidence":"schedule_gate.py refusal_for vs credential_gate; probe in the evidence file","status":"open","found_by":"checker-unit"}
PROPOSED-ISSUE: {"id":"P6","severity":"low","feature":"team-schedule","title":"Manifest wording: Run.trigger and Trigger.SCHEDULE already exist on master (schema/run.py:83, enums.py:155) so HELD 3 is only the launcher and slot_key; QueueEntry.slot_key plus an idempotent enqueue sit in T-203 files already on master (schema/run_queue.py, ui/run_queue.py); wave/t201a-report-delivery is not a local ref; schedule_fakes.py is 88 lines, not 86","evidence":"HELD sub-checker report","status":"open","found_by":"checker-unit"}
PROPOSED-ISSUE: {"id":"P7","severity":"low","feature":"team-schedule","title":".env.example AUTOTESTER_TIMEZONE comment omits that any other value (and lowercase ist/utc) silently falls back to UTC, and the tick-interval comment ignores the 48 h daily rule","evidence":".env.example:89-96; schema/schedule.py:88-90; team-schedule.md TS7","status":"open","found_by":"checker-unit"}
PROPOSED-ISSUE: {"id":"P8","severity":"low","feature":"team-schedule","title":"process: manifest Metrics start=01:30:00Z / wall_min=70 are invented; the branch was created 01:59:32Z and the manifest committed 02:40:04Z (about 41 min); this checker also ran 24 mutations against the L cap of 10 (mutant-cap-raise cited)","evidence":"git log --format=%aI 09828f2d..0d9a3b56; branch reflog","status":"open","found_by":"checker-unit"}

## Notes for the maker
Not merged, T-200 stays open (HELD parts remain, two new modules await the owner). The repair is cycle 1 and must be dual (add the `dual-trigger` line). Unverified, not claimed: `tests/test_hosting_deploy.py` env-key test was probably red on master (scheduler.py reads two keys that master's `.env.example` lacked) and this branch turns it green.
HUMAN_GATE-REQUEST: owner decides whether `schedule_gate.py` stays separate or folds into `explore_consent.py`, and confirms both new modules before merge.
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
Metrics: start=2026-10-11T02:41:00Z end=2026-10-11T03:03:00Z wall_min=22 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=24 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=1320 mutants=20 defects_unit=2 defects_6c=0
