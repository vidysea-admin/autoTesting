"""T-200 TS1: the schedule card and routes behind the T-204 login gate (team-schedule.md TS1).

Four default groups x {own, assigned, other} projects x {GET, save, pause, delete}; a refused
POST leaves `project.json` byte-identical; invalid values name their field and store nothing.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from auth_harness import gate_on, project, team, user_id

from autotester.auth.access import set_owner, set_relation
from autotester.schema.auth import ProjectRelation
from autotester.schema.schedule import ScheduleMode
from autotester.store.project_store import ProjectStore

HTML = {"accept": "text/html"}
FIXED = {"mode": "fixed", "fixed_at": "09:30", "timezone": "UTC"}


@pytest.fixture()
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = gate_on(tmp_path, monkeypatch)
    users = team()
    for slug in ("own", "assigned", "other"):
        project(root, slug)
    set_owner("own", user_id("dev@team.test"))
    set_owner("assigned", user_id("admin@team.test"))
    set_relation("assigned", user_id("sub@team.test"), ProjectRelation.ASSIGNED, True)
    set_owner("other", user_id("admin@team.test"))
    return root, users


def _bytes(root: Path, slug: str) -> bytes:
    return (root / "projects" / slug / "project.json").read_bytes()


def _schedule(root: Path, slug: str):
    return ProjectStore(slug, root).load_project().schedule


# (user, slug) -> may manage. admin: all; sub-admin: assigned; developer: own; tester: none.
MANAGE = {("admin", "own"): True, ("admin", "assigned"): True, ("admin", "other"): True,
          ("sub", "assigned"): True, ("dev", "own"): True}


@pytest.mark.parametrize("who", ["admin", "sub", "dev", "tester"])
@pytest.mark.parametrize("slug", ["own", "assigned", "other"])
def test_ts1_save_needs_schedule_manage_on_the_project(world, who: str, slug: str) -> None:
    root, users = world
    before = _bytes(root, slug)
    resp = users[who].post(f"/projects/{slug}/schedule", data=FIXED)
    if MANAGE.get((who, slug)):
        assert resp.status_code == 303
        saved = _schedule(root, slug)
        assert saved.mode is ScheduleMode.FIXED and saved.owner == f"{who}@team.test"
    else:
        assert resp.status_code in (403, 404)  # 404 when the project is not even viewable
        assert _bytes(root, slug) == before


def test_ts1_403_for_a_viewer_without_the_key(world) -> None:
    root, users = world
    resp = users["tester"].post("/projects/own/schedule", data=FIXED, headers=HTML)
    assert resp.status_code in (403, 404)
    set_relation("own", user_id("tester@team.test"), ProjectRelation.SHARED, True)
    before = _bytes(root, "own")
    resp = users["tester"].post("/projects/own/schedule", data=FIXED)
    assert resp.status_code == 403
    assert "schedule.manage" in resp.text  # TS1: the 403 names the key, and only the key
    for tail in ("pause", "resume", "delete"):
        refused = users["tester"].post(f"/projects/own/schedule/{tail}")
        assert refused.status_code == 403 and "schedule.manage" in refused.text
    assert _bytes(root, "own") == before
    assert users["tester"].get("/projects/own/schedule").status_code == 200  # project.view


def test_ts1_card_hides_controls_without_the_key(world) -> None:
    _root, users = world
    set_relation("own", user_id("tester@team.test"), ProjectRelation.SHARED, True)
    assert "Save schedule" not in users["tester"].get("/projects/own/schedule").text
    page = users["dev"].get("/projects/own/schedule").text
    assert "Save schedule" in page and "Scheduled test" in page
    assert "Scheduled test" in users["dev"].get("/projects/own").text


def test_ts1_pause_resume_delete_round_trip(world) -> None:
    root, users = world
    dev = users["dev"]
    assert dev.post("/projects/own/schedule", data=FIXED).status_code == 303
    assert dev.post("/projects/own/schedule/pause").status_code == 303
    assert _schedule(root, "own").paused is True
    assert "Resume" in dev.get("/projects/own/schedule").text
    assert dev.post("/projects/own/schedule/resume").status_code == 303
    assert _schedule(root, "own").paused is False
    assert "Next run" in dev.get("/projects/own/schedule").text
    assert dev.post("/projects/own/schedule/delete").status_code == 303
    assert _schedule(root, "own") is None


def test_ts1_pause_without_a_schedule_is_refused(world) -> None:
    root, users = world
    before = _bytes(root, "own")
    assert users["dev"].post("/projects/own/schedule/pause").status_code == 400
    assert _bytes(root, "own") == before


def test_ts1_delete_removes_markers_and_records(world) -> None:
    from autotester.schema.schedule import SlotClaim, SlotOutcome, SlotRecord
    from autotester.stages.schedule_store import append_record, claim, project_records_path
    from autotester.stages.schedule_wiring import schedule_paths

    root, users = world
    assert users["dev"].post("/projects/own/schedule", data=FIXED).status_code == 303
    now = datetime.now(UTC)
    paths = schedule_paths(root)
    key = "own:fixed:2026-10-14T09:30Z"
    claim(paths.claims, key, SlotClaim(
        slot_key=key, mode=ScheduleMode.FIXED, instant=now, claimed_at=now,
        intended=SlotOutcome.ENQUEUED))
    records = project_records_path(paths.records, "own")
    append_record(records, SlotRecord(slot_key=key, project="own", mode=ScheduleMode.FIXED,
                                      instant=now, recorded_at=now, outcome=SlotOutcome.ENQUEUED))
    assert records.is_file()
    assert users["dev"].post("/projects/own/schedule/delete").status_code == 303
    assert not records.exists() and list(paths.claims.glob("*own*")) == []


@pytest.mark.parametrize("data,field", [
    ({"mode": "fixed", "fixed_at": "25:00"}, "fixed_at"),
    ({"mode": "fixed", "fixed_at": "24:00"}, "fixed_at"),
    ({"mode": "fixed", "fixed_at": "9:5"}, "fixed_at"),
    ({"mode": "fixed", "fixed_at": "09:30", "timezone": "America/New_York"}, "timezone"),
    ({"mode": "fixed", "fixed_at": "09:30", "timezone": "ist"}, "timezone"),
    ({"mode": "fixed"}, "fixed_at"),
    ({"mode": "custom"}, "custom"),
    ({"mode": "custom", "weekly_at": "09:00"}, "weekly"),
    ({"mode": "custom", "weekdays": ["7"], "weekly_at": "09:00"}, "weekly"),
    ({"mode": "custom", "weekdays": ["1", "1"], "weekly_at": "09:00"}, "weekly"),
    ({"mode": "custom", "one_offs": "2020-01-01T09:00"}, "one_offs"),
    ({"mode": "custom", "one_offs": "not a date"}, "one_offs"),
    ({"mode": "manual", "fixed_at": "09:30"}, "manual"),
    ({"mode": "hourly"}, "mode"),
])
def test_ts1_invalid_values_name_the_field_and_store_nothing(world, data, field) -> None:
    root, users = world
    before = _bytes(root, "own")
    resp = users["dev"].post("/projects/own/schedule", data=data)
    assert resp.status_code == 400 and field in resp.text
    assert _bytes(root, "own") == before


def test_ts1_valid_custom_modes_save(world) -> None:
    root, users = world
    soon = (datetime.now(UTC) + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M")
    resp = users["dev"].post("/projects/own/schedule", data={
        "mode": "custom", "timezone": "IST", "weekdays": ["0", "4"], "weekly_at": "10:15",
        "one_offs": soon})
    assert resp.status_code == 303
    saved = _schedule(root, "own")
    assert saved.weekly.weekdays == [0, 4] and len(saved.one_offs) == 1
    assert saved.timezone.value == "IST"


def test_ts1_manual_default_card_for_a_project_without_schedule(world) -> None:
    _root, users = world
    assert "manual" in users["dev"].get("/projects/own/schedule").text


def test_ts1_cross_origin_post_is_refused_first(world) -> None:
    root, users = world
    before = _bytes(root, "own")
    resp = users["dev"].post("/projects/own/schedule", data=FIXED,
                             headers={"Origin": "https://evil.example"})
    assert resp.status_code == 403
    assert _bytes(root, "own") == before


def test_ts1_every_schedule_route_has_a_policy_row() -> None:
    from autotester.auth import policy
    from autotester.schema.auth import PermissionKey
    rows = {k: v for k, v in policy.ROUTE_POLICY.items() if "/schedule" in k[1]}
    assert rows[("GET", "/projects/{slug}/schedule")].key is PermissionKey.PROJECT_VIEW
    posts = [v for (m, _p), v in rows.items() if m == "POST"]
    assert len(posts) == 4 and all(v.key is PermissionKey.SCHEDULE_MANAGE for v in posts)
