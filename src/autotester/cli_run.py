"""`autotester run`, `run-report`, `catalog`, `mcp-serve`: the machine-facing commands (T-174).

One job: the CLI contract of cli-mcp.md. `--output json` prints one `RegressionReport`
on stdout (everything else goes to stderr), `--dry-run` lists what would run and starts nothing,
and the exit code is an `ExitCode` (CM1). The work is `stages/run_service.py`, shared with the
MCP server; this file only renders and exits.
"""

from __future__ import annotations

import contextlib
import sys
from enum import StrEnum

import typer

from autotester.schema.cli_output import RegressionReport
from autotester.stages import run_service


class OutputFormat(StrEnum):
    TEXT = "text"
    JSON = "json"


OUTPUT = typer.Option(OutputFormat.TEXT, "--output", "-o", help="text (default) or json")


def _emit(report: RegressionReport, output: OutputFormat) -> None:
    """The only writer to stdout. JSON mode: one document, no colour, nothing else."""
    if output is OutputFormat.JSON:
        sys.stdout.write(report.model_dump_json(indent=2) + "\n")
    else:
        colour = typer.colors.GREEN if report.exit_code == 0 else typer.colors.RED
        typer.secho(f"{report.project}: {report.status}"
                    + (f" - {report.message}" if report.message else ""), fg=colour)
        for case in report.cases:
            typer.echo(f"  {case.case_id} {case.outcome.value if case.outcome else '-'}"
                       f" {case.result.value if case.result else 'ungraded'}")
        if report.dry_run:
            for case_id in report.case_ids:
                typer.echo(f"  would run {case_id}")
    raise typer.Exit(report.exit_code)


def regress_cmd(
    project: str = typer.Argument(..., help="project slug"),
    dry_run: bool = typer.Option(False, "--dry-run", help="list what would run; start nothing"),
    output: OutputFormat = OUTPUT,
) -> None:
    """Run every case of a project as a regression. Needs a covering approval (D-018)."""
    if dry_run:
        _emit(run_service.plan_dry_run(project), output)
    with contextlib.redirect_stdout(sys.stderr):    # progress text is never machine output
        report = run_service.run_regression(project)
    _emit(report, output)


def run_report_cmd(
    project: str = typer.Argument(..., help="project slug"),
    run_id: str | None = typer.Argument(None, help="default: the latest run"),
    output: OutputFormat = OUTPUT,
) -> None:
    """Print a finished run's report (already redacted)."""
    _emit(run_service.report_for(project, run_id), output)


def catalog_cmd(
    project: str = typer.Argument(..., help="project slug"), output: OutputFormat = OUTPUT,
) -> None:
    """Which test classes can run for a project, and what blocks the rest."""
    result = run_service.catalog_for(project)
    if isinstance(result, RegressionReport):
        _emit(result, output)
    elif output is OutputFormat.JSON:
        sys.stdout.write(result.model_dump_json(indent=2) + "\n")
    else:
        for entry in result.entries:
            state = "runnable" if entry.runnable else f"blocked: {entry.blocked_reason}"
            typer.echo(f"{entry.case_class.value:28} {entry.tier.value:12} {state}")


def mcp_serve_cmd() -> None:
    """Serve run_tests / get_report / get_catalog to an MCP client over local stdio."""
    from autotester.mcp_server import build_server

    build_server().run("stdio")
