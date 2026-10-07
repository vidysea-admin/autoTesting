"""Fold a freshly ingested FlowSpec into the reviewed one (Track A6, T-135).

This closes the self-extension loop. COVERAGE notices a route nothing knows and
queues a `VideoRequest`; a human records the video; INGEST watches it and
produces a *fresh* `FlowSpec`. Until this stage existed the answer had nowhere
to land: `persist_ingest` refuses to overwrite an APPROVED spec (ingest.md I6)
and its own error text points here — "or merge instead once merge_flowspec
exists". So the ask went out, the video came back, and the gap stayed open
forever, because nothing ever moved a `VideoRequest` off `OPEN`.

Two halves, both deliberately conservative:

- `merge_flowspec` adds what the recording taught and rewrites nothing a human
  already reviewed. A real change sends the spec back to DRAFT so the review
  gate is re-armed rather than bypassed.
- `resolve_requests` closes exactly the requests the merged spec can now
  answer, and `open_requests` surfaces the ones it still cannot — an ask that
  silently disappears is worse than one that stays open.

Contract: qa/contracts/ingest.md I6 (the merge seam it defers to A6) and
qa/contracts/coverage.md V3 (one request per gap, content-addressed).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autotester.core.ids import content_id
from autotester.core.urls import url_template
from autotester.schema.coverage import VideoRequest
from autotester.schema.enums import RequestStatus, ReviewStatus
from autotester.schema.flowspec import Conflict, Flow, FlowSpec, Review, Screen
from autotester.stages.explore_merge import disagreement
from autotester.stages.ingest import legacy_flow_id

if TYPE_CHECKING:  # a stage names the store only in a signature (execute.py's convention)
    from autotester.store.project_store import ProjectStore

# `CoverageGap.id` is content-addressed on (project, kind, subject). A route gap
# comes from a run's evidence and a screen gap from a crawl, but both name the
# same templated path — so a merged spec that covers the path answers either.
_GAP_KINDS = ("route", "screen")


def _new_screens(existing: FlowSpec, incoming: FlowSpec) -> list[Screen]:
    known = {s.id for s in existing.screens}
    return [s for s in incoming.screens if s.id not in known]


def _learned_url_patterns(existing: FlowSpec, incoming: FlowSpec) -> dict[str, str]:
    """Screens the spec ALREADY names, for which this recording finally supplies
    a `url_pattern` the spec lacks.

    `Screen.id` is content-addressed on `(name, signals)` only, so a re-recording
    of a known screen is dropped whole by `_new_screens` — and `ingest.md` I7
    makes `url_pattern=None` the NORMAL outcome for a video with no visible
    address bar. So the common case was: ask for a video of an unknown route, get
    one, learn nothing, and leave the request open forever (AT-290).

    Only ever fills a `None`. An existing pattern is never overwritten — that
    would be rewriting reviewed truth, which is the one thing a merge must not do.
    """
    lacking = {s.id for s in existing.screens if not s.url_pattern}
    return {
        s.id: s.url_pattern
        for s in incoming.screens
        if s.id in lacking and s.url_pattern
    }


def _new_flows(existing: FlowSpec, incoming: FlowSpec) -> list[Flow]:
    """Flows the spec does not hold yet. A saved flow keeps its pre-RC8 name-only
    id (ids are never rewritten), so a re-ingest of the SAME recording -- same
    name, same source -- is recognised through `legacy_flow_id` and not added twice."""
    known = {f.id for f in existing.flows}
    legacy = {(f.id, f.source_id) for f in existing.flows}
    return [f for f in incoming.flows
            if f.id not in known and (legacy_flow_id(f.name), f.source_id) not in legacy]


def _conflicts_for(
    existing: FlowSpec, added: list[Screen], source_id: str,
    learned: dict[str, str] | None = None,
) -> list[Conflict]:
    """A recording claiming a `url_pattern` an existing screen already claims
    under a different name is two sources disagreeing — both are kept and the
    human decides. `disagreement` (explore_merge) is the single place that rule
    lives, so the video seam and the crawl seam cannot drift apart."""
    by_pattern = {s.url_pattern: s for s in existing.screens if s.url_pattern}
    known = {(c.subject, tuple(c.claims)) for c in existing.conflicts}
    # AT-295: a LEARNED pattern is a new claim on a url just as much as a new
    # screen is. `_conflicts_for` used to iterate `added` only, so filling a
    # screen's empty url_pattern with one another screen already claims produced
    # two screens at one pattern and no Conflict — silently picking a winner,
    # which is the single thing this seam exists not to do.
    claimants = list(added) + [
        s.model_copy(update={"url_pattern": learned[s.id]})
        for s in existing.screens if learned and s.id in learned
    ]
    found: list[Conflict] = []
    for screen in claimants:
        conflict = disagreement(by_pattern.get(screen.url_pattern), screen, source_id)
        if conflict is not None and (conflict.subject, tuple(conflict.claims)) not in known:
            found.append(conflict)
    return found


def merge_flowspec(
    existing: FlowSpec | None, incoming: FlowSpec, *, source_id: str | None = None
) -> FlowSpec:
    """Add what `incoming` taught, never rewriting reviewed truth.

    An existing `Screen` or `Flow` is never modified or replaced — a human may
    have corrected it, and a later recording is not evidence that the correction
    was wrong. Only genuinely new rows are added.

    Idempotent: merging the same recording twice adds nothing the second time,
    so the version is not bumped and the review is not reset again. That matters
    because a reset review blocks EXPAND (review-gate R1), and a merge that
    re-armed the gate on every call would make the loop un-closeable.
    """
    if existing is None:
        return incoming
    source = source_id or (incoming.source_ids[0] if incoming.source_ids else "unknown")

    added_screens = _new_screens(existing, incoming)
    added_flows = _new_flows(existing, incoming)
    new_patterns = _learned_url_patterns(existing, incoming)
    new_conflicts = _conflicts_for(existing, added_screens, source, new_patterns)
    if not added_screens and not added_flows and not new_patterns and not new_conflicts:
        return existing

    kept = [
        s if s.id not in new_patterns else s.model_copy(
            update={"url_pattern": new_patterns[s.id]})
        for s in existing.screens
    ]
    learned = len(added_screens) + len(added_flows) + len(new_patterns)
    return existing.model_copy(update={
        "screens": [*kept, *added_screens],
        "flows": [*existing.flows, *added_flows],
        "conflicts": [*existing.conflicts, *new_conflicts],
        "source_ids": sorted({*existing.source_ids, *incoming.source_ids, source}),
        "version": existing.version + 1,
        # Reviewed truth survives; the parts a human never saw do not inherit
        # their approval, so the gate is re-armed rather than bypassed.
        "app_overview": existing.app_overview or incoming.app_overview,
        "review": Review(
            status=ReviewStatus.DRAFT,
            note=f"{learned} screen(s)/flow(s) added from {source} — needs review",
        ),
    })


def _answered_gap_ids(spec: FlowSpec) -> dict[str, str | None]:
    """Every `CoverageGap.id` this spec now covers, mapped to the source that
    actually covers it.

    Recomputed from the spec's own screens rather than read from stored gaps —
    `CoverageGap` is content-addressed, so the id a path *would* produce is the
    id it *did* produce. That is what lets a request be matched to a gap nobody
    persisted.

    The value is the answering screen's own `source_ref.source_id`, not the
    recording being merged (AT-291): a merge that changed nothing still closes a
    request whose gap a human had already covered by hand, and stamping that
    request with an unrelated video's id is a false statement about which
    recording answered the ask.
    """
    # `url_template` is the one place a URL becomes a screen-identity path
    # (coverage.md V1) — a request is judged answered by exactly the rule that
    # judged it unanswered, and it is idempotent, so a stored host-ful pattern
    # and a fresh URL normalise to the same thing (AT-287). `fold_index=True`
    # (AT-618): `stages/coverage.py::_path_of` folds when it OPENS a gap, so
    # this must fold identically when it CLOSES one, or an index-first gap
    # never resolves even after the answering video lands.
    by_path: dict[str, str | None] = {}
    for screen in spec.screens:
        if not screen.url_pattern:
            continue
        path = url_template(screen.url_pattern, keep_host=False, fold_index=True)
        by_path.setdefault(path, screen.source_ref.source_id if screen.source_ref else None)
    return {
        content_id("gap", {"p": spec.project, "k": kind, "s": path}): source
        for path, source in by_path.items()
        for kind in _GAP_KINDS
    }


def resolve_requests(
    store: ProjectStore, spec: FlowSpec, *, source_id: str
) -> list[VideoRequest]:
    """Close every OPEN request the merged spec can now answer.

    Before this, `RequestStatus.FULFILLED` and `fulfilled_by_source` were
    declared in the schema and written by nothing — every request the system
    ever made stayed OPEN for life, so the same gap re-asked forever and a human
    who did record the video got no acknowledgement that it had landed.

    A request whose gap the merge did not cover is deliberately left OPEN: the
    recording did not answer it, and quietly marking it fulfilled would lose the
    ask. `open_requests` is how those stay visible.

    `source_id` is a FALLBACK, not the answer: each request is attributed to the
    screen that actually covers its gap (AT-291), so a no-op merge cannot credit
    an unrelated recording for work a human's hand-edit or an earlier video did.
    """
    answered = _answered_gap_ids(spec)
    resolved: list[VideoRequest] = []
    for request in store.list_requests():
        if request.status is not RequestStatus.OPEN or request.gap_id not in answered:
            continue
        closed = request.model_copy(update={
            "status": RequestStatus.FULFILLED,
            "fulfilled_by_source": answered[request.gap_id] or source_id,
        })
        store.update_request(closed)
        resolved.append(closed)
    return resolved


def open_requests(store: ProjectStore) -> list[VideoRequest]:
    """The asks still waiting on a human — what the system does not understand
    yet, stated out loud instead of buried in a jsonl file."""
    return [r for r in store.list_requests() if r.status is RequestStatus.OPEN]
