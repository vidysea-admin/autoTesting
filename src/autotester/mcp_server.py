"""AutoTester as a local MCP server (stdio): run tests, get report, get catalog.

One job: expose the three `run_ops` functions the CLI already calls as MCP tools -- no stage is
re-implemented here (CM4). `run_tests` goes through the same `RunApproval` gate as every other
entry point and can neither grant nor bypass one. Outputs are the CM2 `RunReport` / the
`Catalog`, already scrubbed. Local stdio only; a networked transport needs its own decision.
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from autotester import run_ops
from autotester.schema.catalog import Catalog
from autotester.schema.cli_output import RunReport

server = MCPServer("autotester", instructions=(
    "Run a project's regression suite, read the stored report, or read what the project can "
    "run. A run needs a human-granted (or credential-derived) approval; this server cannot "
    "grant one. exit_code in the result follows the documented CLI table."))


@server.tool(name="run_tests")
def tool_run_tests(project: str, dry_run: bool = False) -> RunReport:
    """Run the project's cases (or only list them with dry_run) and return the report."""
    return run_ops.perform_run(project, dry_run=dry_run)


@server.tool(name="get_report")
def tool_get_report(project: str, run_id: str | None = None) -> RunReport:
    """The stored report of a run; the latest run when run_id is omitted."""
    return run_ops.get_report(project, run_id)


@server.tool(name="get_catalog")
def tool_get_catalog(project: str) -> Catalog:
    """What the project can run now and what blocks the rest."""
    return run_ops.get_catalog(project)


def serve() -> None:
    """Block serving stdio until the client disconnects. Loads the repo `.env` like the CLI."""
    from autotester.core.env import load_repo_env
    load_repo_env()
    server.run("stdio")


if __name__ == "__main__":
    serve()
