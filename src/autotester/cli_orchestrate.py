"""`autotester orchestrate` — the live caller of `stages/orchestrate.py::run_or_resume`.

AT-575: T-163's resumable orchestrator (D-036) had no entry point outside its
own tests (`tests/test_orchestrate*.py`), so resume-after-interruption was
reachable only from pytest. This command drives that SAME `run_or_resume`,
wiring the two entry stages (INGEST/DISCOVER) plus MODEL — the orchestrator
stops at the review gate by design (contract `orchestrator.md`, D-036); a
human runs `flowspec approve` then `expand` to continue, exactly as they do
today after a manual `ingest run` or `explore --merge`.

Split out of `cli.py` for the same reason `cli_crawl.py` is: that file is at
its line budget, and a stage's commands belong beside the stage they drive.
No new logic is added here beyond wiring — the stage adapters
(`stages/orchestrate_runners.py`) and `cli_crawl.py`'s own D-018 consent
preflight (`_preflight_consent`) are called directly, never copied (C3,
checker cycle 1: a statement-for-statement copy of a security gate is a bug
waiting to drift the first time one copy is tightened and the other isn't).

Cycle 2 (checker FAIL, verdict `a6efb6c`) also fixed: a resume now reads
`mode` from the STORED `RunState` rather than recomputing `choose_mode` on the
current sources (a changed source set could otherwise mismatch runner vs
state), and the crawl-consent preflight is skipped on resume ONLY when the
stored DISCOVER checkpoint's status is exactly `"done"` — failed, pending, or
no DISCOVER checkpoint at all still hits it. An unknown `--run-id` (no
`state.json` on disk) is treated as a fresh run, with a one-line note.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import typer

from autotester import cli_crawl, providers
from autotester.core.ids import run_id as mint_run_id
from autotester.core.paths import ProjectPaths, RepoDocs
from autotester.schema.run_state import RunState, StageName
from autotester.stages.orchestrate import TEACHING_KINDS, StageContext, choose_mode, run_or_resume
from autotester.stages.orchestrate_runners import (
    make_discover_runner,
    make_ingest_runner,
    make_model_runner,
)
from autotester.store.filestore import read_json
from autotester.store.project_store import ProjectStore

if TYPE_CHECKING:
    from autotester.browser.secrets import SecretStore
    from autotester.schema.crawl import Crawl
    from autotester.schema.project import Project, Source
    from autotester.schema.screen_graph import ScreenNode


class NoEntrySource(RuntimeError):
    """`learn` mode needs a teaching Source to (re)run INGEST, and none of the
    project's current sources qualify — named honestly rather than a raw
    `StopIteration` from deep inside a generator."""


def _entry_source(sources: list[Source]) -> Source | None:
    """The Source INGEST watches, or None if the project currently has none
    (a resume can be asked to retry INGEST after its teaching Source was
    removed — that is a clean refusal, not a crash). The earliest match (list
    order = registration order) keeps a re-run deterministic."""
    return next((s for s in sources if s.kind in TEACHING_KINDS), None)


def _load_state(store_: ProjectStore, run_id: str) -> RunState | None:
    """The prior `RunState` for this exact run_id, or None for a fresh /
    unknown one — `state.json` simply not existing yet is not an error."""
    return read_json(store_.paths.run_dir(run_id) / "state.json", RunState)


def _entry_done(prior: RunState | None, mode: str) -> bool:
    """Whether THIS run's entry stage (INGEST for learn, DISCOVER for
    explore) is already `done` in the stored state. Only an exact `"done"`
    counts — `failed`, `pending`, or no checkpoint at all (no prior state, or
    a state from before that stage existed) all mean the entry stage still
    has to run, so its wiring (and, for explore, the consent preflight) is
    still required."""
    if prior is None:
        return False
    stage = StageName.INGEST if mode == "learn" else StageName.DISCOVER
    checkpoint = prior.checkpoint(stage)
    return checkpoint is not None and checkpoint.status == "done"


def _make_crawl_fn(
    proj: Project, store_: ProjectStore, paths: ProjectPaths, secrets: SecretStore,
    bounds: object, login_case_id: str | None,
) -> Callable[[], tuple[Crawl, list[ScreenNode]]]:
    """The DISCOVER stage's injected `crawl_fn` (`orchestrate_runners.py`'s own
    seam): opens the browser and runs the existing bounded-BFS crawl only when
    the DISCOVER stage actually executes, exactly like `explore_cmd` does."""

    def _run() -> tuple[Crawl, list[ScreenNode]]:
        from autotester.browser.observe import PageObserver
        from autotester.browser.session import BrowserSession
        from autotester.stages import explore as explore_stage

        paths.ensure()
        case = store_.get_case(login_case_id) if login_case_id else None
        observer = PageObserver()
        crawl_id = mint_run_id("crawl")
        with BrowserSession(proj, secrets, paths.crawl_shots_dir(crawl_id), paths,
                            observer=observer) as session:
            crawl = explore_stage.run_crawl(proj, session, store_, observer=observer,
                                            bounds=bounds, login_case=case, crawl_id=crawl_id)
        return crawl, store_.list_nodes(crawl.id)

    return _run


def _learn_runners(
    sources: list[Source], project: str, provider_id: str, *, entry_done: bool,
) -> dict[StageName, Callable]:
    """INGEST + MODEL — or, on a resume past a `done` INGEST, MODEL alone: a
    completed INGEST is never re-wired, so a since-removed teaching Source
    cannot break a resume that will never touch it again."""
    if entry_done:
        return {StageName.MODEL: make_model_runner()}
    source = _entry_source(sources)
    if source is None:
        raise NoEntrySource(
            f"{project}: learn mode needs a teaching Source (video/doc/text/audio/email/drive) "
            "to run INGEST, and none is registered — `autotester ingest register` one first")
    model = providers.get(provider_id)
    return {
        StageName.INGEST: make_ingest_runner(source, project, model, RepoDocs()),
        StageName.MODEL: make_model_runner(source_id=source.id),
    }


def _explore_runners(
    proj: Project, store_: ProjectStore, paths: ProjectPaths, secrets: SecretStore,
    bounds: object, login_case_id: str | None, *, entry_done: bool,
) -> dict[StageName, Callable]:
    """DISCOVER + MODEL — or, on a resume past a `done` DISCOVER, MODEL alone.
    The D-018 consent preflight (`cli_crawl._preflight_consent`, the same
    check `explore` runs) is skipped ONLY in that resumed case: no browser
    will open, so an approval that has since expired must not block a resume
    that never needed it."""
    if entry_done:
        return {StageName.MODEL: make_model_runner()}
    cli_crawl._preflight_consent(proj, store_, bounds)
    crawl_fn = _make_crawl_fn(proj, store_, paths, secrets, bounds, login_case_id)
    return {
        StageName.DISCOVER: make_discover_runner(proj, crawl_fn),
        StageName.MODEL: make_model_runner(),
    }


def _resolve_run(
    store_: ProjectStore, sources: list[Source], run_id: str | None,
) -> tuple[str, str, bool]:
    """This invocation's run_id, mode, and whether its entry stage is already
    `done` — the one place that reads (or fails to find) prior `RunState` and
    decides mode from IT rather than from `choose_mode` on a resume, printing
    a one-line note for an explicitly-named but unknown run_id."""
    this_run = run_id or mint_run_id("run")
    prior = _load_state(store_, this_run) if run_id else None
    if run_id and prior is None:
        typer.secho(f"no existing run '{run_id}' for {store_.paths.slug} — starting fresh",
                    fg=typer.colors.YELLOW)
    mode = prior.mode if prior is not None else choose_mode(sources)[0]
    return this_run, mode, _entry_done(prior, mode)


def _build_runners(
    mode: str, sources: list[Source], project: str, proj: Project, store_: ProjectStore,
    paths: ProjectPaths, secrets: SecretStore, provider_id: str, bounds: object,
    login_case_id: str | None, *, entry_done: bool,
) -> dict[StageName, Callable]:
    """The autonomous run wires exactly {INGEST|DISCOVER, MODEL} (STOP point
    at the review gate, `orchestrate.py`'s own contract) — never EXPAND
    onward, so this never grows into a second approval mechanism (OR-no-fire)."""
    if mode == "learn":
        return _learn_runners(sources, project, provider_id, entry_done=entry_done)
    return _explore_runners(proj, store_, paths, secrets, bounds, login_case_id,
                            entry_done=entry_done)


def _echo_state(project: str, state: RunState) -> bool:
    """Print every checkpoint and say what to do next. Returns whether the run
    is clean (no failed stage) — the command's exit code hangs off this."""
    typer.secho(f"{project}: run {state.run_id} — {state.mode} ({state.mode_reason})",
                fg=typer.colors.GREEN)
    ok = True
    for checkpoint in state.stages:
        colour = {"done": typer.colors.GREEN, "failed": typer.colors.RED,
                 "skipped": typer.colors.GREEN}.get(checkpoint.status, typer.colors.YELLOW)
        line = f"  {checkpoint.stage.value:8} {checkpoint.status}"
        if checkpoint.error:
            line += f" — {checkpoint.error}"
            ok = False
        typer.secho(line, fg=colour)
    pending = state.next_pending()
    if pending is None:
        typer.secho("run complete through the wired stages (INGEST|DISCOVER -> MODEL)",
                    fg=typer.colors.GREEN)
    elif pending.status == "failed":
        typer.secho(f"resume with: --run-id {state.run_id}", fg=typer.colors.YELLOW)
    else:
        typer.secho(
            f"stopped at the review gate — `flowspec approve {project} --by <name>` then "
            f"`expand {project}` to continue (resume with --run-id {state.run_id})",
            fg=typer.colors.YELLOW)
    return ok


def orchestrate_cmd(
    project: str = typer.Argument(..., help="project slug"),
    run_id: str = typer.Option(
        None, "--run-id",
        help="resume this run (pass the id a previous invocation printed); "
             "default mints a fresh one; an id with no state on disk starts fresh too"),
    provider: str = typer.Option("gemini", "--provider", help="ingest provider (learn path only)"),
    max_screens: int = typer.Option(30, "--max-screens", help="explore path only"),
    max_actions: int = typer.Option(200, "--max-actions", help="explore path only"),
    wall_clock: float = typer.Option(600.0, "--wall-clock", help="seconds; explore path only"),
    max_depth: int = typer.Option(6, "--max-depth", help="explore path only"),
    login_case: str | None = typer.Option(None, "--login-case", help="explore path only"),
) -> None:
    """Run (or resume) the pipeline for `project`: the same entry-path choice
    (teach->INGEST / creds->DISCOVER) and per-stage `RunState` checkpoints
    `stages/orchestrate.py::run_or_resume` and its tests exercise, now reachable
    from the command line. Stops at the review gate (contract `orchestrator.md`).
    """
    from autotester.browser.secrets import SecretStore
    from autotester.schema.crawl import CrawlBounds

    store_ = ProjectStore(project)
    proj = store_.load_project()
    if proj is None:
        typer.secho(f"no project '{project}' yet", fg=typer.colors.RED)
        raise typer.Exit(1)

    sources = store_.list_sources()
    paths = ProjectPaths(project)
    secrets = SecretStore.load(proj, paths.env_file, strict=False)
    bounds = CrawlBounds(max_screens=max_screens, max_actions=max_actions,
                         wall_clock_s=wall_clock, max_depth=max_depth)

    this_run, mode, entry_done = _resolve_run(store_, sources, run_id)

    try:
        runners = _build_runners(mode, sources, project, proj, store_, paths, secrets, provider,
                                 bounds, login_case, entry_done=entry_done)
    except NoEntrySource as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(1) from None

    ctx = StageContext(store=store_, run_id=this_run, runners=runners, secrets=secrets)
    state = run_or_resume(proj, ctx)
    ok = _echo_state(project, state)
    if not ok:
        raise typer.Exit(1)
