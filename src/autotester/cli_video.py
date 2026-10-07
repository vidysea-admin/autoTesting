"""`autotester ingest` — register a recording and learn a FlowSpec from it.

Separate from `cli.py` for the same reason `cli_crawl.py` is: that file is at
its line budget, and a stage's commands belong beside the stage they drive.
"""

from __future__ import annotations

from pathlib import Path

import typer

from autotester import providers
from autotester.core.paths import RepoDocs
from autotester.schema.enums import ReviewStatus
from autotester.schema.flowspec import StepRef
from autotester.schema.observation import VisionOptions
from autotester.stages.analyze_video import load_transcript
from autotester.stages.ingest import (
    FlowSpecApproved,
    NotARecording,
    SourceChanged,
    ingest_video,
    persist_ingest,
    register_source,
)
from autotester.stages.media_prep import SourceNotPrepared, UnreadableRecording
from autotester.stages.merge_flowspec import merge_flowspec, open_requests, resolve_requests
from autotester.stages.reconcile import narration_drop_report
from autotester.store.project_store import ProjectStore

app = typer.Typer(help="Learn a product's screens and flows from a screen recording.")


@app.command("register")
def register_cmd(
    project: str = typer.Argument(..., help="project slug"),
    path: str = typer.Argument(..., help="path to the recording"),
    label: str = typer.Option(None, "--label", help="who recorded it and what it shows"),
    recorded_on: str = typer.Option(None, "--recorded-on", help="ISO date, e.g. 2026-08-18"),
) -> None:
    """Record a video as a Source. Idempotent on content — the same file twice
    is one source, not two."""
    store = ProjectStore(project)
    try:
        source = register_source(store, Path(path), label=label,
                                 recorded_on=recorded_on)
    except (FileNotFoundError, NotARecording) as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(2) from None
    except OSError as exc:  # AT-446: locked or permission-denied, not a traceback
        typer.secho(f"that recording could not be read ({type(exc).__name__}) — "
                    "check it is not open elsewhere and that you may read it",
                    fg=typer.colors.RED)
        raise typer.Exit(2) from None
    typer.secho(f"{source.id}  {source.label or '(no label)'}  sha256={source.sha256[:12]}",
                fg=typer.colors.GREEN)


@app.command("list")
def list_cmd(project: str = typer.Argument(..., help="project slug")) -> None:
    """Every source registered for this project."""
    store = ProjectStore(project)
    if store.load_project() is None:
        # AT-179: this printed "no sources yet" and exited 0 for a project that
        # does not exist -- indistinguishable from a real project with none.
        # Every sibling (explore, login, flowspec status) refuses on exit 1,
        # and a script branching on this one's exit code was told "fine".
        typer.secho(f"no project '{project}' yet", fg=typer.colors.RED)
        raise typer.Exit(1)
    sources = store.list_sources()
    if not sources:
        typer.secho(f"{project} has no sources yet — `autotester ingest register` adds one.",
                    fg=typer.colors.YELLOW)
        return
    for source in sources:
        typer.echo(f"{source.id}  {source.kind.value:6}  {source.recorded_on or '—':10}  "
                   f"{source.label or Path(source.path or '').name}")


@app.command("prep")
def media_prep_cmd(
    project: str = typer.Argument(..., help="project slug"),
    source_id: str = typer.Argument(..., help="a source id from `ingest list`"),
    chunk_minutes: float = typer.Option(3.0, "--chunk-minutes"),
    no_whisper: bool = typer.Option(False, "--no-whisper",
                                    help="skip transcription even if it is available"),
) -> None:
    """Probe, chunk and transcribe a recording. RUN THIS ON THE HOST — the
    container has no ffmpeg and no GPU."""
    from autotester.stages import media_prep

    store = ProjectStore(project)
    source = _require_source(store, project, source_id)
    try:
        prep = media_prep.prepare(store, source, chunk_minutes=chunk_minutes,
                                  use_whisper=not no_whisper)
    except (FileNotFoundError, ValueError, media_prep.UnreadableRecording) as exc:
        # AT-166: `UnreadableRecording` is a RuntimeError, so this clause did
        # not catch it and the shipped command answered a deliberate refusal
        # with a raw traceback. I fixed the STAGE last cycle and not the path
        # an operator actually runs -- the same mistake as AT-163, one cycle on.
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(2) from None

    transcript = store.load_transcript(source_id)
    narration = f"{len(transcript.segments) if transcript else 0} narration segment(s)"
    if transcript is not None and transcript.engine == "unreadable":  # VL1's third state (AT-465)
        narration = f"narration unreadable ({transcript.unreadable_reason or 'no cause recorded'})"
    tool = prep.ffmpeg_version or "no ffmpeg — one chunk on the original file"
    typer.secho(
        f"{source_id}: {prep.duration_s:.0f}s, {len(prep.chunks)} chunk(s), "
        f"{narration} [{tool}]",
        fg=typer.colors.GREEN,
    )


