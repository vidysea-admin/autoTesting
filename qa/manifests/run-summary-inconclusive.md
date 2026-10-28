# Manifest — run-summary-inconclusive

**Unit:** a run's headline status and exit code may be `passed` / 0 only when at least one case was
judged and every case judged PASS (feedback-inbox 2026-10-28 item 1).
**Contract:** `qa/contracts/cli-mcp.md` CM1 (distinct exit codes, each provoked), CM2 (typed report)
· `qa/contracts/core-invariants.md` C1 (no false green), C2
**Goal task:** none (issue-driven)
**Date:** 2026-10-28
**Status:** ready-for-check
**Fix cycle:** 0 of max 3
**Dual check:** no
**Branch:** fix/run-summary-inconclusive (worktree `.claude/worktrees/run-summary`)

## Bug

`uv run autotester run pathlynks-counsellor` printed `pathlynks-counsellor: passed` and exited 0
while its only case had outcome `errored` and verdict `INCONCLUSIVE` (run budget exhausted), run
`projects/pathlynks-counsellor/runs/run-01M60XBV8HDS26BVFMS1R9G3FV`. Cause:
`stages/run_service.py::report_for` set `TEST_FAILED` only when a FAIL verdict existed and
otherwise `OK`, so errored, inconclusive, blocked and ungraded cases all read as green.

## Change

- `stages/run_service.py`: new `_headline(cases, counts)` is the one rule, used by `report_for`
  (so `run`, `run-report` and the MCP `run_tests` / `get_report` all share it). FAIL -> `failed` (1).
  Else `passed` (0) only if there is >= 1 case and every case has verdict PASS and executor outcome
  not ERRORED / NOT_RUN. Anything else -> `inconclusive` with a message such as
  "1 of 1 case(s) not judged PASS (1 errored or not run, 1 inconclusive): not a pass".
- `core/exit_codes.py`: new `ExitCode.INCONCLUSIVE = 6` (distinct, per "never collapse two"; 1 stays
  "a case FAILed", 4 stays "retry infra"); `--help` table updated.
- `schema/cli_output.py`: `RegressionReport.status` accepts `"inconclusive"`.

## Criteria (all verified by tests, run in this worktree)

1. A run with one errored + INCONCLUSIVE case: status != `passed`, exit != 0 -> `test_errored_inconclusive_case_is_not_passed` (store level), `test_inconclusive` (full CLI `run`, exit 6).
2. All-PASS run still `passed`, exit 0 -> `test_all_pass_still_passes`, existing `test_ok`.
3. A FAIL is still `failed` (exit 1), and outranks inconclusive -> `test_a_fail_is_still_failed`, `test_fail_outranks_inconclusive`, existing `test_test_failed`.
4. BLOCKED, errored-ungraded, NOT_RUN, no verdict, zero cases are never `passed` -> `test_unjudged_cases_never_read_as_passed`.
5. CM1 holds: new code is in the table, in `--help`, and provoked (`test_zz_every_code_in_the_table_was_provoked`).

## Where a run-level "passed" is derived (audit)

- `stages/run_service.py:32` `_STATUS` and `report_for` -> `_headline` (FIXED, the only CLI/MCP site).
- `schema/cli_output.py:33` status Literal (extended).
- `stages/report_delivery.py:35-55` `report_label` (UI inbox/status label): already correct, `green`
  needs every planned case to have a verdict and all PASS; INCONCLUSIVE/BLOCKED/FAIL and missing
  verdicts map to their own labels. Unchanged.
- `ui/routes_report.py:232-234` pass rate = PASS verdicts / planned cases: errored/inconclusive count
  as not passed. Unchanged. UI run lists use per-result `theme.badge` counts, never a run-level "passed".
- `stages/release_compare.py:78-79` flow status and `schema/release.py:161-162` `release is clean`:
  any non-PASS verdict is `failed`, any missing verdict `not_run`. Already strict. Unchanged.
- `stages/unified_report_render.py:42` `_TONE` is a colour map only.

## Notes for the checker

- `tests/test_cli_mcp.py` was at 298 lines; to stay under the C2 cap the two fixture-free CM5 tests
  (`test_mcp_module_is_a_thin_adapter`, `test_mcp_dependency_is_declared`) moved verbatim to
  `tests/test_mcp_declared.py`, and the module docstring was condensed.
- CM1 in `qa/contracts/cli-mcp.md` says "at least" these codes, so adding code 6 needs no contract
  edit; the checker may want to name it in CM1 (maker does not edit contracts).
- `uv run autotester doctor` reports 1 violation that is NOT from this change:
  `decision-citation-dangling: qa/verdicts/6c-1028-signup.md:4 cites D-110` (D-110 sits in the main
  checkout's uncommitted `docs/DECISIONS.md`). No file-length violation remains.
- Verify: `uv run pytest tests/test_cli_mcp.py tests/test_run_summary_inconclusive.py tests/test_mcp_declared.py tests/test_acceptance_comparison.py` -> 51 passed; `uv run ruff check src tests scripts` -> All checks passed.
