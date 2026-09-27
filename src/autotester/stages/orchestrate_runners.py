"""The concrete stage runners the orchestrator threads — thin adapters over the
existing stages, kept out of `orchestrate.py` so the driver owns only sequencing.

Each factory returns a `StageRunner` closure `(ctx, prev_ref) -> new_ref` that
reads only the previous stage's artifact, runs the EXISTING stage, persists its
own typed artifact under the run's directory, and returns the reference (OR6):

- INGEST wraps `stages/ingest.py::ingest_video` (the learn entry).
- DISCOVER wraps the bounded-BFS explore path + `merge_screens` (the explore
  entry); the crawl itself is injected as `crawl_fn` so this stays an adapter.
- MODEL folds the entry stage's proposed FlowSpec into the reviewed one via
  `merge_flowspec` — the single seam that resets to DRAFT and refuses to discard
  an APPROVED spec — so no run ever raw-overwrites approved truth (OR3).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from autotester.core.paths import RepoDocs
from autotester.providers.base import Provider
from autotester.schema.crawl import Crawl
from autotester.schema.flowspec import FlowSpec
from autotester.schema.project import Project, Source
from autotester.schema.run_state import StageName
from autotester.schema.screen_graph import ScreenNode
from autotester.stages.explore_merge import merge_screens
from autotester.stages.ingest import ingest_video
from autotester.stages.merge_flowspec import merge_flowspec
from autotester.stages.orchestrate import StageContext
from autotester.store.filestore import read_json, write_json


class MissingArtifact(RuntimeError):
    """A stage that needs the previous stage's artifact was handed no reference
    (or a reference to nothing) — the run cannot proceed and says so honestly."""


def _proposal_ref(ctx: StageContext, stage: StageName) -> str:
    """Where an entry stage parks its PROPOSED FlowSpec — under the run's own
    directory, never `flowspec.json` (that is the reviewed truth MODEL guards)."""
    return str(ctx.store.paths.run_dir(ctx.run_id) / f"{stage.value}.flowspec.json")


def _persist_proposal(ctx: StageContext, stage: StageName, spec: FlowSpec) -> str:
    ref = _proposal_ref(ctx, stage)
    write_json(Path(ref), spec)
    return ref


def _read_proposal(prev_ref: str | None) -> FlowSpec:
    """The previous stage's FlowSpec, loaded ONLY from its own reference (OR6).
    A missing reference is a hard, named error, never a silent empty spec."""
    if not prev_ref:
        raise MissingArtifact("MODEL was reached with no entry-stage artifact reference")
    spec = read_json(Path(prev_ref), FlowSpec)
    if spec is None:
        raise MissingArtifact(f"no FlowSpec artifact at {prev_ref}")
    return spec


def make_ingest_runner(
    source: Source, project_slug: str, provider: Provider,
    docs: RepoDocs | None = None,
) -> Callable[[StageContext, str | None], str]:
    """INGEST as a stage: watch the recording and park a fresh DRAFT FlowSpec
    proposal for MODEL to fold in. Reuses `ingest_video` unchanged."""

    def _run(ctx: StageContext, prev_ref: str | None) -> str:
        provider.trace = ctx.trace  # D-041: this run's LLM calls join its own trace.jsonl
        spec = ingest_video(source, project_slug, provider, docs)
        return _persist_proposal(ctx, StageName.INGEST, spec)

    return _run


def make_discover_runner(
    project: Project, crawl_fn: Callable[[], tuple[Crawl, list[ScreenNode]]],
) -> Callable[[StageContext, str | None], str]:
    """DISCOVER as a stage: run the existing bounded-BFS explore path (injected
    as `crawl_fn`, which returns its finished `Crawl` and screen graph), then
    assemble those nodes into a DRAFT FlowSpec proposal via `merge_screens`.

    `crawl_fn` is injected rather than built here so this stays a thin adapter:
    the live caller closes it over a `BrowserSession`, and it never reaches into
    another stage's internals (OR6)."""

    def _run(ctx: StageContext, prev_ref: str | None) -> str:
        crawl, nodes = crawl_fn()
        spec = merge_screens(None, nodes, project.slug, crawl_id=crawl.id)
        return _persist_proposal(ctx, StageName.DISCOVER, spec)

    return _run


def make_model_runner(
    *, source_id: str | None = None,
) -> Callable[[StageContext, str | None], str]:
    """MODEL as a stage: fold the entry stage's PROPOSED FlowSpec (read only from
    `prev_ref`) into the reviewed one and persist the result.

    The merge goes through `merge_flowspec`, which adds only genuinely new rows,
    re-arms the review gate by resetting to DRAFT on any real change, and refuses
    to discard an APPROVED spec — so an orchestrated run proposes into a DRAFT and
    an APPROVED spec's bytes survive until a human approves the new one (OR3).
    The orchestrator adds NO approval path of its own; it reuses this seam."""

    def _run(ctx: StageContext, prev_ref: str | None) -> str:
        incoming = _read_proposal(prev_ref)
        existing = ctx.store.load_flowspec()
        merged = merge_flowspec(existing, incoming, source_id=source_id)
        ctx.store.save_flowspec(merged)
        return str(ctx.store.paths.flowspec)

    return _run
