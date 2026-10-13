"""TT7: "My reports" (`GET /inbox`) lists only requests whose report the viewer may read,
with the one stored label; and the queued-with-position state under a contended slot.

Four default groups x two projects x {list, direct URL}; anonymous (302), a pending account
(403), a hidden or missing run (the same 404), a refused / interrupted / low-coverage run with its
label, an all-blocked run that never reads green, and a one-definition grep for the label.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from auth_harness import account, client, gate_on, login, project, team, user_id
from team_run_fakes import FakeQueue

from autotester.auth.access import set_owner, set_relation
from autotester.schema.auth import ProjectRelation
from autotester.schema.delivery import ReportLabel
from autotester.schema.enums import Result
from autotester.schema.run import Run
from autotester.schema.run_queue import QueueStatus
from autotester.schema.verdict import Verdict
from autotester.stages.report_delivery import report_label
from autotester.store.project_store import ProjectStore
from autotester.ui import routes_inbox, routes_team_run, run_queue

HTML = {"accept": "text/html"}
SRC = Path(__file__).resolve().parents[1] / "src" / "autotester"


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = gate_on(tmp_path, monkeypatch)
    queue = FakeQueue()
    monkeypatch.setattr(routes_inbox, "get_queue", lambda: queue)
    monkeypatch.setattr(routes_team_run, "get_queue", lambda: queue)
    project(root, "alpha")
    project(root, "beta")
    return root, queue


def _finish(queue: FakeQueue, root: Path, slug: str, run_id: str, status: QueueStatus,
            results: tuple[Result, ...] = (), by: str = "dev@team.test",
            trigger: str = "button", planned: int | None = None) -> None:
    entry = queue.submit(slug, requested_by=by, trigger=trigger, run_id=run_id)
    queue.start_next()
    queue.finish(entry.id, status, "a reason" if status is not QueueStatus.DONE else None)
    store = ProjectStore(slug, root)
    if results:
        store.save_run(Run(id=run_id, project=slug,
                           case_ids=[f"c{i}" for i in range(planned or len(results))]))
    for i, result in enumerate(results):
        store.save_verdict(run_id, Verdict(run_id=run_id, case_id=f"c{i}", result=result,
                                           grader_provider="mock"))


def _ids(text: str) -> set[str]:
    return set(re.findall(r"<code>(run-[A-Za-z0-9]+)</code>", text))


def test_anonymous_goes_to_login_and_a_pending_account_is_refused(world) -> None:
    resp = client().get("/inbox", headers=HTML)
    assert resp.status_code == 302 and resp.headers["location"].startswith("/auth/login")
    account("admin@team.test")
    account("pending@team.test")                       # no group: no report.view anywhere
    assert login("pending@team.test").get("/inbox", headers=HTML).status_code == 403


def test_scope_table_list_and_direct_url_for_each_default_user(world) -> None:
    root, queue = world
    users = team()
    set_owner("alpha", user_id("dev@team.test"))
    set_relation("beta", user_id("sub@team.test"), ProjectRelation.ASSIGNED, True)
    set_relation("alpha", user_id("tester@team.test"), ProjectRelation.SHARED, True)
    _finish(queue, root, "alpha", "run-alpha1", QueueStatus.DONE, (Result.PASS,))
    _finish(queue, root, "beta", "run-beta1", QueueStatus.DONE, (Result.PASS,))
    sees = {"admin": {"run-alpha1", "run-beta1"}, "dev": {"run-alpha1"},
            "tester": {"run-alpha1"}, "sub": {"run-beta1"}}
    for name, expected in sees.items():
        listed = _ids(users[name].get("/inbox", headers=HTML).text)
        assert listed == expected, name
        for slug, run in (("alpha", "run-alpha1"), ("beta", "run-beta1")):
            code = users[name].get(f"/projects/{slug}/test/{run}", headers=HTML).status_code
            assert code == (200 if run in expected else 404), (name, run)


def test_hidden_run_is_the_same_404_as_a_missing_one(world) -> None:
    root, queue = world
    users = team()
    set_owner("alpha", user_id("sub@team.test"))
    _finish(queue, root, "alpha", "run-alpha1", QueueStatus.DONE, (Result.PASS,))
    hidden = users["dev"].get("/projects/alpha/test/run-alpha1", headers=HTML)
    missing = users["dev"].get("/projects/alpha/test/run-nope", headers=HTML)
    assert hidden.status_code == 404 == missing.status_code
    assert hidden.text.replace("run-alpha1", "") == missing.text.replace("run-nope", "")


def test_cross_user_isolation_one_users_requests_do_not_leak(world) -> None:
    root, queue = world
    users = team()
    set_owner("alpha", user_id("dev@team.test"))
    set_owner("beta", user_id("sub@team.test"))
    _finish(queue, root, "alpha", "run-mine", QueueStatus.DONE, (Result.PASS,))
    _finish(queue, root, "beta", "run-theirs", QueueStatus.DONE, (Result.PASS,),
            by="sub@team.test")
    page = users["dev"].get("/inbox", headers=HTML).text
    assert "run-mine" in page and "run-theirs" not in page and "sub@team.test" not in page


def test_refused_interrupted_and_low_coverage_runs_appear_with_their_labels(world) -> None:
    root, queue = world
    users = team()
    _finish(queue, root, "alpha", "run-refused", QueueStatus.REFUSED)
    _finish(queue, root, "alpha", "run-cut", QueueStatus.INTERRUPTED)
    _finish(queue, root, "beta", "run-low", QueueStatus.DONE, (Result.PASS,), planned=3)
    _finish(queue, root, "beta", "run-allblocked", QueueStatus.DONE,
            (Result.BLOCKED, Result.BLOCKED))
    _finish(queue, root, "beta", "run-green", QueueStatus.DONE, (Result.PASS, Result.PASS))
    page = users["admin"].get("/inbox", headers=HTML).text
    rows = {m.group(1): m.group(0) for m in re.finditer(
        r"<tr><td>\w+</td><td><code>(run-\w+)</code>.*?</tr>", page)}
    assert ">blocked<" in rows["run-refused"] and ">failed<" in rows["run-cut"]
    assert ">low coverage<" in rows["run-low"]
    assert ">blocked<" in rows["run-allblocked"] and ">green<" not in rows["run-allblocked"]
    assert ">green<" in rows["run-green"]
    assert "/projects/beta/runs/run-green" in rows["run-green"]       # done -> the report
    assert "/projects/alpha/test/run-refused" in rows["run-refused"]  # no report -> the status page


def test_the_page_has_labelled_controls_and_names_schedule_runs(world) -> None:
    root, queue = world
    users = team()
    _finish(queue, root, "alpha", "run-sched", QueueStatus.DONE, (Result.PASS,),
            by="owner@team.test", trigger="schedule")
    page = users["admin"].get("/inbox", headers=HTML).text
    assert "aria-label='Open the report for run run-sched'" in page
    assert "<th scope='col'>Report label</th>" in page and "scheduled" in page
    assert "owner@team.test" not in page


def test_label_rules_and_the_label_is_defined_once() -> None:
    done = QueueStatus.DONE
    assert report_label(done, [Result.PASS] * 2, 2) is ReportLabel.GREEN
    assert report_label(done, [Result.PASS, Result.FAIL], 2) is ReportLabel.FAILED
    assert report_label(done, [Result.BLOCKED], 1) is ReportLabel.BLOCKED
    assert report_label(done, [Result.PASS, Result.INCONCLUSIVE], 2) is ReportLabel.INCONCLUSIVE
    assert report_label(done, [], 0) is ReportLabel.LOW_COVERAGE
    assert report_label(QueueStatus.QUEUED, [], 0) is None
    defs = [p for p in SRC.rglob("*.py") if re.search(r"^def report_label\b",
                                                      p.read_text("utf-8"), re.M)]
    assert [p.name for p in defs] == ["report_delivery.py"]
    view = (SRC / "ui" / "inbox_view.py").read_text("utf-8")
    assert "Result." not in view and "def report_label" not in view   # the page only reads it


def test_queued_with_position_under_a_contended_slot(tmp_path, monkeypatch) -> None:
    """One browser slot, three requests: the first runs, the others show their place in the
    line in the inbox, and the second moves up when the first finishes."""
    root = gate_on(tmp_path, monkeypatch)
    project(root, "alpha")
    project(root, "beta")
    jobs: list = []
    queue = run_queue.RunQueue(limit=lambda: 1, spawn=jobs.append, runner=lambda entry: None)
    monkeypatch.setattr(routes_inbox, "get_queue", lambda: queue)
    users = team()
    queue.submit("alpha", requested_by="dev@team.test", run_id="run-first")
    queue.submit("beta", requested_by="dev@team.test", run_id="run-second")
    queue.submit("alpha", requested_by="dev@team.test", run_id="run-third")
    page = users["admin"].get("/inbox", headers=HTML).text
    assert "queued, position #1" in page and "queued, position #2" in page
    assert re.search(r"run-second</code>.*?queued, position #1", page, re.S)
    assert re.search(r"run-third</code>.*?queued, position #2", page, re.S)
    assert "<meta http-equiv='refresh'" in page                        # still moving
    jobs.pop()()                                                       # first finishes
    page = users["admin"].get("/inbox", headers=HTML).text
    assert "queued, position #1" in page and "position #2" not in page
    assert re.search(r"run-third</code>.*?queued, position #1", page, re.S)
    assert re.search(r"run-second</code>.*?running", page, re.S)


def test_finished_time_orders_newest_first(world) -> None:
    root, queue = world
    users = team()
    _finish(queue, root, "alpha", "run-old", QueueStatus.DONE, (Result.PASS,))
    _finish(queue, root, "alpha", "run-new", QueueStatus.DONE, (Result.PASS,))
    queue.entries[0].finished_at = datetime.now(UTC) - timedelta(hours=1)
    queue.entries[1].finished_at = datetime.now(UTC)
    page = users["admin"].get("/inbox", headers=HTML).text
    assert page.index("run-new") < page.index("run-old")
