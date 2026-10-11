"""Command line. Every action the UI offers is available here first."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import typer

from autotester import (
    cli_crawl,
    cli_issues,
    cli_loop,
    cli_orchestrate,
    cli_release,
    cli_video,
    providers,
)
from autotester import doctor as doctor_module
from autotester.cli_auth import app as auth_app
from autotester.core.env import load_repo_env
from autotester.core.paths import RepoDocs
from autotester.ledger import render, store
from autotester.ledger.relitigation import gate_message, relitigate
from autotester.providers.base import ProviderError
from autotester.schema.enums import FeatureEventKind, UserValue
from autotester.stages import expand as expand_stage
from autotester.stages import manual_login as manual_login_stage
from autotester.stages import report_export
from autotester.stages import review as review_stage
from autotester.store import ProjectStore

app = typer.Typer(help="AutoTester — AI automated end-to-end tester", no_args_is_help=True)
ledger_app = typer.Typer(help="The feature ledger (docs/FEATURES.jsonl) — the only write path.")
flowspec_app = typer.Typer(help="The FlowSpec review gate — nothing expands an unreviewed spec.")
report_app = typer.Typer(help="Export a run as a portable tester report (Excel + HTML).")
app.add_typer(ledger_app, name="ledger")
app.add_typer(flowspec_app, name="flowspec")
app.add_typer(report_app, name="report")
app.add_typer(cli_video.app, name="ingest")
app.add_typer(cli_issues.app, name="issues")
app.add_typer(auth_app, name="auth")


@app.callback()
def _bootstrap() -> None:
    """Runs before every command: load the repo-root `.env` the web UI already loads, so both
    entry points agree on whether this machine has credentials (AT-228)."""
    load_repo_env()


@app.command()
def doctor() -> None:
    """Check the repo against the design rules that keep it readable."""
    violations = doctor_module.run()
    if not violations:
        typer.secho("doctor: clean", fg=typer.colors.GREEN)
        raise typer.Exit(0)
    for violation in violations:
        typer.secho(str(violation), fg=typer.colors.RED)
    typer.secho(f"\n{len(violations)} violation(s)", fg=typer.colors.RED, bold=True)
    raise typer.Exit(1)


@app.command("providers")
def providers_check() -> None:
    """Show which model providers have credentials present on this machine."""
    ready = providers.available_ids()
    typer.echo("available providers: " + (", ".join(ready) if ready else "none"))


@app.command("map")
def map_cmd() -> None:
    """Regenerate docs/MAP.md — directory map + schema summary, derived from code."""
    docs = RepoDocs()
    docs.map.write_text(render.apply_map(docs), encoding="utf-8")
    typer.secho("map: docs/MAP.md regenerated", fg=typer.colors.GREEN)


@app.command()
def snapshot(print_only: bool = typer.Option(False, "--print", help="print, do not write")) -> None:
    """Regenerate docs/SNAPSHOT.md — the digest injected at session start."""
    docs = RepoDocs()
    text = render.render_snapshot(docs)
    if print_only:
        typer.echo(text)
        return
    docs.snapshot.write_text(text, encoding="utf-8")
    typer.secho(f"snapshot: {text.count(chr(10))} lines written", fg=typer.colors.GREEN)


@ledger_app.command("add")
def ledger_add(
    feature: str,
    title: str,
    event: FeatureEventKind,
    description: str = typer.Option(..., "--description", "-d"),
    reason: str | None = typer.Option(None, "--reason", "-r"),
    user_value: UserValue = typer.Option(UserValue.NORMAL, "--value"),
    unit: str | None = typer.Option(None, "--unit"),
    verdict_ref: str | None = typer.Option(None, "--verdict"),
    supersedes: str | None = typer.Option(None, "--supersedes"),
    on: str | None = typer.Option(None, "--date", help="YYYY-MM-DD, default today"),
) -> None:
    """Append one feature event. Retirements require a real --reason."""
    docs = RepoDocs()
    events = store.load_events(docs.features)
    row = store.new_event(
        events, feature=feature, title=title, event=event, description=description,
        user_value=user_value, reason=reason, unit=unit, verdict_ref=verdict_ref,
        supersedes=supersedes, on=date.fromisoformat(on) if on else None,
    )
    store.append_event(docs.features, row)
    docs.snapshot.write_text(render.render_snapshot(docs), encoding="utf-8")
    typer.secho(f"{row.id} {row.event.value} {row.feature}", fg=typer.colors.GREEN)
    if row.ask_required:
        typer.secho("ASK: high-value feature with auto reason — confirm or edit the reason "
                    "(`ledger add ... updated --reason ...`)", fg=typer.colors.YELLOW)


@ledger_app.command("weight")
def ledger_weight(feature: str, value: UserValue) -> None:
    """Re-weight a feature after shipping. Raising to high asks for the reason once."""
    docs = RepoDocs()
    row = store.raise_weight(docs.features, feature, value)
    docs.snapshot.write_text(render.render_snapshot(docs), encoding="utf-8")
    typer.secho(f"{row.id} weight -> {value.value}", fg=typer.colors.GREEN)
    if row.ask_required:
        typer.secho("ASK: now high-value — provide the reasoning for this feature",
                    fg=typer.colors.YELLOW)


@ledger_app.command("check")
def ledger_check() -> None:
    """L3: every closed high-value goal task has a live/updated row."""
    docs = RepoDocs()
    events = store.load_events(docs.features)
    missing = store.check_rows_on_pass(events, store.load_goal_tasks(docs.goal))
    if missing:
        typer.secho("missing ledger rows for: " + ", ".join(missing), fg=typer.colors.RED)
        raise typer.Exit(1)
    typer.secho("ledger: every closed high-value task has a row", fg=typer.colors.GREEN)


@ledger_app.command("relitigation")
def ledger_relitigation(unit_text: str, provider: str = typer.Option("mock", "--provider")) -> None:
    """Gate check before a unit is built: is this a retired feature coming back?"""
    docs = RepoDocs()
    retired = store.retired(store.load_events(docs.features))
    verdict = relitigate(unit_text, retired, providers.get(provider), docs)
    if verdict.gate:
        typer.secho(gate_message(verdict, retired), fg=typer.colors.YELLOW)
        raise typer.Exit(2)
    typer.secho(f"no gate — {verdict.justification} ({verdict.decided_by})", fg=typer.colors.GREEN)


@flowspec_app.command("status")
def flowspec_status(project: str) -> None:
    """Show a project's FlowSpec review status."""
    spec = ProjectStore(project).load_flowspec()
    if spec is None:
        typer.secho(f"no flowspec for '{project}' yet", fg=typer.colors.YELLOW)
        raise typer.Exit(1)
    typer.echo(f"{project}: {spec.review.status.value}"
               + (f" — {spec.review.note}" if spec.review.note else ""))


