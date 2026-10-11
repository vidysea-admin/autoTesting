# Verdict: t199a-bug-loop-core (T-199 part a, TB1..TB6 built subset)
Cycle checked: 0 · Checked sha: 325d9903 (code 1976502d, merge base 6504de03, branch wave/t199a-bug-loop-core) · Policy-Version: proportional-verification/2026-10-10.9 · Dual check: no
Lane: normal. Resume: 1 (session interrupted once, then resumed from the C: copy) · Retry: 0

## Plan
Manifest says Tier M. Raised to **L**, citing a concurrency/race trigger: `store/bug_store.py:36-42` (`_read` retries `PermissionError` 20 times against a writer) and `bug_store.py:98-106` (two processes write the same `bev_*.json`; first one wins by `target.exists()` then `os.replace`). Checks: pre-check counts, TB2 table cell by cell against an oracle written by the checker, fold attack (5040 permutations, 800 shuffles, ties, future, duplicates), storage attack (threads, processes, hostile files, path escape), ten gaps, nine mutants. Work only in a `git archive 325d9903` copy on C: (`scratchpad/ck199a`); `autotester.__file__` and pytest rootdir printed inside it. `df -h /d` = 20 GB free. No full suite, no suite lock.

VERDICT: PASS
SCOREBOARD: TB1 met, TB2 met (stored-N clause held), TB3 met in part (mapping built, reading a run directory held), TB4 met in part (stale and closing lists built, detection of a changed or deleted case held), TB5 met, TB6 met in part (idempotent apply built, `process_run` held); TB7 held (correctly not claimed). No failed criterion.
**This PASS covers only the built subset. It cannot close T-199**: TB3/TB4/TB6 held clauses, TB7 and HG-TB1 stay open.
TIER: L (raised from M, triggers above)
FAILURES: none (P1..P10 below are non-blocking PROPOSED-ISSUEs)
CAPABILITY-COVERAGE: 6/6 changed criteria reproduced, one named falsification each (table below)
LIVE-BROWSER: not-applicable (changed paths: stages/bug_loop.py, store/bug_store.py, schema/tracked_bug.py, stages/issues.py, tests; no UI, route or template)
ISSUES-WRITTEN: none (PROPOSED-ISSUE lines only; the maker or sweep mints them)
EXECUTOR: claude-sonnet-subagent (checker coordinator; sub-checkers: storage probes, falsification runs)

## Rulings
- **Dual check: not required.** No security/auth/tenancy/prod-write trigger with a file:line in the diff: no route, no session, no production data; writes are confined to one project directory through `filestore.write_json`, and a hostile `event_id` is refused (`s5.out`). The actor string is unauthenticated (G9), but nothing here reads a session.
- **`mutant-cap-raise` line: unnecessary.** Floor is 6 (one per changed criterion); the builder's 7 are floor plus 1, inside the cap of 3 at M and 10 at L. My own count is 9 distinct mutants (6 floor + TB2a, TB2b, TB6-order) plus the marker-equivalent and one stacked variant, inside the L cap.
- **Manifest honesty.** TB3, TB4, TB6 are honestly "in part" and say what is held. TB2 is called "full" while its stored-config clause (N kept with the project, G8) is held: wording only (P7).
- **Brief caveat.** The brief that names each new module's job was written by the builder on the branch; the contract does not name the modules.

## Per-criterion results
| Crit | Result | Evidence |
|---|---|---|
| TB1 key is (project, case, criterion) | met | `-k tb1` 7 passed; mutant drops `criterion_id` from the key, 1 red |
| TB2 transition table and N | met | 45 cells vs independent oracle, all equal (`probe_fold.out`, BAD 0); `-k tb2` 54 passed; N=1,3,5 close exactly at N; 5040-permutation and 800-shuffle fold invariance; equal timestamps (FAIL first) stable |
| TB3 verdict to event kind | met in part | `kind_of_verdict` is the single door; unevidenced PASS (total 0, 2/3 met, images owed) never closes; `-k tb3` 10 passed. Held: reading verdicts off a run dir |
| TB4 stale and closing lists | met in part | `case_changed` makes open/reopened stale, never `fixed`; closed_by_runs/verdicts listed and cleared on reopen; `-k tb4` 3 passed. Held: detecting the change |
| TB5 issue to bug by fingerprint | met | `issue_to_bug_event` ref `issue/<id>`, replay is `duplicate`; `-k tb5` 3 passed |
| TB6 idempotent, replay-safe | met in part | double apply writes nothing; crash after bug 1 of 2 converges; 16 threads and 6-8 processes: 640 files, no loss, no tear, no exception. Held: `process_run` |

