"""AT-890 at the Generate button: a prompt the secret guard refuses is a themed 400 page
(expand.md X6), not a raw 500 -- and it writes no case, calls no model, echoes nothing."""

from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient

from autotester.providers.mock import MockProvider
from autotester.schema.case import ExpandedSteps
from autotester.schema.enums import Action
from autotester.schema.flowspec import Flow, FlowSpec, Step
from autotester.schema.project import Project, SecretRef
from autotester.stages.expand import propose_cases
from autotester.stages.review import approve
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app

SECRET = "Hunter2-Zebra-4411"


def test_a_guard_refusal_is_a_themed_400_with_nothing_written_sent_or_echoed(
        tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    (tmp_path / ".env").write_text(f"ST_PASS={SECRET}\n", encoding="utf-8")
    encoded = base64.b64encode(SECRET.encode()).decode()
    store = ProjectStore("demo", tmp_path)
    store.save_project(Project(
        slug="demo", name="Demo", base_url="https://demo.test", allowed_domains=["demo.test"],
        secrets=[SecretRef(key="ST_PASS", domains=["demo.test"])]))
    spec = approve(FlowSpec(project="demo", flows=[Flow(
        id="flow_x", name="Sign in", entry_screen="scr", steps=[
            Step(order=1, action=Action.NAVIGATE, target="https://demo.test/signin"),
            Step(order=2, action=Action.FILL, target="password", value=encoded)])]), by="umesh")
    store.save_flowspec(spec)
    rows = propose_cases(spec)
    store.stage_case_proposals(rows)
    for row in rows:
        store.review_case_proposal(row.id, "umesh", approved=True)

    class _Spy(MockProvider):
        def available(self) -> bool:
            return True

    spy = _Spy(responses={"agent": [ExpandedSteps(steps=[], rationale="n/a")] * 60})
    import autotester.ui.routes_learn as routes_learn_module
    monkeypatch.setattr(routes_learn_module, "for_role", lambda project, role: spy)

    response = TestClient(app).post("/projects/demo/cases/generate", follow_redirects=False)

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("text/html")
    assert "Internal Server Error" not in response.text and "AutoTester" in response.text
    assert SECRET not in response.text and encoded not in response.text
    assert spy.prompts == [] and store.list_cases() == []
