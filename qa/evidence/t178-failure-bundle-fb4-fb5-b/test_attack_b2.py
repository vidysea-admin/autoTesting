from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from test_ui_runs import _approve_demo_runs, _onboard_demo, client, scratch_root  # noqa: F401

from autotester.schema.case import Case
from autotester.schema.enums import CaseClass, CaseKind
from autotester.store.project_store import ProjectStore


def _setup(client, scratch_root, monkeypatch):
    _onboard_demo(client)
    store = ProjectStore("demo", scratch_root)
    rows = {}
    for name in ["p0", "p1", "p2", "p3", "pin"]:
        pr = "p2" if name == "pin" else name
        rows[name] = store.add_case(Case(project="demo", flow_id=name, kind=CaseKind.BEST,
                case_class=CaseClass.HAPPY, title=name, priority=pr, pinned=name == "pin"))
    _approve_demo_runs(scratch_root)
    seen = {}
    def execute(store_, run_id, secrets, project, cases, *a):
        seen[run_id] = [c.flow_id for c in cases]
        return SimpleNamespace(n=1, bound_by="config")
    monkeypatch.setattr("autotester.ui.routes_runs._execute_with_trace", execute)
    monkeypatch.setattr("autotester.ui.routes_runs.LangChainFallbackProvider",
                        lambda: SimpleNamespace(available=lambda: True))
    return store, seen


@pytest.mark.parametrize("q", ["", "?priority=", "?priority=P0", "?priority=p0,p1", "?priority=p9&priority=p0",
                               "?priority=p4", "?priority=%20p0", "?priority=p0%00", "?priority=null",
                               "?priority=p0&priority="])
def test_bad_filters_run_nothing(client, scratch_root, monkeypatch, q):  # noqa: F811
    store, seen = _setup(client, scratch_root, monkeypatch)
    r = client.post(f"/projects/demo/run{q}", follow_redirects=False)
    print("STATUS", q, r.status_code, dict(seen))
    if q == "":
        assert r.status_code == 303 and sorted(next(iter(seen.values()))) == sorted(["p0","p1","p2","p3","pin"])
    else:
        assert r.status_code == 422 and seen == {}
        assert not store.paths.runs_dir.exists() or not list(store.paths.runs_dir.iterdir())


def test_each_press_keeps_own_filter(client, scratch_root, monkeypatch):  # noqa: F811
    store, seen = _setup(client, scratch_root, monkeypatch)
    for q in ["?priority=p0", "", "?priority=p3&priority=p3", "?priority=p1&priority=p2"]:
        assert client.post(f"/projects/demo/run{q}", follow_redirects=False).status_code == 303
    import time
    time.sleep(1.5)
    got = sorted(sorted(v) for v in seen.values())
    print("SEEN", got)
    assert got == sorted([sorted(["p0", "pin"]), sorted(["p0","p1","p2","p3","pin"]),
                          sorted(["p3", "pin"]), sorted(["p1", "p2", "pin"])])


def test_legacy_queue_file(scratch_root, monkeypatch):  # noqa: F811
    from autotester.schema.run_queue import QueueEntry, RunQueueFile
    legacy = {"entries": [{"id": "run-x", "project": "demo", "status": "queued", "trigger": "button",
                           "requested_by": None, "enqueued_at": "2026-10-01T00:00:00Z",
                           "started_at": None, "finished_at": None}]}
    for f in RunQueueFile.model_fields:
        pass
    parsed = RunQueueFile.model_validate(legacy) if "entries" in RunQueueFile.model_fields else None
    print("LEGACY", parsed.entries[0].priorities if parsed else RunQueueFile.model_fields.keys())
    assert parsed.entries[0].priorities is None
    # hand-edited unknown priority poisons the whole file
    bad = json.loads(json.dumps(legacy)); bad["entries"][0]["priorities"] = ["p9"]
    with pytest.raises(Exception):
        RunQueueFile.model_validate(bad)
