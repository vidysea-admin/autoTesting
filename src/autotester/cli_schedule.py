"""`autotester schedule tick`: the stateless pass that makes scheduled tests run (T-200, TS7).

One job: the command line of `stages/schedule_wiring.py::tick_all`. Run it from whatever
drives it on this machine (by hand, or a timer you set up yourself): it claims each due slot,
asks the credential gate, and puts one entry in the run queue, then writes the heartbeat. It
holds no runner and imports no browser (TS6): its queue executes through `ui/routes_runs.py`,
the same door the Run button uses, and `launch_run` re-checks every gate.

Exit 0: nothing due, or all handled. 2: a slot was blocked, refused or failed, or a project
errored. 3: a stored schedule would not load. `--dry-run` claims nothing, opens no queue and
writes no heartbeat. `--output json` prints one document on stdout; warnings go to stderr.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

import typer

from autotester.schema.run_queue import QueueEntry
from autotester.schema.schedule import TickReport
from autotester.stages.schedule_wiring import LazyQueue, NullQueue, Submitter, tick_all
from autotester.stages.scheduler import grace_from_env

app = typer.Typer(help="The scheduler: run the tests that are due.")


class OutputFormat(StrEnum):
    TEXT = "text"
    JSON = "json"


def _now() -> datetime:
    return datetime.now(UTC)


def _open_queue() -> Submitter:
    from autotester.ui.routes_runs import (
        tick_queue,  # lazy: the UI stack loads only for a real tick
    )

    return tick_queue()


def _text(report: TickReport) -> str:
    lines = [f"tick at {report.tick_at.isoformat()}" + (" (dry run)" if report.dry_run else "")]
    lines += [f"{r.project}  {r.outcome.value}  {r.slot_key}" + (f"  {r.detail}" if r.detail
                                                                else "") for r in report.records]
    lines += [f"{key}  would fire" for key in report.would_fire]
    lines += [f"{key}  would be blocked" for key in report.would_block]
    lines += [f"{slug}  schedule invalid" for slug in report.invalid]
    lines += [f"error  {error}" for error in report.errors]
    return "\n".join(lines)


@app.command("tick")
def tick_cmd(
    project: Annotated[str | None, typer.Option("--project", help="tick only this project")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="show what would fire")] = False,
    output: Annotated[OutputFormat, typer.Option("--output", help="text or json")
                      ] = OutputFormat.TEXT,
) -> None:
    """One scheduler pass: enqueue every due slot, record every decision, write the heartbeat."""
    grace, warning = grace_from_env(os.environ)
    if warning:
        typer.echo(warning, err=True)
    queue = NullQueue() if dry_run else LazyQueue(_open_queue)
    report = tick_all(_now(), queue=queue, only=project, dry_run=dry_run, grace_minutes=grace,
                      persisted=_server_queue)
    typer.echo(report.model_dump_json(indent=2) if output is OutputFormat.JSON else _text(report))
    raise typer.Exit(report.exit_code)


def _server_queue() -> list[QueueEntry]:
    from autotester.ui.run_queue import persisted_entries  # the server's file, read only

    return persisted_entries()
