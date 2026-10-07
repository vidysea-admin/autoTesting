"""X10-b cycle-2 fixes (checker verdict, x10b-form-typing cycle 1).

Three checker-found gaps around the typing pre-pass, each pinned by its own
falsifying test: AT-532 (a fill that auto-submits off-domain is refused, not
explored), AT-533 (typing and clicking share ONE per-node budget), and
AT-534 (typing refusals are recorded as policy edges, never silently clicked).
AT-535 (condition 3: production approval refuses a typing run) is in
`test_explore_consent.py`.

Contract: qa/contracts/explore.md X7, X10-b, V7b.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from crawl_fake import make_project, make_session

from autotester.browser.observe import PageObserver
from autotester.schema.crawl import CrawlBounds, SafetyPolicy
from autotester.schema.enums import WritePolicy
from autotester.store.project_store import ProjectStore

TYPED_POLICY = SafetyPolicy(write_policy=WritePolicy.TEST_ACCOUNT, synthetic_typing=True)


@pytest.mark.parametrize("reason", ["max_depth", "max_actions", "max_screens", "wall_clock_s"])
@pytest.mark.parametrize(
    "phase", ["before", "after_fill", "after_heartbeat", "after_eligibility"])
def test_typing_stops_before_any_followup_when_bound_latches(monkeypatch, reason, phase):
    """X4: retain the exact bound and perform no subsequent browser work."""
    from autotester.stages import explore, explore_typing

    calls = []
    rt = SimpleNamespace(policy=TYPED_POLICY, stop_reason=None,
                         frontier=SimpleNamespace(actions_used=0),
                         bounds=CrawlBounds(), reached=phase == "before")
    node = SimpleNamespace(elements=[SimpleNamespace(role="textbox"),
                                    SimpleNamespace(role="combobox")])

    def fill(*args):
        calls.append("fill")
        rt.reached = phase == "after_fill"

    def beat(*args):
        calls.append("heartbeat")
        rt.reached = True

    def eligible(el):
        if phase == "after_eligibility":
            rt.reached = True
        return True

    monkeypatch.setattr(explore, "stop_reason", lambda runtime: reason if runtime.reached else None)
    monkeypatch.setattr(explore_typing.crawl_coverage, "is_candidate", lambda el: True)
    monkeypatch.setattr(explore_typing, "typing_target_allowed", eligible)
    monkeypatch.setattr(explore_typing, "_type_one", fill)
    monkeypatch.setattr(explore_typing, "_heartbeat_due", lambda runtime: True)
    monkeypatch.setattr(explore_typing, "heartbeat", beat)
    monkeypatch.setattr(explore_typing, "return_to", lambda *args: calls.append("restore") or True)
    before_action = phase in {"before", "after_eligibility"}
    expected = [] if before_action else ["fill"]
    if phase == "after_heartbeat":
        expected.append("heartbeat")
    assert explore_typing.type_form(rt, node) == (not before_action)
    assert rt.frontier.actions_used == (not before_action)
    assert rt.stop_reason == reason
    assert calls == expected


def _crawl(tmp_path: Path, **kwargs: object) -> tuple[object, Path]:
    from crawl_fake import grant_crawl_approval

    from autotester.stages.explore import run_crawl

    project = kwargs.get("project") or make_project(WritePolicy.TEST_ACCOUNT)
    session, page = make_session(tmp_path, project)
    if "fillable" in kwargs:
        for url, selectors in kwargs["fillable"].items():  # type: ignore[attr-defined]
            page.fillable[url] = selectors  # type: ignore[attr-defined]
    store = ProjectStore("demo", tmp_path)
    bounds = kwargs.get("bounds") or CrawlBounds()
    grant_crawl_approval(store, project, bounds)  # type: ignore[arg-type]
    crawl = run_crawl(
        project, session, store,  # type: ignore[arg-type]
        observer=PageObserver(),
        bounds=bounds,  # type: ignore[arg-type]
        policy=kwargs.get("policy", TYPED_POLICY),
    )
    return crawl, store


def test_a_typing_refusal_is_recorded_and_never_clicked(tmp_path: Path) -> None:
    """AT-534: under READ_ONLY the typing targets get DENIED_POLICY edges with
    the TYPING_DISABLED reason, and the click loop does NOT click them and
    count them exercised."""
    from crawl_fake import make_session as _ms

    from autotester.stages.explore_safety import TYPING_DISABLED

    project = make_project(WritePolicy.READ_ONLY)
    _session, page = _ms(tmp_path, project)
    crawl, store = _crawl(tmp_path, policy=SafetyPolicy(write_policy=WritePolicy.READ_ONLY),
                          project=project)
    crawl_id = store.list_crawl_ids()[0]
    edges = store.list_edges(crawl_id)
    denied = [e for e in edges if e.outcome.value == "denied_policy"
              and e.reason == TYPING_DISABLED]
    assert denied, "typing refusals were never recorded as policy edges"
    assert "input.displayname" not in page.clicks, (
        "a field the gate refused to type was silently clicked afterwards")
    assert "select.grade" not in page.clicks
    coverage = crawl.coverage
    assert coverage is not None
    reasons = {h.reason for h in coverage.holes}
    assert any(r.startswith("policy:") and "typing" in r for r in reasons), reasons


def test_typing_and_clicking_share_one_per_node_budget(tmp_path: Path) -> None:
    """AT-533: with per_node_action_cap=2, the typing pre-pass and the click
    loop together perform AT MOST 2 performed actions on the settings node."""
    __, store = _crawl(
        tmp_path, bounds=CrawlBounds(max_actions=60, per_node_action_cap=2))
    crawl_id = store.list_crawl_ids()[0]
    seed = next(n.id for n in store.list_nodes(crawl_id)
                if n.url_template.endswith("/settings"))
    from autotester.stages.crawl_coverage import _tried

    performed = _tried(seed, store.list_edges(crawl_id))
    assert performed <= 2, f"per-node cap overshot: {performed} performed actions"


def test_a_fill_that_lands_off_domain_is_refused_not_explored(tmp_path: Path) -> None:
    """AT-532 (X7): a fill whose onchange auto-submits to another domain is
    refused after settle — an OFF_DOMAIN_REFUSED edge, a NAVIGATION issue, and
    NO node created or explored at the off-domain url. The crawl recovers and
    keeps going."""
    crawl, store = _crawl(tmp_path, fillable={"https://app.test/trap": {"input.offdomain"}})
    crawl_id = store.list_crawl_ids()[0]
    edges = store.list_edges(crawl_id)
    off = [e for e in edges if e.outcome.value == "off_domain_refused"]
    assert off, "the off-domain fill was never refused — X7's host re-check missing"
    issues = store.list_crawl_issues(crawl_id)
    assert any(i.kind.value == "navigation" for i in issues), issues
    nodes = store.list_nodes(crawl_id)
    assert not any("evil.test" in n.url_example for n in nodes), (
        "an off-domain node was created by a typed action")
    assert crawl is not None