@flowspec_app.command("approve")
def flowspec_approve(
    project: str,
    by: str = typer.Option(..., "--by"),
    note: str | None = typer.Option(None, "--note"),
) -> None:
    """A human approves the project's FlowSpec as-is — required before T-070 expands it."""
    store_ = ProjectStore(project)
    spec = store_.load_flowspec()
    if spec is None:
        typer.secho(f"no flowspec for '{project}' yet", fg=typer.colors.RED)
        raise typer.Exit(1)
    store_.save_flowspec(review_stage.approve(spec, by, note))
    typer.secho(f"{project}: flowspec approved by {by}", fg=typer.colors.GREEN)


@flowspec_app.command("request-edit")
def flowspec_request_edit(
    project: str, by: str = typer.Option(..., "--by"), note: str = typer.Option(..., "--note")
) -> None:
    """A human found something wrong — back to draft with the reason recorded."""
    store_ = ProjectStore(project)
    spec = store_.load_flowspec()
    if spec is None:
        typer.secho(f"no flowspec for '{project}' yet", fg=typer.colors.RED)
        raise typer.Exit(1)
    store_.save_flowspec(review_stage.request_edit(spec, by, note))
    typer.secho(f"{project}: flowspec sent back for edit by {by}", fg=typer.colors.YELLOW)


