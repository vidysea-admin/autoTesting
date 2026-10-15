# Contract — run_case_pipeline: a generic run+grade path (new, 2026-09-04)

**Covers:** ad-hoc unit `run-case-pipeline` (no `.goal` task; prerequisite for the UI run-trigger
in the same plan). **Owner:** /checker.
**Criticality:** HIGH — every future "click Run" and every future case depends on this being
correct; a bad default rubric would make every result meaningless.
**Depends on:** `execute.md` (unchanged, reused), `grade.md` (unchanged, reused).

## Purpose

Umesh: "proper product ki tarah lo isko ... rerun kar paaye" — a UI "Run" button needs a way to
grade an arbitrary case, not just the 3 Pathlynks cases someone hand-wrote a `Rubric` for in a
script. `stages/run_case_pipeline.py::run_and_grade_case` is the one function every caller (CLI,
UI, future scripts) uses to run one case and get a real `Verdict`, lazily building and persisting
a plain default rubric the first time a case has none.

## Criteria

### RP1 — Every case is gradeable, with no hand-written Python
`run_and_grade_case(case, session, judge, run_id)` never raises for a case that lacks a rubric —
it builds `default_rubric(case, rubric_id)` and persists it via `ProjectStore.save_rubric` the
first time, then reuses the persisted one on every subsequent call for the same `rubric_id`.

### RP2 — The default rubric is honest, not a rubber stamp
`default_rubric`'s one criterion is grounded in the case's own `rationale` (falling back to its
`title` only if `rationale` is empty) — never a hardcoded "always pass" or content-free claim.
The criterion id is pinned (`"c1"`) with an explicit instruction to use it exactly, matching the
project's own established pattern (`scripts/regression_proof.py`'s `make_rubric`) for avoiding
`grade.md` G3's self-consistency downgrade from an invented criterion id.

### RP3 — Persistence is idempotent and reuses `ProjectPaths.rubrics_dir`
`ProjectStore.save_rubric`/`load_rubric` write/read exactly one JSON file per rubric id under the
project's existing (previously unused) `rubrics_dir` — no new file format, no new top-level
directory (C1/C3, C4).

### RP4 — Never grades on stale or wrong evidence
`run_and_grade_case` calls the unmodified `stages/execute.py::run_case` and
`stages/grade.py::grade` — this stage adds no new evidence-capture or judgment logic of its own,
only the rubric lookup/creation step between them.

## No-fire list

- Refactoring the 3 existing scripts (`scripts/regression_proof.py`, `scripts/bench_trial.py`,
  `scripts/run_pathlynks_first_cases.py`) to call this new function — deliberately deferred.
  Each is already checker-PASSed against a real product/fixture with its own hand-tuned rubric;
  migrating them risks a regression for no immediate benefit. The UI run-trigger (a separate
  unit) is this function's first real caller.
- An AI-authored or smarter rubric-generation system — `default_rubric`'s plain
  rationale-based criterion is the honest v1 floor, not a claim of sophistication.
- Any change to `execute.py`/`grade.py` themselves.

## Amendment log (append-only; git history is the version)

- 2026-09-04 · init · contract created for the run-case-pipeline unit.

## 2026-10-15 completion amendment (D-099)

### RP4 amendment — Replay and post-result integrations
RP4's unmodified `run_case` call describes the original unit, not a permanent ban
on checked script replay. The production pipeline may use existing deterministic
replay, fresh execution and explicit opt-in repair; grading still consumes only
the current case/run's persisted RawResult evidence. No replay success may reuse
a previous run's judgement or stale evidence. Failed bundle/advisory integration
cannot erase the original functional result. Verify the real pipeline caller for
script success/failure, run/case isolation and post-result integration errors.
