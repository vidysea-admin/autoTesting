# Manifest — at576-577-serial-runs

**Contract:** qa/contracts/execute.md E4 + qa/contracts/ui-run.md RU1-RU4 + qa/contracts/network-assertions.md NA3 + qa/contracts/core-invariants.md C7
**Issues addressed:** AT-576, AT-577, AT-578
**Date:** 2026-09-25
**Fix cycle:** 2 of 3
**Dual check:** no
**Executor:** claude-sonnet-subagent (maker build subagent)
**Branch/worktree:** `wave/at576-577-serial-runs`, `D:/autoTesting/.worktrees/at576-577-serial-runs`
**Base:** master `80256c3` · cycle 2 additionally merges master `ee98f64` (AT-578's ledger row) via `c4c6b81`

## Fix cycle 2

**Cycle 1 checker verdict:** `qa/verdicts/at576-577-serial-runs.md` (checked head `8295b79`) — VERDICT FAIL.
AT-576 confirmed fixed live (real 303 with an entry case + 2 ordinary cases). AT-577's RawResult
scoping confirmed fixed. One FAILURE quoted below, plus AT-578 (found and filed by the checker from
this unit's own cycle-1 disclosed gap, `qa/feedback-inbox.md` item b) folded in as instructed.

### Failure 1 (quoted from the verdict) — entry-case screenshot collision

> `[AT-577 / evidence integrity] sev: high · on the serial path an entry case's screenshots are
> overwritten by the first ordinary case: `_run_entry_case` gives each entry case a fresh
> `BrowserSession` in the SAME `run_dir` with its screenshot counter at 0, and now that entry cases
> run first, the shared session also starts at 0, so both write `01-step01-navigate.png`. Live
> (run-01M3BNKR295JN0DPMR3HM888BZ): 'Homepage loads' (index.html) records `01-step01-navigate.png`
> but that file's sha1 f3a69799 is the login page; 5 PNGs on disk for 6 steps; the run view and HTML
> report show the login page under 'Homepage loads'. · fix: give every entry-case session its own
> namespace (the AT-572 mechanism: `SessionState.evidence_prefix = case.id` in `_run_entry_case`),
> or carry one run-wide counter; a test running an entry case + an ordinary case whose first steps
> both screenshot, asserting distinct paths with different bytes; capability row.`

**Fix:** `src/autotester/ui/routes_runs.py::_run_entry_case` (~line 78) — one new line,
`session.state.evidence_prefix = case.id`, set right after constructing the entry case's dedicated
`BrowserSession` and before `session.start()`. This is exactly the mechanism the checker named:
`BrowserSession.screenshot()` (session.py) already nests under `evidence_prefix` when it is set
(the AT-572 code path T-173's parallel fan-out uses for the same reason — sibling sessions sharing
one `run_dir`). The entry case's screenshots now live under `run_dir/<entry_case.id>/`, so the
shared session's `01-...`, `02-...` numbering in the bare `run_dir` can never collide with them,
regardless of which starts first or how many entry cases exist (each gets its own `case.id`
sub-path). No change to the shared session, `_run_cases_in_parallel`, or `default_session_factory`
— the parallel path already did this correctly (that's where the mechanism was borrowed from).

### Failure 2 (AT-578, folded in per the maker's own request) — network assertion cross-case leak

> `browser/assertions.py::_network_met` scans ALL NETWORK evidence on the session, not just this
> case's: on the serial path (one session shared across cases) a network expectation declared by a
> later case is satisfied by a response an EARLIER case observed, so a regression where the expected
> request no longer happens passes silently (false 'met'). The assertion-side twin of AT-577. ·
> expected: Scope `_network_met` to the current case's evidence (pass `evidence_start` through
> `assert_expected`, or record it on `SessionState` at `run_case` start); a test with two cases on
> one session where case 1 observes the pattern and case 2 does not -> case 2 unmet.`

**Fix, three files, one mechanism (the second option the ledger row offered — record it on
`SessionState`, not threaded through every call signature):**
- `src/autotester/browser/session.py::SessionState` (~line 64) — new field `evidence_start: int = 0`,
  same shape and same reasoning as `evidence_prefix` above it: per-case state a shared session
  carries, defaulting to 0 (correct for a fresh per-case session on the parallel path, unaffected).
- `src/autotester/stages/execute.py::run_case` (~line 117) — right after computing the local
  `evidence_start = len(session.state.evidence)` (AT-577's own value, unchanged), one new line also
  writes it onto `session.state.evidence_start = evidence_start`. One index, two consumers: the
  `RawResult` slice (AT-577, local variable) and now `_network_met` (AT-578, session-level field) —
  no duplicate bookkeeping, no drift between them possible.
- `src/autotester/browser/assertions.py::_network_met` (~line 104) — reads
  `session.state.evidence[session.state.evidence_start:]` instead of the whole list, mirroring
  `_result`'s own slice. `met()` (used by `assert_expected`'s polling loop) and `assert_expected`'s
  own final network check both call `_network_met`, so both are covered by this one change — no
  second call site needed threading.
- Chose session-state over parameter-threading because `Action.ASSERT`'s dispatch-table lambda
  (`execute.py`'s `_ACTIONS` dict) has the fixed `(session, step)` signature every other handler
  shares; threading `evidence_start` through it would touch the dispatch table's shape for one
  handler alone. Storing it on `SessionState` needed no signature change anywhere, and it is the
  exact pattern `evidence_prefix` (AT-572) already established for "per-case state on a
  possibly-shared session."

### What changed (files touched, cycle 2)

- `src/autotester/ui/routes_runs.py` — `_run_entry_case` gets `evidence_prefix` (Failure 1)
- `src/autotester/browser/session.py` — `SessionState.evidence_start` field (Failure 2)
- `src/autotester/stages/execute.py` — `run_case` writes `evidence_start` onto session state (Failure 2)
- `src/autotester/browser/assertions.py` — `_network_met` scoped to `evidence_start` (Failure 2)
- `tests/test_ui_runs_serial_entry_screenshot_namespace.py` — **new**, 1 test (Failure 1, real
  `run_case`/`BrowserSession.screenshot()` against a fake page that writes real distinguishable bytes)
- `tests/test_network_assertions_serial_scope.py` — **new**, 2 tests (Failure 2: unmet when only an
  earlier case observed the pattern; met when the current case observes it itself, guarding against
  over-tightening)
- `tests/test_ui_runs_serial_entry_mix_live.py` — extended (not replaced): the live test now also
  asserts PNG count == total step count across all 3 cases, no path shared across cases, and every
  recorded screenshot file actually exists on disk

No file from cycle 1 was reverted or weakened; every cycle-1 test still passes unchanged (see
Verify below).

### Red on unfixed code (both new test files, each temporarily reverted on the real worktree file
and restored — not `git stash` this time, an anchored single-hunk revert/restore verified
byte-identical after, same discipline as the capability-coverage mutations below)

Failure 1 (`test_ui_runs_serial_entry_screenshot_namespace.py`, `evidence_prefix` line removed):
```
AssertionError: entry and ordinary case screenshots must never share a path: '01-step01-navigate.png'
assert '01-step01-navigate.png' != '01-step01-navigate.png'
1 failed in 11.83s
```
Green after restoring the fix: `1 passed in 1.78s`.

Failure 2 (`test_network_assertions_serial_scope.py`, `_network_met` reverted to the whole-session scan):
```
AssertionError: case 2 must not be satisfied by case 1's earlier network capture
assert <Outcome.COMPLETED: 'completed'> is <Outcome.ASSERTION_FAILED: 'assertion_failed'>
1 failed, 1 passed in 0.51s
```
(The sibling test — case 2 observing its own matching request — stayed green throughout, proving the
fix does not over-tighten.) Green after restoring the fix: `2 passed in 0.50s`.

### Verify — targeted (cycle 2, real worktree)

```
$ uv run pytest tests/test_execute.py tests/test_execute_assertions.py tests/test_execute_new_actions.py \
    tests/test_execute_serial_evidence_scope.py tests/test_ui_runs.py tests/test_ui_runs_serial_resilience.py \
    tests/test_ui_runs_serial_entry_order.py tests/test_ui_runs_serial_entry_screenshot_namespace.py \
    tests/test_ui_runs_serial_entry_mix_live.py tests/test_ui_runs_parallel_trace.py \
    tests/test_ui_runs_parallel_crash_recovery.py tests/test_coverage_wiring.py tests/test_run_case_pipeline.py \
    tests/test_run_case_pipeline_resilient.py tests/test_grade.py tests/test_grade_evidence.py \
    tests/test_agent_loop.py tests/test_network_assertions.py tests/test_network_assertions_serial_scope.py \
    tests/test_report_export.py tests/test_ui_report.py tests/test_ui_report_no_runs.py \
    tests/test_parallel_run_evidence_namespace.py tests/test_run_trace.py
137 passed, 1 skipped, 6 warnings in 10.06s

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```
(1 skip = the live test, still RAM-gated this cycle too — see the updated Live browser evidence
section below. 6 warnings are the same pre-existing, unrelated `test_run_trace.py` advisory as
cycle 1. One flake was observed and NOT counted here:
`test_ui_runs_parallel_trace.py::test_with_max_parallel_2_two_cases_run_concurrently` failed once in
the full targeted run — `peak[0] == 1` instead of `2`, a timing-sensitive thread-overlap assertion
with only a 0.05s sleep — and passed cleanly in isolation immediately after (`1 passed`). Not this
unit's code: neither fix touches `stages/parallel_run.py`, the thread pool, or `_run_cases_in_
parallel`'s concurrency; consistent with the same host memory pressure documented in the Live
browser evidence section.)

### Capability coverage (mutation, cycle 2, C7)

Same discipline as cycle 1: a fresh throwaway copy (`at576-577-capability-copy-c2`, `uv sync
--frozen`'d independently, deleted after use), baseline asserted green first.

```
$ uv run pytest tests/test_ui_runs_serial_entry_screenshot_namespace.py tests/test_network_assertions_serial_scope.py \
    tests/test_network_assertions.py tests/test_execute.py tests/test_execute_serial_evidence_scope.py \
    tests/test_ui_runs_serial_entry_order.py tests/test_ui_runs_serial_resilience.py tests/test_ui_runs.py \
    tests/test_ui_runs_parallel_trace.py tests/test_ui_runs_parallel_crash_recovery.py tests/test_coverage_wiring.py
50 passed in 7.53s
```

| # | Mutation (file, single-hunk) | Reverted behaviour | Kills (named, re-run confirmed) | Survives |
|---|---|---|---|---|
| C | `routes_runs.py`: `_run_entry_case`'s `session.state.evidence_prefix = case.id` line removed | Failure 1 exactly — entry and shared session both number from 01 in the same `run_dir` | `test_entry_and_ordinary_case_screenshots_never_collide_on_disk` (real pytest run, `1 failed`, asserts the exact colliding path `'01-step01-navigate.png'`) | All 49 other tests in the baseline set — `49 passed` alongside the 1 failure |
| D | `assertions.py`: `_network_met` reverted to scanning the whole `session.state.evidence`, ignoring `evidence_start` | AT-578 exactly — a later case's `network` assertion can be satisfied by an earlier case's capture | `test_case_2_network_assertion_is_unmet_when_only_case_1_observed_the_pattern` (real pytest run, `1 failed`, `Outcome.COMPLETED` where `ASSERTION_FAILED` was expected) | `test_case_2_network_assertion_is_met_when_case_2_itself_observes_the_pattern` and all 48 other tests in the baseline set — confirms the mutation breaks only cross-case scoping, not a genuinely-met assertion |

Both mutations applied via the same anchored `text.count(old) == 1` script as cycle 1, re-run,
reverted by the exact inverse replace, re-run green, and each reverted file diffed byte-identical
against the real worktree's fixed file (`diff -u` → no output, `IDENTICAL`). Run independently (C
applied+reverted+confirmed identical before D was applied), so each kill is attributable to its own
named test with nothing else mutated at the same time.

## The bugs

**AT-576** — `ui/routes_runs.py::_run_cases_serially` started the shared, run-wide `BrowserSession`
FIRST (for login continuity across ordinary cases), then looped over every case; hitting an entry
case mid-loop called `_run_entry_case`, which starts a SECOND sync Playwright driver on the same
thread while the shared session's driver was still live. Playwright's sync API detects this and
raises `"It looks like you are using Playwright Sync API inside the asyncio loop"`, 500ing the
whole run before the remaining cases ran or the `Run` record was saved. Reproduced live on master
with no judge outage (`qa/verdicts/at574-serial-resilience.md` Mode D run 1); the ordering dates to
`939af44` (AT-044). Every unit test faked `BrowserSession.start`, so none could see it.

**AT-577** — `stages/execute.py::run_case` returned `RawResult(evidence=list(session.state.
evidence))` — the session's WHOLE evidence history, not this case's own. The serial route reuses
one `BrowserSession` across every non-entry case in a run, so by the time case 2 ran, `session.
state.evidence` already held case 1's screenshots too; case 2's `RawResult` (and case 3's, etc.)
carried every earlier case's evidence in addition to its own. The grader judged later cases partly
on earlier cases' pages, and the run view rendered earlier cases' steps under the wrong card.
Reproduced live (`qa/verdicts/at574-serial-resilience.md` Mode D run 2): "Homepage loads" case
listed evidence 01-05 where 01-04 belonged to the login case.

## Fix

**AT-577 — `src/autotester/stages/execute.py`**
- `run_case` (line ~104): added `evidence_start = len(session.state.evidence)` at entry, before any
  step runs — the index into the (possibly already non-empty) session evidence list where THIS
  case's own items begin.
- `_result` (line ~140): new `evidence_start: int = 0` keyword param; the returned `RawResult` now
  carries `list(session.state.evidence[evidence_start:])` instead of the full list. Every call site
  of `_result` inside `run_case` (BLOCKED_HITL, ERRORED, ASSERTION_FAILED, COMPLETED) passes its own
  `evidence_start`.
- `_assertions_unmet` (unchanged) already took a `pre` index scoped to a single STEP within the same
  `run_case` call — unaffected by the case-level slice, since it always reads live, un-sliced
  `session.state.evidence` at a point captured during the same call.
- **This is the one fix that repairs every reader at once**: `stages/grade.py`, `stages/
  report_export.py`, `stages/agent_loop.py` and `ui/routes_report.py` all read `result.evidence`
  (the `RawResult`'s own field), never `session.state.evidence` directly — confirmed by grep across
  `src/` (only `browser/assertions.py`, `browser/session.py`, `stages/parallel_run.py` and
  `stages/execute.py` itself touch `session.state.evidence`; none of those four are report/grade
  readers). Screenshot filenames stay unique across cases on a reused session because `session.
  state.screenshots` is a session-wide counter untouched by this fix (01, 02, 03… never resets) —
  no filename-collision risk, only the *RawResult's own list* is now scoped.
- **Independent corroboration found while fixing this:** three call-site scripts
  (`scripts/bench_trial.py:97-101`, `scripts/regression_proof.py:140-144`,
  `scripts/run_pathlynks_first_cases.py:125-137`) already work around this exact defect by hand —
  each captures `start = len(session.state.evidence)` BEFORE calling `run_case`, then overwrites
  `result.evidence = list(session.state.evidence[start:])` AFTER. `run_pathlynks_first_cases.py`
  even carries an explicit comment naming the bug: *"execute.py::run_case snapshots ALL of
  session.state.evidence, which is cumulative for the whole (reused) session, not scoped per case
  -- slice to just what THIS case adds, else case 2's RawResult would also carry case 1's evidence
  (found running this for real)."* This independently confirms both the defect and the shape of the
  fix. **Not touched here** — each script's own re-slice still does something `run_case` itself
  does not (folding in evidence recorded AFTER `run_case` returns, e.g. a post-submit screenshot),
  so it stays correct and is simply redundant-but-harmless for the portion `run_case` now already
  scopes correctly. Left as-is; changing three working scripts to remove a no-op is not this unit's
  scope.

**AT-576 — `src/autotester/ui/routes_runs.py::_run_cases_serially`** (line ~114)
- Old order: start the shared session (if any non-entry case exists) → loop over `cases` in their
  original order, branching per-case into `_run_entry_case` (own session) or the shared session.
- New order: loop over `cases` ONCE and run every entry case to completion first (own dedicated
  session, started and closed inside `_run_entry_case`, exactly as before) — **before** the shared
  session is ever constructed. Only after every entry case has finished does the shared session get
  built and started, then every non-entry case runs against it. This is the same entry-cases-first
  shape `_run_cases_in_parallel` (a few lines below in the same file) already uses — AT-576 brings
  the serial path in line with it, not a new pattern.
- Consequence: the shared session's sync Playwright driver is never live while an entry case's own
  driver starts, because the entry cases have already started AND closed their own drivers by the
  time the shared one exists. No two sync Playwright drivers are ever alive on the thread at once.
- Case order in `Run.case_ids` (built in `trigger_run` from the original `cases` list) is unaffected
  — only the *execution* order changed, not what gets recorded or in what order results are read
  back by any caller (`store.load_results` returns by case id, not insertion order).

## What changed (files touched)

- `src/autotester/stages/execute.py` — AT-577 fix (see above)
- `src/autotester/ui/routes_runs.py` — AT-576 fix (see above)
- `tests/test_execute_serial_evidence_scope.py` — **new**, 2 tests (AT-577, fast/fake)
- `tests/test_ui_runs_serial_entry_order.py` — **new**, 1 test (AT-576 ordering decision, fast/fake)
- `tests/test_ui_runs_serial_entry_mix_live.py` — **new**, 1 test (AT-576 the real live defect, real
  Chromium, RAM-gated)

No existing test file was modified.

## New tests (TDD, red first on unfixed code)

### AT-577 — `tests/test_execute_serial_evidence_scope.py`

1. `test_two_cases_on_one_shared_session_get_disjoint_evidence` — two cases run back-to-back on one
   shared fake-page `BrowserSession`; asserts `result1.evidence` and `result2.evidence` share no
   path, and that the session's own accumulated evidence equals the sum of both results' evidence
   (proves the split is a partition, not a loss).
2. `test_a_third_case_still_only_sees_its_own_slice` — three cases on one session, pairwise
   disjoint, guards the off-by-one at the second/third boundary.

**Red on unfixed code** (`git stash` of the `execute.py` fix only, both new tests run against it):
```
AssertionError: case 2's evidence must not include case 1's: shared={'01-step01-click.png', 'clicked #a'}
AssertionError: case 0 and case 1 overlap: {'01-step01-click.png', 'clicked #c0'}
2 failed in 0.76s
```
**Green after the fix** (`git stash pop`):
```
tests/test_execute_serial_evidence_scope.py ..                          [100%]
2 passed in 0.20s
```

### AT-576 (ordering decision) — `tests/test_ui_runs_serial_entry_order.py`

`test_entry_cases_start_before_the_shared_session_starts` — drives the real `/projects/demo/run`
route (`TestClient`), fakes only `BrowserSession.start`/`.close` (recording which session's
`ProjectPaths.slug` started, in order) and the provider/pipeline seams (`run_case`, `grade`) —
never the ordering logic itself. Asserts `starts == ["demo-entry-test", "demo"]` for a run mixing
one entry case with one ordinary case.

**Red on unfixed code** (`git stash` of the `routes_runs.py` fix only):
```
AssertionError: the entry case's own session must start before the shared session: ['demo', 'demo-entry-test']
assert ['demo', 'demo-entry-test'] == ['demo-entry-test', 'demo']
1 failed in 2.29s
```
**Green after the fix** (`git stash pop`):
```
1 passed
```

### AT-576 (the real defect) — `tests/test_ui_runs_serial_entry_mix_live.py`

`test_a_serial_run_mixing_an_entry_case_with_ordinary_cases_does_not_500` — the checker's own
requirement: a fake `BrowserSession.start` cannot reach AT-576 at all (Playwright's sync-API guard
only fires inside a REAL `sync_playwright().start()` call), so this test never fakes the browser.
Real `BrowserSession` driven through the real `/projects/rd/run` route (`TestClient`, which — like
`uvicorn` — runs a sync FastAPI path operation via `anyio`'s worker-thread pool, so `trigger_run`
executes on one real thread exactly as it would in production) against a local fixture site
(`tests/fixtures/regression_site`, served over real HTTP via the `serve_dir` conftest fixture) on an
isolated `AUTOTESTER_ROOT` (`tmp_path`). Only the AI provider is faked:
`routes_runs_module.LangChainFallbackProvider` → a `MockProvider` seeded with 10 queued PASS
`Judgment`s (same "swap the judge, keep the browser real" seam
`test_ui_runs_parallel_trace.py::test_a_real_run_writes_a_trace_with_at_least_one_span` already
uses). 1 entry case (navigates to `base_url`) + 2 ordinary cases (navigate to `login.html` / click
the sign-in link on `index.html`). Asserts `response.status_code == 303`, exactly one `Run` saved,
and 3 results (one per case).

**RAM-gated** (project convention, `qa/contracts/core-invariants.md`; mirrors `parallel_run.py`'s
own `_RAM_FLOOR_MB = 2048.0` plus the `/maker` dispatch prompt's stricter 3.5 GB floor for launching
a real Chromium): the test itself checks free RAM via `stages.parallel_run._free_ram_mb()` at the
top and `pytest.skip`s with the measurement below the floor, rather than launching a browser under
memory pressure on a shared host. **Live-browser evidence and disposition are in the section below.**

## Verify — targeted (real worktree, uncommitted changes at time of writing)

```
$ uv run pytest tests/test_execute.py tests/test_execute_assertions.py tests/test_execute_new_actions.py \
    tests/test_execute_serial_evidence_scope.py tests/test_ui_runs.py tests/test_ui_runs_serial_resilience.py \
    tests/test_ui_runs_serial_entry_order.py tests/test_ui_runs_serial_entry_mix_live.py \
    tests/test_ui_runs_parallel_trace.py tests/test_ui_runs_parallel_crash_recovery.py \
    tests/test_coverage_wiring.py tests/test_run_case_pipeline.py tests/test_run_case_pipeline_resilient.py \
    tests/test_grade.py tests/test_grade_evidence.py tests/test_agent_loop.py tests/test_network_assertions.py \
    tests/test_report_export.py tests/test_ui_report.py tests/test_ui_report_no_runs.py \
    tests/test_parallel_run_evidence_namespace.py tests/test_run_trace.py
134 passed, 1 skipped, 6 warnings in 8.14s
```
(1 skip = the live test, RAM-gated at collection time; 6 warnings are the pre-existing, unrelated
`test_run_trace.py` `secrets=` advisory — present on master too, not introduced here.)

Every reader of `RawResult.evidence` named by the dispatch prompt is covered: `test_grade.py`/
`test_grade_evidence.py` (grade.py), `test_report_export.py` (report_export.py), `test_ui_report.py`/
`test_ui_report_no_runs.py` (routes_report.py), `test_agent_loop.py` (agent_loop.py). The parallel
path's own tests (`test_ui_runs_parallel_trace.py`, `test_ui_runs_parallel_crash_recovery.py`,
`test_parallel_run_evidence_namespace.py`) pass unchanged — `_run_cases_in_parallel`,
`stages/parallel_run.py` and `default_session_factory`'s `evidence_prefix` (AT-572) were not
touched by either fix.

```
$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```

## Capability coverage (mutation, C7)

Never edited the worktree in place. Throwaway copy of `src/`, `tests/`, `scripts/`, `pyproject.toml`,
`uv.lock` (plus a placeholder `README.md`) at
`%TEMP%\claude\d--autoTesting\<session>\scratchpad\at576-577-capability-copy`, `uv sync --frozen`'d
independently (own `.venv`), never touching the bound worktree or `origin`; deleted after use.

**Baseline asserted green first** (C7's baseline clause):
```
$ uv run pytest tests/test_execute_serial_evidence_scope.py tests/test_ui_runs_serial_entry_order.py \
    tests/test_ui_runs_serial_resilience.py tests/test_ui_runs.py tests/test_ui_runs_parallel_trace.py \
    tests/test_ui_runs_parallel_crash_recovery.py tests/test_coverage_wiring.py
26 passed in 4.31s
```

Each mutation applied by an exact anchored string replace (a small Python script asserting
`text.count(old) == 1` before writing, refusing a silent no-op per C7's anchor clause), re-run, then
reverted by the exact inverse replace, re-run green, and the reverted file diffed byte-identical
against the real worktree's fixed file (`diff -u` → no output, `IDENTICAL`).

| # | Mutation (file, single-hunk) | Reverted behaviour | Kills (named, re-run confirmed) | Survives |
|---|---|---|---|---|
| A | `execute.py`: `_result`'s evidence line reverted to `list(session.state.evidence)` (the pre-fix full-history return; `evidence_start` computed but unused) | AT-577 exactly — every case's `RawResult` carries the whole session's evidence again | `test_two_cases_on_one_shared_session_get_disjoint_evidence`, `test_a_third_case_still_only_sees_its_own_slice` (real pytest run, `2 failed`, both assertion messages naming the exact overlapping evidence items) | All 24 other tests in the baseline set — `24 passed` alongside the 2 failures |
| B | `routes_runs.py`: `_run_cases_serially` reverted to the pre-fix shape (shared session started first when any non-entry case exists, entry/non-entry branch inline in one loop) | AT-576 exactly — the shared session starts before an entry case is ever reached | `test_entry_cases_start_before_the_shared_session_starts` (real pytest run, `1 failed`, `starts == ['demo', 'demo-entry-test']` — the exact pre-fix order) | All 25 other tests in the baseline set, **including every AT-574 resilience test** (`test_ui_runs_serial_resilience.py`'s 3 tests, `test_ui_runs_parallel_crash_recovery.py`'s 2) — confirms this mutation touches only the ordering, not AT-574's crash-guard behaviour |

Both mutations run independently (A applied+reverted, confirmed identical, before B was applied) —
never combined in one pass, so each kill is attributable to its own named test with nothing else
mutated at the same time.

## Live browser evidence — cycle 1 — UNVERIFIED (RAM-gated)

`tests/test_ui_runs_serial_entry_mix_live.py` is written, committed, and self-gates on free RAM
(`stages.parallel_run._free_ram_mb()` vs the 3.5 GB floor) rather than ever faking `BrowserSession`
— per the dispatch instruction, never faked to force a green result.

**Measured, bounded poll** (every 300s, ≤30 min, `Get-CimInstance Win32_OperatingSystem.
FreePhysicalMemory`), run in the background for ~20 of its ≤30 minutes before being stopped once the
pattern was clear and corroborated (see root cause below), plus one final spot check:

```
12:05:56 free_mb=150.5
12:10:59 free_mb=3090.3
12:16:01 free_mb=1029.8
12:21:04 free_mb=636.7
12:23:xx free_mb=1737.4  (final spot check, after stopping the stalled full-suite background run)
```

Never once reached the 3.5 GB (3584 MB) floor across 5 measurements spanning ~20 minutes — peak was
3090 MB, still 494 MB short. Root cause confirmed, not guessed: `Get-CimInstance Win32_Process`
during this cycle showed a **second, independent Claude session actively running its own pytest
suite against this same repo concurrently** (a different session id under
`C:\Users\Lenovo\AppData\Local\Temp\claude\d--autoTesting\909303db-...`), plus unrelated live work
from `D:\tracker`, `D:\counsellor_validation_judge`, and a `hermes-agent` venv, and dozens of
pre-existing `chrome.exe` processes none of which this unit started. This is a shared, busy host,
not a dedicated runner — the same condition `at574-serial-resilience`'s manifest recorded, worse
this cycle.

**Given the shortfall's size and persistence, no Chromium was launched** — starting one under this
pressure risks a wedged process on a host other sessions depend on. Confirmed after stopping this
unit's own background tasks: `Get-CimInstance Win32_Process | Where CommandLine -match autoTesting`
shows no `python`/`pytest`/`chrome` process tied to this unit's worktree path or command line —
nothing was left running.

**Disposition: UNVERIFIED, not fixed-and-proven live.** The route-level fake-session test
(`test_ui_runs_serial_entry_order.py`) and the mutation-coverage row B above prove the ORDERING
decision is correct and load-bearing; only the claim "a REAL nested-Playwright 500 no longer
happens" is unverified this cycle. The checker's own Mode D recipe (real Chromium, `MockProvider`
swapped in-process, isolated `AUTOTESTER_ROOT`) is the standing gate for this, same as
`at574-serial-resilience`.

## Live browser evidence — cycle 2 — still UNVERIFIED (RAM-gated, same shared host)

`tests/test_ui_runs_serial_entry_mix_live.py` was extended this cycle (PNG-count == step-count,
no shared path across cases, every recorded file exists on disk — see "Fix cycle 2" above) but
still never fakes `BrowserSession`, and the same RAM gate applies.

**Measured, bounded poll**, run in the background again this cycle (stopped after ~10 of its ≤30
minutes once the pattern reconfirmed):

```
12:43:02 free_mb=2622.1
12:48:06 free_mb=1545.1
```

Peak this cycle (2622 MB) is closer to the floor than cycle 1's peak (3090 MB) but still 962 MB
short of 3584 MB. **Root cause reconfirmed, not merely repeated:** `Get-CimInstance Win32_Process`
this cycle found a DIFFERENT concurrent session this time — an independent Claude session actively
running falsification/mutation `pytest` invocations against `D:\counsellor_validation_judge` (PIDs
46036/36892/45788, `python -m pytest tests/test_output_alignment.py -q -p no:cacheprovider -k
"ignores_unparseable"` against a scratch copy under its own `.../scratchpad/chk-top10-primary`),
confirming this is a genuinely shared host under variable, unpredictable load from OTHER sessions'
legitimate work — not a fluke of cycle 1, and not something this unit's own tests, background tasks,
or the RAM gate's threshold can control. The full non-browser `uv run pytest` suite was also
attempted again this cycle and again produced zero output after several minutes before being
stopped (see Gap 1 below).

**No Chromium was launched this cycle either.** Confirmed after stopping this cycle's background
tasks: `Get-CimInstance Win32_Process | Where CommandLine -match at576-577-serial-runs` shows only
this session's own shell/PowerShell inspection commands — no `python`/`pytest`/`chrome` process tied
to this unit's worktree path or run command was left running.

**Disposition: still UNVERIFIED.** Both fixes (entry-case `evidence_prefix` for the screenshot
collision, `_network_met` scoping for AT-578) are proven by fast, deterministic tests exercising the
real `run_case`/`BrowserSession.screenshot()`/`assert_expected` code paths against fakes that write
real, distinguishable bytes to disk — not weakened, deterministic evidence. What remains unverified
is only the end-to-end real-Chromium claim (303 + correct file layout under a real browser), same as
cycle 1. The checker's own Mode D recipe is the standing gate.

## Gaps (disclosed, not fixed here)

1. **Cycle 1: the full non-browser `uv run pytest` suite (slot-1's actual verify command) did not
   complete.** Launched under the same RAM pressure described above; after 10+ minutes it had
   produced zero output (pytest itself starting is near-instant on this repo normally), consistent
   with the host thrashing under concurrent load rather than this unit's tests hanging — the
   134-test targeted subset (every touched file, every evidence reader, both new fake-session
   tests) is the evidence in its place, `134 passed, 1 skipped` (the live test), plus the
   independent mutation-coverage run against a fully `uv sync`'d throwaway copy (`26 passed`
   baseline, both mutations behaving exactly as predicted, clean revert). Stopped cleanly
   (`TaskStop`), confirmed no orphaned process. The checker's own re-run is the real gate for the
   full suite, same convention `at574-serial-resilience` recorded.

1b. **Cycle 2: repeated, same outcome, different cause on the same host.** Attempted again this
   cycle; again zero output after several minutes; stopped cleanly (`TaskStop`), confirmed no
   orphaned process. Root-caused this time to a DIFFERENT concurrent Claude session running
   falsification `pytest` against `D:\counsellor_validation_judge` (see Live browser evidence —
   cycle 2 above) — not this unit's tests, and not the same cause as cycle 1, which strengthens
   rather than weakens the "shared, busy host" explanation. The 137-test targeted subset this
   cycle (`137 passed, 1 skipped`, includes everything from cycle 1 plus both new AT-577/AT-578
   test files) plus the cycle-2 mutation-coverage run (`50 passed` baseline, both new mutations
   behaving exactly as predicted, clean revert) stand in its place again. The checker's own re-run
   remains the real gate for the full suite.

2. **RESOLVED in cycle 2 (AT-578).** `browser/assertions.py::_network_met` scanned the WHOLE
   `session.state.evidence` for a matching NETWORK item, not scoped to the current case — filed by
   the cycle-1 checker as AT-578 and fixed in the "Fix cycle 2" section above
   (`SessionState.evidence_start`, set by `run_case`, read by `_network_met`). Left here as the
   original disclosure for the record; superseded, not still open.
3. **`qa/contracts/execute.md` E4's wording** ("every `Evidence` the session recorded") predates
   this fix and is now imprecise — it should read "every `Evidence` the session recorded for this
   case." Not editable by the maker (contracts are checker-owned); noted in
   `qa/feedback-inbox.md` for the checker to amend. Still open as of cycle 2 (cycle-1 checker's
   answer #2a: "will be folded when this unit passes").

## Status (cycle 1, superseded by cycle 2 below)

Code + tests committed: `f30b2ac` (base master `80256c3`). Checker verdict: FAIL, cycle 1
(`qa/verdicts/at576-577-serial-runs.md`, head `8295b79`). See "Fix cycle 2" section near the top of
this file for what changed in response, and the final status at the end of this file.

## Status (cycle 2): checked-PASS (qa/verdicts/at576-577-serial-runs.md, Cycle checked: 2, c413326; merged 8e50efc)

Fix cycle 2 of 3. Issues addressed this cycle: AT-577's remaining "keep screenshot names unique"
clause (checker verdict FAIL), plus AT-578 folded in per the checker's own offer. Both fixes are
route/module-level, one line + one field each, proven by fast deterministic tests that exercise the
real code paths (`run_case`, `BrowserSession.screenshot()`, `assert_expected`) against fakes that
write real, distinguishable bytes or real evidence items — never a weakened or faked assertion.
Mutation-tested in a fresh throwaway copy (both new mutations killed by exactly their own named
test, nothing else). Live-browser proof remains UNVERIFIED both cycles, for the same class of
reason both times (a genuinely shared, busy host — corroborated by process inspection each cycle,
not merely asserted) — the checker's own Mode D recipe is the standing gate for it, unchanged from
cycle 1's disposition. Merged current master (`ee98f64`, AT-578's own ledger row) before starting.
No checker dispatch, merge, push, contract/ledger/`.goal` edit, or real `.env` read this cycle.

Code + tests committed this cycle: `77346cb` (on top of the cycle-1 code `f30b2ac` and the
master-merge `c4c6b81`). This manifest commits separately, after this line.
