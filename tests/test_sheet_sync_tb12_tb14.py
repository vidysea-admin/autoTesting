"""T-199d: TB12 (a sheet outage is not a run failure) and TB14 (generic, not one project's layout).

Fake client only: no Google, no network. Contract: qa/contracts/team-bug-loop.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from bug_loop_fixture import KEY, event, seed
from fastapi.testclient import TestClient
from sheet_fake import FakeSheet

from autotester.core.paths import ProjectPaths
from autotester.schema.project import Project
from autotester.schema.sheet_plan import PlanConfirmation, SyncMemory
from autotester.schema.tracked_bug import EventKind
from autotester.stages.sheet_plan import plan_sync
from autotester.stages.sheet_sync import load_status, try_sync
from autotester.stages.tracker_binding import load_binding, propose_binding, save_binding
from autotester.store.bug_store import BugStore
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app

NOW = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)
SECRET = "hunter2-PLANTED-9f3a"
HEADER_A = ["Bug ID", "Title", "Severity", "Screen", "Status", "Assigned To", "Notes"]
HEADER_B = ["ticket", "Summary", "Priority", "Module", "State", "Owner", "First Seen", "Count"]
SRC = Path(__file__).resolve().parents[1] / "src" / "autotester" / "stages"


class DownSheet(FakeSheet):
    """Raises on every call, with a planted secret in the message."""

    def read(self, sheet_id: str, tab: str):
        raise ConnectionError(f"503 from sheet using token {SECRET}")


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    ProjectStore("demo", tmp_path).save_project(Project(
        slug="demo", name="Demo", base_url="https://demo.test/", allowed_domains=["demo.test"]))
    BugStore(ProjectPaths("demo", tmp_path).dir).apply(event(EventKind.FAIL, 1, seed_obj=seed()))
    return tmp_path


def _scrub(text: str) -> str:
    return text.replace(SECRET, "[REDACTED]")


def _confirmed(sheet: FakeSheet, bugs, cols) -> PlanConfirmation:
    plan = plan_sync(bugs, sheet.read(cols.sheet_id, cols.tab), cols, SyncMemory(), _scrub)
    return PlanConfirmation(plan_hash=plan.plan_hash, confirmed_by="umesh", confirmed_at=NOW)


def test_tb12_an_outage_is_a_visible_status_and_the_tracker_is_untouched(root: Path) -> None:
    bugs = BugStore(ProjectPaths("demo", root).dir)
    before = bugs.bugs()
    cols = propose_binding("sheet-1", "Tracker", HEADER_A).to_columns()
    assert cols is not None
    asked = PlanConfirmation(plan_hash="h", confirmed_by="umesh", confirmed_at=NOW)
    status = try_sync("demo", DownSheet(HEADER_A), before.values(), cols, asked, _scrub, NOW, root)
    assert status.sync_status == "error" and status.retry_at and status.retry_at > NOW
    assert SECRET not in (status.last_error or "") and "ConnectionError" in status.last_error
    assert bugs.bugs() == before                        # the in-product tracker is authoritative
    html = TestClient(app).get("/projects/demo/tracker").text
    assert "Sheet sync" in html and "error" in html and "ConnectionError" in html
    assert SECRET not in html and "Checkout button does nothing" in html


def test_tb12_once_the_sheet_is_back_it_converges(root: Path) -> None:
    bugs = BugStore(ProjectPaths("demo", root).dir).bugs().values()
    cols = propose_binding("sheet-1", "Tracker", HEADER_A).to_columns()
    assert cols is not None
    asked = PlanConfirmation(plan_hash="h", confirmed_by="umesh", confirmed_at=NOW)
    try_sync("demo", DownSheet(HEADER_A), bugs, cols, asked, _scrub, NOW, root)
    sheet = FakeSheet(HEADER_A)
    confirmation = _confirmed(sheet, bugs, cols)
    status = try_sync("demo", sheet, bugs, cols, confirmation, _scrub, NOW, root)
    assert status.sync_status == "ok" and load_status("demo", root) == status
    assert len(sheet.rows) == 1 and sheet.rows[0][0] == KEY
    again = try_sync("demo", sheet, bugs, cols, None, _scrub, NOW, root)
    assert len(sheet.rows) == 1 and again.sync_status == "error"   # no confirmation: refused


def test_tb12_a_live_client_is_still_refused_and_recorded_as_an_error(root: Path) -> None:
    bugs = BugStore(ProjectPaths("demo", root).dir).bugs().values()
    cols = propose_binding("sheet-1", "Tracker", HEADER_A).to_columns()
    assert cols is not None
    live = FakeSheet(HEADER_A, live=True)
    status = try_sync("demo", live, bugs, cols, None, _scrub, NOW, root)
    assert status.sync_status == "error" and not live.write_calls


def test_tb14_two_layouts_one_code_and_a_per_project_binding(root: Path) -> None:
    a = propose_binding("sheet-a", "Tracker", HEADER_A)
    b = propose_binding("sheet-b", "Bugs", HEADER_B)
    assert a.columns["bug_key"] == "Bug ID" and a.columns["assignee"] == "Assigned To"
    assert b.columns["bug_key"] == "ticket" and b.columns["severity"] == "Priority"
    assert b.columns["status"] == "State" and b.columns["count"] == "Count"
    assert "last_seen" in a.unmapped and a.unmapped["last_seen"] == []   # unmapped, not guessed
    ProjectStore("other", root).save_project(Project(
        slug="other", name="Other", base_url="https://o.test/", allowed_domains=["o.test"]))
    save_binding("demo", a, root)
    save_binding("other", b, root)
    assert load_binding("demo", root) == a and load_binding("other", root) == b
    assert (ProjectPaths("demo", root).dir / "tracker_binding.json").exists()
    assert load_binding("nobody", root) is None


def test_tb14_two_candidates_or_no_key_is_unmapped_and_the_project_still_works(root: Path) -> None:
    both = propose_binding("s", "T", ["Title", "Summary", "Status"])
    assert "title" in both.unmapped and sorted(both.unmapped["title"]) == ["Summary", "Title"]
    keyless = propose_binding("s", "T", ["Title", "Status"])
    assert keyless.to_columns() is None
    assert TestClient(app).get("/projects/demo/tracker").status_code == 200


def test_tb14_no_project_column_name_in_the_tracker_modules() -> None:
    for path in SRC.glob("tracker_*.py"):
        assert "pathlynks" not in path.read_text(encoding="utf-8").lower(), path.name