@app.command("expand")
def expand_cases(
    project: str,
    provider: str = typer.Option("langchain-fallback", "--provider"),
    proposals: bool = typer.Option(False, "--proposals", help="Stage/list step-less proposals."),
    approve: list[str] = typer.Option([], "--approve", help="Approve a saved proposal ID."),
    prune: list[str] = typer.Option([], "--prune", help="Prune a saved proposal ID."),
    by: str = typer.Option("", "--by", help="Human reviewer; required for decisions."),
) -> None:
    """Review/prune proposals, then generate only persisted human-approved cases.

    AT-239: persisting is this caller's job (expand.md no-fire); AT-260: a provider failure
    discards every in-memory case, so nothing is persisted."""
    store_ = ProjectStore(project)
    if store_.load_project() is None:
        typer.secho(f"no project '{project}'", fg=typer.colors.RED)
        raise typer.Exit(1)
    spec = store_.load_flowspec()
    if spec is None:
        typer.secho(f"no flowspec for '{project}' yet — ingest a recording first", fg="red")
        raise typer.Exit(1)
    try:
        rows = expand_stage.stage_and_review(store_, spec, approve, prune, by)
        if proposals or approve or prune:
            for row in rows:
                typer.echo(f"{row.id} {row.status} {row.case_class.value}: {row.title}")
            return
        store_.preflight_case_proposals(spec)
    except (ValueError, review_stage.FlowSpecNotReviewed) as exc:
        typer.secho(f"{exc}; review with `autotester expand {project} --proposals`", fg="yellow")
        raise typer.Exit(1) from None
    model = cli_orchestrate.usable_provider(provider)   # LL11: refuses before any model call
    try:
        cases = expand_stage.expand(spec, model, store=store_)
    except (ValueError, review_stage.FlowSpecNotReviewed, ProviderError) as exc:
        typer.secho(f"{project}: generation failed, no cases persisted — {exc}", fg="red")
        raise typer.Exit(1) from None
    new = sum(0 if store_.has_case(case.id) else 1 for case in cases)
    for case in cases:
        store_.add_case(case)
    typer.secho(f"{project}: {len(cases)} case(s) from {len(spec.flows)} flow(s), {new} new",
                fg="green")


@app.command("login")
def login(project: str) -> None:
    """Open a real browser for a human to log in by hand -- no password needed.
    Contract: qa/contracts/manual-login.md. The session is saved into the
    project's persistent profile; every later run reuses it."""
    store_ = ProjectStore(project)
    proj = store_.load_project()
    if proj is None:
        typer.secho(f"no project '{project}' yet", fg=typer.colors.RED)
        raise typer.Exit(1)
    manual_login_stage.manual_login(proj)
    typer.secho(f"{project}: login session saved", fg=typer.colors.GREEN)


@report_app.command("excel")
def report_excel(
    project: str,
    run_id: str | None = typer.Argument(None),
    out: str = typer.Option(..., "--out", help="output .xlsx path"),
) -> None:
    """One row per case: outcome, verdict, criteria met, duration."""
    try:
        path = report_export.export_excel(project, run_id, Path(out))
    except ValueError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(1) from exc
    typer.secho(f"wrote {path}", fg=typer.colors.GREEN)


@report_app.command("html")
def report_html(
    project: str,
    run_id: str | None = typer.Argument(None),
    out: str = typer.Option(..., "--out", help="output .html path"),
) -> None:
    """Screen-by-screen report with embedded screenshots, one file, portable."""
    try:
        path = report_export.export_html(project, run_id, Path(out))
    except ValueError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(1) from exc
    typer.secho(f"wrote {path}", fg=typer.colors.GREEN)


app.command("loop-status")(cli_loop.loop_status_cmd)
app.command("explore")(cli_crawl.explore_cmd)
app.command("approve")(cli_crawl.approve_cmd)
report_app.command("crawl")(cli_crawl.report_crawl)
app.command("orchestrate")(cli_orchestrate.orchestrate_cmd)
app.command("release")(cli_release.release_cmd)
app.command("release-log")(cli_release.release_log_cmd)
app.command("release-report")(cli_release.release_report_cmd)


def main() -> None:
    app()
