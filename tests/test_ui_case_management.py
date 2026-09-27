"""Listing, renaming and deleting a project's cases. Contract: qa/contracts/ui.md.

AT-060: `ProjectStore.add_case` is idempotent on the content id, so re-posting
the form with identical steps was silently swallowed while redirecting as if it
had worked. Because `title` sits outside `Case.compute_id()`, that was also the
natural — and silently failing — way a user would try to fix a typo'd title.
Split from test_ui_cases.py once that file passed doctor's 300-line cap.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autotester.schema.enums import Action, CaseClass
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app


@pytest.fixture
def scratch_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _onboard(client: TestClient) -> None:
    client.post("/onboard", data={
        "slug": "demo", "name": "Demo", "base_url": "https://demo.test/signin",
        "allowed_domains": "demo.test",
    })


# -- AT-060: see your cases, fix a title, remove a mistake --------------------

def _add_case(client: TestClient, title: str, target: str = "https://demo.test/signin"):
    return client.post("/projects/demo/cases", data={
        "title": title, "case_class": CaseClass.HAPPY.value,
        "step_action": [Action.NAVIGATE.value], "step_target": [target],
        "step_value": [""], "step_expected": [""],
    }, follow_redirects=False)


def test_resubmitting_identical_steps_is_refused_not_silently_swallowed(
    client: TestClient, scratch_root: Path
) -> None:
    """The trap: `add_case` is idempotent on the content id, so the second post
    used to be discarded while redirecting as if it had worked. Worse, since
    `title` is outside `compute_id`, re-submitting was the natural way a user
    would try to fix a typo — and it failed silently."""
    _onboard(client)
    _add_case(client, "Sign-in page loads")

    response = _add_case(client, "Sign-in page loads (typo fixed)")

    assert response.status_code == 400
    assert "already has a case with exactly these steps" in response.text
    cases = ProjectStore("demo", scratch_root).list_cases()
    assert len(cases) == 1
    assert cases[0].title == "Sign-in page loads"  # unchanged, and the user was told


def test_cases_list_shows_every_case(client: TestClient, scratch_root: Path) -> None:
    _onboard(client)
    _add_case(client, "Front door loads")
    _add_case(client, "Training lookup works", target="https://demo.test/p/me")

    response = client.get("/projects/demo/cases")

    assert response.status_code == 200
    assert "Front door loads" in response.text
    assert "Training lookup works" in response.text


def test_cases_list_on_an_empty_project_points_at_the_add_form(
    client: TestClient, scratch_root: Path
) -> None:
    _onboard(client)

    response = client.get("/projects/demo/cases")

    assert response.status_code == 200
    assert "No cases yet" in response.text
    assert "/projects/demo/cases/new" in response.text


def test_renaming_a_case_keeps_its_id_so_history_stays_attached(
    client: TestClient, scratch_root: Path
) -> None:
    """Title sits outside `Case.compute_id()`, so a rename must not mint a new
    case — its past runs, verdicts and rubric hang off that id."""
    _onboard(client)
    _add_case(client, "Sign-in pge loads")  # typo
    store = ProjectStore("demo", scratch_root)
    original_id = store.list_cases()[0].id

    response = client.post(f"/projects/demo/cases/{original_id}/rename",
                            data={"title": "Sign-in page loads"}, follow_redirects=False)

    assert response.status_code == 303
    cases = ProjectStore("demo", scratch_root).list_cases()
    assert len(cases) == 1
    assert cases[0].title == "Sign-in page loads"
    assert cases[0].id == original_id


def test_renaming_to_a_blank_title_is_refused(
    client: TestClient, scratch_root: Path
) -> None:
    _onboard(client)
    _add_case(client, "Real title")
    case_id = ProjectStore("demo", scratch_root).list_cases()[0].id

    response = client.post(f"/projects/demo/cases/{case_id}/rename", data={"title": "  "})

    assert response.status_code == 400
    assert ProjectStore("demo", scratch_root).list_cases()[0].title == "Real title"


def test_renaming_an_unknown_case_is_404(client: TestClient, scratch_root: Path) -> None:
    _onboard(client)

    response = client.post("/projects/demo/cases/case_nope/rename", data={"title": "x"})

    assert response.status_code == 404


def test_deleting_a_case_removes_it(client: TestClient, scratch_root: Path) -> None:
    _onboard(client)
    _add_case(client, "Added by mistake")
    case_id = ProjectStore("demo", scratch_root).list_cases()[0].id

    response = client.post(f"/projects/demo/cases/{case_id}/delete", follow_redirects=False)

    assert response.status_code == 303
    assert ProjectStore("demo", scratch_root).list_cases() == []


def test_deleting_one_case_leaves_the_others(client: TestClient, scratch_root: Path) -> None:
    _onboard(client)
    _add_case(client, "Keep me")
    _add_case(client, "Delete me", target="https://demo.test/other")
    store = ProjectStore("demo", scratch_root)
    doomed = next(c for c in store.list_cases() if c.title == "Delete me")

    client.post(f"/projects/demo/cases/{doomed.id}/delete")

    remaining = ProjectStore("demo", scratch_root).list_cases()
    assert [c.title for c in remaining] == ["Keep me"]


def test_deleting_an_unknown_case_is_404(client: TestClient, scratch_root: Path) -> None:
    _onboard(client)

    response = client.post("/projects/demo/cases/case_nope/delete")

    assert response.status_code == 404


def test_deleting_then_re_adding_the_same_steps_works(
    client: TestClient, scratch_root: Path
) -> None:
    """Delete must genuinely clear the id from the store's cache, or the
    duplicate guard would refuse a legitimate re-add."""
    _onboard(client)
    _add_case(client, "First go")
    case_id = ProjectStore("demo", scratch_root).list_cases()[0].id
    client.post(f"/projects/demo/cases/{case_id}/delete")

    response = _add_case(client, "Second go")

    assert response.status_code == 303
    cases = ProjectStore("demo", scratch_root).list_cases()
    assert [c.title for c in cases] == ["Second go"]


def test_deleting_a_pinned_case_through_the_ui_is_refused_with_409(
    client: TestClient, scratch_root: Path
) -> None:
    """AT-585: the delete button is the real prune path a human has, and it
    must refuse a pinned case (409, case found and protected) rather than
    silently succeeding or claiming 404 (case not found)."""
    _onboard(client)
    _add_case(client, "Known bug — pinned regression")
    store = ProjectStore("demo", scratch_root)
    case = store.list_cases()[0]
    store.update_case(case.model_copy(update={"pinned": True, "pinned_issue_id": "iss_1"}))

    response = client.post(f"/projects/demo/cases/{case.id}/delete", follow_redirects=False)

    assert response.status_code == 409
    assert [c.id for c in ProjectStore("demo", scratch_root).list_cases()] == [case.id]
