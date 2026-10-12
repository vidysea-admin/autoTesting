# Verdict - t200a-schedule-core (T-200 phase A; does NOT close T-200)

Checked: 2026-10-11 · bound to D:/autoTesting · branch wave/t200a-schedule-core @ 782bb254 (code 4662f250) · base 3a16616c (merge-base with master) · Cycle checked: 0 · Resume: 0 of 2 · Retry: 0
Policy-Version: proportional-verification/2026-10-10.9

## Plan (step 0)
Tier L (manifest; kept, nothing to raise or lower): timing/concurrency at `stages/schedule_store.py:35` (O_EXCL claim) and `stages/scheduler.py:130` (60-min window edge). Single check (no `dual-trigger` line; none applies). Checks: the 112 affected tests re-run; one falsification per criterion TS1/TS2/TS3/TS4/TS7 in isolated copies; two extra guidance mutants (torn-claim rebuild, claim race); step 4c diff read; design-rule scan. No UI, no browser, no model/network, no full suite (trigger: none). Contract judged = ROOT master text (D-078 amendment, 057b6dbb). The worktree copy of `team-schedule.md` is the pre-amendment text (IANA zones, DST rows, tzdata); that difference does not change what TS1-TS4 or TS7 require of this code (the code implements the master text: UTC/IST fixed offsets, no zoneinfo). No contract edited.

VERDICT: PASS
SCOREBOARD: 5/5 criteria met (TS1, TS2, TS3, TS4, TS7 at phase-A scope per the brief), 0/0 invariants touched
TIER: L (concurrency/timing: `schedule_store.py:35`, `scheduler.py:130`)
FAILURES: none
CAPABILITY-COVERAGE: 5/5 rows reproduced (+2 guidance mutants)
LIVE-BROWSER: not-applicable (no UI surface changed: core/, schema/, stages/, tests/)
ISSUES-WRITTEN: none (see PROPOSED-ISSUE lines)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## Evidence (all re-run by this checker in a `git archive 782bb254` copy; the builder's lines carry no `blobs=`, so none reused)
- Affected tests: the six schedule test files together -> 112 passed (34 s). `ruff check src tests scripts` -> All checks passed.
- [TS1] model: 45 passed in `test_schedule_model.py`. Falsify: weekday check `d > 6` -> `d > 7` (schema/schedule.py): 45 green -> RED `test_invalid_schedule_is_refused_with_a_reason_naming_the_field[weekday 7]`.
- [TS2] pure `due()`, UTC/IST, O_EXCL claim: 14 passed in `test_schedule_due.py`; marker file 6 passed. Falsify: fixed-rule `resolve_local(..., tz)` -> `UTC` (schedule_time.py): 14 green -> RED 4 (`test_ist_nine_oclock_is_0330_utc_every_day_of_the_year` and 3 more).
- [TS3] catch-up: 22 passed. Falsify: `fire = inside[-1]` -> `inside[0]`: RED `test_two_slots_inside_the_window_run_only_the_latest_and_the_earlier_is_superseded`.
- [TS4] overlap: 6 passed. Falsify: blocker ignores `e.active`: RED `test_a_finished_entry_does_not_block` and `test_the_next_slot_is_judged_fresh_after_a_skip`.
- [TS7 pure part] 19 passed. Falsify: stale limit `>` -> `>=` (scheduler.py:282): RED `...stale_after_two_intervals_of_48_hours[48h-exactly]` and `[120-healthy]`. One of the three items the builder did not falsify; now falsified, the exact-limit boundary is pinned (contract says "exceeds", `>` is right).
- Guidance mutants (2 of cap 10): torn-claim rebuild `_rebuilt` -> `return None`: 6 green -> RED `test_a_claim_file_torn_before_its_body_was_written_is_still_driven_to_one_entry`. Claim race: below.
- Every green-before ran in the copy; every red is on the named assertion, not an import error. Scripts: scratchpad `check-t200a/falsify.py`, `race.py`.

