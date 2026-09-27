# Manifest — at574-serial-resilience

**Contract:** qa/contracts/core-invariants.md (C7) + qa/contracts/parallel-run.md PR6 (the shape
this generalizes to the serial path) + qa/contracts/ui-run.md
**Issues addressed:** AT-574
**Date:** 2026-09-25
**Fix cycle:** 1 of 3
**Dual check:** no
**Executor:** claude-sonnet-subagent (maker build subagent)
**Branch/worktree:** `wave/at574-serial-resilience`, `D:/autoTesting/.worktrees/at574-serial-resilience`
**Commit:** `c0a11b4` (from master `5444604`)

## The bug

`ui/routes_runs.py::_run_cases_serially` (`plan.n <= 1`, the default path) called
`run_and_grade_case(case, session, judge, run_id, store)` for every non-entry case with no
exception handling at all — not even the AT-573 grader guard the parallel path already had. The
shared `_run_entry_case` helper (used by *both* the serial and parallel routes for entry-screen
cases) had the identical unguarded call. One grader/provider exception, or a crash inside
`run_case` itself, propagated straight out of `trigger_run` → 500: the remaining cases in the
batch never ran, `store.save_run(...)` was never reached, and any results already saved for
earlier cases in the loop were orphaned (no matching `Run` record).

## Fix

**`src/autotester/ui/routes_runs.py:55-76`** — new `_run_and_grade_resilient(case, session, judge,
run_id, store)`:
```python
try:
    return run_and_grade_case_resilient(case, session, judge, run_id, store)
except Exception as exc:  # AT-574: reported as this case's own ERRORED result
    result = RawResult(case_id=case.id, outcome=Outcome.ERRORED,
                        error=f"{type(exc).__name__}: {exc}")
    verdict = grade_errored_result(case, result, judge, run_id, store)
    return result, verdict
```
Calls the already-existing `run_and_grade_case_resilient` (AT-573, `stages/run_case_pipeline.py`),
which keeps the real `COMPLETED` `RawResult` and downgrades only the verdict to `INCONCLUSIVE`
when grading raises after execution finished. The outer `try/except` here is the new part: it
catches anything `run_and_grade_case_resilient` does **not** itself catch — chiefly a crash inside
`run_case` before that function ever captures a result — and reports it through the exact
`grade_errored_result` path (AT-568) the parallel route's own fallback already uses, so a
crashed case still gets a real `ERRORED` result and a graded verdict, never a bare exception.

- **`src/autotester/ui/routes_runs.py:91`** — `_run_entry_case` now calls
  `_run_and_grade_resilient(...)` instead of the bare `run_and_grade_case(...)`. This function is
  shared by both `_run_cases_serially` and `_run_cases_in_parallel`, so the entry-case path is now
  resilient on both routes, not just the serial one.
- **`src/autotester/ui/routes_runs.py:143`** — `_run_cases_serially`'s non-entry branch now calls
  `_run_and_grade_resilient(...)` instead of the bare `run_and_grade_case(...)`.
- **`src/autotester/ui/routes_runs.py:19,32-35`** — import swap: `Outcome` added (for the
  synthetic `ERRORED` result), `run_and_grade_case` dropped from the `stages.run_case_pipeline`
  import (no longer called anywhere in this file; still exported and used by CLI scripts that want
  the plain, self-grading path).
- **`src/autotester/ui/routes_runs.py:119-127, 236-240`** — two stale docstrings corrected
  (`_run_cases_serially` no longer says "UNCHANGED"; `trigger_run` no longer claims it calls
  `run_and_grade_case` for every route).
- **`_run_cases_in_parallel`, `stages/parallel_run.py`, `stages/run_case_pipeline.py` — untouched.**
  The parallel fan-out's own `_run_and_grade` closure already went through
  `run_and_grade_case_resilient` + `grade_errored_result` since AT-568/AT-573; this unit only
  brings the serial loop and the shared entry-case helper up to the same standard. No new pipeline
  function was created — `_run_and_grade_resilient` is a thin route-level composition of the two
  existing pipeline functions, mirroring the shape `stages/parallel_run.py::_run_one` already uses
  for the parallel path (its own per-case `try/except Exception` around a callable, reporting an
  `ERRORED RawResult`).

