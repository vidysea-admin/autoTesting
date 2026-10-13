"""The AutoTester MCP server: three tools, a thin adapter over `stages/run_service.py` (T-174 CM4).

One job: expose exactly `run_tests`, `get_report` and `get_catalog` on a local stdio server. Each
tool calls the same function the CLI calls; this module holds no stage logic, imports no stage
internals, and cannot grant or skip an approval -- `run_tests` goes through the launcher, whose
`RunApproval` gate (D-018) answers with `exit_code` 3 and starts nothing when none covers the run.
`get_report` returns the stored, already-redacted report; no tool reads or returns a raw secret.
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from autotester.schema.catalog import Catalog
from autotester.schema.cli_output import RegressionReport
from autotester.stages import run_service

TOOL_NAMES = ("run_tests", "get_report", "get_catalog")


def run_tests(project: str, dry_run: bool = False) -> RegressionReport:
    """Run all cases of a project as a regression. Refused (exit_code 3) without an approval."""
    return run_service.plan_dry_run(project) if dry_run else run_service.run_regression(project)


def get_report(project: str, run_id: str | None = None) -> RegressionReport:
    """The redacted report of a run (the latest when run_id is omitted)."""
    return run_service.report_for(project, run_id)


def get_catalog(project: str) -> Catalog | RegressionReport:
    """Which test classes can run for the project, and the one action that unblocks the rest."""
    return run_service.catalog_for(project)


def build_server() -> MCPServer:
    server = MCPServer("autotester", instructions="Run, report on and catalog AutoTester tests.")
    for fn in (run_tests, get_report, get_catalog):
        server.tool()(fn)
    return server
