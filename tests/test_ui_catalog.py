"""The test-catalog page. Contract: qa/contracts/catalog.md CT4, CT8."""

from __future__ import annotations

import re
from html import escape
from pathlib import Path
from xml.etree import ElementTree

import pytest
from fastapi.testclient import TestClient

from autotester.schema.catalog import TIER_BY_CLASS, BlockedReason, Catalog, CatalogEntry
from autotester.schema.enums import Action, CaseClass, ReviewStatus
from autotester.schema.flowspec import Flow, FlowSpec, Review, Step
from autotester.schema.project import Project, SecretRef
from autotester.store.project_store import ProjectStore
from autotester.ui import routes_catalog
from autotester.ui.app import app


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectStore:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    result = ProjectStore("demo", tmp_path)
    result.save_project(Project(
        slug="demo", name="Demo", base_url="https://demo.test/signin",
        allowed_domains=["demo.test"],
        secrets=[SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])],
    ))
    return result


def _auth_flow() -> Flow:
    return Flow(
        id="flow_login", name="Login", entry_screen="scr_login",
        steps=[
            Step(order=1, action=Action.NAVIGATE, target="https://demo.test/signin"),
            Step(order=2, action=Action.FILL, target="Password", value="{{SECRET:DEMO_PASSWORD}}"),
            Step(order=3, action=Action.CLICK, target="Sign in"),
        ],
    )


# -- CT4: no FlowSpec -> the page renders the reason on every row -----------

def test_no_flowspec_page_renders_the_reason_on_every_row_not_a_generic_empty_state(
    store: ProjectStore,
) -> None:
    response = TestClient(app).get("/projects/demo/catalog")
    assert response.status_code == 200
    assert response.text.count("no FlowSpec yet") >= 15  # one per CaseClass, none skipped
    assert "record a source" in response.text


def test_catalog_page_404s_for_an_unknown_project() -> None:
    response = TestClient(app).get("/projects/nope/catalog")
    assert response.status_code == 404


# -- CT8: a blocked row states the reason AND the specific action -----------

def test_missing_credential_row_names_the_key_not_the_bare_enum(store: ProjectStore) -> None:
    store.save_flowspec(FlowSpec(
        project="demo", flows=[_auth_flow()], review=Review(status=ReviewStatus.APPROVED),
    ))
    response = TestClient(app).get("/projects/demo/catalog")
    assert response.status_code == 200
    assert "DEMO_PASSWORD" in response.text
    # the bare enum literal alone is never the whole story on a blocked row --
    # the specific action text must accompany it.
    assert "set DEMO_PASSWORD in the repo-root .env" in response.text


def test_runnable_happy_path_renders_as_runnable(store: ProjectStore) -> None:
    store.save_flowspec(FlowSpec(
        project="demo", flows=[_auth_flow()], review=Review(status=ReviewStatus.APPROVED),
    ))
    response = TestClient(app).get("/projects/demo/catalog")
    assert response.status_code == 200
    assert "runnable" in response.text
    assert "happy" in response.text


def test_page_escapes_a_hostile_project_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    store = ProjectStore("demo", tmp_path)
    store.save_project(Project(
        slug="demo", name="<script>alert(1)</script>", base_url="https://demo.test/signin",
        allowed_domains=["demo.test"],
    ))
    response = TestClient(app).get("/projects/demo/catalog")
    assert response.status_code == 200
    assert "<script>alert(1)</script>" not in response.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.text


def test_page_reports_the_runnable_count(store: ProjectStore) -> None:
    store.save_flowspec(FlowSpec(
        project="demo", flows=[_auth_flow()], review=Review(status=ReviewStatus.APPROVED),
    ))
    response = TestClient(app).get("/projects/demo/catalog")
    assert response.status_code == 200
    # CT9: this secret FILL feeds all 15 classes, so every row needs its missing key.
    assert "0</" in response.text
    assert response.text.count("set DEMO_PASSWORD in the repo-root .env") == 15
    assert "15" in response.text
    assert "/projects/demo/catalog" in TestClient(app).get("/projects/demo").text


