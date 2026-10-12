# Manifest — t199a-bug-loop-core (T-199 bug loop, pure core: lifecycle table + event store)

**Contract:** qa/contracts/team-bug-loop.md TB1, TB2, TB3 (part), TB4 (part), TB5, TB6 (part); TB7 held
**Brief:** qa/briefs/t199a-bug-loop-core.md (never edits qa/contracts)
**Fix cycle:** 0 of max 2
**Dual check:** no (no auth/tenancy/prod-write trigger: the actor is an opaque validated string, no route or CLI exists in this slice, and the store writes only under a directory the caller passes)
**Persona walk:** skip (no UI route or screen)
**Executor:** claude-sonnet-subagent
**Branch:** wave/t199a-bug-loop-core
**Head:** 1976502dd4d80f89c5ec1824a4ff4b3a1fa8d0e4

## Criteria served (quoted from the brief's coverage table; contract text is in qa/contracts/team-bug-loop.md)

- TB1 stable key — **full**: `case_bug_key(project, case_id, criterion_id)`; a video bug's key is `Issue.id`; a seed whose key is not derived from its own parts is refused by the schema.
- TB2 lifecycle table — **full** over every (state, event) cell: 5 states x 9 event kinds, tested over the whole cross product against a hand-written expectation. N = the store's `close_passes`, default 2.
- TB3 verdicts only — **part**: `kind_of_verdict(Verdict | None)` is the only reader of a grade; no `RawResult` import (AST test); an unevidenced PASS and a verdict-less result change nothing.
- TB4 honest close — **part**: `closed_by_runs` / `closed_by_verdicts` kept; `case_changed` makes an open bug `stale`, never `fixed`.
- TB5 adapter in `stages/issues.py` — **full**: `issue_to_bug_event`, +16 lines, file 258 lines (cap 300), the only place a key is derived from an `Issue`.
- TB6 idempotent — **part**: an event applied twice, a batch replayed after a crash, 6 racing threads, 6 racing processes, 8 processes on the same events: same files, no event lost, nothing raised.

**Held (after t205/t204 merge):** TB7 tracker page (route, template, `report.view` / `project.edit` enforcement); the `assign` event itself is built. Also held: any route, CLI command, sheet client, `Project.bug_close_passes` (`schema/project.py` is a forbidden file), `core/paths.py` helper, `process_run` over a run directory (reading verdicts off disk), detecting a deleted case or changed criterion (needs `ProjectStore`), the pinned-case test (TB4 part), and the contract's "processed-run marker" (replaced by per-event ids, see gap G5).

## Transition table (one dict in `stages/bug_loop.py::TABLE`; u = unchanged, no write)

| state \ event | fail | pass | pass_unevidenced, inconclusive, blocked, not_run, no_verdict | case_changed | assign |
|---|---|---|---|---|---|
| none | OPEN | refuse `no_bug` | u | refuse `no_bug` | refuse `no_bug` |
| open | REFAIL (count+1, last_seen, streak reset) | PASS_STEP (streak+1; at N -> `fixed`) | u | MARK_STALE | ASSIGN |
| reopened | REFAIL | PASS_STEP | u | MARK_STALE | ASSIGN |
| fixed | REOPEN (`reopened`, count+1) | u | u | refuse `closed_record` | ASSIGN |
| stale | refuse `stale_bug` | refuse `stale_bug` | u | refuse `already_stale` | ASSIGN |

