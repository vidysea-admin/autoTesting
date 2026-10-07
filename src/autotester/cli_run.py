"""CLI commands a pipeline can gate on: `run`, `catalog`, `report show`, `mcp`.

One job: the typer layer over `run_ops` (the same three functions the MCP server calls).
With `--output json` stdout carries exactly one JSON document -- a `RunReport` or, for
`catalog`, a `Catalog` -- and progress text goes to stderr (CM2). Exit codes come from the one
`ExitCode` table in `schema/cli_output.py`, mirrored in `--help` (CM1). Contract: cli-mcp.md.
"""

from __future__ import annotations

from enum import StrEnum

import typer

from autotester.run_ops import error_report, exit_code_for, get_catalog, get_report, perform_run
from autotester.schema.cli_output import EXIT_CODE_MEANING, ExitCode, RunReport

EXIT_CODES_HELP = "Exit codes: " + "; ".join(
    f"{int(code)} {code.name} = {EXIT_CODE_MEANING[code]}" for code in ExitCode)
"""Rendered from the enum, so the documented table cannot drift from the real one."""


class OutputFormat(StrEnum):
    TEXT = "text"
    JSON = "json"


OUTPUT_OPT = typer.Option(OutputFormat.TEXT, "--output", "-o",
                          help="text (default) or json: one document on stdout, nothing else")


def _emit(report: RunReport, output: OutputFormat) -> None:
    """Print the report and leave with its exit code."""
    if output is OutputFormat.JSON:
        typer.echo(report.model_dump_json(indent=2))
    else:
        typer.echo(f"{report.project}: {report.status}"
                   + (f" -- {report.message}" if report.message else ""))
        for case in report.cases:
            typer.echo(f"  {case.result.value if case.result else 'NOT_GRADED':<12} "
                       f"{case.title or case.case_id}")
        if report.counts:
            typer.echo("  " + ", ".join(f"{k}={v}" for k, v in sorted(report.counts.items())))
        for case_id in report.planned_case_ids:
            typer.echo(f"  would run {case_id}")
    raise typer.Exit(report.exit_code)


def run_tests_cmd(
    project: str,
    dry_run: bool = typer.Option(False, "--dry-run", help="list the cases that would run; "
                                 "no browser, no provider call, nothing written"),
    output: OutputFormat = OUTPUT_OPT,
) -> None:
    """Run a project's cases in a real browser and judge them. The run needs a live_case
    approval exactly as the Run button does; --dry-run is not a route around it.

    Exit codes: see the table below."""
    typer.echo(f"{'planning' if dry_run else 'running'} {project} ...", err=True)
    _emit(perform_run(project, dry_run=dry_run), output)


run_tests_cmd.__doc__ = (run_tests_cmd.__doc__ or "").replace(
    "Exit codes: see the table below.", EXIT_CODES_HELP)


def report_show_cmd(
    project: str, run_id: str | None = typer.Argument(None), output: OutputFormat = OUTPUT_OPT,
) -> None:
    """Print a stored run's report (the latest run when RUN_ID is omitted). Exits with the
    run's own code: 0 when every case passed, 1 otherwise."""
    _emit(get_report(project, run_id), output)


def catalog_cmd(project: str, output: OutputFormat = OUTPUT_OPT) -> None:
    """Print what this project can run now and what blocks the rest (a pure read)."""
    try:
        cat = get_catalog(project)
    except Exception as exc:
        _emit(error_report(project, exc), output)
        return
    if output is OutputFormat.JSON:
        typer.echo(cat.model_dump_json(indent=2))
        return
    typer.echo(f"{project}: {cat.runnable_count} of {len(cat.entries)} classes runnable")
    for entry in cat.entries:
        why = f" -- {entry.unblock_action}" if entry.unblock_action else ""
        typer.echo(f"  {entry.case_class.value:<22} {entry.tier.value:<12} "
                   f"{'runnable' if entry.runnable else 'blocked'}{why}")


def mcp_cmd() -> None:
    """Serve AutoTester over MCP on stdio: tools run_tests, get_report, get_catalog."""
    from autotester.mcp_server import serve
    try:
        serve()
    except Exception as exc:
        typer.echo(f"mcp: {type(exc).__name__}: {exc}", err=True)
        raise typer.Exit(int(exit_code_for(exc))) from None


def attach_commands(app: typer.Typer, report_app: typer.Typer) -> None:
    """Attach these commands to the main app (kept out of `cli.py`, which sits at the C2 cap)."""
    app.command("run")(run_tests_cmd)
    app.command("catalog")(catalog_cmd)
    app.command("mcp")(mcp_cmd)
    report_app.command("show")(report_show_cmd)
