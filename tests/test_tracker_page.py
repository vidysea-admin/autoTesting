"""T-199c: the tracker page (TB7 read-only view, TB8 preview, TB10 conflicts, TB12 status, TB13)."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from bug_loop_fixture import PROJECT, T0, event
from fastapi.testclient import TestClient
from tracker_fakes import ALLOWED, LAYOUT_A, binding

from autotester.core.paths import ProjectPaths
from autotester.schema.project import Project
from autotester.schema.tracked_bug import EventKind
from autotester.schema.tracker_binding import ConflictNote, SyncState
from autotester.stages.tracker_mapping import confirm_mapping, propose_mapping
from autotester.store.bug_store import BugStore
from autotester.store.project_store import ProjectStore
from autotester.store.tracker_store import save_binding
from autotester.ui import routers, routes_tracker
from autotester.ui.app import app

NOW = T0 + timedelta(days=1)
SECRET = "hunter2-sekret"


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    ProjectStore(PROJECT, tmp_path).save_project(Project(
        slug=PROJECT, name="Demo", base_url="https://demo.test/", allowed_domains=["demo.test"]))
    return tmp_path


def _page(root: Path) -> str:
    response = TestClient(app).get(f"/projects/{PROJECT}/tracker")
    assert response.status_code == 200
    return response.text


def test_the_page_works_with_no_sheet_and_no_bugs(root: Path) -> None:
    html = _page(root)
    assert "No bugs tracked yet" in html and "No sheet is bound" in html
    assert "Nothing has been written to the sheet" in html


def test_the_page_lists_bugs_mapping_status_conflicts_and_the_scrubbed_error(root: Path) -> None:
    bugs = BugStore(ProjectPaths(PROJECT, root).bugs_dir, clock=lambda: NOW)
    bugs.apply(event(EventKind.FAIL, 1))
    start = binding(PROJECT).model_copy(update={"mapping": propose_mapping([*LAYOUT_A, "Extra"])})
    done = confirm_mapping(start, "umesh.s", ALLOWED, NOW)
    state = SyncState(sync_status="error", last_error=f"503 from {SECRET} <b>x</b>",
                      last_attempt_at=NOW, retry_at=NOW + timedelta(minutes=15),
                      conflicts=[ConflictNote(bug_key="k1", column="Status",
                                              sheet_has="Won't fix")])
    save_binding(done.model_copy(update={"sync": state}), root)
    (root / ".env").write_text(f"UNRELATED_TOKEN={SECRET}\n", encoding="utf-8")
    html = _page(root)
    assert "Checkout button does nothing" in html
    assert "confirmed by umesh.s" in html and "Bug Title" in html
    assert 'id="sync-status">error' in html.replace("'", '"')
    assert "Sync conflicts" in html and "not overwritten" in html
    assert SECRET not in html and "<b>x</b>" not in html


def test_the_page_is_a_get_only_route_with_a_report_view_policy(root: Path) -> None:
    methods = {m for r in routes_tracker.router.routes for m in r.methods}
    assert methods == {"GET"}
    assert routes_tracker.ROUTE_POLICY == {
        "GET /projects/{slug}/tracker": ("report.view", "project")}
    assert routes_tracker.router in routers.ROUTERS
