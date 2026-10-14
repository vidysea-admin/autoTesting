# Verdict - budget-judge-time

**Cycle checked:** 1
**Verdict:** PASS

- Judge time separate: `RunBudget.judging()` (run_budget.py) excludes grade() time from the approval clock; both grade() calls in run_case_pipeline.py are wrapped; run_launcher uses `RunBudget.for_cases`.
- Still bounded: exclusion capped at `judge_allowance_s` (45 s/case); excess charged to the clock; total <= wall_clock_s + allowance. Zero/missing wall clock still fails closed; default allowance 0 keeps old behaviour.
- Cost cap: action/probe counting untouched.
- Tests: 24 passed (judge_time + budget/pipeline files). ruff clean. doctor clean. merge-tree: 0 conflicts.
- Notes (non-blocking): wall_clock_request_s now includes allowance (grant asks for more); parallel_run.py:199 default `RunBudget(approval)` has no allowance (only when no budget passed).
