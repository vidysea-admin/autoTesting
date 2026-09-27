"""COVERAGE stage. Contract: qa/contracts/coverage.md V1-V4."""

from __future__ import annotations

from pathlib import Path

from autotester.schema.enums import EvidenceKind, Outcome
from autotester.schema.flowspec import FlowSpec, Screen
from autotester.schema.run import Evidence, RawResult
from autotester.schema.screen_graph import ScreenNode
from autotester.stages.coverage import (
    diff_coverage,
    diff_crawl,
    request_for,
    unreached_screens,
)
from autotester.store.project_store import ProjectStore


def make_spec(*url_patterns: str) -> FlowSpec:
    screens = [Screen(id=f"scr_{i}", name=f"screen {i}", url_pattern=p)
               for i, p in enumerate(url_patterns)]
    return FlowSpec(project="pathlynks", screens=screens)


def make_result(case_id: str, *urls: str) -> RawResult:
    evidence = [Evidence(kind=EvidenceKind.URL, path=u) for u in urls]
    return RawResult(case_id=case_id, outcome=Outcome.COMPLETED, evidence=evidence)


# -- V1 a known route produces no gap ----------------------------------------

def test_known_route_produces_no_gap() -> None:
    spec = make_spec("https://app.test/signin", "https://app.test/dashboard")
    results = [make_result("case_1", "https://app.test/dashboard")]

    gaps = diff_coverage(spec, results)

    assert gaps == []


# -- V2 an unseen route produces exactly one gap -----------------------------

def test_unseen_route_produces_exactly_one_gap() -> None:
    spec = make_spec("https://app.test/signin")
    results = [make_result("case_1", "https://app.test/reports/new")]

    gaps = diff_coverage(spec, results)

    assert len(gaps) == 1
    assert gaps[0].subject == "/reports/new"
    assert gaps[0].project == "pathlynks"


def test_the_same_unseen_route_seen_by_two_cases_dedupes_to_one_gap() -> None:
    spec = make_spec("https://app.test/signin")
    results = [
        make_result("case_1", "https://app.test/reports/new"),
        make_result("case_2", "https://app.test/reports/new"),
    ]

    gaps = diff_coverage(spec, results)

    assert len(gaps) == 1


# -- redacted evidence is never mistaken for a route -------------------------

def test_redacted_evidence_string_is_not_treated_as_a_route() -> None:
    spec = make_spec("https://app.test/signin")
    results = [make_result("case_1", "[REDACTED]:PATHLYNKS_USER_LOGIN_URL")]

    gaps = diff_coverage(spec, results)

    assert gaps == []


# -- V3 exactly one VideoRequest per gap, deduped on re-diff -----------------

def test_request_for_names_the_gap(tmp_path: Path) -> None:
    spec = make_spec("https://app.test/signin")
    results = [make_result("case_1", "https://app.test/reports/new")]
    gap = diff_coverage(spec, results)[0]

    request = request_for(gap)

    assert request.gap_id == gap.id
    assert "/reports/new" in request.prompt


def test_add_request_is_idempotent(tmp_path: Path) -> None:
    store = ProjectStore("pathlynks", tmp_path)
    spec = make_spec("https://app.test/signin")
    results = [make_result("case_1", "https://app.test/reports/new")]
    gap = diff_coverage(spec, results)[0]
    request = request_for(gap)

    store.add_request(request)
    store.add_request(request)  # same gap, re-diffed later -> must not duplicate

    assert len(store.list_requests()) == 1


# -- V1 amendment (T-144): both sides templated, and crawl-sourced coverage ---

def make_node(url: str, crawl_id: str = "crawl_1") -> ScreenNode:
    return ScreenNode(
        crawl_id=crawl_id, project="pathlynks", url_template=f"app.test{url}",
        url_example=f"https://app.test{url}", signature=f"sig{url}",
        name=url,
    )


def test_an_id_bearing_route_no_longer_looks_unknown() -> None:
    """Before T-144 both sides were compared as raw paths, so a run that
    visited `/students/1` was reported as a gap against a screen whose pattern
    is `/students/{id}` — every id-bearing route looked uncovered forever."""
    spec = make_spec("/students/{id}")
    results = [make_result("case_1", "https://app.test/students/1")]

    assert diff_coverage(spec, results) == []


