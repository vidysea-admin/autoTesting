"""The proposal review page (FB5): it calls the CLI's own functions, under project.edit."""

from __future__ import annotations

import re
from html import escape
from pathlib import Path

import pytest
from auth_harness import gate_on, project, team, user_id
from fastapi.testclient import TestClient

from autotester.auth.access import set_owner, set_relation
from autotester.schema.auth import ProjectRelation
from autotester.schema.enums import CaseClass, ReviewStatus
from autotester.schema.flowspec import Action, Flow, FlowSpec, Review, Step
from autotester.store.project_store import ProjectStore

URL = "/projects/mine/proposals"


@pytest.fixture()
def users(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, TestClient]:
    root = gate_on(tmp_path, monkeypatch)
    out = team()
    project(root, "mine")
    set_owner("mine", user_id("dev@team.test"))
    set_relation("mine", user_id("tester@team.test"), ProjectRelation.SHARED, True)
    return out


def _spec(status: ReviewStatus = ReviewStatus.APPROVED) -> ProjectStore:
    store = ProjectStore("mine")
    store.save_flowspec(FlowSpec(project="mine", review=Review(status=status), flows=[Flow(
        id="flow-login", name="Sign in", entry_screen="scr_signin",
        steps=[Step(order=1, action=Action.NAVIGATE, target="https://mine.test/")])]))
    return store


def _stage(client: TestClient) -> ProjectStore:
    store = _spec()
    assert client.post(URL + "/stage").status_code == 303
    return store


def test_page_lists_staged_proposals_with_flow_and_reason(users: dict[str, TestClient]) -> None:
    store = _stage(users["dev"])
    page = users["dev"].get(URL)
    assert page.status_code == 200
    for p in store.list_case_proposals():
        assert p.title.split(" — ")[0] in page.text and escape(p.rationale) in page.text
    assert "scr_signin" in page.text and "Why proposed" in page.text


def test_unapproved_flowspec_shows_no_rows_and_refuses_stage(users: dict[str, TestClient]) -> None:
    _spec(ReviewStatus.DRAFT)
    assert "Review the FlowSpec" in users["dev"].get(URL).text
    assert users["dev"].post(URL + "/stage").status_code == 400
    assert ProjectStore("mine").list_case_proposals() == []


def test_single_approve_and_prune_use_the_stage_functions(users: dict[str, TestClient]) -> None:
    store = _stage(users["dev"])
    rows = {p.case_class: p for p in store.list_case_proposals()}
    happy = rows[CaseClass.HAPPY]
    resp = users["dev"].post(URL + "/review", data={"by": "Ana", "single": f"approve:{happy.id}"})
    assert resp.status_code == 303
    other = next(p for c, p in rows.items() if c is not CaseClass.HAPPY)
    users["dev"].post(URL + "/review", data={"by": "Ana", "single": f"prune:{other.id}"})
    now = {p.id: p for p in store.list_case_proposals()}
    assert now[happy.id].status == "approved" and now[happy.id].reviewed_by == "Ana"
    assert now[other.id].status == "pruned"


def test_bulk_approve_all_and_unsigned_is_refused(users: dict[str, TestClient]) -> None:
    store = _stage(users["dev"])
    ids = [p.id for p in store.list_case_proposals()]
    assert users["dev"].post(URL + "/review", data={
        "by": " ", "decision": "approve", "proposal_id": ids}).status_code == 400
    assert {p.status for p in store.list_case_proposals()} == {"proposed"}
    assert users["dev"].post(URL + "/review", data={
        "by": "Ana", "decision": "approve", "proposal_id": ids}).status_code == 303
    assert {p.status for p in store.list_case_proposals()} == {"approved"}


def test_pruning_the_happy_path_keeps_it_pending(users: dict[str, TestClient]) -> None:
    store = _stage(users["dev"])
    happy = next(p for p in store.list_case_proposals() if p.case_class is CaseClass.HAPPY)
    users["dev"].post(URL + "/review", data={"by": "Ana", "single": f"prune:{happy.id}"})
    assert next(p for p in store.list_case_proposals() if p.id == happy.id).status == "proposed"


def test_unknown_id_is_404_and_a_bulk_with_one_bad_id_changes_nothing(
        users: dict[str, TestClient]) -> None:
    store = _stage(users["dev"])
    good = store.list_case_proposals()[0].id
    resp = users["dev"].post(URL + "/review", data={
        "by": "Ana", "decision": "approve", "proposal_id": [good, "proposal_nope"]})
    assert resp.status_code == 404
    assert {p.status for p in store.list_case_proposals()} == {"proposed"}


def test_403_for_view_only_and_404_for_unviewable_and_unknown_project(
        users: dict[str, TestClient]) -> None:
    store = _stage(users["dev"])
    pid = store.list_case_proposals()[0].id
    data = {"by": "T", "single": f"approve:{pid}"}
    assert users["tester"].get(URL).status_code == 200            # may view
    for path, body in ((URL + "/review", data), (URL + "/stage", None)):
        assert users["tester"].post(path, data=body).status_code == 403
    assert {p.status for p in store.list_case_proposals()} == {"proposed"}
    assert users["admin"].get(URL).status_code == 200
    assert users["admin"].get("/projects/ghost/proposals").status_code == 404
    assert users["sub"].get(URL).status_code == 404               # not assigned: not viewable


def test_every_control_is_labelled(users: dict[str, TestClient]) -> None:
    _stage(users["dev"])
    html = users["dev"].get(URL).text
    html = html[html.index("<form method='post' action='/projects/mine/proposals/review'"):]
    for tag in re.findall(r"<(?:input|button)\b[^>]*>(?:[^<]*</button>)?", html):
        assert ("aria-label=" in tag or "id='by'" in tag or "Selected" in tag
                or "selected" in tag or "Approve" in tag or "Prune" in tag), tag
    assert "<label for='by'>" in html and "<caption" in html
