# Verdict - t174-cli-mcp

Cycle checked: 1
Judged: branch wave/t174-cli-mcp, code head 582a873a (the only later change is this verdict, the manifest flip and the contract/feedback-inbox edits).
Contract: `qa/contracts/cli-mcp.md`, tightened and made ACTIVE by this checker before judging (see its amendment log; folded in `qa/feedback-inbox.md`).

VERDICT: PASS

## Per criterion

- **CM1 PASS.** One `ExitCode` enum (`core/exit_codes.py`), mirrored in the `run --help` epilog (read from live `--help`). Per-code tests: OK, TEST_FAILED, USAGE, REFUSED, INFRA (ProviderError and TimeoutError), INTERNAL, plus `test_zz_every_code_in_the_table_was_provoked`. Sabotage: set INTERNAL = 4; `test_infra` went red on `assert 'internal' == 'infra'` (an assertion, not an import error); reverted. `doctor` untouched. `schedule tick` keeps its own `TickReport.exit_code` (`cli_schedule.py:69`): acceptable, scoped in the contract, not a gap.
- **CM2 PASS.** stdout is one document (`test_json_stdout_is_exactly_one_document`, with a print injected into the run path); `RegressionReport`/`CaseReport` are `extra="forbid"` in `schema/cli_output.py`; every report passes the project `Redactor.scrub_obj` (`run_service._report`); planted-secret test green.
- **CM3 PASS.** `plan_dry_run` never calls `launch_run`, so it builds no browser or provider, makes no run dir and mints no D-068 derived approval row. Test asserts an identical tree hash. Real stdio dry-run also left the tree hash unchanged. Without `--dry-run` and without a grant the run exits 3. A dry run proves nothing about approval; the message says so, and the contract now says so.
- **CM4 PASS.** Exactly three tools (in-memory test and real stdio). Run goes through `launch_run`, so the RunApproval gate (`require_live_case_approval`) is enforced there; the MCP layer holds no approval logic. No claim is made for paths that do not call the launcher (UI case runs, AT-570). `mcp_server.py` imports only schema and `stages.run_service` (test pins the import set). `get_catalog` returns the existing `Catalog` (T-125) or a usage `RegressionReport`: accepted, now stated in the contract.
- **CM5 PASS.** `mcp>=2.3,<3` added in this unit's commit only (diff of 582a873a); `doctor: clean`.

## Evidence

- `uv run pytest tests/test_cli_mcp.py tests/test_cli_subapp_hook.py tests/test_cli_surface.py tests/test_cli_schedule.py`: 95 passed. `ruff check src tests scripts`: clean. `autotester doctor`: clean. No full suite, per brief.
- Real stdio smoke: subprocess `autotester mcp-serve` through `mcp.client.stdio` + `ClientSession`: initialize ok, `tools/list` = [get_catalog, get_report, run_tests]; called run_tests(dry_run), run_tests (no-credential project), get_catalog, get_report, unknown project; clean shutdown, under 60 s.
- Secret-leak probe: project with a `SecretRef`, the value in repo `.env` and also planted in project name and case title; every raw tool result over stdio was searched for the value: absent. In-process `test_no_tool_returns_a_secret` also runs with a leaking executor and a FAIL verdict: absent.

## Observations (non-blocking)

- `cli_run.py:78-83`: the CLI redirects stdout to stderr during a real run, but `mcp_server.run_tests` has no such guard. No `print` was found on the launch path, so stdio framing is safe today; a future stdout write there would corrupt the MCP channel. A hardening unit could wrap `run_regression` in the MCP adapter.
- `run_service.py` imports `_latest_run_id` and `_load_redactor` (underscore names) from `report_export`: reuse is correct, the privacy convention is not. Rename if touched.
- The judge check precedes the approval check in the launcher, so a credential-less project with no provider reports USAGE (2), not REFUSED (3). Both are refusals before any side effect; the REFUSED test uses a fake judge.
- The mapping `LaunchRefused.status == 403` to REFUSED relies on the launcher's status convention.
