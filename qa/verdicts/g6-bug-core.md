# Verdict — g6-bug-core (G6 bug-loop pure core, TB1-TB6)

Date: 2026-10-07. Checker: claude-sonnet-subagent (single checker, Tier M). Bound to d:/autoTesting, worktree `.worktrees/g6-bug-core`, branch wave/g6-bug-core.
HEAD 7e23fa9a, base c09debd1. Contract: `qa/contracts/team-bug-loop.md` as on origin/master (identical to the base's copy: `git diff c09debd1 origin/master -- qa/contracts/team-bug-loop.md qa/contracts/core-invariants.md` is empty), TB1-TB6 only; TB7 and wiring are owed and not judged.
Policy-Version: proportional-verification/2026-10-06.6 (manifest pin); the .7 rules apply to this unit at dispatch (no per-unit full suite).
Cycle checked: 0

## Check plan (step 0)

Diff = 10 files, 837 added, 0 removed (`git diff --diff-filter=DR` empty). Signals: logic changed -> affected tests + falsification floor; schema read added (`Project.bug_close_passes`) -> M. No UI surface, no external portal, no data artifact, no prompt/LLM, no security/auth/prod-write, no performance line. Persona walks: not applicable (pure core, no UI; TB7 owed). One check type, so no sub-checker fan-out. SERIAL: nothing shared except the scratchpad.

## Verdict

VERDICT: CONTINUE-NEEDED
remaining: full suite (combined G-core head) — to be run once by the maker on the integration head of G2, G3, G5 and G6 (policy .7 / maker step 6c), not here. All TB1-TB6 evidence is complete and PASS-grade; no defect found. On a green combined suite the unit closes; nothing else here needs re-running unless TB files change.
SCOREBOARD: 6/6 criteria evidenced (TB1-TB6), 5/5 touched invariants hold (C1, C2, C3, C5, C6)
TIER: M (multi-file behaviour: new shared schema + stage module + one-field schema read on `Project`, `src/autotester/schema/project.py:146`; no L trigger in the changed non-test files)
FAILURES: none
CAPABILITY-COVERAGE: 14/14 falsification rows reproduced, all green-before / red-after in isolated copies
LIVE-BROWSER: not-applicable (changed paths: src/autotester/{schema,stages,core}/, tests/, docs/MAP.md, qa/manifests; no UI surface)
ISSUES-WRITTEN: none (see PROPOSED-ISSUE lines; sibling-branch ledgers collide on ISS ids, so the maker mints ids at merge)
EXECUTOR: claude-sonnet-subagent (G6 builder) (checker: claude-sonnet-subagent)
EXPLANATION: The pure core meets TB1-TB6 on evidence I produced myself: every named test is green in a git-archive copy, and every criterion has at least one falsifying edit that turns exactly the named test red. Ruff and doctor are clean. The verdict is CONTINUE-NEEDED only because the one combined full suite is owed to the maker's integration head, per the dispatch. The maker's assumptions are all ruled below and none is a FAIL.
Metrics: start=2026-10-07T15:21:00Z end=2026-10-07T15:38:00Z wall_min=17 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=14 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.6
slow: mutant copies ~9 min (14 serial copies of the whole tree in one runner; a shared scratch dir name `base` was overwritten by a sibling checker mid-run and one row had to be re-run in a unique dir)

## Per-criterion result

| id | result | evidence I produced |
|---|---|---|
| TB1 key stable | MET | `test_tb1_*` 4 green in copy. Mutants: wall-clock `time_ns` hashed into the key -> `test_tb1_three_nightly_runs...` RED; criterion dropped from key -> `test_tb1_two_failing_criteria...` RED. Key is `content_id("bug", {project, case_id, criterion_id})` (`schema/tracked_bug.py:39`); the case id is itself a content hash, so a secret in case text cannot reach it (`test_tb1_a_secret_planted...` green, `hunter2` absent). |
| TB2 lifecycle table | MET | `TRANSITIONS` is total over (None + 4 states) x 3 signals (`test_tb2_the_table_is_total...`), 14 parametrised cells green. Mutants: INCONCLUSIVE counted as a pass -> `...neither_closes_nor_opens[INCONCLUSIVE]` RED; N=1 -> 2 tests RED; (fixed, FAIL) made NOOP -> `...reopened` RED; FAIL no longer resets the streak -> `...resets_the_streak` RED. My own probe (not in the maker's suite): a FAIL at +5 min sets `last_seen` 00:05 while `first_seen` stays 00:00 and count 2; after two PASSes a FAIL gives `reopened`, count 3, `first_seen` kept, `last_seen` 00:20. |
| TB3 verdicts only | MET | `test_tb3_*` 4 green. Mutants: RawResult `assertion_failed` read as FAIL -> `...raw_result_changes_nothing` RED; PASS with `met` below total or unseen screenshots counted -> `...cites_no_evidence...` RED. `process_run` calls `store.load_verdicts` only (it globs `*.verdict.json`); `RawResult` is never imported by `bug_loop.py`. A replayed run (`used_script=True`) with a verdict opens and closes a bug (green). |
| TB4 honest close | MET | `test_tb4_*` 4 green. Mutants: stale sweep disabled -> 2 tests RED (deleted case; rewritten criterion even after 2 PASSes); closing id lists dropped -> RED; close deletes the pinned case row via `delete_jsonl_row` -> RED. The two id lists (`closed_by_runs`, `closed_by_verdicts`) read back as `['r2','r3']` and `['r2/<case>','r3/<case>']`. |
| TB5 adapter in place | MET | `git diff --numstat c09debd1 HEAD -- src/autotester/stages/issues.py` = `16 0` (cap 58); file is 258 lines (cap 300). `autotester doctor`: clean. The only function deriving a key from an `Issue` is `bug_from_issue` (`stages/issues.py:112-125`); `case_bug_key` derives from case ids. Mutant: key = `issue.id + created_at` -> `test_tb5_a_video_found_issue...` RED. |
| TB6 idempotent per run | MET | `test_tb6_*` 5 green (byte-identical store on re-processing; marker deleted still no double count; crash after bug 1 of 2 then retry gives counts [1,1]; N is a stored project value). Mutants: applied-guard removed -> 2 tests RED; marker early-return AND guard removed -> byte-identical test RED. The marker is written last via `write_json` (`os.replace`, no platform calls); the Ubuntu run stays owed to T-203's deploy check per the contract. |

Invariants: C1 (TrackedBug/ProcessedRun in `schema/`, `extra="forbid"` via `Artifact` / explicit config; `tests/test_schema.py` green), C2 (`bug_loop.py` 220, `tracked_bug.py` 82 lines; doctor clean), C3 (doctor clean; no duplicate public name), C5 (no secret field; key is a hash), C6 (`bugs.jsonl` and `bug_runs/<run>.json` are human-editable JSON, atomic writes).

## Rulings on the maker's flagged assumptions

1. "A PASS cites evidence" = `criteria_total > 0`, every criterion met, and `not graded_on_partial_evidence`; no screenshot owed. Ruled: acceptable reading of TB3 (it needs only that the grade rule is not weakened, and `Verdict` has no evidence field). Not a FAIL.
2. Verdict id = `run_id/case_id` (`verdict_ref`). Ruled: acceptable; it is the verdict's file location and stable.
3. `(stale, FAIL) -> open` with count reset. Ruled: acceptable; the contract is silent and a new failure of a changed check is a new bug. Test cell `(STALE, FAIL, OPEN, 1, 0)` pins it.
4. `(reopened, FAIL) -> reopened` (count +1). Ruled: acceptable and consistent with `(open, FAIL)`.
5. Fixed bugs are never swept to stale. Ruled: correct reading of TB4 (the "deleted case or changed criterion -> stale" rule governs a bug not yet closed; a closed record stays honest). Not a FAIL.
6. `BugStatus` in `schema/tracked_bug.py` (enums.py at the 300-line cap). Ruled: acceptable; one definition, doctor clean.
7. Persistence module-level in `bug_loop.py` (`project_store.py` at the cap). Ruled: acceptable for this slice.
8. A FAIL verdict moves only its failed criteria; a PASS moves every open/reopened bug of the case. Ruled: acceptable per-bug reading (see PROPOSED-ISSUE P2, low).

## Probes of my own (non-blocking findings)

- Late verdict after an empty processing is dropped (P1, medium). `process_run` writes the marker even when the run had no verdict yet, so when the judge's verdict for run R lands later and `process_run(R)` is called again, `if marker.exists(): return` (`stages/bug_loop.py:197-199`) skips it, and a real FAIL never opens a bug. Reproduced in a copy: RawResult-only run processed, then `save_verdict` FAIL, then `process_run` again -> 0 bugs. TB3 ("a result with no verdict changes nothing") and TB6 ("processing run R twice yields the same") are both met as written, so this is not a FAIL here; settle it when the call site is wired (call after grading, or write the marker only when every case of the run has a verdict, or drop the early return since the `applied` guard already makes a re-process safe).
- Per-bug streak and a FAIL on another criterion (P2, low). Case with C1 and C2: PASS, then a FAIL verdict that fails only C1, then PASS: C2 reaches `fixed` with a FAIL verdict between its two PASS verdicts (probe printed `C1 open 2 1` and `C2 fixed 1 0`). The contract's "consecutive only if no FAIL falls between" can be read per bug (what this does) or per case. The contract leaves it open, so it is a decision for the contract maintainer, not a FAIL.
- `adopt_issue` compares `b.bug_key == issue.id` (`stages/bug_loop.py:155`) instead of `bug_from_issue(issue).bug_key` (P3, low): not a key derivation, but it couples to the key's definition in a second place.
- `last_seen` / `first_seen` per cell (P4, low, test gap): behaviour is correct (probe above), but `test_tb2_every_cell_of_the_table` asserts only status, count and streak, and uses `at == first_seen == last_seen == T0`, so a mutant that stops updating `last_seen` would survive the maker's suite. The contract's Verify line asks for the pair per cell.
- Stale resolver: a case-failure bug opened while the criterion cannot be resolved stores `criterion_fp == ""` and goes `stale` on the next run (probe: FAIL on a case deleted before `process_run` -> `open` then `stale`). Honest and harmless; no row.

## What I ran

- Copies: `git archive HEAD` of the worktree (including `scripts/`), content identical to the bound tree apart from line endings, under the scratchpad (`g6chk-7e23fa9a`, `g6mut0..13`, `probe`); runner and probes outside the repo. Bound tree untouched (`git status` clean).
- Affected tests (copy, `-m "not harness"`): `tests/test_bug_loop.py test_bug_loop_close.py test_issues.py test_pinned_regression.py test_ui_issues.py test_ui_sources.py test_cli_issues.py test_store.py test_store_crawl.py test_schema.py test_schema_video.py test_doctor.py test_parallel_run.py` -> 218 passed, 1 skipped, 1 failed. The one failure is `tests/test_ui_sources.py::test_uploaded_recordings_are_gitignored`, an artifact of the `git archive` copy having no `.git` (`git check-ignore` exit 128); the same node run in the bound worktree: 1 passed. This equals the maker's 219 passed, 1 skipped.
- `ruff check src tests scripts` -> All checks passed. `autotester doctor` -> clean.
- Falsification: 14 rows, each in its own fresh copy, green before then red after on the named node(s); each fired on the named test.

## Diff scope (4c)

`git diff c09debd1 HEAD --stat`: 10 files, +837, no deletion or rename of any function, class, export, route, test or config key. Files touched match the manifest's "What changed" (plus the manifest itself).

## Full-suite status

No L trigger, so no per-unit full suite. `docs/MAP.md` is regenerated and will conflict with sibling units; regenerate at merge (the maker already notes this). The one combined full suite on the G2+G3+G5+G6 integration head is owed by the maker; I ran no full suite.

## PROPOSED-ISSUE lines (maker mints ids)

PROPOSED-ISSUE: {"title":"bug loop: process_run marker blocks a verdict that lands after the run was first processed","severity":"medium","type":"correctness","where":"src/autotester/stages/bug_loop.py:197-199, 215","detail":"A run processed before its verdicts exist gets a marker; a later process_run(run) returns early and the FAIL never opens a bug. Reproduced with RawResult-only run, then save_verdict FAIL, then process_run -> 0 bugs. Fix when wiring the call site: call only after the run is graded, or write the marker only when every case of the run has a verdict, or drop the early return (the applied guard already makes a re-process a no-op).","contract":"team-bug-loop TB3/TB6 (not violated as written)"}
PROPOSED-ISSUE: {"title":"TB2 consecutive-PASS reading is per bug, not per case (contract question)","severity":"low","type":"contract-question","detail":"C2 can reach fixed with a FAIL verdict on C1 between its two PASS verdicts. Checker/contract maintainer to state per-bug or per-case in TB2 at the next amendment; code follows per-bug today."}
PROPOSED-ISSUE: {"title":"adopt_issue compares b.bug_key to issue.id instead of bug_from_issue(issue).bug_key","severity":"low","type":"drift","where":"src/autotester/stages/bug_loop.py:155"}
PROPOSED-ISSUE: {"title":"test gap: TB2 cell test does not pin first_seen/last_seen","severity":"low","type":"test-gap","where":"tests/test_bug_loop.py CELLS / test_tb2_every_cell_of_the_table","detail":"at == first_seen == last_seen == T0 so a mutant that never updates last_seen survives. Behaviour verified correct by checker probe; add distinct timestamps."}
PROPOSED-ISSUE: {"title":"process: mutant batch ran ~9 min serially for 14 rows; shared scratchpad dir name collided with a sibling checker","severity":"low","type":"process","detail":"Use a unique scratch dir per unit and run the independent copies in parallel."}
