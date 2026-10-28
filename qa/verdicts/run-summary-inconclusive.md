# Verdict - run-summary-inconclusive (Mode A)

**Verdict:** PASS
**Cycle checked:** 0
**Unit:** `fix/run-summary-inconclusive` @ 975b03e1 (off e74664f8), worktree `.claude/worktrees/run-summary`
**Judged against:** `qa/contracts/cli-mcp.md` CM1/CM2, `qa/contracts/core-invariants.md` C1/C2, CLAUDE.md design rules.
Read-only toward the code; only this verdict and the manifest status flip are committed. Nothing merged or pushed.

## Commands re-run by the checker (in the worktree)

1. `uv run pytest tests/test_cli_mcp.py tests/test_run_summary_inconclusive.py tests/test_mcp_declared.py tests/test_acceptance_comparison.py` plus every other `tests/test_cli_*.py`
   -> `1 failed, 294 passed in 681.87s`. The one red, `tests/test_cli_advice_resolves.py::test_the_collector_reports_what_it_could_not_resolve`, reports `ui/routes_crawl_approval.py:192`; that file and test are untouched by `git diff master...HEAD` (7 files, none of them), so it is a pre-existing master red, not this unit's.
2. `uv run ruff check src tests scripts` -> `All checks passed!`
3. `uv run autotester doctor` -> 2 violations, both `decision-citation-dangling` for D-110: `qa/verdicts/6c-1028-signup.md:4` (pre-existing, ignored per brief) and `qa/manifests/run-summary-inconclusive.md:62` (the manifest's own prose quoting that same D-110 line). No file-length / design-rule violation. Non-blocking: same root cause, clears when D-110 lands on master; doctor was already red at the base for the first one.

## Criteria

1. **Errored + INCONCLUSIVE case is not `passed`, exit != 0.** `run_service.py` `_headline` returns `ExitCode.INCONCLUSIVE` unless every case has verdict PASS and outcome not ERRORED/NOT_RUN. `test_errored_inconclusive_case_is_not_passed` (store level) and `test_cli_mcp.py::test_inconclusive` (full CLI `run -o json`, exit 6, status `inconclusive`) pass.
2. **All-PASS still `passed`/0.** `test_all_pass_still_passes` asserts `("passed", 0, None)`; existing `test_ok` passes.
3. **FAIL stays `failed`/1 and outranks inconclusive.** FAIL check is first in `_headline`; `test_a_fail_is_still_failed`, `test_fail_outranks_inconclusive` (errored+INCONCLUSIVE alongside a FAIL -> `failed`), existing `test_test_failed` pass.
4. **Adversarial: BLOCKED, errored-ungraded, NOT_RUN, completed-without-verdict, zero cases are never `passed`.** `test_unjudged_cases_never_read_as_passed` parametrises all five (including `[(COMPLETED,P),(NOT_RUN,None)]` mixed with a pass and `[]`), all -> `inconclusive`/6. Zero-case branch gives message "no case was judged". Also covered: one PASS + one INCONCLUSIVE -> `inconclusive`. Mixed FAIL + errored -> `failed` (criterion 3).
5. **CM1 exit-code table.** `core/exit_codes.py` adds `INCONCLUSIVE = 6` (distinct from 1 and 4) with a `_MEANING` entry, so it appears in the `--help` epilog; `test_exit_code_table_names_the_new_code`, `test_the_table_has_distinct_values` and `test_zz_every_code_in_the_table_was_provoked` pass (code 6 provoked by `test_inconclusive`). CM1 says "at least" the five classes, so no contract edit is required.
6. **CM2 typed report.** `schema/cli_output.py` `Literal` gains `"inconclusive"`, `extra="forbid"` model unchanged; the JSON run in `test_inconclusive` validates against it.
7. **MCP shares the rule.** `mcp_server.py:23,28` call `run_service.run_regression` / `report_for`; `run_regression` ends in `report_for` (`run_service.py` line ~137). No other `src`/`scripts` site derives a run-level "passed" from exit code (`grep` for `status == "passed"|ExitCode.OK|exit_code == 0`: only `cli_run.py:34` colour, which keys on non-zero and so correctly turns red). The maker's audit of UI/release sites matches the code.
8. **Moved tests byte-identical.** Extracted `test_mcp_module_is_a_thin_adapter` and `test_mcp_dependency_is_declared` from `git show master:tests/test_cli_mcp.py` and from `tests/test_mcp_declared.py`; compared programmatically -> `IDENTICAL True`. `test_cli_mcp.py` is 290 lines, `test_mcp_declared.py` 23, `test_run_summary_inconclusive.py` 91, `run_service.py` 146, `exit_codes.py` 38 (all under the C2 cap). The only other `test_cli_mcp.py` change is the added `test_inconclusive` and a condensed docstring.

## Notes (non-blocking)

- Dry runs still report OK/0 (`plan_dry_run` untouched), consistent with the exit-code meaning text.
- Behaviour change for CI callers: a run that previously exited 0 with only errored/inconclusive cases now exits 6. That is the intended fix; no repo workflow/script keys on exit code 0 of `autotester run` (grep of yml/sh/ps1 found none).
- Maker may reword manifest line 62 to avoid the D-110 token if a clean doctor is wanted before D-110 reaches master.
