"""`autotester release` / `release-log` — the release manager's way to run the whole suite (T-167).

`release <project>` stitches every flow's persisted plan into one release run: it is refused
(exit 2, with the grant command) unless a signed `RunApproval` covers it, then pauses at the
human confirm; `--approve-by NAME` / `--decline-by NAME` answers that pause on the same
`--run-id`. `release-log` prints the finished run's single issues log and its regression diff.
`release-report` writes the one damage-control report file for a run (T-168).
This CLI wires no live executor yet: EXECUTE/GRADE come from the stage runners a host injects
into `stages/release.py::start_release` (T-174/T-203), so a confirmed run stops there and says so.
"""

from __future__ import annotations

from pathlib import Path

import typer

from autotester.browser.secrets import SecretStore
from autotester.core.consent import ApprovalRequired
from autotester.core.ids import run_id as mint_run_id
from autotester.core.paths import ProjectPaths
from autotester.schema.release import ReleaseDecision, ReleaseRecord, ReleaseScope
from autotester.schema.run_state import RunState
from autotester.stages.release import ReleaseError, start_release
from autotester.stages.unified_report import (
    ReportUnavailable,
    ReportUnreadable,
    export_unified_html,
)
from autotester.store.project_store import ProjectStore


def _echo_scope(scope: ReleaseScope) -> None:
    """What the pause is asking the release manager to approve (AT-899)."""
    for plan in scope.plans:
        typer.echo(f"  flow {plan.flow_id} - {len(plan.case_ids)} case(s)")
    typer.echo(f"  scope: {len(scope.case_ids)} case(s), up to {scope.max_actions} action(s)")
    typer.echo(f"  build: {scope.git_sha or 'not given (pass --git-sha)'}")
    if scope.unplanned_flow_ids:
        typer.echo("  unplanned (reported `not run`): " + ", ".join(scope.unplanned_flow_ids))


def _echo_closing(project: str, state: RunState, scope: ReleaseScope | None) -> None:
    pending = state.next_pending()
    decision = state.release_decision
    if decision is not None and not decision.approved:
        typer.secho(f"declined by {decision.by}: release stopped, nothing was run and no "
                    "release record exists", fg=typer.colors.YELLOW)
        typer.echo(f"next: `autotester release {project}` starts a new release")
    elif pending is None:
        typer.secho(f"finished - see `autotester release-log {project} {state.run_id}`")
    elif pending.status == "awaiting_human":
        if scope is not None:
            _echo_scope(scope)
        typer.secho(f"paused for your decision: `autotester release {project} --run-id "
                    f"{state.run_id} --approve-by <name>` (or --decline-by <name>)",
                    fg=typer.colors.YELLOW)
    else:
        by = f"approved by {decision.by}: " if decision is not None else ""
        typer.secho(f"{by}stopped at {pending.stage.value}: no executor is wired into this CLI "
                    "(a host injects EXECUTE/GRADE runners)", fg=typer.colors.YELLOW)
        typer.echo(f"next: once a host has run it, `autotester release-log {project} "
                   f"{state.run_id}` prints the issues log")


def _echo_state(project: str, state: RunState, scope: ReleaseScope | None = None) -> None:
    typer.secho(f"{project}: release {state.run_id}", fg=typer.colors.GREEN)
    for cp in state.stages:
        colour = {"done": typer.colors.GREEN, "failed": typer.colors.RED,
                  "skipped": typer.colors.GREEN}.get(cp.status, typer.colors.YELLOW)
        typer.secho(f"  {cp.stage.value:8} {cp.status}" + (f" - {cp.error}" if cp.error else ""),
                    fg=colour)
    _echo_closing(project, state, scope)


def release_cmd(
    project: str = typer.Argument(..., help="project slug"),
    run_id: str = typer.Option(None, "--run-id", help="resume this release (default: new)"),
    approve_by: str = typer.Option(None, "--approve-by", help="answer the pause: go ahead"),
    decline_by: str = typer.Option(None, "--decline-by", help="answer the pause: do not run"),
    git_sha: str = typer.Option(None, "--git-sha", help="the build under release"),
) -> None:
    """Run (or resume) a release: every flow's validation plan, one issues log."""
    store = ProjectStore(project)
    proj = store.load_project()
    if proj is None:
        typer.secho(f"no project '{project}' yet", fg=typer.colors.RED)
        raise typer.Exit(1)
    if approve_by and decline_by:
        typer.secho("pass --approve-by OR --decline-by, not both", fg=typer.colors.RED)
        raise typer.Exit(1)
    by = approve_by or decline_by
    decision = ReleaseDecision(approved=bool(approve_by), by=by) if by else None
    secrets = SecretStore.load(proj, ProjectPaths(project).env_file, strict=False)
    rid = run_id or mint_run_id("rel")
    try:
        state = start_release(proj, store, run_id=rid, runners={},
                              secrets=secrets, git_sha=git_sha, decision=decision)
    except (ApprovalRequired, ReleaseError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(2) from None
    except ValueError:
        if decision is None:
            raise
        typer.secho(f"release {rid} is not waiting for an answer - already answered (or never "
                    f"paused); see `autotester release-log {project} {rid}`", fg=typer.colors.RED)
        raise typer.Exit(1) from None
    _echo_state(project, state, store.load_release_scope(rid))


def _echo_log(record: ReleaseRecord) -> None:
    for flow in record.flows:
        typer.echo(f"flow {flow.flow_id}: {flow.status.replace('_', ' ')}")
    typer.echo(f"issues: {len(record.issues)}")
    for issue in record.issues:
        typer.echo(f"  [{issue.flow_id}] {issue.case_id or '-'} {issue.kind}: {issue.detail}")
    diff = record.diff
    typer.echo(f"baseline: {diff.baseline_run_id or 'none'} - {diff.note}")
    typer.echo(f"regressed: {', '.join(diff.regressed) or '-'}; fixed: "
               f"{', '.join(diff.fixed) or '-'}")


def release_log_cmd(project: str = typer.Argument(...), run_id: str = typer.Argument(...)) -> None:
    """Print a finished release's single issues log and regression diff."""
    record = ProjectStore(project).load_release_record(run_id)
    if record is None:
        typer.secho(f"no release record for {project} run {run_id}", fg=typer.colors.RED)
        raise typer.Exit(1)
    _echo_log(record)


def release_report_cmd(
    project: str = typer.Argument(..., help="project slug"),
    run_id: str = typer.Argument(None, help="run to report on (default: the newest)"),
    out: str = typer.Option(..., "--out", help="output .html path"),
) -> None:
    """Write the damage-control report: regression, API failures, workflows, change history."""
    try:
        path = export_unified_html(project, run_id, Path(out))
    except (ReportUnavailable, ReportUnreadable) as exc:  # fixed text, never stored values (DC4)
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(1) from None
    typer.secho(f"wrote {path}", fg=typer.colors.GREEN)
