# Manifest - flowplan-writer

**Status:** checked-PASS
**Fix cycle:** 1
**Base SHA:** f6c1ac4e63c466db09f1c7a465863a55faec513e
**Candidate SHA:** the commit carrying this file (`git log -1 -- qa/manifests/flowplan-writer.md`)
**Issues addressed:** AT-898. AT-794 (`run_ux_advisory` no caller) is a different seam (`ui/routes_runs.py::trigger_run`, T-125) and is NOT touched.

## What changed
- `stages/flow_plan.py` (new, pure): `plans_from_batch(PipelineBatch) -> list[FlowPlan]`, one plan per flow whose cases all have a result and verdict.
- `stages/orchestrate_downstream.py::make_report_stage`: after exports it persists each plan via `store.save_flow_plan` (upsert by flow_id; REPORT is where every case is observed and graded). `orchestrate.py` untouched (295 lines).
- `tests/test_flow_plan_writer.py` (new): real EXPAND/EXECUTE/GRADE/REPORT, plan saved, `start_release` freezes it in scope, pauses, resumes to done; an incomplete flow gets no plan.

## Consumers
`store.list_flow_plans` -> `stages/release.py::build_scope` / `_frozen_or_new`, `orchestrate_gate.plans_cost`.

## Contract clauses
release-regression RR6 (each completed flow leaves a persisted plan; no plan means not run); core invariants: stages pure, file/function limits.

## Required checks
`pytest tests/test_flow_plan_writer.py tests/test_orchestrate_downstream.py`, ruff on changed paths, `autotester doctor` delta vs base.

## Fix cycle 1
Regenerated docs/MAP.md via `autotester map` (row for stages/flow_plan.py). Doctor exit 0 on candidate. Note: the shared venv editable install pointed at another worktree, so CLI runs need PYTHONPATH=<this worktree>/src.