@app.command("frames")
def media_frames_cmd(
    project: str = typer.Argument(..., help="project slug"),
    source_id: str = typer.Argument(..., help="a source id from `ingest list`"),
) -> None:
    """Extract the stills the vision pass named. Needs an analysis on disk."""
    from autotester.stages import media_prep

    store = ProjectStore(project)
    source = _require_source(store, project, source_id)
    analysis = store.load_analysis(source_id)
    if analysis is None:
        # AT-172: this named `autotester ingest analyze`, which does not exist
        # -- that stage is Track A4 and is not built. Pointing an operator at a
        # future command is the same dead end as AT-163, one command over, and
        # it survived three fix cycles spent on exactly that shape. When there
        # is nothing to run, say so instead of inventing something to run.
        typer.secho(
            f"{source_id} has no analysis.json — the analyze stage (Track A4) is not "
            f"built yet, so there are no frames to extract",
            fg=typer.colors.YELLOW)
        raise typer.Exit(2)

    try:
        written = media_prep.extract_frames(store, source, analysis)
    except (FileNotFoundError, ValueError, media_prep.UnreadableRecording) as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(2) from None
    # AT-173: a vanished recording printed a GREEN `0 frame(s) written`, exit 0
    # -- success for work that could not even be attempted.
    colour = typer.colors.GREEN if written else typer.colors.YELLOW
    typer.secho(f"{source_id}: {len(written)} frame(s) written", fg=colour)


def _require_source(store: ProjectStore, project: str, source_id: str):
    source = next((s for s in store.list_sources() if s.id == source_id), None)
    if source is None:
        typer.secho(f"{project} has no source {source_id} — try `autotester ingest list`.",
                    fg=typer.colors.RED)
        raise typer.Exit(2)
    return source


def _merge_into_reviewed(store: ProjectStore, spec, source) -> None:
    """The door `merge_flowspec` needs (coverage.md V6 / expand.md X6: a stage
    with no caller is an absent feature, not a slow one — AT-220, AT-240).

    `persist_ingest`'s own refusal names this path: an APPROVED FlowSpec would
    otherwise force `--replace`, throwing away the review to accept a recording
    that was asked for. Merging keeps the review's truth, re-arms the gate, and
    closes the requests this recording actually answered."""
    merged = merge_flowspec(store.load_flowspec(), spec, source_id=source.id)
    store.save_flowspec(merged)
    closed = resolve_requests(store, merged, source_id=source.id)
    typer.secho(
        f"{merged.project}: v{merged.version}, {len(merged.screens)} screens, "
        f"{len(merged.flows)} flows after merging {source.label or source.id} "
        f"(review status {merged.review.status.value}, {len(closed)} request(s) closed)",
        fg=typer.colors.GREEN,
    )
    for request in open_requests(store):
        typer.secho(f"  still unanswered: {request.prompt}", fg=typer.colors.YELLOW)


