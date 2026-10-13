# Manifest — t174-cli-mcp

**Unit:** T-174 CLI contract (`--output json`, one exit-code table, `--dry-run`) + AutoTester MCP server
(run tests, get report, get catalog).
**Contract:** `qa/contracts/cli-mcp.md` CM1-CM5 (ACTIVE) · `qa/contracts/core-invariants.md` C3, C5, C11
**Goal task:** T-174 (D-071 approved the `mcp` SDK dependency)
**Date:** 2026-10-13
**Status:** checked-PASS
**Fix cycle:** 1
**Dual check:** no

## What was built

- `core/exit_codes.py` — the ONE table: OK 0, TEST_FAILED 1, USAGE 2, REFUSED 3, INFRA 4, INTERNAL 5; `exit_code_table()` is the `run --help` epilog (CM1).
- `schema/cli_output.py` — `RegressionReport` / `CaseReport`, `extra="forbid"` (CM2).
- `stages/run_service.py` — `run_regression` (calls `launch_run`, every gate inside it), `plan_dry_run`, `report_for`, `catalog_for`; never raises, scrubs every report through the project `Redactor`.
- `cli_run.py` — `run [--dry-run] [-o json]`, `run-report`, `catalog`, `mcp-serve`; registered from `cli_subapps.py` (cli.py is at its 300-line cap). JSON mode: stdout is one document, run-time prints are redirected to stderr. `OutputFormat` moved here from `cli_schedule.py` (one concept).
- `mcp_server.py` — exactly `run_tests`, `get_report`, `get_catalog` over local stdio (official `mcp` SDK 2.x `MCPServer`), each a one-line call into `run_service`.
- `pyproject.toml` / `uv.lock` — `mcp>=2.3,<3`, added in this unit only (CM5).
- `tests/golden/cli_commands.json` regenerated (4 new commands); `docs/MAP.md` regenerated.

## Points for the checker

- **Dry run mints no approval.** `launch_run` can write a D-068 derived approval row, so `--dry-run` does not call it: it lists non-retired case ids and starts nothing. A dry run therefore does NOT prove an approval exists (it says so in `message`).
- **Refusal fixtures strip the project's credentials.** With a provisioned credential D-068 derives a covering approval, so a run is not refused; the REFUSED tests use a credential-less project with no human grant.
- `get_catalog` returns the existing `Catalog` schema (or a `RegressionReport` with exit_code 2 for an unknown project); `run_tests`/`get_report` use `RegressionReport`. CM4 says "tool outputs use the CM2 schema" — checker to decide whether `Catalog` satisfies that.
- Exit codes cover `run`/`run-report`/`catalog`; `schedule tick` keeps its own `report.exit_code` (not touched). `orchestrate`, `explore` etc. are unchanged.
- Not exercised: a real stdio subprocess (tests use the SDK's in-memory `Client`); no timeout flag (TimeoutError maps to INFRA).

## Verification run

`uv run pytest tests/test_cli_mcp.py tests/test_cli_subapp_hook.py tests/test_cli_surface.py tests/test_cli_schedule.py tests/test_run_launcher_approval.py` · `uv run ruff check src tests scripts` · `uv run autotester doctor` — see the commit message / report for counts.