Who may move it: every status move is made by **bug-loop (machine)** under the reserved actor `system:bug-loop`; a user actor on a status event is refused `actor_not_allowed`. `assign` is made by a **project editor** (a named user; the `project.edit` check is T-204's); the machine actor is refused there.

## New modules (D-082 item 1; each named in the brief, one-job docstring, `autotester doctor` clean)

- `src/autotester/schema/tracked_bug.py` (174 lines) — tracked bug, its events and the stable key.
- `src/autotester/stages/bug_loop.py` (221) — the lifecycle table and its fold (pure, no I/O).
- `src/autotester/store/bug_store.py` (116) — one-file-per-event bug log under a caller-given directory (writes with `store/filestore.py::write_json`; no second helper).
- Edit in place: `src/autotester/stages/issues.py` (+16, 258 total). Tests: `tests/test_bug_loop.py` (289), `tests/test_bug_store.py` (263), `tests/test_bug_store_concurrency.py` (73), `tests/bug_loop_fixture.py` (60). `docs/MAP.md` regenerated.

## Contract gaps (conservative reading taken; checker to rule)

- G1 `(fixed, pass)` undefined: read as unchanged, not a second close.
- G2 `(stale, fail|pass)` undefined: refused, so a real regression on a stale key is reported as a refusal and is not reopened or restarted. Flipping it is one table entry. This is the main ruling needed.
- G3 `(fixed, case_changed)`: refused; the closed record stays honest.
- G4 streak is per bug (a FAIL on C1 does not break C2's streak). Per-case needs a contract sentence.
- G5 TB6 names a "processed-run marker"; per-event ids (`content_id(bug_key, ref, kind)`) give the same result without dropping a late verdict. The contract's sabotage "drop the marker, the count doubles" has no literal equivalent: the file-exists check is the marker.
- G6 `reopened` behaves as `open`; `assign` is legal in every state; a FAIL verdict with no cited failure maps to `inconclusive`; "PASS cites evidence" = every criterion met and no screenshot owed.
- G7 no note concept in the contract; none built.
- G8 replay order is `(at, FAIL-first, event_id)`; a PASS older than the latest FAIL cannot close the bug. `close_passes` is a store argument, not in the log, so a changed N re-folds history and can move an already-reported `fixed`.
- G9 the actor is an unauthenticated string here: T-204's route must set it from the session, never from a request.
- G10 a verdict re-judged under the same ref with a different kind is two events (both counted); replay (D-072) must reuse the original kind.
- Fresh-context review (senior-software-engineer) found one Block (concurrent appends lose and tear lines across Windows processes) and, on the redesign, two medium and two low items (a different kind on the same ref could shadow an event; a transient `PermissionError` for a reader racing a writer; actor-refusal reported against the wrong twin; equal-timestamp ties). All fixed and tested; not fixed, flagged: `filestore._atomic_write` has no fsync (a power cut could leave a zero-length event file that makes `bugs()` raise by design), and `apply()` re-reads every event file per call (O(n^2) in a loop).

## Verification scope
Policy-Version: proportional-verification/2026-10-10.9
Tier: M — new modules with a store written from several processes; the shared `write_json` helper is used, not changed.

Pre-check: 1976502dd4d80f89c5ec1824a4ff4b3a1fa8d0e4 uv --directory D:/autoTesting/.worktrees/t199a-bug-loop-core run pytest tests/test_bug_loop.py tests/test_bug_store.py tests/test_bug_store_concurrency.py -k tb1 -p no:xdist -o addopts= -> 7 passed (criterion TB1 stable key) t=3
Pre-check: 1976502dd4d80f89c5ec1824a4ff4b3a1fa8d0e4 uv --directory D:/autoTesting/.worktrees/t199a-bug-loop-core run pytest tests/test_bug_loop.py tests/test_bug_store.py tests/test_bug_store_concurrency.py -k tb2 -p no:xdist -o addopts= -> 54 passed (criterion TB2 lifecycle table, 45 cells) t=5
Pre-check: 1976502dd4d80f89c5ec1824a4ff4b3a1fa8d0e4 uv --directory D:/autoTesting/.worktrees/t199a-bug-loop-core run pytest tests/test_bug_loop.py tests/test_bug_store.py tests/test_bug_store_concurrency.py -k tb3 -p no:xdist -o addopts= -> 10 passed (criterion TB3 verdicts only) t=3
Pre-check: 1976502dd4d80f89c5ec1824a4ff4b3a1fa8d0e4 uv --directory D:/autoTesting/.worktrees/t199a-bug-loop-core run pytest tests/test_bug_loop.py tests/test_bug_store.py tests/test_bug_store_concurrency.py -k tb4 -p no:xdist -o addopts= -> 3 passed (criterion TB4 honest close) t=3
Pre-check: 1976502dd4d80f89c5ec1824a4ff4b3a1fa8d0e4 uv --directory D:/autoTesting/.worktrees/t199a-bug-loop-core run pytest tests/test_bug_loop.py tests/test_bug_store.py tests/test_bug_store_concurrency.py -k tb5 -p no:xdist -o addopts= -> 3 passed (criterion TB5 issue adapter) t=3
Pre-check: 1976502dd4d80f89c5ec1824a4ff4b3a1fa8d0e4 uv --directory D:/autoTesting/.worktrees/t199a-bug-loop-core run pytest tests/test_bug_loop.py tests/test_bug_store.py tests/test_bug_store_concurrency.py -k "tb6 or concurrent or racing" -p no:xdist -o addopts= -> 8 passed (criterion TB6 idempotent, including 6 racing threads and processes) t=34

## Evidence (run in the worktree with uv --directory; no full suite)
- Affected files together: `tests/test_bug_loop.py tests/test_bug_store.py tests/test_bug_store_concurrency.py tests/test_issues.py tests/test_pinned_regression.py tests/test_ui_issues.py tests/test_cli_issues.py tests/test_schema.py tests/test_doctor.py` -> `250 passed, 1 skipped, 1 warning in 55.35s`.
- `uv --directory <wt> run ruff check src tests scripts` -> `All checks passed!`; `uv --directory <wt> run autotester doctor` -> `doctor: clean`; `autotester map` run (docs/MAP.md current).

## Falsifications (git archive of src+tests+scripts at the head into a throwaway copy on C:, one edit, run the named test, copy deleted; red@ is the mutated file's blob sha, green@ the head)
Falsify[TB1]: tests/test_bug_store.py::test_tb1_two_failing_criteria_on_one_case_are_two_bugs red@0d559a5eed33 green@1976502d — dropping `criterion_id` from the key: 1 failed, green copy 1 passed.
Falsify[TB2]: tests/test_bug_loop.py -k tb2_every_cell red@d274cee2ad3a green@1976502d — making `inconclusive` act as a pass in the table: 4 failed, 41 passed; green 45 passed.
Falsify[TB3]: tests/test_bug_loop.py -k tb3_a_verdict_maps red@8dadfc000830 green@1976502d — an unevidenced PASS counted as PASS: 3 failed, 6 passed; green 9 passed.
Falsify[TB4]: tests/test_bug_loop.py -k tb4_a_changed_case red@76d2e42b894f green@1976502d — `case_changed` moves an open bug to `fixed` instead of `stale`: 1 failed; green 1 passed.
Falsify[TB5]: tests/test_bug_store.py -k tb5_a_video_found_issue red@38183be2b8ac green@1976502d — a time in the adapter's ref makes the same issue a new event: 1 failed; green 1 passed.
Falsify[TB6]: tests/test_bug_store.py -k tb6_applying_an_event_twice red@0d86c3b0f5bc green@1976502d — the store stops reporting a known event as a duplicate: 1 failed; green 1 passed.
Falsify[TB6-order]: tests/test_bug_store.py -k function_of_the_event_set red@0654851df76b green@1976502d — replay in input order instead of time order: 1 failed; green 1 passed. (An earlier version of this mutant targeted a test that survived it, so the target was changed to the 720-permutation test.)
mutant-cap-raise: seven mutations at Tier M (one per served criterion plus an ordering mutant for TB6, whose convergence claim has two independent mechanisms: the id and the replay order).

Metrics: start=2026-10-11T07:56:58Z end=2026-10-11T12:00:00Z wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=7 cycle=0 resumes=1 tokens=unavailable policy=proportional-verification/2026-10-10.9

**Status:** checked-PASS

PASS covers the built subset only; T-199 stays open (TB7, HG-TB1, and the held clauses of TB2/TB3/TB4/TB6)