## Falsifications (one per criterion, each green before and red after, in its own copy)
| Row | Edit (file:line) | Red |
|---|---|---|
| TB1 | `tracked_bug.py:61` drop `criterion_id` from the key | `assert 1 == 2` in test_tb1_two_failing_criteria_on_one_case_are_two_bugs |
| TB2 | `bug_loop.py:75` make `inconclusive` a PASS_STEP in the live row | 2 red `[open-inconclusive]`, `[reopened-inconclusive]` |
| TB2 (N) | `bug_loop.py:125` `len(refs) < n` to `< 1` | 14 red across loop and store files (the table test does not catch it; the default-N test does) |
| TB3 | `bug_loop.py:110` always return `K.PASS` | 3 red `[pass_unevidenced]` |
| TB4 | `bug_loop.py:150` MARK_STALE yields `FIXED` | 1 red `FIXED is STALE` |
| TB5 | `issues.py:123` ref gets a uuid | 1 red `APPLIED is DUPLICATE` |
| TB6 | `bug_store.py:80` `known = set()` | 1 red `APPLIED is DUPLICATE` |
| TB6 order | `bug_loop.py:209` `list(events)` for sorted | 1 red, fold differs |
| TB6 marker-equivalent | `bug_store.py` uuid in filename, `known=set()`, early return removed | 5 red (3 tb6, 2 concurrency; `assert 180 == 5+6*25`) |
No mutant survived. Pre-check: tb1 7, tb2 54, tb3 10, tb4 3, tb5 3, tb6/concurrent 8, three files 123 passed (51 s). `ruff check src tests scripts` clean, `autotester doctor` clean.

## Gap rulings G1..G10
- G1 `(fixed, pass)` unchanged: MET.
- G2 `(stale, fail)` refused `stale_bug`: **UNMET in intent, needs a contract line** `(stale, FAIL) -> open`. Probed: a new FAIL on a stale key is never tracked (`probe_gaps.out`), so a real regression on a changed case is silent until the key is replaced. P1.
- G3 `(fixed, case_changed)` refused `closed_record`: MET.
- G4 streak per bug: MET; needs a contract sentence (consecutive per bug, not per case).
- G5 marker equivalence: MET. The equivalent sabotage was run (above): red on file-level tests. Note the fold layer (`judge` DUPLICATE) independently hides doubling; with that guard also removed the count triples, and 5 more tests go red. No test asserts `bug.count` unchanged when only the store layer is broken (P9).
- G6 `reopened` as `open`, `assign` legal everywhere, PASS-evidence rule: MET. A FAIL verdict with no cited failure maps to `inconclusive`, so it does not break a streak (F,P,uncited-FAIL,P closes): needs a contract line. P2.
- G7 no note concept: MET (nothing required).
- G8 replay order and stored N: order MET (an old PASS cannot close a later FAIL). Stored N not built: a changed N moves an already reported `fixed`. P6, needs a contract line.
- G9 unauthenticated actor: MET as scoped. Probed: any caller can pass `system:bug-loop`. T-204's route must derive the actor from the session; needs a contract line (carry to TB7 / HG-TB1).
- G10 re-judged verdict under the same ref with a different kind is two events: MET; replay (D-072) must reuse the original kind, needs a contract line.

## "Not fixed" notes
- No fsync (`filestore.py:22-31`): PROPOSED-ISSUE P5, not blocking (os.replace prevents torn reads; power loss could leave an empty file, see P4).
- O(n^2) in `apply()`: PROPOSED-ISSUE P3, not blocking now (no caller yet). Measured: 800 ms per apply at 1000 files, 70 s cumulative for 400 applies. Becomes blocking before T-199b wires a run directory.

