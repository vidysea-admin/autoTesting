# Verdict - flowplan-writer

**Verdict:** FAIL
**Status:** FAIL
**Cycle checked:** 0
**Reviewed SHA:** 77479abbffce461057dc3939f109b47e9212b499
**Base SHA:** f6c1ac4e63c466db09f1c7a465863a55faec513e
**Issue:** AT-898 (RR6 producer)

## Blocking finding (proven)
`uv run autotester doctor` is clean at base and reports `1 violation(s)` at the candidate:
`stale-generated: docs/MAP.md - generated sections differ; run autotester map`.
Cause: the new module `src/autotester/stages/flow_plan.py` has no row in `docs/MAP.md` (grep
`flow_plan` in MAP.md: no match). The repo adapter requires doctor green. Fix: run
`autotester map` and commit the regenerated `docs/MAP.md` (generated section, never hand-edited).
Everything else below passed, so this is the only change needed for cycle 1.

## Probe results (independent)
1. Semantics - OK. `FlowPlan` is "the cases that decide whether the flow still works" (schema/release.py),
   not a pass baseline; RR3 baseline pass-ness is decided later from graded results. Saving a plan for a
   failing flow is correct: omitting it would report a failing flow `not run`, hiding the failure (RR6).
   Skipping a flow with an ungraded case: REPORT already raises unless every frozen case has a verdict
   (`make_report_stage`), so that branch is defensive and effectively unreachable via REPORT; a
   half-run flow stays `not run`, which RR6 reports by name. Minor, non-blocking: no log line says a flow
   was skipped (suggest only).
2. Idempotency - OK. `save_flow_plan` is `upsert_jsonl(key="flow_id")`; re-running REPORT rewrites the same
   row. A frozen release scope embeds its plans in scope.json and `_frozen_or_new` returns it before reading
   plans, and `start_release` wires its own REPORT (`make_report_runner`), not `make_report_stage`, so a
   re-save cannot alter a frozen scope. Expand freezes all non-retired cases, so plans are not partial subsets.
3. Purity - OK. `plans_from_batch` reads only the `PipelineBatch` (previous artifact); defined once
   (grep), 26 lines.
4. Tests (own run, PYTHONPATH=src, repo .venv py3.11, import root verified = worktree src):
   `tests/test_flow_plan_writer.py tests/test_orchestrate_downstream.py tests/test_release_gate.py
   tests/test_regression_trigger.py tests/test_cli_release.py` -> 40 passed, exit 0
   (.work/chk/pytest.out). `tests/test_acceptance_baseline.py tests/test_unified_report.py` -> 37 passed, exit 0.
5. ruff on changed src/test paths: exit 0. doctor: base clean (exit 0); candidate 1 violation (above).

## Not run
Sabotage mutation (remove the save call) not run; the writer test asserts the saved plan directly.
Full suite not run (scoped per policy). No push, master untouched.

## Metrics (BOOTSTRAP_REVIEW, maker usage unknown, ratio unverified)
Active wall ~150 s incl. ~70 s of pytest; tokens: host exposes none, recorded null.
