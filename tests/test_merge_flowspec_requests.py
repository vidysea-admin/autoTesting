"""The VideoRequest lifecycle around a merge — `resolve_requests` / `open_requests`.

Split from `test_merge_flowspec.py` at the 300-line cap (C2). That file owns
merge SEMANTICS (what a merge does to a FlowSpec); this one owns what a merge
does to the asks the system has outstanding.

Before T-135, `RequestStatus.FULFILLED` and `fulfilled_by_source` were declared
in the schema and written by nothing anywhere in src/ or tests/ — every request
this system ever made stayed OPEN for life.
"""

from __future__ import annotations

from pathlib import Path

from autotester.schema.coverage import VideoRequest
from autotester.schema.enums import EvidenceKind, Outcome, RequestStatus, ReviewStatus
from autotester.schema.flowspec import FlowSpec, Review, Screen, SourceRef
from autotester.schema.run import Evidence, RawResult
from autotester.stages.coverage import diff_coverage, queue_requests
from autotester.stages.merge_flowspec import merge_flowspec, open_requests, resolve_requests
from autotester.store.project_store import ProjectStore

PROJECT = "pathlynks"


def screen(sid: str, name: str, url_pattern: str | None = None) -> Screen:
    return Screen(id=sid, name=name, url_pattern=url_pattern)


def approved(*screens: Screen) -> FlowSpec:
    return FlowSpec(
        project=PROJECT, version=3, screens=list(screens), source_ids=["src_video_1"],
        review=Review(status=ReviewStatus.APPROVED, by="umesh", at="2026-09-10T00:00:00Z"))


def ingested(*screens: Screen, source_id: str = "src_video_2") -> FlowSpec:
    return FlowSpec(project=PROJECT, screens=list(screens), source_ids=[source_id])


def make_result(case_id: str, *urls: str) -> RawResult:
    evidence = [Evidence(kind=EvidenceKind.URL, path=u) for u in urls]
    return RawResult(case_id=case_id, outcome=Outcome.COMPLETED, evidence=evidence)


def test_a_request_the_merged_spec_now_answers_is_closed(tmp_path: Path) -> None:
    store = ProjectStore(PROJECT, tmp_path)
    spec = approved(screen("scr_1", "Sign in", "https://app.test/signin"))
    gaps = diff_coverage(spec, [make_result("case_1", "https://app.test/reports/new")])
    queue_requests(store, gaps)

    merged = merge_flowspec(
        spec, ingested(screen("scr_2", "New report", "https://app.test/reports/new")),
        source_id="src_video_2")
    resolved = resolve_requests(store, merged, source_id="src_video_2")

    assert len(resolved) == 1
    stored = store.list_requests()[0]
    assert stored.status is RequestStatus.FULFILLED
    assert stored.fulfilled_by_source == "src_video_2"


def test_a_request_the_recording_did_not_answer_stays_open(tmp_path: Path) -> None:
    store = ProjectStore(PROJECT, tmp_path)
    spec = approved(screen("scr_1", "Sign in", "https://app.test/signin"))
    gaps = diff_coverage(spec, [make_result("case_1", "https://app.test/reports/new")])
    queue_requests(store, gaps)

    # The human recorded a different screen entirely.
    merged = merge_flowspec(
        spec, ingested(screen("scr_3", "Settings", "https://app.test/settings")),
        source_id="src_video_3")
    resolved = resolve_requests(store, merged, source_id="src_video_3")

    assert resolved == []
    assert [r.status for r in store.list_requests()] == [RequestStatus.OPEN]
    assert len(open_requests(store)) == 1


def test_resolving_twice_does_not_rewrite_an_already_closed_request(tmp_path: Path) -> None:
    store = ProjectStore(PROJECT, tmp_path)
    spec = approved(screen("scr_1", "Sign in", "https://app.test/signin"))
    queue_requests(store, diff_coverage(
        spec, [make_result("case_1", "https://app.test/reports/new")]))
    merged = merge_flowspec(
        spec, ingested(screen("scr_2", "New report", "https://app.test/reports/new")),
        source_id="src_video_2")

    resolve_requests(store, merged, source_id="src_video_2")
    second = resolve_requests(store, merged, source_id="src_video_99")

    assert second == []
    assert store.list_requests()[0].fulfilled_by_source == "src_video_2"
    assert len(store.list_requests()) == 1


def test_open_requests_surfaces_only_what_is_still_unanswered(tmp_path: Path) -> None:
    store = ProjectStore(PROJECT, tmp_path)
    store.add_request(VideoRequest(project=PROJECT, gap_id="gap_a", prompt="record a"))
    store.add_request(VideoRequest(project=PROJECT, gap_id="gap_b", prompt="record b"))
    closed = store.list_requests()[0].model_copy(
        update={"status": RequestStatus.FULFILLED, "fulfilled_by_source": "src_1"})
    store.update_request(closed)

    still_open = open_requests(store)

    assert [r.gap_id for r in still_open] == ["gap_b"]