## D-082 new-module table
bug_loop.py (221 lines, one job: judge/trace/fold), bug_store.py (116, one job: event files), tracked_bug.py (174, shapes), bug_loop_fixture.py (60, test fixture). All under 300 lines, functions under 50, docstring states one job, doctor clean. Diff scope equals the manifest list; nothing removed or weakened. Stale docstring in `bug_store.py` (P10).

## PROPOSED-ISSUEs
- P1 {"severity":"medium","feature":"team-bug-loop","title":"A stale bug key blocks tracking of a new FAIL on that (case, criterion); add contract line (stale, FAIL) -> open (G2)","evidence":"fold/probe_gaps.out: stale then FAIL -> stale count 1; bug_loop.py table row stale"}
- P2 {"severity":"medium","feature":"team-bug-loop","title":"A graded FAIL verdict with no cited failure maps to inconclusive and does not break a pass streak; contract line needed (G6)","evidence":"fold/probe_gaps.out: F,P,uncited,P -> fixed; bug_loop.py kind_of_verdict"}
- P3 {"severity":"low","feature":"team-bug-loop","title":"BugStore.apply re-reads and re-folds every event file; 800 ms per apply at 1000 files, 70 s cumulative for 400. Fix before T-199b feeds it a run directory","evidence":"storage/s7.out; bug_store.py apply/_report"}
- P4 {"severity":"medium","feature":"team-bug-loop","title":"One corrupt or zero-length event file makes events()/bugs()/history()/apply() raise for the whole store, and apply() stores the new event then raises","evidence":"storage/s4.out, s6.out (e4 file written despite raise); bug_store.py _read"}
- P5 {"severity":"low","feature":"team-bug-loop","title":"_atomic_write has no fsync; a crash can leave a zero-length event file (feeds P4)","evidence":"filestore.py:22-31"}
- P6 {"severity":"low","feature":"team-bug-loop","title":"close_passes N is a store argument, not stored with the project; changing N re-folds history and can move a reported fixed (G8)","evidence":"fold/probe_gaps.out: N=2 fixed, N=3 open"}
- P7 {"severity":"low","feature":"team-bug-loop","title":"Manifest says TB2 full while the stored-config clause is held; use in-part wording","evidence":"qa/manifests/t199a-bug-loop-core.md"}
- P8 {"severity":"medium","feature":"team-bug-loop","title":"No clock validation on event.at: a future-dated FAIL reopens a closed bug (year 2096 probe) and future PASSes can close one; also the same (bug_key, ref, kind) with different at raced by two processes folds non-deterministically (reachable via issues.py:123-124). Use a deterministic at or bound it","evidence":"fold/probe_future.out; storage/s2.out diff-at outcomes split 11/9; bug_store.py:98-106"}
- P9 {"severity":"low","feature":"team-bug-loop","title":"No test asserts bug.count unchanged after replay when only the store layer is broken; add one, and a length/control-character check on bug_key","evidence":"falsify/transcript2.txt marker-equivalent notes"}
- P10 {"severity":"low","feature":"team-bug-loop","title":"bug_store.py docstring still says event id is (bug_key, ref); it also holds kind","evidence":"store/bug_store.py module docstring vs tracked_bug.py event_id derivation"}
- P11 {"severity":"low","type":"process","title":"Check passed the 10-minute hard checkpoint (about 56 min wall incl. one interruption); mutant copies of a 2,000+ file archive and 62 s three-file runs dominate","evidence":"Metrics slow: line"}

Metrics: start=2026-10-11T18:43 end=2026-10-11T19:42 wall_min=59 agent_min=unavailable blocked_min=unavailable suite_runs=0 repeat_runs=1 mutations=10 cycle=0 resumes=1 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=3540 mutants=10 defects_unit=0 defects_6c=0 slow: session interrupted once (not measured); mutant copies and the 62 s three-file run per TB2 mutant dominate. Evidence: qa/evidence/t199a-bug-loop-core/