# -- AT-588: standard packs render on the same page --------------------------


def test_no_flowspec_page_blocks_every_pack_no_flowspec_too(store: ProjectStore) -> None:
    response = TestClient(app).get("/projects/demo/catalog")
    assert response.status_code == 200
    assert response.text.count("no FlowSpec yet") >= 15 + 3  # 15 case classes + 3 packs


def test_oauth_pack_renders_runnable_when_google_signup_step_present(
    store: ProjectStore,
) -> None:
    store.save_flowspec(FlowSpec(
        project="demo",
        flows=[Flow(
            id="flow_signup", name="Sign up", entry_screen="scr_signup",
            steps=[
                Step(order=1, action=Action.NAVIGATE, target="https://demo.test/signup"),
                Step(order=2, action=Action.CLICK, target="Sign up with Google"),
            ],
        )],
        review=Review(status=ReviewStatus.APPROVED),
    ))
    response = TestClient(app).get("/projects/demo/catalog")
    assert response.status_code == 200
    assert "OAuth sign-up carry-over" in response.text
    assert "Excel column-mapping upload" in response.text


def test_pack_not_applicable_renders_distinct_from_blocked(store: ProjectStore) -> None:
    store.save_flowspec(FlowSpec(
        project="demo", flows=[_auth_flow()], review=Review(status=ReviewStatus.APPROVED),
    ))
    response = TestClient(app).get("/projects/demo/catalog")
    assert response.status_code == 200
    assert "not applicable" in response.text


@pytest.mark.parametrize("reason,label", [
    (BlockedReason.NO_GROUND_TRUTH, "no ground truth"),
    (BlockedReason.NO_LIVE_ENDPOINT, "no live endpoint"),
])
def test_reserved_blocked_reasons_render_label_action_and_escape_in_actual_route(
    store: ProjectStore, monkeypatch: pytest.MonkeyPatch, reason: BlockedReason, label: str,
) -> None:
    """Injected renderer fixtures only; production catalog does not emit these reasons."""
    action = 'provide <script>alert("fixture")</script> & review the evidence'
    entries = [CatalogEntry(
        case_class=cc, tier=TIER_BY_CLASS[cc], applicable=True,
        runnable=cc is not CaseClass.HAPPY,
        blocked_reason=reason if cc is CaseClass.HAPPY else None,
        unblock_action=action if cc is CaseClass.HAPPY else None,
    ) for cc in CaseClass]
    injected = Catalog(project="demo", entries=entries)
    monkeypatch.setattr(routes_catalog, "build_catalog", lambda *_: injected)
    response = TestClient(app).get("/projects/demo/catalog")
    assert response.status_code == 200
    tables = [ElementTree.fromstring(markup) for markup in
              re.findall(r"<table>.*?</table>", response.text, flags=re.DOTALL)]
    matching = [table for table in tables if
                [cell.text for cell in table.findall("./thead/tr/th")]
                == ["Case class", "Tier", "Applicable", "Status"]]
    assert len(matching) == 1
    rows = matching[0].findall("./tbody/tr")
    assert len(rows) == len(CaseClass) == 15
    cells = [row.findall("td") for row in rows]
    assert all(len(row) == 4 for row in cells)
    assert sorted(row[0].text for row in cells) == sorted(cc.value for cc in CaseClass)
    assert all(row[1].text == TIER_BY_CLASS[CaseClass(row[0].text)].value for row in cells)
    assert all(row[2].text == "yes" for row in cells)
    blocked = next(row[3] for row in cells if row[0].text == CaseClass.HAPPY.value)
    assert blocked.find("span").text == label != reason.value
    assert blocked.find("div").text == action
    assert blocked.findall(".//script") == []
    assert escape(action) in response.text
    assert '<script>alert("fixture")</script>' not in response.text
    assert sum(row[3].find("span").text == "runnable" for row in cells) == 14
    assert "<div class='value'>14</div><div class='label'>runnable now</div>" in response.text
    assert "<div class='value'>15</div><div class='label'>case classes</div>" in response.text
