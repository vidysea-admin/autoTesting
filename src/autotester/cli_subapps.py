"""The list of CLI sub-apps `autotester` registers (T-205/TF5, design rule).

One job: hold `SUBAPPS`, the `(name, typer_app)` pairs `cli.py` adds with `add_typer`, so a new
command group (`schedule`, `tracker`, `video review`, ...) is registered by appending one pair
here, never by editing `cli.py`, which sits at the 300-line cap. A sub-app defined in `cli.py`
itself (`ledger`, `flowspec`, `report`) cannot be listed here without a circular import.
"""

from __future__ import annotations

import typer

from autotester import cli_issues, cli_revoke, cli_run, cli_schedule, cli_sweep, cli_video
from autotester.cli_auth import app as auth_app
from autotester.core.exit_codes import exit_code_table

SUBAPPS: list[tuple[str, typer.Typer]] = [
    ("ingest", cli_video.app),
    ("issues", cli_issues.app),
    ("schedule", cli_schedule.app),
    ("auth", auth_app),  # T-204 team login
    ("sweep", cli_sweep.app),  # AT-699 qa/.last-sweep append-only writer
]


def register_subapps(app: typer.Typer) -> None:
    """Add every `SUBAPPS` pair to `app`, in order, then the T-174 machine-facing commands."""
    for name, sub in SUBAPPS:
        app.add_typer(sub, name=name)
    app.command("run", help="Run a project's cases as a regression (--output json, --dry-run).",
                epilog=exit_code_table())(cli_run.regress_cmd)
    app.command("run-report", help="Print a finished run's redacted report.")(
        cli_run.run_report_cmd)
    app.command("revoke", help="Revoke an approval with a signed row.")(cli_revoke.revoke_cmd)
    app.command("catalog", help="Which test classes can run for a project.")(cli_run.catalog_cmd)
    app.command("mcp-serve", help="Serve run_tests, get_report, get_catalog over stdio MCP.")(
        cli_run.mcp_serve_cmd)