@app.command("run")
def run_cmd(
    project: str = typer.Argument(..., help="project slug"),
    source_id: str = typer.Argument(..., help="a source id from `ingest list`"),
    provider: str = typer.Option("gemini", "--provider", help="'mock' runs without a model"),
    model: str = typer.Option(None, "--model", help="override the provider's default model"),
    replace: bool = typer.Option(False, "--replace",
                                 help="overwrite an APPROVED FlowSpec, discarding its review"),
    merge: bool = typer.Option(False, "--merge",
                               help="fold into the existing FlowSpec instead of replacing it, "
                                    "and close the video requests this recording answers"),
) -> None:
    """Watch one source and write the FlowSpec it produces."""
    if merge and replace:
        typer.secho("--merge and --replace are opposites: merge keeps the reviewed spec, "
                    "replace discards it. Pick one.", fg=typer.colors.RED)
        raise typer.Exit(2)
    store = ProjectStore(project)
    source = _require_source(store, project, source_id)

    prov = providers.get(provider, **({"model": model} if model else {}))
    dropped: list[StepRef] = []
    try:  # AT-784: the transcript media prep persisted counts when no sidecar exists
        spec = ingest_video(source, project, prov, RepoDocs(), dropped=dropped,
                            transcript=load_transcript(store, source), options=VisionOptions())
    except SourceChanged as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(2) from None
    if report := narration_drop_report(dropped):  # AT-785: ids and a count, never text
        typer.secho(report, fg=typer.colors.YELLOW)
    if merge:
        _merge_into_reviewed(store, spec, source)
        return
    try:
        persist_ingest(store, spec, replace=replace)
    except FlowSpecApproved as exc:
        typer.secho(str(exc), fg=typer.colors.YELLOW)
        raise typer.Exit(2) from None
    typer.secho(
        f"{project}: {len(spec.screens)} screens, {len(spec.flows)} flows from "
        f"{source.label or source.id} (review status {spec.review.status.value})",
        fg=typer.colors.GREEN,
    )


@app.command("analyze")
def analyze_cmd(
    project: str = typer.Argument(..., help="project slug"),
    source_id: str = typer.Argument(..., help="a source id from `ingest list`"),
    models: str = typer.Option(None, "--models",
                               help="comma-separated provider ids; two is the ensemble "
                                    "(default: the project's vision config, which may "
                                    "name several)"),
    force: bool = typer.Option(False, "--force", help="re-request cached observations"),
) -> None:
    """Run the ensemble over a prepared recording and adjudicate it.

    AT-220: `stages/analyze_video.py::analyze` shipped checker-PASSed with NO
    caller anywhere under `src/`. It could not be run, so the pipeline it sits in
    the middle of could not produce anything, and the scorer's advice named a
    command that did not exist."""
    from autotester.stages.analyze_video import DuplicateProviders, NoObservations, analyze

    store = ProjectStore(project)
    source = _require_source(store, project, source_id)
    # AT-542: default to the project's own vision config (which may name
    # several providers); an explicit --models still overrides.
    defaulted = False
    if models:
        names = models
    else:
        project_record = store.load_project()
        if project_record is not None:
            names = ",".join(project_record.providers.vision_ensemble())
            defaulted = project_record.providers.vision_ensemble_defaulted()
        else:
            names = "gemini"
    provs = [providers.get(name.strip()) for name in names.split(",") if name.strip()]
    try:
        analysis = analyze(store, source, provs, docs=RepoDocs(), options=VisionOptions(),
                           force=force, vision_config_defaulted=defaulted)
    except (SourceNotPrepared, UnreadableRecording, NoObservations, DuplicateProviders) as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(2) from None

    coverage = f"{analysis.observations_used}/{analysis.observations_expected} model calls"
    typer.secho(
        f"{project}: {len(analysis.screens)} screens, {len(analysis.issues)} issues from "
        f"{source.label or source.id} ({coverage}"
        f"{'' if analysis.is_complete else ' — PARTIAL'})",
        fg=typer.colors.GREEN if analysis.is_complete else typer.colors.YELLOW)


@app.command("map")
def map_product_cmd(project: str = typer.Argument(..., help="project slug")) -> None:
    """Fold every persisted video analysis into the project's product map."""
    from autotester.stages.product_map import attach_screenshots, build_screen_map

    store = ProjectStore(project)
    if store.load_project() is None:
        typer.secho(f"no project '{project}' yet", fg=typer.colors.RED)
        raise typer.Exit(1)
    screen_map = build_screen_map(store)
    store.save_screen_map(screen_map)
    spec = store.load_flowspec()
    if spec is not None and spec.review.status is not ReviewStatus.APPROVED:
        store.save_flowspec(attach_screenshots(spec, screen_map))
    typer.secho(
        f"{project}: {len(screen_map.screens)} screen(s), "
        f"{len(screen_map.journeys)} journey(s)", fg=typer.colors.GREEN)
