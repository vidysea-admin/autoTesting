# Manifest — t199b-bug-loop-run (T-199 second slice: run directory to bug events, store hardening, sheet DRY RUN plan)

**Contract:** qa/contracts/team-bug-loop.md TB3, TB4, TB6 (held clauses of t199a closed); TB9, TB10, TB11, TB13 (part, as a dry-run plan on a fake client); TB2 stored-N clause, TB7, TB8, TB12, TB14, HG-TB1 held
**Brief:** qa/briefs/t199b-bug-loop-run.md (and qa/briefs/t199-bug-loop-dry-run.md it builds on; never edits qa/contracts)
**Fix cycle:** 0 of max 2
**Dual check:** no. No `dual-trigger`: this slice has no auth, tenancy or security surface (no route, no session, no permission key; the confirmer is a named string and the `project.edit` check is T-204's), and it is not a prod write. The sheet-write PLAN has no live client: `SheetClient` has one implementation, a test fake, and `write_confirmed_plan` raises `LiveWriteRefused` on any client whose `live` is true (`src/autotester/stages/sheet_write.py:77`). No Google API, no `gws`, no network, no first-write-confirmed record was created.
**Persona walk:** skip (no UI route or screen; TB7 is held)
**Executor:** claude-sonnet-subagent
**Branch:** wave/t199b-bug-loop-run
**Base:** d55bec37 (t199a merged; master 4e0903cd)
**Head:** 50676d85fae1198f2cabbe3d2ac68ae265ab0b87 (code is unchanged since 0d263eab; 50676d85 adds only the two briefs)

## Criteria served

- TB3 verdicts only, replayed runs included — **full, including the held clause**. `stages/bug_run.py::process_run` reads `Verdict` files off a finished run directory and maps each through `kind_of_verdict` (`verdict_events`, the one door). It imports no `RawResult` and no network (AST test `test_the_run_stage_never_reads_a_raw_result_or_the_network`). Raw-only run: no change; replayed run with a judge verdict: counted; PASS without evidence: not counted.
- TB4 honest close — **full except as listed in gaps**. A case deleted, or a criterion removed or edited (`Criterion.fingerprint`), makes a live bug `stale` through a `case_changed` event at the next processed run, never `fixed`; a `case_changed` and a PASS at one instant go stale (rank in `order_key`); a closed bug is not swept; closing never deletes the pinned case (`delete_case` still refuses).
- TB6 idempotent per run — **full on Windows; the Ubuntu run is held to T-203's deploy check** (contract text). Event `at` is the run's own time (`finished_at or created_at`), never the clock, so processing a run twice leaves the store byte for byte equal; a crash after bug 1 of 2 converges on retry with no double count; racing processes writing one fact with different times converge (P8). The contract's "processed-run marker" is the per-event id plus the file check (gap G5 of t199a).
- TB9 first write shown and confirmed — **part (dry run)**. `plan_sync` and `render_plan` show exact cells (sheet, tab, row action, before, after) under "DRY RUN - nothing has been written"; `write_confirmed_plan` writes nothing without a `PlanConfirmation` of the exact `plan_hash`, recomputes the plan from a fresh sheet read, and raises `PlanChanged` on any one-cell difference; a machine cannot confirm; a live client is refused whatever the confirmation. Held: `first_write_confirmed_by/at` stored on the project and the `project.edit` check (T-204 / the live slice).
- TB10 own rows only — **part**. The `SheetClient` Protocol has `read`, `append_row`, `update_cells` and no delete or clear (asserted on the Protocol's attributes); rows are located by the bug-key column; unmapped columns are never in a write; a cell that differs from what we last wrote is a reported conflict, never a write (`SyncMemory`). Held: the `sync_conflict` flag on the bug and the tracker-page list (TB7).
- TB11 idempotent and convergent — **part**. Syncing twice: no duplicate rows, second plan empty; a crash after row k converges with every row once (memory is updated per row).
- TB13 clean values — **part**. Every planned value passes `scrub` (the `Redactor`) before it is planned or shown; a leading `=`, `+`, `-`, `@`, tab or CR is neutralised with an apostrophe before the hash. Held: error-string scrub, authenticated-link check, sheet-id fixed at confirmation (needs the binding, TB8).
- Checker findings of t199a folded in: P3, P4, P8, P9 (below). P1 and P2 are pinned, not decided. P6 (stored `close_passes`) is not built.

**Held / not built:** TB2 stored-N clause (P6), TB7 tracker page and routes, TB8 mapping proposal and binding, TB12 outage status, TB14 two-layout fixture, HG-TB1 the live write (`qa/gates/t199-first-live-write.md`, OPEN), a live sheet client, `Project.bug_close_passes`.

## Checker findings folded in

- **P3** (O(n²) re-read): `BugStore.snapshot()` reads every event file once; `apply_all(events, snapshot=...)` takes the caller's snapshot, and `process_run` takes one snapshot per run. Tests count `read_json` calls: a batch of 10 into a store of 30 reads 30 files, not 40; a run reads each file once.
- **P4** (corrupt or zero-length file): `snapshot().bad` names each bad file (torn JSON, zero-length, non-event JSON, a file name that is not its event's name); valid events are kept; nothing is deleted; the same event applied again repairs its own invalid file; a persistent `PermissionError` still raises (it is not corruption). `RunReport.bad_files` carries them. The t199a test that expected a raise was changed to assert contained plus named (`tests/test_bug_store.py`).
- **P8** (event time): **refuse, not clamp.** `storable(event, now)` refuses `Refusal.IMPLAUSIBLE_TIME` when `at` is later than now + 5 minutes or earlier than 2020-01-01 UTC; at write time only, through an injectable `BugStore(clock=...)`; the fold never reads the clock, so a stored event always folds the same. A refused time writes nothing and is accepted once its time has come. Clamping was rejected: it would silently change the recorded fact. Deterministic fold: the file name is now `bev_<id>@<UTC time>Z.json`, so two writers of one fact (same bug_key, ref, kind) with different `at` keep both files; the fold counts the fact once, at its earliest applied copy, whatever the write order (all 6 orders of 3 copies tested; racing processes tested).
- **P9** (`bug_key`): 1..200 characters, no control characters (`no_control`) on `BugSeed` and `BugEvent`; and a store-only replay test asserts `bug.count` and every file byte unchanged over three replays.
- **P1** (a new FAIL on a stale key) and **P2** (an uncited FAIL breaks a pass streak): behaviour kept, pinned by `test_p1_choice_pinned_a_new_fail_on_a_stale_key_is_refused_not_reopened` and `test_p2_choice_pinned_an_uncited_fail_does_not_break_a_pass_streak`. Both are HUMAN_GATE questions below.

## New modules (D-082 item 1; each named in the brief, one-job docstring, `autotester doctor` clean)

| File | Lines | One job |
|---|---|---|
| `src/autotester/schema/bug_run.py` | 66 | shapes: `BadEventFile`, `BugSnapshot`, `RunOutcome`, `RunReport` |
| `src/autotester/stages/bug_run.py` | 163 | `process_run` and its two event builders; reads verdicts and the case list, nothing else |
| `src/autotester/schema/sheet_plan.py` | 154 | plan shapes: `SheetColumns`, `SheetState`, `PlanRow`, self-hashing `SheetPlan`, `SyncMemory`, `PlanConfirmation` |
| `src/autotester/stages/sheet_plan.py` | 143 | the pure plan and its rendering; no client, no file, no network |
| `src/autotester/stages/sheet_write.py` | 92 | `SheetClient` Protocol, `dry_run`, `write_confirmed_plan` (refuses live) |
| `tests/bug_run_fixture.py` | 57 | test helper: a project with cases, rubrics and run directories |
| `tests/sheet_fake.py` | 55 | the in-memory fake `SheetClient` that records every call |
| `tests/test_bug_run.py` | 272 | TB3, TB4, P1/P2 pins, unresolved failures, run guards |
| `tests/test_bug_run_idempotent.py` | 126 | TB6, P3 and P4 over a run, import guard |
| `tests/test_bug_store_hardening.py` | 203 | P3, P4, P8, P9 on the store |
| `tests/test_sheet_plan.py` | 284 | TB9, TB10, TB11, TB13 on the fake sheet |

Edited in place (no new file for them): `src/autotester/store/bug_store.py` (170), `src/autotester/stages/bug_loop.py` (236), `src/autotester/schema/tracked_bug.py` (186), `src/autotester/schema/verdict.py` (121, `Criterion.fingerprint`), `tests/test_bug_store.py` (265, one test changed as above). `docs/MAP.md`, `docs/SNAPSHOT.md` regenerated. All files at or under 300 lines.

## Contract gaps (conservative reading taken; checker to rule)

- G1 A FAIL verdict citing criterion X gives no PASS credit to the case's other bugs: a failed verdict is one FAIL event for X only; the case's other bugs see nothing from it.
- G2 An edited criterion keeps its id, so its bug key is unchanged: the old bug goes `stale` and a new FAIL on that key is refused (this is P1). Keying with the criterion fingerprint would open a fresh bug; held for the owner.
- G3 `case_changed` is detected at the next processed run, not at the instant of the edit, and uses the current case list; an empty or missing case list is `unverifiable` for every live bug, never "all cases deleted".
- G4 A FAIL naming a case or criterion that no longer exists opens no bug (it would be stale on the next look) and is listed in `RunReport.unresolved_failures` each time, the same each time (idempotent).
- G5 `Run.finished_at` is never set by the product; `run.json` is saved after the last case, so its existence means finished, and the event time is `finished_at or created_at`.
- G6 `SyncMemory` (what we last wrote) is a plain model here; where it is stored and how it is loaded is the live slice's.
- G7 `PlanConfirmation` has no compare-and-set and `confirmed_at` is unchecked: a confirmation of a hash can be reused while the plan stays equal. The `project.edit` check is T-204's. `client.live` is the client's own claim; the real client must set it true and the live slice must not trust it alone.
- G8 D-083 item 3 (the maker's unconfirmed reading of the first-write gate) is not acted on.
- G9 Old `<id>.json` event file names (t199a) would show as bad files; no such data exists outside tests.
- G10 `trace` keeps the first applied copy of a duplicated event id; "counted once, at its earliest time" is the rule for the fold.
- G11 The contract's TB13 "authenticated product URLs" has no link in the plan yet (no screenshot column is mapped); held with TB7.
- Fresh-context review (senior-software-engineer): Warning. Fixed: a FAIL on a missing case or criterion opened a non-idempotent bug; an empty case list read as mass deletion; a corrupt rubric crashed a run; formula-looking cells; duplicate live-status tuples (now `LIVE_STATUSES`); a doc claim. Not fixed: the confirmation replay (G7), noted for the live slice; the edited-criterion key (G2 / P1), a HUMAN_GATE.

## HUMAN_GATE questions (owner decides; the behaviour is kept and pinned by a named test)

1. **P1.** When a bug is `stale` (its criterion was edited or its case deleted), should a new FAIL on that key open or reopen the bug? Today it is refused (`stale_bug`) and listed; the alternative is a bug key that includes the criterion fingerprint so an edited criterion starts a fresh bug. Pin: `test_p1_choice_pinned_a_new_fail_on_a_stale_key_is_refused_not_reopened`.
2. **P2.** Should a FAIL that cites no criterion (inconclusive-shaped) break a pass streak? Today it does not: the streak is per bug and only a FAIL citing that bug's criterion resets it. Pin: `test_p2_choice_pinned_an_uncited_fail_does_not_break_a_pass_streak`.
3. HG-TB1 stays open: the first live write to the real Pathlynks Tracker (`qa/gates/t199-first-live-write.md`). This slice does not touch it.

## Verification scope
Policy-Version: proportional-verification/2026-10-10.9
Tier: L — racing writers on the event store (several processes write one log, with a file-name change), and an outward-facing write PLAN (CRITICAL criteria TB9, TB10, TB13, proven on a fake client).

Pre-check: 50676d85fae1198f2cabbe3d2ac68ae265ab0b87 uv --directory D:/autoTesting/.worktrees/t199b-bug-loop-run run pytest tests/test_bug_run.py tests/test_bug_run_idempotent.py tests/test_bug_store_hardening.py tests/test_sheet_plan.py -k "tb3 or p2_choice" -p no:xdist -o addopts= -> 9 passed (criterion TB3 verdicts only, run directory) t=9
Pre-check: 50676d85fae1198f2cabbe3d2ac68ae265ab0b87 uv --directory D:/autoTesting/.worktrees/t199b-bug-loop-run run pytest tests/test_bug_run.py tests/test_bug_run_idempotent.py tests/test_bug_store_hardening.py tests/test_sheet_plan.py -k "tb4 or case_list_is_not or corrupt_rubric or p1_choice" -p no:xdist -o addopts= -> 11 passed (criterion TB4 honest close, changed and deleted cases) t=9
Pre-check: 50676d85fae1198f2cabbe3d2ac68ae265ab0b87 uv --directory D:/autoTesting/.worktrees/t199b-bug-loop-run run pytest tests/test_bug_run.py tests/test_bug_run_idempotent.py tests/test_bug_store_hardening.py tests/test_sheet_plan.py -k "tb6 or gone_opens_no_bug or p3 or p4 or p8 or p9 or not_finished" -p no:xdist -o addopts= -> 32 passed (criterion TB6 idempotent per run, plus P3 P4 P8 P9) t=17
Pre-check: 50676d85fae1198f2cabbe3d2ac68ae265ab0b87 uv --directory D:/autoTesting/.worktrees/t199b-bug-loop-run run pytest tests/test_bug_run.py tests/test_bug_run_idempotent.py tests/test_bug_store_hardening.py tests/test_sheet_plan.py -k "tb9" -p no:xdist -o addopts= -> 8 passed (criterion TB9 confirm before write, zero writes, live refused) t=7
Pre-check: 50676d85fae1198f2cabbe3d2ac68ae265ab0b87 uv --directory D:/autoTesting/.worktrees/t199b-bug-loop-run run pytest tests/test_bug_run.py tests/test_bug_run_idempotent.py tests/test_bug_store_hardening.py tests/test_sheet_plan.py -k "tb10" -p no:xdist -o addopts= -> 4 passed (criterion TB10 own rows only) t=7
Pre-check: 50676d85fae1198f2cabbe3d2ac68ae265ab0b87 uv --directory D:/autoTesting/.worktrees/t199b-bug-loop-run run pytest tests/test_bug_run.py tests/test_bug_run_idempotent.py tests/test_bug_store_hardening.py tests/test_sheet_plan.py -k "tb11" -p no:xdist -o addopts= -> 2 passed (criterion TB11 idempotent and convergent) t=8
Pre-check: 50676d85fae1198f2cabbe3d2ac68ae265ab0b87 uv --directory D:/autoTesting/.worktrees/t199b-bug-loop-run run pytest tests/test_bug_run.py tests/test_bug_run_idempotent.py tests/test_bug_store_hardening.py tests/test_sheet_plan.py -k "tb13 or formula" -p no:xdist -o addopts= -> 2 passed (criterion TB13 clean values) t=17

## Evidence (run in the worktree with uv --directory; no full suite)
- Affected files together: `tests/test_bug_run.py tests/test_bug_run_idempotent.py tests/test_sheet_plan.py tests/test_bug_store_hardening.py tests/test_bug_store.py tests/test_bug_loop.py tests/test_bug_store_concurrency.py tests/test_issues.py tests/test_pinned_regression.py tests/test_schema.py tests/test_doctor.py` -> `298 passed, 1 skipped in 66.49s`.
- `uv --directory <wt> run ruff check src tests scripts` -> `All checks passed!`; `uv --directory <wt> run autotester doctor` -> `doctor: clean`; `autotester map` run (docs/MAP.md current, `git status` clean after).
- No `.env` value was read or printed; no network, no `gws`, no Google call; the only sheet is the in-memory fake in `tests/sheet_fake.py`.

## Falsifications (git archive of the head into a throwaway copy on C:, one edit, run the named tests green then edited then restored; red@ is the edited file's sha1 prefix, green@ the head; the copy imports its own `autotester`)
Falsify[TB3]: tests/test_bug_run.py -k tb3 red@4911ef27da3e green@50676d85 — kind taken from the failures list instead of the `kind_of_verdict` door: 5 failed, 3 passed; green 8 passed, restored 8 passed.
Falsify[TB4-deleted]: tests/test_bug_run.py::test_tb4_a_case_deleted_after_a_fail_makes_the_bug_stale_at_the_next_run red@c2804d8d1bc4 green@50676d85 — a deleted case is no longer a change: 1 failed; green 1 passed.
Falsify[TB4-criterion]: tests/test_bug_run.py::test_tb4_an_edited_criterion_makes_the_bug_stale_never_fixed red@4e296e0b1e8d green@50676d85 — fingerprint comparison disabled: 1 failed; green 1 passed.
Falsify[TB4-order]: tests/test_bug_run.py::test_tb4_a_change_and_a_pass_at_one_instant_go_stale_not_fixed red@d237c5a40aab green@50676d85 — `case_changed` ranked after PASS in `order_key`: 1 failed; green 1 passed.
Falsify[TB6]: tests/test_bug_run_idempotent.py::test_tb6_processing_the_same_run_twice_changes_nothing_byte_for_byte red@c67aeb12bcc3 green@50676d85 — event time taken from the clock instead of the run: 1 failed; green 1 passed.
Falsify[TB6-unresolved]: tests/test_bug_run.py::test_a_fail_on_a_case_or_criterion_that_is_gone_opens_no_bug_and_is_reported_each_time red@dd9556ea6555 green@50676d85 — a FAIL naming a missing criterion opens a bug anyway: 1 failed; green 1 passed.
Falsify[P3]: tests/test_bug_store_hardening.py tests/test_bug_run_idempotent.py -k p3 red@e23793fd2057 green@50676d85 — the batch reads the log twice and ignores a caller's snapshot: 3 failed; green 3 passed.
Falsify[P4]: tests/test_bug_store_hardening.py tests/test_bug_run_idempotent.py -k p4 red@33e6d3aabec3 green@50676d85 — a corrupt file is no longer caught: 6 failed, 2 passed; green 8 passed.
Falsify[P8-time]: tests/test_bug_store_hardening.py -k "p8_a_future or p8_the_bounds or p8_a_refused" red@17edb95f387d green@50676d85 — the time bounds disabled: 3 failed; green 3 passed.
Falsify[P8-fold]: tests/test_bug_store_hardening.py -k "p8_one_fact or p8_the_fold" red@c84457608f2b green@50676d85 — the time left out of the file name (one copy overwrites the other): 4 failed, 3 passed; green 7 passed.
Falsify[P9-control]: tests/test_bug_store_hardening.py -k p9_a_bug_key red@2da19b6e5d13 green@50676d85 — the control-character check removed: 3 failed, 2 passed; green 5 passed.
Falsify[P9-length]: tests/test_bug_store_hardening.py -k p9_a_bug_key red@244a7cd3cc3b green@50676d85 — the length limit removed from both models: 1 failed, 4 passed; green 5 passed.
Falsify[TB9-hash]: tests/test_sheet_plan.py -k tb9 red@b6cc72524176 green@50676d85 — the plan hash comparison skipped: 2 failed, 6 passed; green 8 passed.
Falsify[TB9-live]: tests/test_sheet_plan.py::test_tb9_a_live_client_is_refused_even_with_a_correct_confirmation red@b7d27c1779b5 green@50676d85 — the live-client refusal removed: 1 failed; green 1 passed.
Falsify[TB9-confirmation]: tests/test_sheet_plan.py -k tb9 red@b414c3521634 green@50676d85 — the missing-confirmation refusal removed: 1 failed, 7 passed; green 8 passed.
Falsify[TB10]: tests/test_sheet_plan.py -k tb10 red@8de29cbf9a65 green@50676d85 — write unconditionally over a human edit: 2 failed, 2 passed; green 4 passed.
Falsify[TB11-empty]: tests/test_sheet_plan.py::test_tb11_syncing_twice_makes_no_duplicate_rows_and_the_second_plan_is_empty red@f9a900a30b31 green@50676d85 — a cell that already matches is planned again: 1 failed, 1 passed; green 2 passed.
Falsify[TB11-append]: tests/test_sheet_plan.py -k tb11 red@414bf5ce5f75 green@50676d85 — every bug appended as a new row: 2 failed; green 2 passed.
Falsify[TB13-scrub]: tests/test_sheet_plan.py::test_tb13_a_planted_secret_is_in_neither_the_plan_nor_its_rendering_nor_the_sheet red@9b3b81f94fa7 green@50676d85 — values not passed through `scrub`: 1 failed; green 1 passed.
Falsify[TB13-formula]: tests/test_sheet_plan.py::test_a_value_that_would_run_as_a_formula_is_written_as_plain_text red@ebf2067dd761 green@50676d85 — the formula guard removed: 1 failed; green 1 passed.
mutant-cap-raise: twenty mutations at Tier L (cap 10): seven criteria served plus the four folded findings (P3, P4, P8, P9), each with two independent mechanisms in several (TB4 has three, P8 two, P9 two, TB9 three, TB11 two, TB13 two). The P1 and P2 pins are not mutated: they pin a choice the owner has not made, so a mutant would only show the choice flipping. Runner kept outside the repo.

Metrics: start=unavailable end=unavailable wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=20 cycle=0 resumes=1 tokens=unavailable policy=proportional-verification/2026-10-10.9

**Status:** checked-PASS
**Merged:** c015593cea5d19fec8e7140d70d2f76466b91d75
