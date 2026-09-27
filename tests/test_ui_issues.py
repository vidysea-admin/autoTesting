"""Video-issues page and workbook download tests."""

from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from autotester.schema.enums import Action, IssueCategory
from autotester.schema.issue import Issue
from autotester.schema.project import Project
from autotester.stages.issues import ISSUE_COLUMNS
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectStore:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    result = ProjectStore("demo", tmp_path)
    result.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                                allowed_domains=["demo.test"]))
    return result


def _hostile_issue() -> Issue:
    return Issue(project="demo", source_id="src_one", recording_label="Demo clip", at_s=4,
                 screen="Login", title="<script>alert(1)</script>",
                 what_is_wrong="Submit does nothing", category=IssueCategory.LOGIC_ERROR)


def test_issues_page_escapes_persisted_issue(store: ProjectStore) -> None:
    store.add_issue(_hostile_issue())
    response = TestClient(app).get("/projects/demo/issues")
    assert response.status_code == 200
    assert "<script>alert(1)</script>" not in response.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.text


def test_issues_workbook_has_the_human_thirteen_column_header(store: ProjectStore) -> None:
    store.add_issue(_hostile_issue())
    response = TestClient(app).get("/projects/demo/issues.xlsx")
    assert response.status_code == 200
    sheet = load_workbook(BytesIO(response.content)).active
    assert [cell.value for cell in sheet[1]] == ISSUE_COLUMNS


# -- AT-597: a human path from a found issue to a pinned regression case -----

def _a_signup_issue(**kw) -> Issue:
    return Issue(
        project="demo", source_id="src_one", recording_label="Demo clip", at_s=4,
        screen="Signup", title=kw.pop("title", "Google sign-in drops the data filled at signup"),
        what_is_wrong="fields filled before the Google redirect are gone on return",
        category=IssueCategory.LOGIC_ERROR, **kw,
    )


def _pin_form_data(target: str = "https://demo.test/signup") -> dict:
    return {
        "step_action": [Action.NAVIGATE.value, Action.CLICK.value],
        "step_target": [target, "#google-sign-in"],
        "step_value": ["", ""],
        "step_expected": ["", "signup form still has my email"],
    }


def test_issues_page_offers_a_pin_action_for_an_unpinned_issue(store: ProjectStore) -> None:
    issue = _a_signup_issue()
    store.add_issue(issue)

    response = TestClient(app).get("/projects/demo/issues")

    assert response.status_code == 200
    assert f"/projects/demo/issues/{issue.id}/pin" in response.text
    assert "Pin as regression case" in response.text


def test_pin_form_shows_the_issue_and_a_step_editor(store: ProjectStore) -> None:
    issue = _a_signup_issue()
    store.add_issue(issue)

    response = TestClient(app).get(f"/projects/demo/issues/{issue.id}/pin")

    assert response.status_code == 200
    assert "Google sign-in drops the data filled at signup" in response.text
    assert "step_action" in response.text and "step_target" in response.text


def test_pinning_an_unknown_issue_is_404(store: ProjectStore) -> None:
    response = TestClient(app).get("/projects/demo/issues/iss_nope/pin")
    assert response.status_code == 404


def test_pinning_with_confirmed_steps_creates_a_protected_case(store: ProjectStore) -> None:
    issue = _a_signup_issue()
    store.add_issue(issue)

    response = TestClient(app).post(
        f"/projects/demo/issues/{issue.id}/pin", data=_pin_form_data(), follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/projects/demo/cases"
    cases = store.list_cases()
    assert len(cases) == 1
    assert cases[0].pinned is True
    assert cases[0].pinned_issue_id == issue.id
    assert issue.title in cases[0].title


def test_pinning_with_no_confirmed_steps_is_refused(store: ProjectStore) -> None:
    """AT-597: steps must be human-confirmed -- an all-blank submission must
    never silently mint a case with no way to reproduce the bug."""
    issue = _a_signup_issue()
    store.add_issue(issue)

    response = TestClient(app).post(f"/projects/demo/issues/{issue.id}/pin", data={
        "step_action": [Action.NAVIGATE.value], "step_target": [""],
        "step_value": [""], "step_expected": [""],
    })

    assert response.status_code == 400
    assert store.list_cases() == []


def test_pinning_an_unreachable_navigate_step_is_refused(store: ProjectStore) -> None:
    """Same AT-058/AT-432 guard the hand-add case form uses: a step that could
    never run at execution time is refused at creation time too."""
    issue = _a_signup_issue()
    store.add_issue(issue)

    response = TestClient(app).post(
        f"/projects/demo/issues/{issue.id}/pin",
        data=_pin_form_data(target="https://not-allowed.test/signup"),
    )

    assert response.status_code == 400
    assert store.list_cases() == []


def test_a_pinned_issue_shows_pinned_instead_of_the_pin_link(store: ProjectStore) -> None:
    issue = _a_signup_issue()
    store.add_issue(issue)
    client = TestClient(app)
    client.post(f"/projects/demo/issues/{issue.id}/pin", data=_pin_form_data())

    response = client.get("/projects/demo/issues")

    assert response.status_code == 200
    assert f"/projects/demo/issues/{issue.id}/pin" not in response.text
    assert "pinned" in response.text.lower()


def test_pinning_the_same_issue_and_steps_twice_is_refused_not_silently_swallowed(
    store: ProjectStore,
) -> None:
    """Same AT-060 duplicate guard the hand-add case form uses
    (`ui/routes_cases.py::_refuse_duplicate`): `add_case` is idempotent on the
    content id, so a second identical pin must say so rather than redirecting
    as if a second case had been created."""
    issue = _a_signup_issue()
    store.add_issue(issue)
    client = TestClient(app)
    client.post(f"/projects/demo/issues/{issue.id}/pin", data=_pin_form_data())

    response = client.post(f"/projects/demo/issues/{issue.id}/pin", data=_pin_form_data())

    assert response.status_code == 400
    assert "already has a case with exactly these steps" in response.text
    assert len(store.list_cases()) == 1


def test_repinning_an_issue_with_different_steps_is_refused_409(store: ProjectStore) -> None:
    """AT-604: `Case.id` is content-addressed on its steps, so a second pin
    with DIFFERENT steps would not collide with the first pinned case and
    would silently leave two protected cases for the same finding."""
    issue = _a_signup_issue()
    store.add_issue(issue)
    client = TestClient(app)
    client.post(f"/projects/demo/issues/{issue.id}/pin", data=_pin_form_data())

    response = client.post(
        f"/projects/demo/issues/{issue.id}/pin",
        data=_pin_form_data(target="https://demo.test/other-signup"),
    )

    assert response.status_code == 409
    assert len(store.list_cases()) == 1
