"""COVERAGE: diff what a run actually saw against what the FlowSpec knows.

Contract: qa/contracts/coverage.md V1-V4. "When it meets a screen it does not
know, it asks the human for a video instead of guessing" — this stage is that
mechanism: any URL a run's evidence reached that matches no known screen's
`url_pattern` becomes a `CoverageGap`, and exactly one `VideoRequest` per gap
(both content-addressed, so re-running the diff never duplicates either).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autotester.core.urls import url_template
from autotester.schema.coverage import CoverageGap, VideoRequest
from autotester.schema.enums import EvidenceKind
from autotester.schema.flowspec import FlowSpec, Screen
from autotester.schema.run import RawResult
from autotester.schema.screen_graph import ScreenNode

if TYPE_CHECKING:  # a stage names the store only in a signature (execute.py's convention)
    from autotester.store.project_store import ProjectStore


def _path_of(url: str) -> str:
    """Both sides of every coverage diff are normalised the same way (V1
    amendment, T-144): a run that visited `/students/1` must not be reported as
    a gap against a screen whose pattern is `/students/{id}`. Before this,
    coverage compared raw paths and every id-bearing route looked unknown.

    `fold_index=True` (AT-618): this is a screen-identity comparison, the same
    kind `stages/screen_identity.py::node_from` and `urls.screen_url_pattern`
    already fold — a screen reached by `/index.html` and a `Screen.url_pattern`
    of `/` (or vice versa) must agree here too, or coverage reports a gap for a
    page the FlowSpec already knows."""
    return url_template(url, keep_host=False, fold_index=True)


def _known_paths(spec: FlowSpec) -> set[str]:
    return {_path_of(s.url_pattern) for s in spec.screens if s.url_pattern}


def _seen_urls(results: list[RawResult]) -> list[tuple[str, str]]:
    """(url, case_id) pairs actually observed — only real http(s) URLs; a
    redacted evidence string (e.g. `[REDACTED]:KEY`) never matches this and is
    silently skipped, not mistaken for a route."""
    return [
        (ev.path, result.case_id)
        for result in results
        for ev in result.evidence
        if ev.kind is EvidenceKind.URL and ev.path.startswith(("http://", "https://"))
    ]


def diff_coverage(spec: FlowSpec, results: list[RawResult]) -> list[CoverageGap]:
    """Every URL a run actually reached whose path matches no known screen."""
    known = _known_paths(spec)
    gaps: dict[str, CoverageGap] = {}
    for url, case_id in _seen_urls(results):
        path = _path_of(url)
        if path in known:
            continue
        gap = CoverageGap(
            project=spec.project, kind="route", subject=path, seen_in_run=case_id,
            reason=f"observed '{path}' but no screen in the FlowSpec has this url_pattern",
        )
        gaps.setdefault(gap.id, gap)  # content-addressed on (project, kind, subject): deduped
    return list(gaps.values())


def request_for(gap: CoverageGap) -> VideoRequest:
    """Exactly one `VideoRequest` per gap — content-addressed on (project, gap_id),
    so asking twice for the same gap never produces a second request."""
    return VideoRequest(
        project=gap.project,
        gap_id=gap.id,
        prompt=f"Record a short video showing the screen/flow at '{gap.subject}' — {gap.reason}",
    )


# -- crawl coverage (T-144): the same diff, sourced from a screen graph -------

def _crawled_paths(nodes: list[ScreenNode]) -> dict[str, ScreenNode]:
    """Keyed on the templated path of each node's real example URL — the node's
    own `url_template` carries a host, and a `Screen.url_pattern` does not."""
    return {_path_of(node.url_example): node for node in nodes}


def diff_crawl(spec: FlowSpec, nodes: list[ScreenNode]) -> list[CoverageGap]:
    """Every screen the crawl actually reached that the FlowSpec cannot name."""
    known = _known_paths(spec)
    gaps: dict[str, CoverageGap] = {}
    for path, node in _crawled_paths(nodes).items():
        if path in known:
            continue
        gap = CoverageGap(
            project=spec.project, kind="screen", subject=path, seen_in_run=node.crawl_id,
            reason=f"the crawl reached '{path}' but no screen in the FlowSpec has this "
                   f"url_pattern",
        )
        gaps.setdefault(gap.id, gap)
    return list(gaps.values())


def queue_requests(store: ProjectStore, gaps: list[CoverageGap]) -> list[VideoRequest]:
    """Persist exactly one `VideoRequest` per gap — the one place a gap becomes
    an ask, so the run path and the crawl path cannot drift apart.

    AT-240: `diff_coverage`, `request_for` and `ProjectStore.add_request` were
    each correct and each called only from tests, so no `VideoRequest` had ever
    been created and the north star's "it asks the human for a video instead of
    guessing" never happened. Idempotent by construction (V3: `add_request` is
    content-addressed on `(project, gap_id)`), so re-running a suite over the
    same unknown route re-asks nothing.

    Callers pass `diff_coverage(...)` (a run's evidence) or `diff_crawl(...)`
    (a crawl's screens). `unreached_screens` must NEVER be passed here — V5: a
    bounded crawl seeing less than the spec describes is expected, and asking a
    human to re-record a screen the system already understands is the opposite
    of self-extension.
    """
    return [store.add_request(request_for(gap)) for gap in gaps]


def unreached_screens(spec: FlowSpec, nodes: list[ScreenNode]) -> list[Screen]:
    """The other direction: screens the FlowSpec claims that the crawl never
    got to. Not a gap — the spec is not wrong for describing more than one
    bounded crawl saw — but it is what tells a human the crawl stopped early or
    that a route needs a login the crawl did not have."""
    crawled = set(_crawled_paths(nodes))
    return [s for s in spec.screens if s.url_pattern and _path_of(s.url_pattern) not in crawled]
