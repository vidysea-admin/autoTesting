"""`autotester ingest zip` and `ingest fetch-drive`: hand over recordings without the browser.

Contract: team-intake.md TI3 (one JSON/table row per member), TI5 (exit code 2 on anything but a
clean intake), TI7 (`fetch-drive <file-id-or-link>`). Registered on the `ingest` app by a
two-line hook in `cli_video.py`, which is at its line budget.
"""

from __future__ import annotations

from pathlib import Path

import typer

from autotester.schema.intake import IntakeReport
from autotester.sources.drive_intake import default_drive, intake_drive
from autotester.sources.drive_link import DriveLinkError, parse_drive_link
from autotester.sources.intake_commit import IntakeBusy
from autotester.sources.zip_intake import expand_zip
from autotester.stages.ingest import project_redactor
from autotester.store.project_store import ProjectStore

_WHO = typer.Option(None, "--uploaded-by", help="email of the person handing the files over")
_JSON = typer.Option(False, "--json", help="print the report as JSON")


def render_report(report: IntakeReport) -> str:
    """The per-member table as plain text: one outcome and reason per row."""
    lines = [f"{report.archive}: {report.status.value} "
             + ", ".join(f"{n} {k}" for k, n in report.counts.items() if n)]
    lines += [f"  {m.outcome.value:10} {m.member}" + (f"  -- {m.reason}" if m.reason else "")
              for m in report.members]
    lines += [f"  note: {n}" for n in report.notes]
    return "\n".join(lines)


def _store(project: str) -> ProjectStore:
    store = ProjectStore(project)
    if store.load_project() is None:
        typer.secho(f"no project '{project}' yet", fg=typer.colors.RED)
        raise typer.Exit(1)
    return store


def _finish(report: IntakeReport, as_json: bool) -> None:
    typer.echo(report.model_dump_json(indent=2) if as_json else render_report(report))
    raise typer.Exit(report.exit_code)


def zip_cmd(project: str = typer.Argument(..., help="project slug"),
            archive: str = typer.Argument(..., help="path to the .zip of recordings"),
            uploaded_by: str = _WHO, as_json: bool = _JSON) -> None:
    """Register every video in a zip; exit 2 when any member failed (never 0 for partial)."""
    store, path = _store(project), Path(archive)
    if not path.is_file():
        typer.secho("that zip file was not found", fg=typer.colors.RED)
        raise typer.Exit(1)
    try:
        report = expand_zip(store, path, uploaded_by=uploaded_by,
                            scrub=project_redactor(project).scrub)
    except IntakeBusy as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(2) from None
    _finish(report, as_json)


def fetch_drive_cmd(project: str = typer.Argument(..., help="project slug"),
                    link: str = typer.Argument(..., help="Drive file/folder link or id"),
                    uploaded_by: str = _WHO, as_json: bool = _JSON) -> None:
    """Fetch a Google Drive video, folder or zip through the server's `gws` login."""
    store = _store(project)
    try:
        ref = parse_drive_link(link)
    except DriveLinkError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(2) from None
    report = intake_drive(store, ref, default_drive(store), uploaded_by=uploaded_by,
                          scrub=project_redactor(project).scrub)
    _finish(report, as_json)


def register_intake_commands(app: typer.Typer) -> None:
    app.command("zip")(zip_cmd)
    app.command("fetch-drive")(fetch_drive_cmd)
