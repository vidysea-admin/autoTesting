"""hosting.md HO4 (local half), HO12, HO15, HO19, HO21 -- the rows T-203 left open until T-204.

Scenarios: a watcher opens the live view with and without live.control and the proxy asks the
app about them; an admin edits the server limits; a queued run starts after its requester lost
project.run; two developers each look at their own project's queue; the server is restarted.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from auth_harness import ADMIN, account, client, gate_on, group_id, login, project, user_id

from autotester.auth import accounts, groups
from autotester.auth.access import set_owner
from autotester.schema.run_queue import QueueEntry, QueueStatus
from autotester.store.server_settings import (
    effective_max_concurrent_runs,
    effective_max_upload_bytes,
    settings_path,
)
from autotester.ui import routes_runs, run_queue
from autotester.ui.run_queue import RunQueue, RunRefused

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = gate_on(tmp_path, monkeypatch)
    account(ADMIN)
    return path


# -- HO12 --------------------------------------------------------------------------------------
def test_auth_check_answers_the_proxy_per_session(root: Path) -> None:
    account("dev@team.test", "developer")
    account("tester@team.test", "tester")
    assert client().get("/auth/check").status_code == 401
    assert client().get("/auth/check", headers={"accept": "text/html"}).status_code == 302
    assert login("tester@team.test").get("/auth/check").status_code == 403   # no live.view
    viewer = login("dev@team.test")
    assert viewer.get("/auth/check").json()["email"] == "dev@team.test"
    assert viewer.get("/auth/check?need=control").status_code == 403         # no live.control
    assert login(ADMIN).get("/auth/check?need=control").status_code == 200


def test_live_page_is_gated_and_view_only_without_live_control(root: Path) -> None:
    account("dev@team.test", "developer")
    account("tester@team.test", "tester")
    assert client().get("/live").status_code == 401
    assert login("tester@team.test").get("/live").status_code == 403
    watcher = login("dev@team.test").get("/live").text
    assert "view_only=1" in watcher and "live.control" in watcher
    assert "view_only" not in login(ADMIN).get("/live").text


def _caddy_block(head: str) -> str:
    caddy = (ROOT / "docker" / "Caddyfile").read_text(encoding="utf-8")
    return caddy[caddy.index(head):].split("\n\t}\n")[0]


def test_proxy_has_two_gated_endpoints_with_distinct_upstreams() -> None:
    view, control = _caddy_block("handle /novnc-view/*"), _caddy_block("handle /novnc/*")
    assert "uri /auth/check?need=view" in view and "reverse_proxy autotester:6081" in view
    assert "uri /auth/check?need=control" in control and "reverse_proxy autotester:6080" in control
    assert "forward_auth autotester:8000" in view and "forward_auth autotester:8000" in control
    assert "503" not in view + control
    caddy = (ROOT / "docker" / "Caddyfile").read_text(encoding="utf-8")
    assert "@vnc_other path" in caddy and "respond \"Forbidden\" 403" in caddy


def test_entrypoint_runs_a_viewonly_vnc_server_behind_the_view_port() -> None:
    sh = (ROOT / "docker" / "entrypoint.sh").read_text(encoding="utf-8")
    assert "-rfbport 5901 -viewonly" in sh and "6081 localhost:5901" in sh
    assert "6080 localhost:5900" in sh
    control_line = next(x for x in sh.splitlines() if "-rfbport 5900" in x)
    assert "-viewonly" not in control_line


@pytest.mark.parametrize("path,expect", [
    ("/auth/check?need=view", {"anon": 401, "tester": 403, "dev": 200, "admin": 200}),
    ("/auth/check?need=control", {"anon": 401, "tester": 403, "dev": 403, "admin": 200}),
    ("/auth/check", {"anon": 401, "tester": 403, "dev": 200, "admin": 200}),
    ("/auth/check?need=CONTROL", {"anon": 401, "tester": 403, "dev": 400, "admin": 400}),
    ("/auth/check?need=", {"anon": 401, "tester": 403, "dev": 400, "admin": 400}),
    ("/auth/check?need=view&need=control", {"anon": 401, "tester": 403, "dev": 403, "admin": 200}),
    ("/auth/check/../check?need=view", {"anon": 401}),
])
def test_auth_check_decision_matrix(root: Path, path: str, expect: dict[str, int]) -> None:
    """Viewer: view allowed, control 403. Controller: both. Anonymous 401. Unknown or
    alternate `need` values fail closed (never fall back to the weaker check)."""
    account("dev@team.test", "developer")
    account("tester@team.test", "tester")
    who = {"anon": client(), "tester": login("tester@team.test"),
           "dev": login("dev@team.test"), "admin": login(ADMIN)}
    for name, code in expect.items():
        got = who[name].get(path).status_code
        assert got == code or (name == "anon" and got in (302, 401, 404)), (name, path, got)


def test_viewer_page_uses_the_viewonly_endpoint_and_controller_the_input_one(
    root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTOTESTER_NOVNC_URL",
                       "/novnc/vnc.html?autoconnect=true&path=novnc/websockify")
    account("dev@team.test", "developer")
    watcher = login("dev@team.test").get("/live").text
    assert "/novnc-view/vnc.html" in watcher and "path=novnc-view/websockify" in watcher
    assert "src='/novnc/" not in watcher
    controller = login(ADMIN).get("/live").text
    assert "src='/novnc/vnc.html" in controller and "novnc-view" not in controller


def test_view_only_url_local_default_uses_the_viewonly_port() -> None:
    from autotester.ui.routes_live import view_only_url
    assert view_only_url("http://localhost:6080/vnc.html?a=1") == "http://localhost:6081/vnc.html?a=1"


# -- HO15 --------------------------------------------------------------------------------------
def test_settings_page_needs_settings_manage(root: Path) -> None:
    account("dev@team.test", "developer")
    assert client().get("/settings/server").status_code == 401
    assert login("dev@team.test").get("/settings/server").status_code == 403
    assert login("dev@team.test").post("/settings/server", data={
        "max_concurrent_runs": "9", "max_upload_bytes": "2147483648"}).status_code == 403
    assert not settings_path(root).exists()
    assert "Server limits" in login(ADMIN).get("/settings/server").text


def test_a_valid_change_applies_at_once_and_is_audited(root: Path) -> None:
    admin = login(ADMIN)
    assert effective_max_concurrent_runs(root) == 2
    resp = admin.post("/settings/server", data={"max_concurrent_runs": "5",
                                                "max_upload_bytes": "1048576"})
    assert resp.status_code == 303
    assert effective_max_concurrent_runs(root) == 5 and effective_max_upload_bytes(root) == 1048576
    page = admin.get("/settings/server").text
    assert "value='5'" in page and "value='1048576'" in page
    audit = (root / ".work" / "audit.jsonl").read_text(encoding="utf-8")
    assert "server-settings" in audit and "max_concurrent_runs 2->5" in audit


@pytest.mark.parametrize("runs,upload", [
    ("0", "2147483648"), ("-1", "2147483648"), ("65", "2147483648"), ("abc", "2147483648"),
    ("2.5", "2147483648"), ("", "2147483648"), ("99999999999999999999999", "2147483648"),
    ("3", "1048575"), ("3", str(64 * 1024**3 + 1)), ("3", "2GB"), ("3", ""), ("3", "1e9"),
])
def test_invalid_values_are_refused_and_nothing_is_stored(root: Path, runs: str, upload: str
                                                          ) -> None:
    resp = login(ADMIN).post("/settings/server", data={"max_concurrent_runs": runs,
                                                       "max_upload_bytes": upload})
    assert resp.status_code == 400 and "Nothing was changed" in resp.text
    assert not settings_path(root).exists()
    assert effective_max_concurrent_runs(root) == 2


def test_corrupt_settings_fall_back_and_say_so(root: Path) -> None:
    settings_path(root).parent.mkdir(parents=True, exist_ok=True)
    settings_path(root).write_text('{"max_concurrent_runs": "lots"}', encoding="utf-8")
    page = login(ADMIN).get("/settings/server").text
    assert "defaults are in force" in page and effective_max_concurrent_runs(root) == 2


def test_raising_the_cap_starts_the_waiting_run_without_another_press() -> None:
    cap = [1]
    queue = RunQueue(limit=lambda: cap[0], spawn=lambda job: None, runner=lambda e: None)
    queue.submit("alpha")
    assert queue.submit("beta").status is QueueStatus.QUEUED
    cap[0] = 2
    queue.nudge()
    assert {e.status for e in queue.snapshot()} == {QueueStatus.RUNNING}


# -- HO19 --------------------------------------------------------------------------------------
@pytest.fixture
def launched(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    seen: list[str] = []
    monkeypatch.setattr(routes_runs.run_launcher, "launch_run",
                        lambda slug, **kw: seen.append(slug))
    return seen


def _entry(email: str | None, slug: str = "alpha") -> QueueEntry:
    return QueueEntry(id="run-1", project=slug, requested_by=email)


def test_a_requester_who_still_holds_project_run_starts(root: Path, launched: list[str]) -> None:
    project(root, "alpha")
    set_owner("alpha", account("dev@team.test", "developer"))
    routes_runs._run_queued(_entry("dev@team.test"))
    assert launched == ["alpha"]


def test_losing_project_run_between_enqueue_and_start_is_refused(root: Path,
                                                                  launched: list[str]) -> None:
    project(root, "alpha")
    uid = account("dev@team.test", "developer")
    set_owner("alpha", uid)
    accounts.set_user_groups(uid, [group_id("tester")])   # demoted while the run waited
    with pytest.raises(RunRefused, match=r"no longer has project.run"):
        routes_runs._run_queued(_entry("dev@team.test"))
    assert launched == []


def test_a_disabled_or_deleted_requester_is_refused_and_no_browser_starts(
        root: Path, launched: list[str]) -> None:
    project(root, "alpha")
    uid = account("dev@team.test", "developer")
    set_owner("alpha", uid)
    accounts.set_disabled(uid, True)
    with pytest.raises(RunRefused, match="no longer an active account"):
        routes_runs._run_queued(_entry("dev@team.test"))
    with pytest.raises(RunRefused, match="no longer an active account"):
        routes_runs._run_queued(_entry("gone@team.test"))
    assert launched == []


def test_a_refused_start_is_recorded_refused_never_done(root: Path, launched: list[str]) -> None:
    project(root, "alpha")
    queue = RunQueue(runner=routes_runs._run_queued, spawn=lambda job: job())
    entry = queue.submit("alpha", requested_by="gone@team.test")
    assert entry.status is QueueStatus.REFUSED and "no longer" in (entry.reason or "")
    assert launched == []


# -- HO21 --------------------------------------------------------------------------------------
def test_every_entry_records_who_and_how_and_the_panel_shows_it(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project(root, "alpha")
    set_owner("alpha", account("dev@team.test", "developer"))
    monkeypatch.setattr(routes_runs.run_launcher, "prepare_run", lambda *a, **k: None)
    queue = RunQueue(spawn=lambda job: None, runner=lambda e: None)
    run_queue.set_queue(queue)
    dev = login("dev@team.test")
    assert dev.post("/projects/alpha/run").status_code == 303   # the legacy Run button
    entry = queue.snapshot()[0]
    assert entry.requested_by == "dev@team.test" and entry.trigger == "button"
    assert entry.requested_by_id == user_id("dev@team.test")
    page = dev.get("/projects/alpha/report").text
    assert "dev@team.test" in page and "(button)" in page


def test_a_user_sees_only_queue_rows_of_projects_they_may_view(root: Path) -> None:
    for slug, who in (("alpha", "a@team.test"), ("beta", "b@team.test")):
        project(root, slug)
        set_owner(slug, account(who, "developer"))
    queue = RunQueue(spawn=lambda job: None, runner=lambda e: None)
    run_queue.set_queue(queue)
    alpha = queue.submit("alpha", requested_by="a@team.test")
    queue.submit("beta", requested_by="b@team.test")
    b = login("b@team.test")
    own = b.get("/projects/beta/report").text
    assert "b@team.test" in own and "a@team.test" not in own
    assert b.get("/projects/alpha/report").status_code == 404   # same answer as a missing project
    assert b.get(f"/projects/alpha/test/{alpha.id}").status_code == 404


# -- HO4 (local half) -----------------------------------------------------------------------------
def test_state_survives_a_restart_and_the_listing_shows_it(root: Path) -> None:
    spec = importlib.util.spec_from_file_location(
        "hosting_state_listing", ROOT / "scripts" / "hosting_state_listing.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    project(root, "alpha")
    groups.create_group("Ops", ["settings.manage"])
    account("dev@team.test", "developer")
    login(ADMIN).post("/settings/server", data={"max_concurrent_runs": "3",
                                                "max_upload_bytes": "2147483648"})
    queue = RunQueue(spawn=lambda job: None, runner=lambda e: None, path=run_queue._queue_file)
    queue.submit("alpha", requested_by="dev@team.test")
    before = mod.listing(root)
    assert before["projects"] == ["alpha"] and "dev@team.test" in before["users"]
    assert "Ops" in before["groups"] and before["settings"]["max_concurrent_runs"] == 3
    # restart: a new process has no memory, only the data root; the running run is interrupted
    RunQueue(spawn=lambda job: None, runner=lambda e: None,
             path=run_queue._queue_file).recover()
    after = mod.listing(root)
    assert json.dumps({**before, "queue": []}) == json.dumps({**after, "queue": []})
    assert [e["id"] for e in after["queue"]] == [e["id"] for e in before["queue"]]
    assert after["queue"][0]["status"] == QueueStatus.INTERRUPTED.value
