# Manifest — t167-release-regression (T-167: LangGraph release-regression orchestrator)
**Contract:** qa/contracts/release-regression.md RR1-RR6
**Goal task:** T-167
**Status:** ready-for-check
**Date:** 2026-10-11
**Fix cycle:** 0
**Dual check:** required
**dual-trigger:** security: src/autotester/core/consent.py:182 (`require_approval`, the signed-approval gate this unit calls before any graph invocation)
**Persona walk:** required (release-manager). Build is CLI-only; commands to walk: `autotester release <project> [--run-id] [--approve-by|--decline-by] [--git-sha]` and `autotester release-log <project> --run-id <id>` (no UI surface touched).
**Executor:** claude-sonnet-subagent

## What changed
- pyproject.toml / uv.lock — `langgraph==1.2.14` (resolved `langgraph-checkpoint` 4.2.0); one added line, comments untouched.
- src/autotester/stages/orchestrate.py:1-295 — converted IN PLACE to a LangGraph StateGraph (node per stage, conditional `_route`, CONFIRM node uses `interrupt()`); `run_or_resume` calls `release_preflight` first.
- src/autotester/stages/orchestrate_gate.py (new, 61) — `release_preflight` (reads the signed row named by the scope, calls `require_approval`, never mints), `check_lineage`, `reenter`, `paused_view`.
- src/autotester/stages/orchestrate_checkpoint.py (new, 264) — durable JSON-only `FileCheckpointer`; the checkpointer is the resume authority, `state.json` is its projection.
- src/autotester/stages/release.py (new, 91) — the trigger `start_release`; computes cost and requires a covering approval BEFORE writing anything; stitches per-flow plans into one scope.
- src/autotester/stages/release_compare.py (new, 135) — `trusted_baseline`, diff, one issues log, COMPARE/REPORT runners, `flag_bad`; reads verdicts, never grades.
- src/autotester/schema/release.py (new, 162) — `BASELINE_RULE`, `FlowPlan`, `ReleaseScope`, `ReleaseDecision`, `FlowOutcome`, `ReleaseIssue`, `RegressionDiff`, `ReleaseRecord`.
- src/autotester/schema/run_state.py, store/run_store.py, core/paths.py (294; freed lines by condensing two docstrings), cli.py (299), cli_release.py (new, 90).
- tests/test_regression_trigger.py (298, 18 tests), tests/test_cli_release.py (58, 4 tests); docs/MAP.md and docs/SNAPSHOT.md regenerated.

## Verification scope
Policy-Version: proportional-verification/2026-10-10.9
Tier: L — dependency bump, concurrency/resume, config/CI; plus an approval gate
Base / checked state: branch wave/t167-release-regression from master 4f8f5da1 (master has since moved to 3a16616c; not merged); code commit 00fae668
Gate answers: D-068 (signed row required before the graph, auto-minted only for credentialed projects; this unit never mints), write-policy-tier.md (not re-litigated), d081-run-approvals.md authorizes NO live T-167 run -> fixture-only, no browser, no model call, no network.
Untouched by design: ui/run_execution.py, run_budget.py, filestore.py, schema/run.py, orchestrate_runners.py, cli_orchestrate.py.
Metrics: start=unavailable end=2026-10-11 wall_min=unavailable agent_min=unavailable blocked_min=60 suite_runs=3 repeat_runs=0 mutations=6 cycle=0 resumes=1 tokens=unavailable policy=proportional-verification/2026-10-10.9

## Pre-checks (run on final code commit 00fae668)
Pre-check[RR1]: 00fae668 `uv run pytest tests/test_regression_trigger.py -k rr1` -> 3 passed (plus tests/test_orchestrate.py 7 passed: OR1-OR5 still hold)
Pre-check[RR2]: 00fae668 `uv run pytest tests/test_regression_trigger.py -k rr2` -> 5 passed (plus tests/test_cli_release.py 4 passed)
Pre-check[RR3]: 00fae668 `uv run pytest tests/test_regression_trigger.py -k rr3` -> 4 passed
Pre-check[RR4]: 00fae668 `uv run pytest tests/test_regression_trigger.py -k rr4` -> 3 passed
Pre-check[RR5]: 00fae668 `uv run pytest tests/test_regression_trigger.py -k rr5` -> 1 passed; `uv run autotester doctor` -> doctor: clean
Pre-check[RR6]: 00fae668 `uv run pytest tests/test_regression_trigger.py -k rr6` -> 2 passed
Regression: 00fae668 `uv run pytest tests/test_orchestrate_runners.py tests/test_cli_orchestrate.py tests/test_cli_orchestrate_resume.py tests/test_schema.py tests/test_store.py tests/test_consent.py tests/test_parallel_run_approval.py` -> 105 passed
Lint: `uv run ruff check src tests scripts` -> All checks passed!

## Capability coverage (each criterion -> its isolating falsification)
Run in a THROWAWAY COPY (scratchpad, PYTHONPATH to the copy; worktree untouched), one hunk, same nodes: green before, red after, restored byte-identical and green again.

| Criterion | falsifying edit | observed |
|---|---|---|
| RR1 | new thread id per call in `run_or_resume` (checkpointer no longer the resume record) | rr1 done-stage-not-redone + raise-then-reenter: 2 failed |
| RR2 | `release_preflight` moved from the top of `run_or_resume` to just before `graph.invoke` | test_rr2_a_forged_scope_cannot_skip_the_gate...: failed (1 failed, 2 passed) |
| RR3 | drop `r.is_trusted` from `trusted_baseline` (latest earlier run is the baseline) | rr3 third-run-vs-first and flagged-never-baseline: 2 failed, 1 passed |
| RR4 | append `from ...enums import Result` and `_DECIDED = Result.PASS` to release_compare.py | rr4 no-verdict/no-grader check [release_compare]: failed |
| RR5 | delete the `langgraph==` line from the copy's pyproject.toml | test_rr5_langgraph_is_declared...: failed |
| RR6 | replace the not-run FlowOutcome+issue block in `_flow_lines` with `pass` | test_rr6_a_flow_without_a_plan...: failed (1 failed, 1 passed) |

Note: moving the preflight to just AFTER `_compile` is NOT caught by any test (compile touches no disk); the named RR2 edit is therefore the later move. Checker may want a test that spies on `graph.invoke`.

## Live browser evidence
Not applicable: CLI-only, no UI file touched. No live run was made (fixture-only).

## Known limits
- `autotester release` wires no live EXECUTE/GRADE runner; a confirmed run stops at EXECUTE with a message saying so. A host (T-174/T-203) injects runners into `start_release`.
- Brief said base 4f8f5da1; master is 3a16616c. The input worktree's budget state, `artifact_lock` and strict validators were NOT ported.

## For T-168
Record: `ProjectPaths.run_release_record(run_id)` = `projects/<slug>/runs/<run_id>/release.json` (`ReleaseRecord`, schema/release.py); frozen scope beside it as `scope.json`; read with `ProjectStore.load_release_record` / `list_release_records`. Diff shape: `record.diff = RegressionDiff{baseline_rule, baseline_run_id|None, regressed[], fixed[], new_cases[], note}`; one log `record.issues[] = {flow_id, case_id|None, kind: failed|errored|not_run|regressed, detail}`; per-flow `record.flows[] = {flow_id, status: passed|failed|not_run, case_ids}`.
