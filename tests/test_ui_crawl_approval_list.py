"""Saving a crawl approval says so, and the approvals in force are listed. AT-435.

Found by live-browser validation: "Save crawl approval" redirected back to an
identical page — no message, no list — so a human who could not tell whether it
worked clicked again, and `approvals.jsonl` gained a second, duplicate grant.
Consent is a file a human writes once (D-018); a page that hides the file makes
that impossible to do on purpose.

Split from `test_ui_crawls.py` (at doctor's 300-line cap) along a real seam: that
file proves a grant is saved correctly; this one proves the human can SEE it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autotester.schema.approval import RunApproval
from autotester.schema.enums import ApprovalKind
from autotester.schema.project import Project
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app

_GRANT = {
    "granted_by": "Umesh", "scope": "read and click safe controls",
    "expires_at": "2099-09-11T12:00", "timezone_offset_minutes": "330",
    "max_actions": "17", "wall_clock_s": "45",
}


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectStore:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    s = ProjectStore("demo", tmp_path)
    s.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                           allowed_domains=["demo.test"]))
    return s


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _approval(**overrides: object) -> RunApproval:
    fields: dict[str, object] = dict(
        project="demo", run_kind=ApprovalKind.CRAWL, target="https://demo.test",
        scope="listed scope", max_actions=5, wall_clock_s=30.0, granted_by="Asha",
        granted_at="2026-09-16T00:00:00+00:00", expires_at="2099-01-01T00:00:00+00:00",
    )
    fields.update(overrides)
    return RunApproval(**fields).sign()


def test_saving_shows_a_confirmation_naming_the_saved_grant(
    client: TestClient, store: ProjectStore,
) -> None:
    page = client.post("/projects/demo/crawl-approval", data=_GRANT)  # follows the 303

    assert page.status_code == 200
    saved = store.list_approvals()
    assert len(saved) == 1
    assert "Crawl approval saved" in page.text
    assert saved[0].id in page.text


def test_a_second_identical_submit_saves_nothing_new_and_says_so(
    client: TestClient, store: ProjectStore,
) -> None:
    """The live reproduction: two clicks, two rows. Now the second click finds the
    grant already on file instead of silently minting a twin."""
    client.post("/projects/demo/crawl-approval", data=_GRANT)
    page = client.post("/projects/demo/crawl-approval", data=_GRANT)

    assert len(store.list_approvals()) == 1
    assert "already on file" in page.text


def test_a_grant_that_differs_in_any_bound_is_a_new_grant(
    client: TestClient, store: ProjectStore,
) -> None:
    """Idempotency must not swallow a real change: a wider grant is a decision."""
    client.post("/projects/demo/crawl-approval", data=_GRANT)
    client.post("/projects/demo/crawl-approval", data={**_GRANT, "max_actions": "18"})

    assert len(store.list_approvals()) == 2


def test_the_page_lists_approvals_in_force_with_their_bounds(
    client: TestClient, store: ProjectStore,
) -> None:
    store.add_approval(_approval())

    text = client.get("/projects/demo/env").text

    assert "Approvals in force" in text
    for shown in ("Asha", "listed scope", "2099-01-01", _approval().id):
        assert shown in text


def test_expired_edited_and_other_target_grants_are_not_listed_as_in_force(
    client: TestClient, store: ProjectStore,
) -> None:
    """Listing a grant the consent gate would refuse would be a false reassurance."""
    store.add_approval(_approval(granted_by="Expired", expires_at="2000-01-01T00:00:00+00:00"))
    store.add_approval(_approval(granted_by="Elsewhere", target="https://other.test"))
    edited = _approval(granted_by="Edited").model_dump(mode="json")
    edited["max_actions"] = 9999  # widened after granting; the id no longer matches
    with store.paths.approvals.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(edited) + "\n")

    text = client.get("/projects/demo/env").text

    for hidden in ("Expired", "Elsewhere", "Edited"):
        assert hidden not in text
    assert "3 more on file" in text, "say they exist, so nobody re-grants blindly"


@pytest.mark.parametrize("kind", [ApprovalKind.READ, ApprovalKind.ADVERSARIAL,
                                  ApprovalKind.LIVE_CASE])
def test_a_grant_for_another_kind_of_run_is_not_counted_with_a_false_reason(
    client: TestClient, store: ProjectStore, kind: ApprovalKind,
) -> None:
    """AT-452: an intact, unexpired, same-target grant for a DIFFERENT kind of run
    was counted in "N more on file are expired, edited after granting, or for
    another target" — every word of which is false about it. This card is about
    crawl approvals; other kinds are not its business to count."""
    store.add_approval(_approval(granted_by="OtherKind", run_kind=kind))

    text = client.get("/projects/demo/env").text

    assert "OtherKind" not in text, "not a crawl approval, so not listed as one"
    assert "more on file" not in text


def test_a_crawl_grant_naming_another_project_is_counted_with_a_true_reason(
    client: TestClient, store: ProjectStore,
) -> None:
    """AT-455: an intact, unexpired, same-target CRAWL grant whose `project` names
    another project is rightly not honoured here (the consent gate matches the
    project), but the note gave "expired, edited, or for another target" — none
    of which is true of it. The reason must name the case that is."""
    store.add_approval(_approval(granted_by="ElsewhereProject", project="another-project"))

    text = client.get("/projects/demo/env").text

    assert "ElsewhereProject" not in text, "not in force here, so not listed"
    assert "1 more on file" in text
    assert "another target or project" in text


def test_the_saved_banner_is_driven_by_disk_not_by_the_query_string(
    client: TestClient, store: ProjectStore,
) -> None:
    """`?saved=` names an id; the page must not echo whatever it is handed."""
    canary = "<script>alert(1)</script>"

    text = client.get("/projects/demo/env", params={"saved": canary}).text

    assert canary not in text
    assert "Crawl approval saved" not in text


def test_approval_text_is_escaped_when_listed(client: TestClient, store: ProjectStore) -> None:
    store.add_approval(_approval(scope="<img src=x onerror=alert(1)>"))

    text = client.get("/projects/demo/env").text

    assert "<img src=x onerror=alert(1)>" not in text
    assert "&lt;img src=x onerror=alert(1)&gt;" in text
