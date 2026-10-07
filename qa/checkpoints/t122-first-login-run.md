# Checkpoint: t122-first-login-run (cycle 1, single coordinator)

Verdict: qa/verdicts/t122-first-login-run.md (PASS). Env: Windows 11, worktree .venv via uv, tree = 77c5e090 (+ uncommitted projects/pathlynks/approvals.jsonl, not judged).
Hashes: git HEAD 77c5e090704dadaba06a65b474eee01f3c900bc4; src/autotester unchanged since af8f3218 for core/, stages/run_case_pipeline.py, stages/grade.py, ui/routes_runs.py. Dependency lock not changed by the diff.
Attribution: claude-sonnet-subagent checker, this file.

| Check | Command / scope | Result |
|---|---|---|
| C1 done_check | `uv run pytest tests/test_execute.py tests/test_run_case_pipeline.py` (20 collected) | 20 passed, exit 0 |
| Case/UI tests | `uv run pytest tests/test_run_pathlynks_first_cases.py tests/test_ui_case_management.py tests/test_ui_cases.py tests/test_ui_runs_live_case_approval.py tests/test_ui_case_navigate_reachability.py` (42 collected) | 42 passed, exit 0 |
| Lint | `uv run ruff check src tests scripts` | clean |
| Doctor | `uv run autotester doctor` | clean |
| Secrets | `scripts/check_no_secrets.py qa/evidence/t122-first-login-run-2026-10-07 qa/manifests` | 328 files, 0 leaks |
| C2/C6 | read run.json, case result JSON, verdict JSON, step-4 screenshots of run-01M4B13T7QH17156NNK2PWGEYS and run-01M4B2KP0PQQ2NZTGYBQ463YWW (data snapshot = recorded evidence, no new production hit) | both runs completed, assertions met, judge PASS |
| Re-author | `Case.compute_id()` over projects/pathlynks/cases.jsonl; row diff vs 642ab4bd; project.json diff | new id matches; changes as claimed (+ `pinned: false` default, wording O2) |
| C4/C5 | approval rows in cycle1/approval-rows-minted.jsonl; cycle-0 consent falsifications reused (core/ unchanged) | met |
| Code reads | run_case_pipeline.py:37-101, grade.py:26-67,123-190, routes_runs.py:131-174, run_budget.py:30-165, enums.py:102-105 | PROPOSED-ISSUE 1/2/3 confirmed |

Live production login by the checker: none made.
