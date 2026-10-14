"""T-200 TS5: a blocked or refused scheduled slot reaches the website inbox (`GET /inbox`).

A real `tick_project` with a refusing gate (and a refusing owner guard) writes the slot record;
the inbox then lists it for a viewer with `report.view` on that project, never for one without,
and never lists a slot that was enqueued or skipped. No run, queue entry or run directory exists.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from auth_harness import gate_on, project, team, user_id
from schedule_fakes import daily, make_deps, utc
from team_run_fakes import FakeQueue

from autotester.auth.access import set_owner
from autotester.core.paths import team_path
from autotester.stages.schedule_store import project_records_path
from autotester.stages.scheduler import tick_project
from autotester.ui import routes_inbox

HTML = {"accept": "text/html"}
NOW = utc(2026, 10, 14, 9, 0)


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = gate_on(tmp_path, monkeypatch)
    monkeypatch.setattr(routes_inbox, "get_queue", lambda: FakeQueue())
    project(root, "alpha")
    project(root, "beta")
    return root


def _tick(slug: str, *, gate=None, guard=None):
    deps, q = make_deps(tmp := team_path("schedule", "claims").parent / slug, slug, gate=gate)
    deps = type(deps)(**{**deps.__dict__, "records_path": project_records_path(
        team_path("schedule", "records"), slug), "claim_dir": tmp / "claims",
        "owner_guard": guard})
    records = tick_project(slug, daily(), NOW, deps, since=utc(2026, 10, 14, 8, 0))
    return records, q


def test_blocked_slot_is_listed_for_the_owner_and_not_for_others(world) -> None:
    users = team()
    set_owner("alpha", user_id("dev@team.test"))
    set_owner("beta", user_id("sub@team.test"))
    records, q = _tick("alpha", gate=lambda s: "no_secret_ref: no credential pair declared")
    assert [r.outcome.value for r in records] == ["blocked_no_credentials"]
    assert len(q) == 0                                   # still no queue entry
    mine = users["dev"].get("/inbox", headers=HTML).text
    assert "alpha" in mine and "blocked" in mine and "/projects/alpha/schedule" in mine
    assert "scheduled" in mine
    assert "alpha" not in users["sub"].get("/inbox", headers=HTML).text
    assert "/projects/alpha/schedule" in users["admin"].get("/inbox", headers=HTML).text


def test_refused_slot_is_listed_too(world) -> None:
    users = team()
    set_owner("alpha", user_id("dev@team.test"))
    records, _ = _tick("alpha", guard=lambda s: "owner_refused: owner disabled")
    assert [r.outcome.value for r in records] == ["refused"]
    assert "/projects/alpha/schedule" in users["dev"].get("/inbox", headers=HTML).text


def test_enqueued_slot_adds_no_slot_row(world) -> None:
    users = team()
    set_owner("alpha", user_id("dev@team.test"))
    records, q = _tick("alpha")
    assert [r.outcome.value for r in records] == ["enqueued"] and len(q) == 1
    assert "/projects/alpha/schedule" not in users["dev"].get("/inbox", headers=HTML).text
