# Brief — t199a-bug-loop-core: the pure core of T-199's in-product bug loop (state machine + append-only store)

Policy-Version: proportional-verification/2026-10-10.9 · Tier: M · Base: master `6504de03` · Branch `wave/t199a-bug-loop-core`.
Contract: `qa/contracts/team-bug-loop.md` TB1-TB7 (never edited here). Re-lands the pure half of `wave/g6-bug-core` (D-080 item 1: that branch is
56 commits behind and conflicts, so it is an input, not a base); its two open probes (marker drops a late verdict; per-bug vs per-case streak) are
answered by design below. Reads `qa/briefs/t199-bug-loop-dry-run.md` only to keep the shape compatible: `TrackedBug` carries no sync field; G8 keeps
its sync state in its own model keyed by `bug_key`.

## Criteria: served in full, in part, held

| Criterion | Here | Held until |
|---|---|---|
| TB1 stable key | **full**: `case_bug_key(project, case_id, criterion_id)` and the video key = `Issue.id`; a seed whose key does not match is refused by the schema | - |
| TB2 lifecycle table | **full** over every (state, event) cell; N is the store's `close_passes` argument, default 2 | the stored per-project value (`schema/project.py` is forbidden) |
| TB3 verdicts only | **part**: `kind_of_verdict(Verdict or None)` is the only reader; no `RawResult` import; unevidenced PASS and verdict-less results change nothing | reading a run's verdicts off disk, the replay path |
| TB4 honest close | **part**: `closed_by_runs`/`closed_by_verdicts` kept; `case_changed` makes an open bug `stale`, never `fixed` | detecting a deleted case or changed criterion (needs `ProjectStore`); the pinned-case test (the core never touches cases) |
| TB5 adapter in `stages/issues.py` | **full**: one function, <= 58 added lines, file <= 300 | - |
| TB6 idempotent | **part**: an event applied twice, a whole batch replayed after a crash, 2 racing writers: same bytes / same state | the processed-run marker (event ids make it redundant here; the run-reading slice decides) |
| TB7 tracker page | **held**; the data side, the `assign` event, is built | route, template, `report.view` / `project.edit` enforcement (T-204/T-205) |

## Lifecycle: events and the table (one dict per state in `stages/bug_loop.py`)

Events (closed enum): `fail`, `pass`, `pass_unevidenced`, `inconclusive`, `blocked`, `not_run`, `no_verdict`, `case_changed`, `assign`.
States: none, `open`, `reopened`, `fixed`, `stale`. 5 x 9 = 45 cells, each a Move or a named Refusal. "u" = unchanged (no write).

| state \ event | fail | pass | pass_unevid., inconcl., blocked, not_run, no_verdict | case_changed | assign |
|---|---|---|---|---|---|
| none | OPEN (a) | refuse `no_bug` | u (b) | refuse `no_bug` | refuse `no_bug` |
| open | REFAIL: count+1, last_seen, streak reset (c) | PASS_STEP: streak+1; at N -> `fixed` (d) | u (b) | MARK_STALE (e) | ASSIGN (j) |
| reopened | REFAIL (f) | PASS_STEP (f) | u | MARK_STALE (f) | ASSIGN |
| fixed | REOPEN: `reopened`, count+1 (g) | u (h) | u | refuse `closed_record` (i) | ASSIGN |
| stale | refuse `stale_bug` (k) | refuse `stale_bug` (k) | u | refuse `already_stale` | ASSIGN |

Traces: (a) TB2 "(none, FAIL)->open". (b) TB2 "(any, INCONCLUSIVE | BLOCKED | NOT_RUN)->unchanged", TB3 "a result with no verdict changes nothing",
"a PASS counts toward closing only when its verdict cites evidence". (c) TB2 "(open, FAIL)->open, count+1, last_seen". (d) TB2 "(open, PASS x k)->open for k < N,
(open, PASS x N)->fixed"; "consecutive only if no FAIL falls between". (e) TB4 "if its case was deleted or its criterion changed, it becomes stale, never fixed".
(f) R44 states re-fail and N-pass with no state qualifier, so `reopened` behaves as `open`. (g) TB2 "(fixed, FAIL)->reopened". (i) TB4 reads as governing a bug not yet closed.
(j) TB7 "editing the assignee" lists bugs in every status.

Who may move it (role names; the actor is an opaque validated string recorded on each event): every status move is made by **bug-loop (machine)** under the
reserved actor `system:bug-loop`; a user actor on a status event is refused `actor_not_allowed` (TB2 "statuses are machine-owned"). `assign` is made by a
**project editor** (a named user; the `project.edit` check is T-204's) and the reserved machine actor is refused there.

## Contract gaps (not defined; conservative reading taken)

- G1 (h) `(fixed, pass)`: undefined; read as unchanged, not a second close.
- G2 (k) `(stale, fail|pass)`: undefined; refused, so a new failure on a stale key is reported as a refusal, never silently restarted (the old branch restarted with count 1). Flipping it is one table entry; checker to rule.
- G3 (i) `(fixed, case_changed)`: refused; the closed record stays honest.
- G4 streak is per bug: a FAIL on criterion C1 does not break C2's streak (old probe P2). Per-case needs a contract sentence.
- G5 TB6 names a "processed-run marker"; event ids give the same result without the late-verdict loss (old probe P1). Marker held.
- G6 `reopened` as `open` (f), `assign` in all states (j), a FAIL verdict with no cited failure maps to `inconclusive` (cannot name a criterion), "PASS cites evidence" read as every criterion met and no screenshot owed (the old branch's ruling).
- G7 notes: the contract defines no note concept; none built.

## Design

State is a fold of an append-only event log (`bug_events.jsonl` in a directory the caller passes). History is never rewritten; `fold` is the single interpreter, so a racing
writer's event is applied in file order, or skipped as a duplicate (`event_id = content_id(bug_key, ref)`, first wins). Appends and reads use `store/filestore.py`
`append_jsonl`/`read_jsonl` (the repo's helper; no second lock helper, no `fcntl`, R65). A torn tail line from a power cut raises loudly with `path:line`.

## Files

- New `src/autotester/schema/tracked_bug.py` (<= 170): `BugStatus`, `EventKind`, `BugSeed`, `BugEvent`, `TrackedBug`, `case_bug_key`, `SYSTEM_ACTOR`. C1: `extra="forbid"`.
- New `src/autotester/stages/bug_loop.py` (<= 250): the table, `judge`, `fold`, `kind_of_verdict`. Pure, no I/O.
- New `src/autotester/store/bug_store.py` (<= 120): `BugStore(root, close_passes)`: `apply`, `apply_all`, `bugs`, `get`, `history`.
- Edit `src/autotester/stages/issues.py` (242 lines, +<= 58): `issue_to_bug_event`, the only key derivation from an `Issue`.
- New `tests/test_bug_loop.py`, `tests/test_bug_store.py`, `tests/bug_loop_fixture.py`; manifest `qa/manifests/t199a-bug-loop-core.md`; `docs/MAP.md` via `autotester map`.
- Held (after t205/t204 merge): `ui/routes_tracker.py`, any route, CLI command, `Project.bug_close_passes`, `core/paths.py` helper, sheet client, `process_run` over a run directory.

New modules (D-082 item 1): `schema/tracked_bug.py` (tracked bug, events, key); `stages/bug_loop.py` (the lifecycle table and its fold); `store/bug_store.py` (append-only bug event log under a caller-given directory).
`store/bug_store.py` is the third, named here so `bug_loop.py` stays pure and under the cap.