def test_crawled_screen_the_spec_cannot_name_is_a_gap() -> None:
    spec = make_spec("/signin")
    gaps = diff_crawl(spec, [make_node("/reports/new")])

    assert len(gaps) == 1
    assert gaps[0].subject == "/reports/new"
    assert gaps[0].kind == "screen"
    assert gaps[0].seen_in_run == "crawl_1"


def test_a_crawled_screen_matching_a_templated_pattern_is_not_a_gap() -> None:
    spec = make_spec("/students/{id}")
    assert diff_crawl(spec, [make_node("/students/7")]) == []


def test_two_crawled_ids_of_one_screen_produce_at_most_one_gap() -> None:
    spec = make_spec("/signin")
    gaps = diff_crawl(spec, [make_node("/students/1"), make_node("/students/2")])

    assert len(gaps) == 1


def test_unreached_screens_names_what_the_crawl_never_got_to() -> None:
    spec = make_spec("/signin", "/billing")
    unreached = unreached_screens(spec, [make_node("/signin")])

    assert [s.url_pattern for s in unreached] == ["/billing"]


def test_a_screen_with_no_url_pattern_is_never_reported_unreached() -> None:
    """A screen the FlowSpec cannot locate by URL cannot be shown as missed —
    that would be a permanent false alarm on every crawl."""
    spec = FlowSpec(project="pathlynks", screens=[Screen(id="s1", name="modal")])
    assert unreached_screens(spec, [make_node("/signin")]) == []


# -- AT-287: a screen learned from a video is not a permanent gap -------------

def test_a_screen_learned_from_a_video_is_not_a_permanent_gap() -> None:
    """`stages/ingest.py` stored `url_pattern` host-ful while the crawl stored it
    host-less, and coverage re-templated to compare — so `demo.test/students/{id}`
    became `/demo.test/students/{id}`, matched no observed path, and every
    video-learned route looked unknown forever. coverage.md V1's trap in a second
    disguise. Both producers are now canonically host-less.
    """
    from autotester.core.urls import url_template

    ingested_pattern = url_template("https://demo.test/students/42", keep_host=False)
    spec = FlowSpec(project="demo",
                    screens=[Screen(id="scr_1", name="Student", url_pattern=ingested_pattern)])
    results = [make_result("case_1", "https://demo.test/students/99")]

    assert diff_coverage(spec, results) == []


# -- AT-618: the index.html fold must hold at every coverage seam, not just
#    node identity (screen_identity.node_from already folded) ---------------

def test_diff_crawl_folds_an_index_html_node_against_a_slash_pattern() -> None:
    """`coverage._path_of` must fold identically to `screen_identity.node_from`
    and `urls.screen_url_pattern` — before AT-618 it did not, so a crawl node
    whose `url_example` ends in `index.html` was reported as a gap against a
    spec screen pinned at the folded `/`, even though both are the same page."""
    spec = make_spec("/")
    assert diff_crawl(spec, [make_node("/index.html")]) == []


def test_index_first_crawl_then_a_slash_visit_is_not_a_gap() -> None:
    """AT-618, reproduced end to end the way the checker measured it: node
    identity already folded (`screen_identity.node_from`), but
    `explore_merge.screen_from` derived `Screen.url_pattern` from whichever
    node's unfolded `url_example` the dedupe happened to keep — so an
    index-first crawl persisted `Screen.url_pattern == '/index.html'`, and a
    run that only ever visited '/' was reported as a false CoverageGap even
    though the crawl and the run saw the same page."""
    from autotester.schema.screen_graph import PageObservation
    from autotester.stages.explore_merge import screen_from
    from autotester.stages.screen_identity import node_from

    node = node_from(PageObservation(url="https://app.test/index.html"), "crawl_1", "pathlynks",
                     depth=0)
    spec = FlowSpec(project="pathlynks", screens=[screen_from(node)])
    results = [make_result("case_1", "https://app.test/")]

    assert diff_coverage(spec, results) == []


def test_slash_first_crawl_then_an_index_html_visit_is_not_a_gap() -> None:
    """The same seam, the other order — coverage.md V1 requires both sides to
    normalise the same way regardless of which form the crawl saw first."""
    from autotester.schema.screen_graph import PageObservation
    from autotester.stages.explore_merge import screen_from
    from autotester.stages.screen_identity import node_from

    node = node_from(PageObservation(url="https://app.test/"), "crawl_1", "pathlynks", depth=0)
    spec = FlowSpec(project="pathlynks", screens=[screen_from(node)])
    results = [make_result("case_1", "https://app.test/index.html")]

    assert diff_coverage(spec, results) == []
