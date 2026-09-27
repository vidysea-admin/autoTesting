# Manifest — at562-564-live-wiring

**Contract:** qa/contracts/parallel-run.md (PR1-PR7) + qa/contracts/run-trace.md (RT1-RT7) +
qa/contracts/core-invariants.md
**Goal tasks:** T-172, T-173
**Date:** 2026-09-25
**Fix cycle:** 3 of 3
**Dual check:** no
**Issues addressed:** AT-562, AT-564, AT-565 (cycle 1), AT-568, AT-569 (cycle 2, checker cycle-1
FAIL), AT-572, AT-573 (cycle 3, checker cycle-2 FAIL). AT-570 (medium, case runs have no
`RunApproval` gate) is explicitly NOT addressed — the checker's own verdict confirms it
pre-existing and out of this unit's scope (see cycle-1 design decision 3 below).
**Executor:** claude-sonnet-subagent

## Fix cycle 2 (checker cycle-1 FAIL, qa/verdicts/at562-564-live-wiring.md)

**First: merged current master into this branch.** The branch's base (8a97eca) had diverged from
master (which had moved to 99a6989 via unrelated checker sweep/roadmap commits, plus the cycle-1
checker's own AT-568/AT-569/AT-570 issue rows). `git merge origin/master --no-edit` at `1bb436a`
— no conflicts, 21 files, none touching this unit's own paths.

**Failure 1, quoted verbatim (checker):**
> `[PR6 / AT-565, live route] sev: high · ui/routes_runs.py::_run_cases_in_parallel saves
> \`verdicts[result.case_id]\` blindly, but a verdict is captured only when run_and_grade_case
> completes. An ERRORED result from a session_factory crash (the exact AT-565 case) or from any
> exception in run_and_grade_case (it catches nothing — e.g. a grader/provider error) has no
> verdict -> KeyError. Checker probe (...: 3 cases, n=2, the factory raises for case_1, stub
> grader) -> "KeyError: 'case_1'": case_0 saved with its verdict, case_1's result saved WITHOUT a
> verdict, case_2 never saved, and store.save_run (which follows) never runs -> the route 500s and
> the Run record is lost. PR6 requires every other case to complete and report its own outcome. ·
> fix: never index the capture dict blindly — for any result without a captured verdict, produce
> one through the same grade path the serial route uses for an ERRORED result (or an explicit
> ERRORED verdict); add a ROUTE-level test where the factory raises for one of three cases (all
> three results + verdicts and the Run saved; siblings keep their real outcomes) and a capability
> row that reverts the handling and goes red. · issue: AT-568**

**Fix (AT-568):** `stages/run_case_pipeline.py` gains a shared rubric-resolution seam,
`_rubric_for(case, store)` — extracted from `run_and_grade_case`'s own inline lookup (same
behaviour, zero change to it) — and a new `grade_errored_result(case, result, judge, run_id,
store)` that grades a `RawResult` which never reached a `run_and_grade_case` call at all, through
the exact same `_rubric_for` + `grade()` path. Safe unconditionally: every caller of this function
hands it a `result.outcome is Outcome.ERRORED` `RawResult`, and `grade()`'s own `_outcome_verdict`
short-circuits ERRORED/BLOCKED_HITL deterministically, before ever building a prompt or calling
`judge` — proven directly by `test_grade_errored_result_never_calls_the_judge` (a `MockProvider`
with **no** queued judge response; if the judge were ever reached it would raise). `ui/
routes_runs.py::_run_cases_in_parallel` now does `verdicts.get(result.case_id)` instead of
`verdicts[result.case_id]`, and calls `grade_errored_result` for any miss.

**Failure 2, quoted verbatim (checker):**
> `[concurrency, introduced by sharing one judge across worker threads] sev: medium ·
> providers/base.py::Provider.record has no lock: \`entry.calls += 1\` / \`+= tokens\` on shared
> ProviderUsage rows and the not-matched -> append path race when grades finish concurrently ->
> lost usage/cost increments or a duplicate role row. · fix: a threading.Lock around the
> accumulation in record(), or one judge per worker. · issue: AT-569**

**Fix (AT-569):** `providers/base.py::Provider.__init__` gains `self._usage_lock =
threading.Lock()`; `record()`'s whole accumulate-then-append-then-trace block (the entire critical
section named in the finding) is wrapped in `with self._usage_lock:` — T-172's `trace.record_llm`
call stays inside the lock (not merely "immediately after"), so the trace line for one call is
written from the exact usage snapshot that call just produced. `load_skill_prompt` (T-175) is
untouched.

**TDD, both shown red first on the actual code:**
- `tests/test_ui_runs_parallel_crash_recovery.py` (new; split from `test_ui_runs_parallel_trace.py`
  at the 300-line cap) — a route-level test with the factory raising for one of three cases at
  `max_parallel=2` (the exact AT-565/PR6 shape at the route), shown `KeyError` on the pre-fix code
  in a scratch copy (see Capability coverage), and a second variant where `run_and_grade_case`
  itself raises (the "any exception... e.g. a grader/provider error" shape) — both now save every
  result + verdict + the `Run`, no 500.
- `tests/test_provider_record_concurrency.py` (new) — hammers `Provider.record()` from 50 threads
  behind a `threading.Barrier` (so every thread's first call races the others for the same
  brand-new role — the duplicate-row shape — then keeps racing the shared row's counters for many
  more calls — the lost-increment shape), repeated over many independent trials so an unlocked
  `record()` is red **reliably**, not just occasionally (measured: 15/15 full-file runs red
  unlocked, 8/8 green locked — see Capability coverage for the tuning).
- `tests/test_run_case_pipeline.py` gains two unit-level tests directly on `grade_errored_result`
  (never calls the judge; persists the same rubric a normal run would).

**Capability rows for both, plus the two new unit tests, in Capability coverage below.**

**Doctor finding, disclosed, NOT fixed (out of scope, no ledger edit permitted this cycle):**
`uv run autotester doctor` reports `ledger-row-lost` violations naming AT-568/AT-569/AT-570 — 3
against `qa/verdicts/at562-564-live-wiring.md` (the checker's own cycle-1 file), and, once this
manifest itself names those same issue ids in its own required "Issues addressed" header (as every
manifest must), 3 more against `qa/manifests/at562-564-live-wiring.md` — 6 total, all the same root
cause. This is a pre-existing bug in `ledger/checks.py::check_qa_issue_rows`'s own regex
(`"id":\s*"(...)".*?"status":\s*"(\w+)"` requires `id` before `status` on the same JSONL line)
colliding with the **checker's own** AT-568/569/570 rows in `qa/issues.jsonl` (commit `99a6989`,
master), which put `"status"` BEFORE `"id"` — a different field order than the convention every
earlier row used. Both the verdict file (`6c42270`) and the issue rows (`99a6989`) were authored by
the checker, not this maker, in cycle 1 and its own ledger write; neither `ledger/checks.py` nor
`qa/issues.jsonl` is touched by this cycle's diff (confirmed: `git log -3 -- src/autotester/ledger/
checks.py` shows nothing from this branch). Naming AT-568/AT-569 in this manifest's own header is
required by the handshake convention, not optional, so the count rising to 6 is an unavoidable
consequence of writing an honest manifest against a pre-existing checker-tooling bug, not a new
defect. Not fixed here because (a) it is out of the two-issue scope this cycle was dispatched for,
and (b) fixing it would mean editing `qa/issues.jsonl` (a ledger edit) or `ledger/checks.py` (a
shared, unrelated regex), both explicitly off-limits this cycle. Flagging for the checker/a human to
fix or file forward.

## Fix cycle 3 (checker cycle-2 FAIL, qa/verdicts/at562-564-live-wiring.md)

**First: merged current master into this branch.** Master had moved on with, among other things, the
AT-571 doctor fix (`ledger/checks.py` reads ledger rows as JSON instead of a field-order-sensitive
regex) — confirmed after the merge that the 6 `ledger-row-lost` false positives disclosed in Fix
cycle 2 above are gone (`uv run autotester doctor` → `doctor: clean`, see Actual outputs).

**Failure 1, quoted verbatim (checker):**
> `[PR2 / live path] sev: high · the parallel route's sessions (stages/parallel_run.py::
> default_session_factory) all write evidence into the SAME run_dir and each restarts browser/
> session.py's screenshot counter at 01, so sibling cases overwrite each other's screenshots
> (01-step01-navigate.png) and a case's judge can grade a sibling's screenshot -> silent wrong
> verdict. Reproduced live (Mode D run: 2 cases reference one file; 4 PNGs for 6 steps) and
> deterministically (real BrowserSession probe, cases run one after the other: two different pages
> -> one path). · fix: a per-case evidence namespace in the parallel factory (run_dir/<case_id>/ or
> a case-id prefix) that the grader + run view resolve; a test driving two cases with different
> first pages through default_session_factory asserting distinct paths with different bytes; a
> capability row. · issue: AT-572`

**Fix (AT-572):** `browser/session.py`'s `SessionState` gains `evidence_prefix: str = ""` (empty by
default — the serial path never sets it, so its behaviour is byte-for-byte unchanged: confirmed by
`test_serial_path_is_unaffected_evidence_path_stays_a_bare_filename`). `screenshot()` now builds
`rel = f"{prefix}/{name}"` when a prefix is set, else the bare `name` exactly as before, creates the
parent dir (`full.parent.mkdir(parents=True, exist_ok=True)`), and stores `rel` (not the bare name)
as the `Evidence.path`. `stages/parallel_run.py::default_session_factory`'s inner `_factory` sets
`state.evidence_prefix = case.id` right after building each case's session — so two cases sharing one
`run_dir` now write to `run_dir/<case_id_1>/01-....png` and `run_dir/<case_id_2>/01-....png` instead
of colliding on `run_dir/01-....png` twice. **No reader needed a change**: `run_dir / ev.path` (a
`pathlib.Path` division) resolves a case-id-prefixed relative path exactly like a bare filename, and
`report_export.py::png_base64`'s `candidate.is_relative_to(resolved_safe_root)` security check
already handles nested subdirectories — confirmed by reading `grade.py::_screenshot_paths`,
`routes_report.py`, and `report_export.py` end to end and by the fact that no test outside
`browser/`/`parallel_run.py` needed touching. `getattr(session, "state", None)` guards the factory's
new line defensively, so the pre-existing `FakeBrowserSession` test double (no `.state` attribute) in
`test_parallel_run.py` keeps passing unmodified.

**Failure 2, quoted verbatim (checker):**
> `[PR6 reporting / AT-568 fallback] sev: medium · a grader/provider exception after run_case
> COMPLETED makes run_cases replace the real RawResult with outcome=errored; grade_errored_result
> then records "not judged: execution errored" and the run view shows "no screenshots captured" --
> the real outcome and step evidence are discarded and the failure is misattributed to execution. ·
> fix: in _run_and_grade, run the case and capture its RawResult first, then grade; on a grader
> error keep the real RawResult and save an INCONCLUSIVE verdict naming the grader failure. · issue:
> AT-573`

**Fix (AT-573):** new `stages/run_case_pipeline.py::run_and_grade_case_resilient(case, session,
judge, run_id, store)` — calls `run_case` first (unconditionally, exactly like `run_and_grade_case`),
then wraps only the rubric-resolution + `grade()` call in `try/except Exception`. On success it
behaves identically to `run_and_grade_case`. On a grader/provider exception, `result` (the real,
already-produced `RawResult`, with its real evidence) is still returned, paired with a
`Verdict(result=Result.INCONCLUSIVE, grader_provider="rule", scoreboard="not judged: the grader
failed after execution completed", note=f"{type(exc).__name__}: {exc}")` naming the failure — never
propagating up into `run_cases`'s own exception handling, which is exactly the path that used to
manufacture a synthetic `ERRORED` `RawResult` with no evidence (T-173's `_run_one`). `ui/
routes_runs.py::_run_cases_in_parallel`'s `_run_and_grade` closure now calls
`run_and_grade_case_resilient` instead of `run_and_grade_case` — the ONLY call site changed; the
serial route (`_run_cases_serially`, `_run_entry_case`) still calls the plain `run_and_grade_case`
directly, unchanged, since a grader failure there was never routed through `run_cases`'s
result-discarding exception path to begin with.

**TDD, both shown red first on the actual code:**
- `tests/test_parallel_run_evidence_namespace.py` (new; split from `test_parallel_run.py` at the
  300-line cap) — two cases with different first pages driven through the real
  `default_session_factory` one after another (mirroring how `run_cases` actually drives them);
  shown red on pre-fix code via `git stash` (`assert '01-step01-navigate.png' !=
  '01-step01-navigate.png'`, the exact live-run collision), green after. A second test pins the
  serial path's bare-filename behaviour as unaffected.
- `tests/test_run_case_pipeline_resilient.py` (new; split from `test_run_case_pipeline.py` at the
  300-line cap) — a `MockProvider(responses={})` (its `.judge()` raises `ProviderError` exactly like
  a real provider failure) drives `run_and_grade_case_resilient` directly: shown red pre-fix via
  `git stash` (`ImportError: cannot import name 'run_and_grade_case_resilient'` — the function did
  not exist at all before this cycle), green after, asserting `result.outcome is COMPLETED`,
  `result.evidence` is non-empty, and the verdict is `INCONCLUSIVE`/`"rule"` naming the
  `ProviderError`. A second test pins the happy-path (grading succeeds) as behaviourally identical to
  `run_and_grade_case`.
- Three pre-existing tests that monkeypatched the old `run_and_grade_case` module-level name inside
  the PARALLEL route (`_run_cases_in_parallel` no longer calls it — only `run_and_grade_case_resilient`
  does) were updated to monkeypatch the new name:
  `test_ui_runs_parallel_trace.py::test_with_max_parallel_2_two_cases_run_concurrently`,
  `test_ui_runs_parallel_crash_recovery.py::test_a_session_factory_crash_for_one_case_still_saves_
  every_case_and_the_run`, and that same file's second test — **repurposed**, not just renamed: its
  original scenario ("`run_and_grade_case` itself raises for one case, e.g. a grader/provider
  error") is factually superseded by the AT-573 fix (that exact shape no longer reaches this
  fallback at all — it is now caught INSIDE `run_and_grade_case_resilient` and produces
  COMPLETED+INCONCLUSIVE, not ERRORED). Renamed to
  `test_run_and_grade_case_resilient_itself_raising_still_saves_every_case_and_the_run` — a genuine
  AT-568-defense-in-depth case (the wrapper itself raising unexpectedly, a bug in it rather than a
  grader error inside it) — and its module docstring updated to point at
  `test_run_case_pipeline_resilient.py`/`test_ui_runs_parallel_trace.py` for the actual AT-573
  behaviour. The three serial-path tests in `test_ui_runs_parallel_trace.py` that use
  `max_parallel=1` (default) were NOT touched — the serial route never called
  `run_and_grade_case_resilient` and still doesn't.

**Capability rows for both in Capability coverage below.**

**Doctor finding from Fix cycle 2 (`ledger-row-lost` x6): resolved by the master merge, not by this
cycle's own diff** — AT-571 landed on master before this merge and fixed `ledger/checks.py`'s
field-order-sensitive regex; `uv run autotester doctor` is clean this cycle (see Actual outputs).

## What the two goal-coverage gaps were

- **AT-562:** `stages/parallel_run.py::run_cases` (T-173) PASSed at unit level, but nothing in
  `src/` outside its own test suite called it. No real run could execute cases in parallel or
  record `Run.parallel_n`/`parallel_bound_by`.
- **AT-564:** the only trace writer is `stages/orchestrate.py`'s `StageContext`/`run_or_resume`
  (D-041), and nothing outside `stages/orchestrate*.py` constructed a `StageContext`. A real
  CLI/UI run wrote no `trace.jsonl`, so T-172's run-view trace card had nothing to show for a real
  run.

**Live entry point found:** `ui/routes_runs.py::trigger_run` (`POST /projects/{slug}/run`) — the
**only** live case-execution path in the whole repo. There is no `autotester run` CLI command
(`cli.py` has no `@app.command("run")`; `cli_crawl.py`'s `explore_cmd` drives DISCOVER, not
EXECUTE). Wiring `run_or_resume`'s full learn/explore pipeline in here would have been a much
larger redesign than these two issues ask for (this route already has its cases via a prior
EXPAND, and its entry-case/shared-session model predates the orchestrator) — per the brief's own
"if wiring the whole orchestrator turns out to be larger than these issues imply, STOP and build
the smallest safe slice", the slice built is exactly the one the brief itself named as an example:
*"the execute path builds a StageContext with secrets and writes a trace, and runs cases via
run_cases with n from plan_parallel_run."*

## What changed

- **`src/autotester/ui/routes_runs.py`** (238 lines, was 123)
  - `trigger_run` (:186-213, was :80-122) now:
    1. builds `ctx = StageContext(store=store, run_id=run_id, secrets=secrets)` — the project's
       **real** `SecretStore`, not a fixture — so the auto-built trace's redactor is real (AT-564,
       RT6; without `secrets=` the writer falls back to an unredacted `Redactor({})`, AT-561);
    2. attaches it to the judge provider (`judge.trace = ctx.trace`) so every LLM call the judge
       makes during grading joins this run's trace (RT4/RT5 — the only span-append site stays
       `Provider.record()`, nothing here writes a span itself);
    3. calls `plan_parallel_run(project)` (T-173) **before any case executes**, and always records
       the result — `Run.parallel_n=plan.n`, `Run.parallel_bound_by=plan.bound_by` — on every run,
       serial or not (AT-562, PR1);
    4. records one `StageSpan` for `StageName.EXECUTE` (`started`/`finished` wrapping the whole
       batch) once the cases are done (RT3 — a coarse span; see Gaps).
    Steps 1-4 live in the new `_execute_with_trace` (:155-179), extracted so `trigger_run` itself
    stays under the 50-line/function cap (C2); `trigger_run` calls it at :207-209.
  - New `_run_cases_serially(...)` (:88-114) — **the pre-existing behaviour, byte-for-byte, only
    moved into its own function.** One shared `BrowserSession` reused across every non-entry case
    (login continuity), one dedicated wiped profile per entry case (AT-044). Used whenever
    `plan.n <= 1` — the default (`Project.max_parallel=1`).
  - New `_run_cases_in_parallel(...)` (:119-153) — used only when `plan.n > 1`. Entry cases still
    run first, serially, each on its own dedicated wiped profile via the existing
    `_run_entry_case` (unchanged). Non-entry cases then fan out through
    `stages.parallel_run.run_cases(normal_cases, plan, session_factory, _run_and_grade)`
    (call at :152), with `session_factory = default_session_factory(project, secrets, run_dir)`
    (T-173's own isolated per-case `BrowserSession`, PR2) and `_run_and_grade` (:144-147) wrapping
    `run_and_grade_case` (a closure capturing each case's `Verdict` in a dict, since `run_cases`'s
    `RunFn` only returns `RawResult`).
  - Imports added: `StageCheckpoint`, `StageName` (schema.run_state); `StageContext`
    (stages.orchestrate); `ParallelPlan`, `default_session_factory`, `plan_parallel_run`,
    `run_cases` (stages.parallel_run).

- **`src/autotester/stages/parallel_run.py`** (AT-565, scope-add)
  - `_run_one` (:178-205): `session = session_factory(case)` used to sit **above** the
    `try`/`except` that guards `run_fn` — so a real `BrowserSession.start()` raising under N-way
    concurrency (exactly what `default_session_factory` now drives live, per the change above)
    propagated straight out of `run_cases`'s `[f.result() for f in futures]`, discarding every
    sibling's already-finished result instead of reporting just that one case as `ERRORED` (PR6).
    Fixed by moving the assignment inside the guarded region (`session: object | None = None`,
    then `session = session_factory(case)` as the try's first line); `finally` now closes it only
    `if session is not None`.

- **Tests (new files, split from the two files these tests naturally extend, at doctor's
  300-line cap — see "Split rationale" below):**
  - `tests/test_ui_runs_parallel_trace.py` — drives the REAL `/projects/{slug}/run` route (fakes:
    `BrowserSession.start`/`close`, `run_and_grade_case`, `LangChainFallbackProvider`; a temp
    project root via `AUTOTESTER_ROOT`, never the real `.env`/`projects/`):
    - `test_a_real_run_writes_a_trace_with_at_least_one_span` — asserts `trace.jsonl` exists and
      carries exactly one `kind="stage"` span, `stage="execute"`, `status="done"` (distinct from
      the `kind="llm_call"` span the fake grading call also leaves via `judge.record(...)`).
    - `test_a_declared_fake_secret_never_appears_raw_in_the_trace` — declares a fake `SecretRef`,
      writes its value to a temp `.env`, drives a fake LLM call whose `fed_id` embeds it; asserts
      the raw value never reaches `trace.jsonl` and `"REDACTED"` does.
    - `test_run_records_parallel_n_and_bound_by_even_when_serial` — default project
      (`max_parallel=1`): asserts the persisted `Run` has `parallel_n == 1` and a `parallel_bound_by`
      in `{"config","budget","write_policy"}`.
    - `test_with_max_parallel_2_two_cases_run_concurrently` — `max_parallel=2`, `plan_parallel_run`
      monkeypatched to a fixed `ParallelPlan(n=2, bound_by="config", ...)` (the plan's own
      RAM/CPU measurement is `test_parallel_run.py`'s concern, not this wiring test's — never
      falsify against live host memory); two fake case runs record their own concurrency peak via
      a lock — asserts `peak == 2` and `Run.parallel_n/parallel_bound_by == (2, "config")`.
  - `tests/test_parallel_run_session_crash.py` — the AT-565 regression:
    `test_pr6_a_session_factory_that_raises_for_one_case_does_not_abort_siblings` — a factory that
    raises for one of three cases; asserts that case is `ERRORED` with the raised exception's
    message, and the other two report their real outcomes.

**Split rationale (C2, 300-line file cap):** both host files
(`tests/test_ui_runs.py`, `tests/test_parallel_run.py`) were already near the cap; adding these
tests in place would have pushed them to 438 and 323 lines respectively. Split following the
repo's own established convention (`tests/test_execute_assertions.py`/`test_execute_new_actions.py`
importing shared fixtures from `test_execute.py`): the new files import `_onboard_demo`/
`_only_run_id` from `test_ui_runs` and `_case`/`_project` from `test_parallel_run`, and (for
`test_ui_runs_parallel_trace.py`) duplicate the `scratch_root`/`client` pytest fixtures exactly as
every other `test_ui_*.py` file in this repo already does (a pre-existing, accepted repo-wide
pattern, not something this unit introduces or is scoped to fix). `git diff` against `master`
confirms `tests/test_ui_runs.py` and `tests/test_parallel_run.py` are byte-identical to their
pre-unit state.

### Cycle 2 additions (AT-568, AT-569)

- **`src/autotester/stages/run_case_pipeline.py`** (134 lines, was 104)
  - `_rubric_for(case, store)` (:86-96, new) — extracted verbatim from `run_and_grade_case`'s own
    inline rubric lookup; `run_and_grade_case` (:100-113) now calls it instead of repeating the
    lookup (behaviour unchanged — same lines, moved).
  - `grade_errored_result(case, result, judge, run_id, store)` (:116-134, new) — grades a
    `RawResult` that never reached a `run_and_grade_case` call at all (AT-568), through the same
    `_rubric_for` + `grade()` path. See Fix cycle 2 above for why this is always safe.
- **`src/autotester/ui/routes_runs.py`** (250 lines, was 238)
  - `_run_cases_in_parallel` (:119-163, was :119-153): the blind `verdicts[result.case_id]` index
    is now `verdicts.get(result.case_id)`, falling back to `grade_errored_result(case_by_id[result
    .case_id], result, judge, run_id, store)` on a miss (:157-161).
  - Import line (:32) now also names `grade_errored_result`.
- **`src/autotester/providers/base.py`** (189 lines, was 176)
  - `Provider.__init__` (:42-56): new `self._usage_lock = threading.Lock()`.
  - `Provider.record` (:97-137, was :97-133): the whole accumulate-then-append-then-trace body is
    now inside `with self._usage_lock:` (:121-137).
  - `import threading` added.
- **Tests, new files (cycle 2 split, same convention as cycle 1):**
  - `tests/test_ui_runs_parallel_crash_recovery.py` — two route-level tests (session-factory crash;
    `run_and_grade_case` raise), imports `client`/`scratch_root`/`_non_entry_case` from
    `test_ui_runs_parallel_trace` (that file's own module-level `__all__` marks the two fixtures as
    intentional re-exports, matching `test_ui_requests.py`'s pre-existing import of `client`/
    `scratch_root` from `test_ui_learn`).
  - `tests/test_provider_record_concurrency.py` — two thread-hammer tests for `Provider.record`.
  - `tests/test_run_case_pipeline.py` gains `test_grade_errored_result_never_calls_the_judge` and
    `test_grade_errored_result_builds_and_persists_the_same_default_rubric` (in place, +38 lines).

### Cycle 3 additions (AT-572, AT-573)

- **`src/autotester/browser/session.py`** (300 lines, was 293 — exactly at the C2 cap; the
  `settle()`/`assert_expected()` docstrings were compressed to reclaim lines without dropping any
  fact they recorded, AT-045/AT-046/E5/D-032/AT-540/C7 all still named)
  - `SessionState` gains `evidence_prefix: str = ""` (new field, docstring explains AT-572).
  - `screenshot()` (:266-287): computes `rel` as a prefix-joined path when `evidence_prefix` is set,
    else the unchanged bare `name`; `full.parent.mkdir(parents=True, exist_ok=True)` added so the
    per-case subdirectory always exists before the write; `_record(..., rel, ...)` replaces the old
    `_record(..., name, ...)`.
- **`src/autotester/stages/parallel_run.py`** (258 lines)
  - `default_session_factory`'s inner `_factory` (AT-572): `state.evidence_prefix = case.id` set on
    the session's `SessionState` right after `build(...)`, guarded by `getattr(session, "state",
    None)` so a test double without `.state` never breaks. Docstring updated.
- **`src/autotester/stages/run_case_pipeline.py`** (166 lines, was 134)
  - New `run_and_grade_case_resilient(case, session, judge, run_id, store)` (:117-146, AT-573) — see
    Fix cycle 3 above. `run_and_grade_case` itself is untouched.
  - `from autotester.schema.enums import Result` import added (already had `Outcome`/`Result` via
    other imports in this file's siblings; this file specifically needed `Result.INCONCLUSIVE`).
- **`src/autotester/ui/routes_runs.py`** (259 lines, was 250)
  - Import line: `run_and_grade_case_resilient` added alongside `grade_errored_result`,
    `run_and_grade_case`.
  - `_run_cases_in_parallel`'s `_run_and_grade` closure (:149-156): now calls
    `run_and_grade_case_resilient` instead of `run_and_grade_case` — the only call-site change.
- **Tests, new files (cycle 3 split, same convention as cycles 1-2):**
  - `tests/test_parallel_run_evidence_namespace.py` — two tests: distinct-namespace-per-case (AT-572)
    and serial-path-unaffected.
  - `tests/test_run_case_pipeline_resilient.py` — two tests: grader-raises-after-COMPLETED keeps the
    real result (AT-573) and the happy path matches `run_and_grade_case`.
  - `tests/test_ui_runs_parallel_crash_recovery.py` — test 1 renamed fake/monkeypatch target to
    `run_and_grade_case_resilient` (behaviour unchanged); test 2 repurposed as described in Fix cycle
    3 above (module docstring updated to match).
  - `tests/test_ui_runs_parallel_trace.py` — `test_with_max_parallel_2_two_cases_run_concurrently`'s
    fake/monkeypatch target renamed to `run_and_grade_case_resilient` (behaviour unchanged; this test
    exercises `max_parallel=2` so it goes through the parallel route). The three `max_parallel=1`
    tests in this file were not touched.

## Design decisions and why (for the checker)

1. **`plan.n <= 1` is NOT routed through `run_cases`.** `run_cases`'s own contract (via `_run_one`)
   starts and closes one session per case — correct for real isolation at `n>1`, but reusing that
   contract for the pre-existing single-shared-session serial loop would tear the shared session
   down after the first case. Rather than hack a close-suppressing proxy around a session object
   `run_cases` was never designed to receive twice, the pre-existing serial loop is kept verbatim
   (moved, not rewritten) and used whenever `plan.n <= 1` — which is every project until a human
   explicitly sets `max_parallel > 1` (default `1`, `schema/project.py:133-137`). Zero behavioural
   change to the default, overwhelmingly common path.
2. **Entry cases (AT-044) always run serially, before the fan-out**, in both branches — an
   entry-screen assertion is about one genuinely-logged-out state, not something concurrency
   helps, and this preserves the existing dedicated-wiped-profile guarantee unconditionally.
3. **`RunApproval`/consent is not newly gated here.** `trigger_run` consulted no `RunApproval`
   before this unit either (confirmed: `grep -n "RunApproval\|require_approval" ui/routes_runs.py`
   returned nothing pre-unit) — this unit does not invent a new gate. `run_cases` is called with
   `approval=None` (its default), so its internal `RunBudget` is unlimited — i.e., parallel width
   cannot multiply a budget that this route did not enforce to begin with. Wiring D-018 consent
   into this route is a separate, larger unit than these two goal-coverage gaps ask for.
4. **The EXECUTE stage span is coarse** — one span wrapping the whole case batch (run + grade for
   every case), not one span per pipeline sub-stage. `run_and_grade_case` bundles execute+grade in
   one call with no seam between them at this route's level; splitting that seam is out of scope
   for these two issues and is recorded under Gaps.

## How to verify (commands + expected)

- `uv run pytest tests/test_ui_runs.py tests/test_ui_runs_parallel_trace.py tests/test_ui_runs_parallel_crash_recovery.py tests/test_run_case_pipeline.py tests/test_run_case_pipeline_resilient.py tests/test_parallel_run.py tests/test_parallel_run_session_crash.py tests/test_parallel_run_evidence_namespace.py tests/test_provider_record_concurrency.py` → exit 0 (cycle-3 targeted set)
- `uv run ruff check src tests scripts` → exit 0
- `uv run autotester doctor` → `doctor: clean` (the 6 cycle-2 `ledger-row-lost` false positives are
  gone post-merge — AT-571 fixed the root cause on master)
- Full non-browser suite (`uv run pytest` with the browser-launching files `--ignore`d) and the Mode
  D own smoke, both once RAM/exclusivity allowed — see below.

## Actual outputs (from maker's own run)

```
$ uv run pytest tests/test_ui_runs.py tests/test_ui_runs_parallel_trace.py tests/test_ui_runs_parallel_crash_recovery.py tests/test_parallel_run.py tests/test_parallel_run_session_crash.py tests/test_provider_record_concurrency.py tests/test_run_case_pipeline.py tests/test_run_trace.py tests/test_orchestrate.py tests/test_orchestrate_runners.py tests/test_execute.py tests/test_execute_assertions.py tests/test_execute_new_actions.py tests/test_consent.py tests/test_approval_signing.py
110 passed, 15 warnings in 5.60s
(warnings are all the pre-existing, expected AT-561 RuntimeWarning from fixture StageContexts in
test_orchestrate.py/test_orchestrate_runners.py that intentionally declare no secrets)

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
ledger-row-lost: qa/manifests/at562-564-live-wiring.md — AT-568 is named here but has no row in qa/issues.jsonl
ledger-row-lost: qa/manifests/at562-564-live-wiring.md — AT-569 is named here but has no row in qa/issues.jsonl
ledger-row-lost: qa/manifests/at562-564-live-wiring.md — AT-570 is named here but has no row in qa/issues.jsonl
ledger-row-lost: qa/verdicts/at562-564-live-wiring.md — AT-568 is named here but has no row in qa/issues.jsonl
ledger-row-lost: qa/verdicts/at562-564-live-wiring.md — AT-569 is named here but has no row in qa/issues.jsonl
ledger-row-lost: qa/verdicts/at562-564-live-wiring.md — AT-570 is named here but has no row in qa/issues.jsonl
6 violation(s)
```
(all 6 are the same pre-existing checker-tooling bug disclosed in Fix cycle 2 above — the 3 against
the verdict file were already present right after the master merge, before this cycle's own code
changed a single line; the 3 against this manifest appear only because this manifest's own required
"Issues addressed" header names the same issue ids, which every manifest must do. Not touched, per
this cycle's explicit no-ledger-edit instruction)

**`Provider.record` concurrency test, reliability measured (not just asserted):** run 5 times
locked, 5/5 green; the same test on the pre-fix (unlocked) code, run 15 times via the full file,
15/15 red (see Capability coverage row 7 for the tuning that got there).

**Full `uv run pytest` (whole suite, 16 browser-launching files excluded — this project has no
registered pytest marker, so "the project's equivalent" of `-m "not live"` is `--ignore`ing every
test file matched by `grep -rl "BrowserSession(\|sync_playwright\|playwright.sync_api" tests/test_*.py`),
under the same RAM gate:**

**GAP this cycle: the 60-minute cap elapsed without the full suite ever running.** A background
poller measured real `GlobalMemoryStatusEx` free RAM every 300s for the full hour; this machine was
persistently RAM-constrained throughout this fix cycle (a second, unrelated poller was running the
Mode D live-browser gate concurrently, and other processes on this shared host never fully freed
up):

```
07:36:26 free_gb=2.14   08:06:28 free_gb=2.96   08:31:31 free_gb=1.30
07:41:26 free_gb=2.88   08:11:29 free_gb=3.15   08:36:31 free_gb=3.50 (0.004 GB short; deadline
07:46:27 free_gb=3.25   08:16:29 free_gb=2.84                          had already passed by then)
07:51:27 free_gb=3.22   08:21:29 free_gb=2.84
07:56:28 free_gb=2.90   08:26:30 free_gb=2.50
08:01:28 free_gb=2.31
GAP: 60 minutes elapsed without RAM/exclusivity conditions being met -- declaring as a gap
```

No other `D:/autoTesting` pytest process was ever detected — exclusivity was never the blocker,
free RAM was, and it came within 4 MB of the threshold at the very last check, one poll cycle after
the deadline. Not fabricated or approximated: this cell is left as a genuine gap rather than pasting
a number that was never actually produced this cycle.

**What DOES stand as verification this cycle**, in place of the full suite: the 15-file targeted run
above (110 passed, covering every file touched or newly added this cycle, plus every file the
cycle-1 checker's own re-run already covers), `ruff`/`doctor` clean (module 3 pre-existing
false positives), and cycle 1's own full-suite run three commits ago (`1552 passed, 5 skipped, exit
0`, `qa/manifests/at562-564-live-wiring.md`'s cycle-1 section) — against which this cycle's diff is
purely additive (two new functions, a lock, two new test files, two new tests in an existing file;
no existing function's signature or call sites outside `_run_cases_in_parallel`/`routes_runs.py`'s
own imports changed). The checker's own Mode A re-run (`qa/adapter.json` slot 1) is the actual gate
this needs to clear; flagging the gap honestly rather than asserting a result never observed.

### Cycle 3 actual outputs (AT-572, AT-573)

```
$ uv run pytest tests/test_ui_runs.py tests/test_ui_runs_parallel_trace.py tests/test_ui_runs_parallel_crash_recovery.py tests/test_run_case_pipeline.py tests/test_run_case_pipeline_resilient.py tests/test_parallel_run.py tests/test_parallel_run_session_crash.py tests/test_parallel_run_evidence_namespace.py tests/test_provider_record_concurrency.py
40 passed, 1 warning in 4.19s
(the one warning is the pre-existing starlette/anyio BlockingPortal DeprecationWarning, unrelated)

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```

**TDD red-first, confirmed on the actual code (not asserted):**
- `tests/test_parallel_run_evidence_namespace.py::test_default_session_factory_gives_each_case_its_own_evidence_namespace`
  — `git stash` (reverting `browser/session.py` + `stages/parallel_run.py`), red:
  `AssertionError: assert '01-step01-navigate.png' != '01-step01-navigate.png'`; `git stash pop`,
  green (2 passed).
- `tests/test_run_case_pipeline_resilient.py` (both tests) — `git stash` (reverting
  `stages/run_case_pipeline.py` + `routes_runs.py`), red: `ImportError: cannot import name
  'run_and_grade_case_resilient' from 'autotester.stages.run_case_pipeline'` (the function is new
  this cycle — there is no earlier version of it to regress to, so a hard collection error is the
  correct red); `git stash pop`, green (2 passed).

All 5 falsifications reproduced in throwaway copies outside the worktree
(`%TEMP%\claude\...\scratchpad\mutation-copy-565\` for AT-565's own fix,
`%TEMP%\claude\...\scratchpad\mutation-copy-routes\` for the four wiring tests) — never against the
bound worktree. Baseline asserted green before every edit; each edit reverted immediately after its
red run, suite re-confirmed green before the next row.

| # | Claim | Falsifying edit | Baseline | Result |
|---|---|---|---|---|
| 1 | AT-564/RT3: a real run's trace carries an EXECUTE stage span | `_execute_with_trace`: delete the `ctx.trace.record_stage(StageCheckpoint(stage=StageName.EXECUTE, ...))` call | `4 passed` (mutation-copy-routes) | RED — `assert [] == ['execute']` → reverted → `4 passed` |
| 2 | AT-564/AT-561/RT6: the project's real `SecretStore` is threaded into `StageContext`, so a declared secret is redacted | `StageContext(store=store, run_id=run_id, secrets=secrets)` → drop `secrets=secrets` | `4 passed` | RED — secret found raw in `trace.jsonl` (`'sk-fake-AT564-...' is contained here`), plus the AT-561 `RuntimeWarning` fires → reverted → `4 passed` |
| 3 | AT-562/PR1: every run records `Run.parallel_n`/`parallel_bound_by`, even the serial default | `store.save_run(Run(...))` → drop `parallel_n=plan.n, parallel_bound_by=plan.bound_by` | `4 passed` | RED — `assert None == 1` → reverted → `4 passed` |
| 4 | AT-562/PR1-PR2: `max_parallel=2` actually fans cases out through `run_cases`, not just records a wider N | `if plan.n > 1:` → `if False and plan.n > 1:` | `4 passed` | RED — `assert 1 == 2` (peak concurrency) → reverted → `4 passed` |
| 5 | AT-565/PR6: `session_factory`'s own raise is caught and reported as that case's ERRORED outcome, not propagated | `_run_one`: move `session = session_factory(case)` back above the `try` | `11 passed` (test_parallel_run.py, pre-split) | RED — `RuntimeError: boom starting the session` propagates out of `run_cases` uncaught → reverted → `11 passed` |

Row 5 was additionally shown red on the **unmodified pre-fix code** at the point AT-565 was filed
(before any fix was applied), reproduced verbatim in `mutation-copy-565`:
```
$ uv run pytest tests/test_parallel_run.py::test_pr6_a_session_factory_that_raises_for_one_case_does_not_abort_siblings
...
E           RuntimeError: boom starting the session
1 failed in 0.39s
```
then green after the real fix landed (`11 passed in 1.26s`).

### Cycle 2 rows (AT-568, AT-569)

Reproduced in `%TEMP%\claude\...\scratchpad\mutation-copy-c2\` (a fresh copy of the branch after
the master merge and after this cycle's fix already landed) — never against the bound worktree.
Baseline asserted green before every edit; each edit reverted immediately after its red run, the
relevant file re-confirmed byte-identical to the worktree (`diff` exit 0) after every revert.

| # | Claim | Falsifying edit | Baseline | Result |
|---|---|---|---|---|
| 6 | AT-568/PR6: a `session_factory` crash or a `run_and_grade_case` raise for one case still saves every result+verdict+the Run | `_run_cases_in_parallel`: revert `verdicts.get(result.case_id)` + `grade_errored_result(...)` fallback back to the blind `verdicts[result.case_id]` | `2 passed` (`test_ui_runs_parallel_crash_recovery.py`) | RED — both tests: `KeyError: 'case_...'` at `routes_runs.py:153` → reverted → `2 passed` |
| 7 | AT-569: `Provider.record()` loses no increments and makes no duplicate role row under N-way concurrency | `record()`: remove the `with self._usage_lock:` wrapper (dedent the body back to unguarded) | `2 passed` (`test_provider_record_concurrency.py`, locked) | RED — reliably: measured 15/15 full-file runs failing unlocked (`AssertionError` on either the duplicate-row count or the exact-calls total) vs 8/8 passing locked. Tuned to `_TRIALS = 50` independent races per test after measuring a single untrialed race is flaky (~1-in-6 to 1-in-8 false green) — the repeated-trials structure is itself what makes this row's RED reliable, not a lucky seed → reverted → `2 passed` |
| 8 | `grade_errored_result` never reaches the judge for an ERRORED result | force `result.outcome` to `COMPLETED` before calling `grade()` inside `grade_errored_result` | `11 passed` (`test_run_case_pipeline.py`) | RED — `ProviderError: mock provider has no queued response for role=judge` (the judge WAS reached) → reverted → `11 passed` |
| 9 | `grade_errored_result` persists a rubric through the same seam a normal run uses | `_rubric_for`: drop the `store.save_rubric(rubric)` call on the lazily-built default | `11 passed` | RED — 3 failures: the new test plus 2 pre-existing tests sharing the same seam (`test_run_and_grade_case_builds_and_persists_a_default_rubric_when_none_exists`, `test_a_case_whose_rationale_changed_gets_a_regenerated_default_rubric`) → reverted → `11 passed` |

Row 7's reliability tuning, measured directly (not asserted): a single race at `n_threads=50,
calls_per_thread=40` with no repeated trials caught the unlocked bug only ~1-in-6 to 1-in-8 runs
via `uv run pytest` (high scheduler-timing variance observed even at `n_threads=100-300`); wrapping
the same race in a loop of independent trials per test, with both tests in the file summing to 100
trials per full-file run, brought it to 15/15 — the manifest's own claim is about the FULL FILE as
shipped, which is what `qa/adapter.json`'s slot-1 (`uv run pytest`, no per-file selection) actually
runs.

### Cycle 3 rows (AT-572, AT-573)

Reproduced in fresh throwaway copies (`src`+`tests`+`scripts`, never `.venv` — the shared venv's
python was invoked with `PYTHONPATH` pointed at the copy's `src`, so only the `autotester` package
itself resolved to the mutated copy) at `%TEMP%\claude\...\scratchpad\mutation-at572\` and
`\mutation-at573\` — never against the bound worktree. Baseline asserted green before every edit;
each edit reverted immediately after its red run, the mutated file re-confirmed byte-identical to
the worktree (`diff` exit 0) after every revert.

| # | Claim | Falsifying edit | Baseline | Result |
|---|---|---|---|---|
| 10 | AT-572/PR2: `default_session_factory` gives each parallel case's session its own evidence namespace, so two cases never collide on the same screenshot filename | `browser/session.py::screenshot()`: `rel = f"{self.state.evidence_prefix}/{name}" if self.state.evidence_prefix else name` → `rel = name` (ignore the prefix unconditionally) | `2 passed` (`test_parallel_run_evidence_namespace.py`) | RED — `assert '01-step01-navigate.png' != '01-step01-navigate.png'`, the exact live-run collision the checker's Mode D run hit → reverted → `2 passed`, `diff` clean |
| 11 | AT-573: `run_and_grade_case_resilient` keeps the real COMPLETED result (and its evidence) when only the grader fails after execution, downgrading just the verdict to INCONCLUSIVE | `run_case_pipeline.py::run_and_grade_case_resilient`: delete the `try/except Exception` wrapper around the rubric+grade call (grading now propagates uncaught, exactly like the pre-AT-573 shape `run_cases` used to catch and discard) | `2 passed` (`test_run_case_pipeline_resilient.py`) | RED — `autotester.providers.base.ProviderError: mock provider has no queued response for role=judge` propagates uncaught out of the function instead of becoming an INCONCLUSIVE verdict → reverted → `2 passed`, `diff` clean |

## Live browser evidence

**Cycle 1: SKIPPED** (free RAM 2.09-2.55 GB at the time, not polled to a cap).

**Cycle 2: Mode D is mandatory per the coordinator's brief — attempted properly this time, still
SKIPPED after the full 45-minute cap.** Prepared in advance so the attempt could fire the instant
conditions allowed: an isolated `AUTOTESTER_ROOT`, a `demo` project pointed at
`tests/fixtures/crawl_site` served locally, `max_parallel=2`, two real cases, a declared fake
secret, and only the JUDGE provider faked (a `MockProvider` returning pre-seeded PASS judgments,
monkeypatched onto `routes_runs_module.LangChainFallbackProvider` in-process before `uvicorn.run` —
never the real `.env`, never a real model call) — everything else (`StageContext`+secrets,
`plan_parallel_run`, the real `run_cases` fan-out, `grade_errored_result`, a real `BrowserSession`
driving real Chromium) would have been the actual production code.

A background poller measured real `GlobalMemoryStatusEx` free RAM every 300s for the full 45-minute
cap and never once reached the ≥3.5 GB floor `stages/parallel_run.py::_RAM_FLOOR_MB` itself reserves
before spending RAM on browser contexts — it came close three times (3.35, 3.22, 3.19, 3.16 GB)
but never sustained it long enough for the launcher's own check to catch it:

```
07:36:19 free_gb=2.23   07:51:20 free_gb=3.19   08:06:21 free_gb=2.93
07:41:19 free_gb=2.94   07:56:20 free_gb=2.70   08:11:21 free_gb=3.16
07:46:19 free_gb=3.35   08:01:21 free_gb=2.55   08:16:21 free_gb=2.57
                                                 08:21:22 free_gb=2.87
GAP: 45 minutes elapsed without RAM/exclusivity conditions being met -- SKIP live-browser smoke
```

No other `D:/autoTesting` pytest process was ever detected during the poll (so exclusivity was
never the blocker — free RAM was). Per the coordinator's explicit instruction ("Only if free RAM
≥3.5 GB; poll every 300 s, max 45 min, else SKIP with measurements"), this is disclosed as a SKIP
with full measurements, not fixed or faked. No `qa/evidence/browser-at562-564-live-wiring-*`
directory was created this cycle, since no browser was ever actually launched — writing an empty or
synthetic `report.json` would misrepresent a smoke that did not happen. The checker's own verdict
already says it "will do its own Mode D regardless," which is the backstop this SKIP defers to.

**Cycle 3: attempted, but declared SKIP — the host went RAM-unstable mid-attempt, not a controlled
pass.** A background poller cleared the ≥3.5 GB floor twice (4.33 GB, then 3.81 GB) and the own-smoke
script ran for real against a locally-served fixture site with an in-process mock judge (real
Chromium, real `uvicorn`, the actual `/projects/{slug}/run` route) — the first real run did show
`AT-572` holding (two distinct screenshot paths, `01-step01-navigate.png` and
`case_a944c0957ada/01-step01-navigate.png`, disjoint), but the attempt's own AT-573 assertions had a
bug (comparing `Result.INCONCLUSIVE`/`Result.PASS` against the wrong-case string literals
`"inconclusive"`/`"pass"` instead of `"INCONCLUSIVE"`/`"PASS"`), so a clean run was never actually
banked before free RAM fell to 0.67 GB on a re-run (a second attempt also hit an unrelated
`playwright`-in-asyncio-loop error on the entry-case path, and `plan_parallel_run`'s own real
measurement dropped the plan to serial `n=1` once RAM was low, which is not the shape AT-572/AT-573
need to see exercised). Per the coordinator's direction, this is disclosed as a SKIP rather than
asserting a clean result that was never actually observed — the checker's own Mode D is the real
gate. No lingering process from this attempt was left running (confirmed: no `python.exe` matching
`mode_d_smoke`/`uvicorn`/`scratchpad` after the fact); the elevated Chrome count on the host is the
user's own browser, not touched.

## Gaps (disclosed, not fixed here)

1. **No CONTROLLED, clean live-browser smoke of `routes_runs.py`'s changed code paths, across all
   three cycles** — cycles 1-2 were RAM-gated the full cap with no attempt possible; cycle 3's own
   attempt DID launch a real browser twice (see Live browser evidence above) and its first run showed
   AT-572 genuinely holding live, but the host went RAM-unstable (0.67 GB free) before a clean
   PASS/FAIL could be banked, so this is disclosed as SKIP rather than an asserted result. All
   verification here is otherwise through `TestClient` + mocked `BrowserSession`/`run_and_grade_case`
   (or `run_and_grade_case_resilient`). The checker's own Mode D is the real gate for this route.
2. **The EXECUTE stage span is coarse** (design decision 4 above) — one span for the whole
   run+grade batch, not a separate span per case or per execute/grade sub-phase. If a future unit
   wants per-case or execute-vs-grade trace granularity through this route, `run_and_grade_case`
   needs its own seam between `run_case` and `grade` first.
3. **`RunApproval`/D-018 consent is still not consulted by `trigger_run`** (pre-existing, confirmed
   absent before this unit too — design decision 3). This route can still launch a real browser
   against a real project with no human-granted approval on disk. Flagging for a future unit; not
   introduced or worsened by AT-562/AT-564/AT-565.
4. ~~`_run_cases_in_parallel`'s per-case `Verdict` capture (`verdicts: dict[str, Verdict]`) is not
   thread-locked.~~ **Adjudicated by the checker (cycle 1), not fixed as a gap:** "each worker
   writes only its own key and a dict store is atomic under the GIL, so the dict itself is fine;
   the defect is the MISSING keys" — i.e. this was never the real bug; AT-568 (the missing-key
   `KeyError`) was, and is now fixed. Struck through rather than deleted so the cycle-1 self-report
   and its correction both stay visible.
5. **`RunApproval`/D-018 consent (AT-570, medium, filed by the checker cycle 1) is still not
   consulted by `trigger_run`.** Confirmed by the checker as pre-existing and explicitly deferred
   to T-122's live-case gate (qa/contracts/consent.md "Out of scope"); listed in this manifest's
   header as NOT addressed this cycle, on the checker's own instruction (only AT-568/AT-569 were
   dispatched). `RunBudget(None)` stays unbounded for an opted-in `max_parallel > 1` fan-out until
   T-122 lands.
6. ~~The doctor `ledger-row-lost` false positive~~ (Fix cycle 2 above) is disclosed, not fixed — fixing
   it means editing `qa/issues.jsonl` or `ledger/checks.py`, both off-limits this cycle. **Resolved
   this cycle by the master merge, not by this unit's diff:** AT-571 landed on master and fixed
   `ledger/checks.py`'s regex; `doctor: clean` post-merge (Cycle 3 actual outputs). Struck through
   rather than deleted so the history stays visible.
7. **AT-572, AT-573 (cycle 3): fixed and TDD-verified, see Fix cycle 3 above.** No new gap opened by
   either fix — no reader needed a change for AT-572 (confirmed by reading `grade.py`,
   `routes_report.py`, `report_export.py`), and AT-573's only call-site change is the parallel
   route's `_run_and_grade` closure.
8. **The full non-browser `uv run pytest` suite did not run this cycle either.** A background poller
   ran the whole cycle, RAM never sustained ≥3.5 GB long enough before the cap elapsed (dipping as low
   as 0.67-1.14 GB while the Mode D attempt above was in flight). The 8-file targeted run (40 passed,
   Cycle 3 actual outputs), `ruff`/`doctor` clean, and cycle 1's own full-suite run (1552 passed, 5
   skipped) stand in its place; the checker's own re-run is the real gate.

## What changed (files touched)

- `src/autotester/ui/routes_runs.py` (cycle 3: `_run_and_grade` calls `run_and_grade_case_resilient`)
- `src/autotester/stages/parallel_run.py` (cycle 3: `default_session_factory` sets `evidence_prefix`)
- `src/autotester/stages/run_case_pipeline.py` (cycle 2; cycle 3: `run_and_grade_case_resilient`)
- `src/autotester/browser/session.py` (new this cycle: `SessionState.evidence_prefix`, `screenshot()`)
- `src/autotester/providers/base.py` (cycle 2)
- `tests/test_ui_runs_parallel_trace.py` (new, cycle 1; cycle 3: one monkeypatch target renamed)
- `tests/test_parallel_run_session_crash.py` (new, cycle 1)
- `tests/test_ui_runs_parallel_crash_recovery.py` (new, cycle 2; cycle 3: test 1 monkeypatch target
  renamed, test 2 repurposed, module docstring updated)
- `tests/test_provider_record_concurrency.py` (new, cycle 2)
- `tests/test_run_case_pipeline.py` (cycle 2, +2 tests)
- `tests/test_parallel_run_evidence_namespace.py` (new, cycle 3)
- `tests/test_run_case_pipeline_resilient.py` (new, cycle 3)

## Status: checked-PASS (qa/verdicts/at562-564-live-wiring.md, Cycle checked: 3, f4451ee)