## Claim race (the builder's unfalsified item), plainly
The real claim has NO check-then-act: `schedule_store.py:35` is one `os.open(O_CREAT|O_EXCL|O_WRONLY)`, atomic on Windows and Ubuntu; the loser gets FileExistsError and returns False. Real code: the two-process test passed 6 of 6 extra re-runs (and in the 112 run). Mutant `exists()` then `os.open` without O_EXCL: the two-process test went RED in 6 of 12 runs (p about 0.5, so N=ceil(3/p)=6 passes catch it with about 98 percent probability). So TS2's claim test does cover the race, but as a probabilistic detector (one run misses it half the time); not a floor failure. Residual (narrow, not a FAIL): the RE-DRIVE of an aged recordless claim (`scheduler.py:196-210` -> `_write` -> `_fire` -> `deps.enqueue` at :161) takes no exclusive lock, so two ticks re-driving the same claim at once both call `enqueue`; at-most-one then rests on the queue idempotency key, which TS2 assigns to T-203/HO23 and phase A models only in `schedule_fakes.py`. No test drives two concurrent re-drivers. Tier L is correct; I raise nothing.

## Other checks
- 4c diff scope: merge-base..HEAD = 5 src + 7 tests new, the manifest, `docs/MAP.md` +14/-0 (generated). No deletion or rename; the 12 code/test files are blob-identical to `wave/g5-schedule-core` (12 of 12). No existing module touched.
- `scheduler.py` (284 lines): imports only schema, schedule_store, schedule_time and stdlib; no browser/runner/network import; no clock call; `due()` reads no env or file. In this phase it writes only the injected `claim_dir` and `records_path`; `write_heartbeat` exists in the store but the tick never calls it (owed to phase B). It starts no run except through injected `deps.enqueue`.
- Design rules: files <= 300, every function < 40 lines, module docstrings present; all 4 Pydantic models (`WeeklyRule`, `ScheduleConfig`, `SlotRecord`, `SlotClaim`) are in `schema/schedule.py` with `extra="forbid"`. The frozen dataclasses in `scheduler.py` (Slot, Due, MissedSlot, QueueSnapshot, SchedulerStatus, TickDeps) are internal seam types, as in 8 other stage modules; low note only. `autotester doctor` not re-run (the copy has no git); the manifest's single `stale-generated: docs/SNAPSHOT.md` comes from master and no unit file breaches a rule I measured.
- Seam count: 0 earlier verdicts in `qa/verdicts/` name these files; D-014 cap not reached.
- Full-suite trigger: none. Persona walk: skip (no UI). Owed to phase B and not judged here: TS5, TS6, TS1 routes / `Project.schedule` / purge, TS7 CLI / heartbeat write / card / inbox, HO24 `refused`.

## Proposed issues (all low; none blocks)
PROPOSED-ISSUE: {"severity":"low","feature":"team-schedule","title":"Re-drive of an aged claim is not exclusive; at-most-one enqueue rests on the T-203 queue idempotency key; add a concurrent re-drive test in phase B","evidence":"stages/scheduler.py:196-210,161; tests/test_schedule_marker.py has no concurrent re-drive case"}
PROPOSED-ISSUE: {"severity":"low","feature":"team-schedule","title":"TickDeps.scrub defaults to identity; phase B must wire a real scrubber before failure details reach slot records (no-fire list: no secret in a record)","evidence":"stages/scheduler.py:101"}
PROPOSED-ISSUE: {"severity":"low","feature":"team-schedule","title":"_rebuilt classifies a torn claim by file mtime vs instant (> grace) while due() uses the minute-floored clock: a torn claim written in the last minute of grace can be rebuilt as missed instead of enqueued (read only, not run)","evidence":"stages/scheduler.py:191 vs :130"}
PROPOSED-ISSUE: {"severity":"low","feature":"team-schedule","title":"The two-process claim test detects an exists()-then-write claim in about half of runs (6 of 12); a barrier inside the claim would make the contract mutation deterministic","evidence":"scratchpad check-t200a/race.py"}

Metrics: start=2026-10-10T19:47:00Z end=2026-10-10T20:09:00Z wall_min=22 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=18 mutations=7 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=1320 mutants=2 defects_unit=0 defects_6c=0