# -- the loop, end to end -----------------------------------------------------

def test_the_full_loop_closes_a_gap_end_to_end(tmp_path: Path) -> None:
    """Unknown route -> ask -> recording -> merge -> the gap is gone and the ask
    is closed. Before T-135 this stopped dead at the merge: an APPROVED spec
    refused the ingest, so the same gap was re-asked on every run forever."""
    store = ProjectStore(PROJECT, tmp_path)
    spec = approved(screen("scr_1", "Sign in", "https://app.test/signin"))
    results = [make_result("case_1", "https://app.test/reports/new")]

    gaps = diff_coverage(spec, results)
    queue_requests(store, gaps)
    assert len(gaps) == 1 and len(open_requests(store)) == 1

    merged = merge_flowspec(
        spec, ingested(screen("scr_2", "New report", "https://app.test/reports/new")),
        source_id="src_video_2")
    resolve_requests(store, merged, source_id="src_video_2")

    assert diff_coverage(merged, results) == []
    assert open_requests(store) == []


def test_an_id_bearing_route_is_answered_by_a_templated_pattern(tmp_path: Path) -> None:
    """The request was raised on the templated path (coverage.md V1), so it must
    be judged answered by the same templating — not by a literal string match."""
    store = ProjectStore(PROJECT, tmp_path)
    spec = approved(screen("scr_1", "Sign in", "https://app.test/signin"))
    results = [make_result("case_1", "https://app.test/students/42")]
    queue_requests(store, diff_coverage(spec, results))

    merged = merge_flowspec(
        spec, ingested(screen("scr_2", "Student", "https://app.test/students/{id}")),
        source_id="src_video_2")
    resolve_requests(store, merged, source_id="src_video_2")

    assert open_requests(store) == []


# -- AT-291: attribution must name the source that actually answered ----------

def test_a_no_op_merge_does_not_credit_an_unrelated_recording(tmp_path: Path) -> None:
    """A human hand-edits the FlowSpec to cover a gap (the documented review/edit
    workflow), then an unrelated video is merged. The ask is genuinely answered,
    so closing it is right — but stamping it with the unrelated video's id is a
    false statement about which recording answered it."""

    store = ProjectStore(PROJECT, tmp_path)
    covered = screen("scr_1", "Reports", "https://app.test/reports/new")
    covered = covered.model_copy(update={"source_ref": SourceRef(source_id="src_the_real_one")})
    spec = approved(covered)
    # the gap was raised before the screen existed
    queue_requests(store, diff_coverage(
        FlowSpec(project=PROJECT),
        [make_result("case_1", "https://app.test/reports/new")]))

    merged = merge_flowspec(spec, ingested(), source_id="src_unrelated_video")
    assert merged is spec, "precondition: this merge taught nothing"
    resolve_requests(store, merged, source_id="src_unrelated_video")

    assert store.list_requests()[0].fulfilled_by_source == "src_the_real_one"


# -- AT-290: learning a pattern must close the ask that requested it ----------

def test_a_stored_index_html_pattern_answers_a_slash_gap(tmp_path: Path) -> None:
    """AT-618: `stages/coverage.py::_path_of` folds `index.html` when it OPENS a
    gap; `merge_flowspec._answered_gap_ids` must fold identically when it
    CLOSES one, or a Screen whose stored `url_pattern` is the unfolded
    '/index.html' form never answers a gap raised against '/' — the ask stays
    open forever even after the answering video lands."""
    store = ProjectStore(PROJECT, tmp_path)
    spec = approved(screen("scr_1", "Sign in", "https://app.test/signin"))
    queue_requests(store, diff_coverage(spec, [make_result("case_1", "https://app.test/")]))
    assert len(open_requests(store)) == 1

    merged = merge_flowspec(
        spec, ingested(screen("scr_2", "Home", "https://app.test/index.html")),
        source_id="src_video_2")
    resolve_requests(store, merged, source_id="src_video_2")

    assert open_requests(store) == []


def test_learning_a_url_pattern_closes_the_request_that_asked_for_it(tmp_path: Path) -> None:
    """The whole point of AT-290: the loop must close on the COMMON case, not
    only when the recording happens to reveal a screen name nobody knew."""
    store = ProjectStore(PROJECT, tmp_path)
    spec = approved(screen("scr_1", "Login", None))
    queue_requests(store, diff_coverage(
        spec, [make_result("case_1", "https://app.test/login")]))
    assert len(open_requests(store)) == 1

    merged = merge_flowspec(
        spec, ingested(screen("scr_1", "Login", "https://app.test/login")),
        source_id="src_video_2")
    resolve_requests(store, merged, source_id="src_video_2")

    assert open_requests(store) == []
