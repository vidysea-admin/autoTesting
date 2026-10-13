"""HO24: the schedule's owner's rights are re-checked at fire time; a lost owner pauses it."""

from __future__ import annotations

from pathlib import Path

import pytest
from auth_harness import ADMIN, account, gate_on
from schedule_fakes import daily, make_deps, utc

from autotester.auth import accounts, db, groups
from autotester.schema.project import Project
from autotester.schema.schedule import SlotOutcome
from autotester.stages.schedule_owner import owner_guard
from autotester.stages.scheduler import tick_project
from autotester.store.project_store import ProjectStore

NOW = utc(2026, 10, 14, 9, 0)
SINCE = utc(2026, 10, 14, 8, 0)


@pytest.fixture()
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = gate_on(tmp_path, monkeypatch)
    account(ADMIN)
    store = ProjectStore("p", root)
    store.save_project(Project(slug="p", name="P", base_url="https://x.test",
                               schedule=daily().model_copy(update={"owner": "own@team.test"})))
    return root, store


def _fire(store: ProjectStore, tmp_path: Path):
    deps, q = make_deps(tmp_path, "p")
    deps = deps.__class__(**{**deps.__dict__, "owner_guard": owner_guard(
        "p", "own@team.test", store)})
    project = store.load_project()
    return tick_project("p", project.schedule, NOW, deps, since=SINCE), q


def test_ho24_owner_without_project_run_is_refused_and_paused(world, tmp_path) -> None:
    _root, store = world
    uid = account("own@team.test")
    grp = groups.create_group("None", ["project.view@all"])
    accounts.set_user_groups(uid, [grp.id])
    records, q = _fire(store, tmp_path)
    assert [r.outcome for r in records] == [SlotOutcome.REFUSED]
    assert "project.run" in (records[0].detail or "")
    assert q.entries() == []
    assert store.load_project().schedule.paused is True


def test_ho24_disabled_or_missing_owner_is_refused(world, tmp_path) -> None:
    _root, store = world
    uid = account("own@team.test")
    accounts.set_disabled(uid, True)
    records, _q = _fire(store, tmp_path)
    assert records[0].outcome is SlotOutcome.REFUSED
    assert store.load_project().schedule.paused is True


def test_ho24_owner_with_project_run_still_fires(world, tmp_path) -> None:
    _root, store = world
    uid = account("own@team.test")
    grp = groups.create_group("Runner", ["project.view@all", "project.run@all"])
    accounts.set_user_groups(uid, [grp.id])
    records, q = _fire(store, tmp_path)
    assert records[0].outcome in (SlotOutcome.ENQUEUED, SlotOutcome.CATCH_UP)
    assert len(q.entries()) == 1 and store.load_project().schedule.paused is False


def test_ho24_auth_on_with_no_account_store_fails_closed(tmp_path, monkeypatch) -> None:
    """No store at all is not 'nothing to check': with auth ON the slot is refused and paused."""
    root = gate_on(tmp_path, monkeypatch)
    store = ProjectStore("p", root)
    store.save_project(Project(slug="p", name="P", base_url="https://x.test",
                               schedule=daily().model_copy(update={"owner": "own@team.test"})))
    assert not db.store_exists()
    records, q = _fire(store, tmp_path)
    assert [r.outcome for r in records] == [SlotOutcome.REFUSED]
    assert "owner_refused" in (records[0].detail or "")
    assert q.entries() == [] and store.load_project().schedule.paused is True


def test_ho24_auth_disabled_loopback_skips_the_owner_check(tmp_path, monkeypatch) -> None:
    root = gate_on(tmp_path, monkeypatch)
    monkeypatch.setenv("AUTOTESTER_AUTH_DISABLED", "1")
    store = ProjectStore("p", root)
    store.save_project(Project(slug="p", name="P", base_url="https://x.test",
                               schedule=daily().model_copy(update={"owner": "own@team.test"})))
    records, q = _fire(store, tmp_path)
    assert records[0].outcome in (SlotOutcome.ENQUEUED, SlotOutcome.CATCH_UP)
    assert len(q.entries()) == 1
