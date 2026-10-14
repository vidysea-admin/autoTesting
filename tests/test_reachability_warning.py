"""AT-887 clause 2: a run warns about cases whose first target the latest crawl never reached.

Warning only -- the cases are never removed. Uses a fixture CrawlSummary, no browser."""

from __future__ import annotations

import json

from autotester.schema.case import Case
from autotester.schema.crawl import CrawlBounds
from autotester.schema.crawl_summary import CrawlSummary
from autotester.schema.enums import Action, CaseClass, CaseKind, CrawlStatus
from autotester.schema.flowspec import Step
from autotester.stages.reachability import reachability_warnings
from autotester.ui.preflight_view import warnings_card


def _case(cid: str, target: str, action: Action = Action.NAVIGATE) -> Case:
    return Case(id=cid, project="p", flow_id="f", title=cid, kind=CaseKind.BEST,
                case_class=CaseClass.HAPPY,
                steps=[Step(order=1, action=action, target=target)])


def _summary(**kw) -> CrawlSummary:
    return CrawlSummary(crawl_id="crawl_X", project="p", status=CrawlStatus.STOPPED_BOUND,
                        bounds=CrawlBounds(), **kw)


FIXTURE = _summary(reached_paths=["/dashboard", "/courses"],
                   unreached_paths=["/admin/supply-partners"])


def test_frontier_and_unseen_targets_are_warned_and_reached_are_not() -> None:
    cases = [_case("ok", "https://x.test/dashboard"),
             _case("frontier", "https://x.test/admin/supply-partners"),
             _case("unseen", "/billing")]
    out = reachability_warnings(cases, FIXTURE)
    assert len(out) == 2
    assert "frontier" in out[0] and "never visited" in out[0] and "crawl_X" in out[0]
    assert "unseen" in out[1] and "not seen" in out[1]
    assert all("will still run" in line for line in out)


def test_never_removes_cases_and_ignores_unmatchable_first_steps() -> None:
    cases = [_case("a", "button 'Menu'", Action.CLICK), _case("b", "{{SECRET:URL}}")]
    assert reachability_warnings(cases, FIXTURE) == []
    assert len(cases) == 2


def test_no_summary_or_old_summary_without_lists_says_nothing() -> None:
    case = [_case("a", "/billing")]
    assert reachability_warnings(case, None) == []
    assert reachability_warnings(case, _summary()) == []


def test_old_summary_json_without_new_fields_still_loads() -> None:
    raw = json.loads(_summary().model_dump_json())
    raw.pop("reached_paths"), raw.pop("unreached_paths")
    assert CrawlSummary.model_validate(raw).reached_paths == []


def test_report_card_lists_warnings_escaped_and_is_empty_without() -> None:
    assert warnings_card([]) == "" and warnings_card(None) == ""
    html = warnings_card(["case <b>: x"])
    assert "Preflight warnings (1)" in html and "&lt;b&gt;" in html
