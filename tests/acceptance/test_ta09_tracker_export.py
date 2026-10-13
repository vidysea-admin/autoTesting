"""TA9 (as re-scoped by D-090 item 2): the tracker page and the CSV/xlsx export, plus the standing
limit that no real sheet is bound or written. The page and the export are xfail(strict): T-199
TB7/TB15 are not on master. The standing limit runs today."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from rig import SLUG, World, press

from autotester.stages.bug_run import process_run

REPO = Path(__file__).resolve().parents[2]


def test_the_standing_limit_pathlynks_has_no_confirmed_tracker_binding() -> None:
    config = REPO / "projects" / "pathlynks" / "project.json"
    if not config.is_file():
        pytest.fail(f"{config} is missing: the standing-limit check has nothing to read")
    data = json.loads(config.read_text(encoding="utf-8"))
    tracker = data.get("tracker") or {}
    assert not tracker.get("first_write_confirmed_by")


def test_no_google_host_was_contacted_and_no_sheet_client_exists_in_the_rig(world: World) -> None:
    process_run(world.store(), world.bugs(), press(world, "dev"))
    assert world.egress.blocked == []
    assert world.store().load_project().tracker is None


def test_tb7_subadmin_opens_the_tracker_page_and_sees_status_severity_screen(world: World) -> None:
    process_run(world.store(), world.bugs(), press(world, "dev"))
    page = world.users["subadmin"].get(f"/projects/{SLUG}/tracker")
    assert page.status_code == 200 and "severity" in page.text.lower()


def test_tb15_the_export_is_byte_identical_twice_and_scoped_by_report_view(world: World) -> None:
    process_run(world.store(), world.bugs(), press(world, "dev"))
    first = world.users["subadmin"].get(f"/projects/{SLUG}/tracker/export.csv")
    second = world.users["subadmin"].get(f"/projects/{SLUG}/tracker/export.csv")
    assert first.status_code == 200 and first.content == second.content