**Existing tests updated (same-shape rename, not new coverage):** four pre-existing tests in
`tests/test_ui_runs.py` (2), `tests/test_ui_runs_parallel_trace.py` (3, all exercising the serial
path with `max_parallel=1` despite the file's name) and `tests/test_coverage_wiring.py`'s
`_run_with_urls` helper (used by 4 tests) monkeypatched `routes_runs_module.run_and_grade_case` to
control the route's case outcome. Since the serial/entry-case call sites no longer reference that
name, these were renamed to patch `run_and_grade_case_resilient` instead — the same seam
`test_with_max_parallel_2_two_cases_run_concurrently` (the parallel-path test in the same file)
already patched. No assertion logic changed in any of them.

## What changed (files touched)

- `src/autotester/ui/routes_runs.py` — the fix (see above)
- `tests/test_ui_runs_serial_resilience.py` — **new**, 3 route-level regression tests (below)
- `tests/test_ui_runs.py` — 2 monkeypatch targets renamed (`run_and_grade_case` →
  `run_and_grade_case_resilient`), module docstring corrected
- `tests/test_ui_runs_parallel_trace.py` — 3 monkeypatch targets renamed, same reason
- `tests/test_coverage_wiring.py` — 1 monkeypatch target renamed (in the shared `_run_with_urls`
  helper), same reason

## New tests (TDD, red first on master `5444604`)

`tests/test_ui_runs_serial_resilience.py`, all driving the real `/projects/demo/run` route through
`TestClient`, faking `stages.run_case_pipeline.run_case` and `...grade` (not the resilient wrapper
itself — that keeps the real `run_and_grade_case_resilient`/`grade_errored_result` wiring under
test, not a re-implementation of it):

1. `test_a_grader_crash_for_one_of_three_serial_cases_still_saves_every_case_and_the_run` —
   grading raises for the middle of 3 serial cases; asserts all 3 results+verdicts saved, the
   crashed case keeps its real `COMPLETED` result with an `INCONCLUSIVE` verdict, its siblings keep
   `PASS`, and the `Run` is saved (303, not 500).
2. `test_a_run_case_crash_for_one_of_three_serial_cases_still_saves_every_case_and_the_run` —
   `run_case` itself raises for the middle case; asserts that case is `ERRORED` with the crash
   message in `.error`, its siblings keep their real `COMPLETED`/`PASS` outcomes, and the `Run` is
   saved.
3. `test_an_entry_case_crash_still_saves_every_case_and_the_run` — `run_case` raises for the
   dedicated entry-screen case; asserts the entry case is `ERRORED`, the other (non-entry) case
   keeps its real outcome, and the `Run` is saved.

**Red on unfixed code (master `5444604`, before the fix, verified before writing any fix code):**
```
FAILED tests/test_ui_runs_serial_resilience.py::test_a_grader_crash_for_one_of_three_serial_cases_still_saves_every_case_and_the_run
FAILED tests/test_ui_runs_serial_resilience.py::test_a_run_case_crash_for_one_of_three_serial_cases_still_saves_every_case_and_the_run
FAILED tests/test_ui_runs_serial_resilience.py::test_an_entry_case_crash_still_saves_every_case_and_the_run
3 failed, 1 warning in 10.40s
```
(all three failed with the unhandled `RuntimeError` propagating through `trigger_run` → 500,
exactly the bug's shape — traceback for the entry-case variant pasted in the build log, e.g.
`src\autotester\ui\routes_runs.py:69: in _run_entry_case … return run_and_grade_case(...) …
RuntimeError: boom entering`)

**Green after the fix:**
```
tests/test_ui_runs_serial_resilience.py ...                              [100%]
3 passed, 1 warning in 5.60s
```

## Verify — targeted (real worktree, `c0a11b4`)

```
$ uv run pytest tests/test_ui_runs_serial_resilience.py tests/test_ui_runs.py tests/test_ui_runs_parallel_trace.py tests/test_coverage_wiring.py tests/test_ui_runs_parallel_crash_recovery.py tests/test_run_case_pipeline.py tests/test_run_case_pipeline_resilient.py
....................................                                     [100%]
36 passed, 1 warning in 4.67s

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```

## Capability coverage (mutation, C7)

Never edited the worktree in place for this — a throwaway copy of `src/`, `tests/`, `scripts/`,
`pyproject.toml`, `uv.lock` (plus a placeholder `README.md` `pyproject.toml` needs to build) at
`%TEMP%\claude\d--autoTesting\<session>\scratchpad\at574-capability-copy`, `uv sync --frozen`'d
independently (own `.venv`), never touching the bound worktree or `origin`. **Baseline asserted
green first** (C7's baseline clause): `uv run pytest tests/test_ui_runs_serial_resilience.py
tests/test_ui_runs.py tests/test_ui_runs_parallel_trace.py tests/test_coverage_wiring.py
tests/test_ui_runs_parallel_crash_recovery.py` → `23 passed` before any mutation.

| # | Mutation (file, single-hunk) | Reverted behaviour | Kills (named, re-run confirmed) | Survives (named) |
|---|---|---|---|---|
| A | `routes_runs.py`: `_run_cases_serially`'s non-entry branch reverted to call the bare `run_and_grade_case` (import restored) instead of `_run_and_grade_resilient` | The pre-fix call site exactly — no grader guard, no run_case-crash guard, for the non-entry serial branch | `test_a_grader_crash_for_one_of_three_serial_cases_still_saves_every_case_and_the_run`, `test_a_run_case_crash_for_one_of_three_serial_cases_still_saves_every_case_and_the_run` (both: real pytest run, `2 failed`, failure tracebacks land in `_run_cases_serially` at the reverted line, attributed to the exact fake exception each test raises) | `test_an_entry_case_crash_still_saves_every_case_and_the_run` (untouched call site — `1 passed`) |
| B | `routes_runs.py`: `_run_and_grade_resilient`'s `try/except` removed — reduced to `return run_and_grade_case_resilient(...)` with nothing catching a `run_case` crash | The new outer guard this unit adds, for both callers of `_run_and_grade_resilient` | `test_a_run_case_crash_for_one_of_three_serial_cases_still_saves_every_case_and_the_run`, `test_an_entry_case_crash_still_saves_every_case_and_the_run` (both: real pytest run, `2 failed`, traceback bottoms out in `run_case_pipeline.py::run_and_grade_case_resilient` calling the faked `run_case`, uncaught) | `test_a_grader_crash_for_one_of_three_serial_cases_still_saves_every_case_and_the_run` (grading failure is still caught INSIDE `run_and_grade_case_resilient`, unaffected by removing the outer guard — `1 passed`) |

Each mutation applied by an exact anchored string replace (`assert src.count(old) == 1` before
writing, so a silent no-op patch is refused per C7's anchor clause), re-run, then reverted by the
exact inverse replace and re-run green (`3 passed` both times), and the reverted copy diffed
byte-identical against the real worktree's fixed `routes_runs.py` (`diff -u` → no output, `IDENTICAL
to worktree's fixed file`) — confirming the revert left no residue and the two mutations together
are a clean partition of what each of the 3 new tests actually defends: test 1 (grading) is killed
by A alone, test 3 (entry-case run_case crash) is killed by B alone, test 2 (non-entry run_case
crash) needs both call-site swap and outer guard, so both A and B kill it. Throwaway copy deleted
after use (`rm -rf` the temp dir; nothing under it was ever pushed, committed, or left running).

## Live browser evidence — SKIP (RAM-gated)

`ui/routes_runs.py` is UI-facing, but no real-browser smoke was attempted. Measured free RAM
during this cycle: **0.52 GB → 0.70 GB → 1.5 GB** across three checks spaced through the build
(`Get-CimInstance Win32_OperatingSystem | FreePhysicalMemory`), never approaching the 3.5 GB floor
the checker's own recipe (swap `LangChainFallbackProvider` for an in-process `MockProvider`,
`uvicorn.run` against an isolated `AUTOTESTER_ROOT`) requires before launching a real Chromium.
Other heavy processes were active on this shared host throughout (`D:\Captain`'s own `pytest -q`
under two interpreters, `D:\universityPlan`'s `ollama`-backed worker at `--workers 4`) — this is a
shared machine, not a dedicated CI runner. Given the shortfall's size (never within 2 GB of the
floor) and that launching a browser under memory pressure risks leaving a wedged process, **nothing
was launched**; no `python.exe`/`uvicorn`/`chromium` process from this unit's work was started or
left running at any point (confirmed before finishing: only the pre-existing, unrelated host
processes from other projects listed above). Declared as a gap below rather than a full 30-minute
poll loop, given the magnitude and persistence of the shortfall.

## Gaps (disclosed, not fixed here)

1. **The full non-browser `uv run pytest` suite (slot-1's actual verify command) did not run this
   cycle.** Free RAM stayed at 0.52-1.5 GB throughout the build (see Live browser evidence above),
   never reaching the ≥3.5 GB floor this project's own convention requires before a heavy run
   alongside other hosts' work. The 7-file targeted run (36 passed) plus a fully independent
   mutation run against a throwaway `uv sync`'d copy (23 passed baseline, both mutations behaving
   exactly as predicted, clean revert) stand in its place. The checker's own re-run is the real
   gate for the full suite.
2. **No live-browser smoke** — see above; RAM never came close to the 3.5 GB floor. The checker's
   own Mode D is the real gate for this route, per the same convention `at562-564-live-wiring`
   recorded.
3. **`_run_and_grade_resilient` is new, route-local composition, not exported** — if a future unit
   wants the same "resilient path + outer crash guard" behaviour outside `ui/routes_runs.py` (e.g.
   a CLI script), it would need to either import this private helper or have the same three lines
   duplicated. Not addressed here since AT-574's own scope is the live route, and the CLI's
   existing scripts (`scripts/run_pathlynks_first_cases.py` etc.) call `run_and_grade_case`
   directly by design (RU1-RU4's "a CLI script that wants the un-guarded, self-grading path still
   calls `run_and_grade_case` directly" — unaffected by this fix).

## Status: checked-PASS (qa/verdicts/at574-serial-resilience.md, Cycle checked: 1, 3b20159)
