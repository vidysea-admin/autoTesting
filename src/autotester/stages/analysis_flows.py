"""Turn a finished `VideoAnalysis` into DRAFT flows in the FlowSpec (TV9, R37).

The analyze route used to save issues and a product map only; the flows the
ensemble had already adjudicated were never proposed. This reuses the existing
mapping (`flowspec_from_observation`) and the one merge seam (`merge_flowspec`):
no new model call, no approval step, and a reviewed spec is never rewritten.
"""

from __future__ import annotations

from autotester.core.redact import Redactor
from autotester.schema.analysis import VideoAnalysis
from autotester.schema.enums import ReviewStatus
from autotester.schema.flowspec import FlowSpec
from autotester.schema.observation import VideoObservation
from autotester.schema.project import Source
from autotester.stages.analyze_video import load_transcript
from autotester.stages.ingest import flowspec_from_observation, project_redactor
from autotester.stages.merge_flowspec import merge_flowspec
from autotester.stages.reconcile import verify_narration
from autotester.store.project_store import ProjectStore


def propose_draft_flows(
    store: ProjectStore, source: Source, analysis: VideoAnalysis,
    *, redactor: Redactor | None = None,
) -> FlowSpec | None:
    """Fold `analysis.flows` into the stored FlowSpec as DRAFT flows carrying `source.id`.

    Returns the saved spec, or None when nothing was proposed (no flows seen, or the
    stored spec is APPROVED: a reviewed spec's bytes are never touched here).
    Narrations survive only as verbatim, scrubbed quotes of the transcript (RC3)."""
    if not analysis.flows:
        return None
    existing = store.load_flowspec()
    if existing is not None and existing.review.status is ReviewStatus.APPROVED:
        return None
    observation = VideoObservation(
        screens=list(analysis.screens), flows=list(analysis.flows), summary=analysis.summary)
    incoming = flowspec_from_observation(observation, source.id, store.paths.slug)
    transcript = load_transcript(store, source)
    heard = {source.id: transcript} if transcript else {}
    scrub = redactor if redactor is not None else project_redactor(store.paths.slug)
    checked = [verify_narration(f, heard, scrub)[0] for f in incoming.flows]
    unique = list({f.id: f for f in reversed(checked)}.values())[::-1]  # one id, one row
    incoming = incoming.model_copy(update={"flows": unique})
    merged = merge_flowspec(existing, incoming, source_id=source.id)
    store.save_flowspec(merged)
    return merged
