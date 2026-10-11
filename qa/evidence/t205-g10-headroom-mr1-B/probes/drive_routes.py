"""Behavioural probe of the run-trigger route (blind dual check MR1-B). Same script on head and master.
No real browser, site or model. Prints a JSON document of observations to argv[1]."""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import threading
from pathlib import Path

os.environ["AUTOTESTER_APPROVAL_KEY"] = "probe-only-signing-key-not-real"
os.environ["AUTOTESTER_ALLOWED_HOSTS"] = "testserver"
os.environ.pop("PYTEST_CURRENT_TEST", None)

import autotester  # noqa: E402

OUT = {"autotester_file": autotester.__file__, "rows": {}}

from fastapi.testclient import TestClient  # noqa: E402

from autotester.browser.session import BrowserSession  # noqa: E402
from autotester.providers.base import ProviderError  # noqa: E402
from autotester.schema.case import Case  # noqa: E402
from autotester.schema.enums import CaseClass, CaseKind, Outcome, Result  # noqa: E402
from autotester.schema.run import RawResult  # noqa: E402
from autotester.schema.verdict import Verdict  # noqa: E402
from autotester.store.project_store import ProjectStore  # noqa: E402
from autotester.ui import routes_runs, run_execution, run_queue  # noqa: E402
from autotester.ui.app import app  # noqa: E402

sys.path.insert(0, os.path.join(os.getcwd(), "tests"))
RUN_ID = re.compile(r"run-[0-9A-Za-z]{20,}")
TS = re.compile(r"\d{4}-\d{2}-\d{2}T[\d:.]+(?:Z|[+-]\d\d:\d\d)?")
HEX = re.compile(r"\b[0-9a-f]{12,}\b")


def norm(text: str) -> str:
    text = RUN_ID.sub("RUN", text)
    text = TS.sub("TS", text)
    return HEX.sub("HEX", text)


class State:
    executed: list = []
    judge_calls: list = []
    sessions = 0
    fail_judge = None
    available = True
    unavailable_reason = None
    deferred: list = []
    defer = False


def install(monkeypatch_list):
    State.executed, State.judge_calls, State.sessions = [], [], 0
    State.fail_judge, State.available, State.unavailable_reason = None, True, None
    State.deferred, State.defer = [], False

    class Judge:
        trace = None

        def available(self):
            return State.available

        def unavailable_reason(self):
            return State.unavailable_reason

    def for_role(project, role):
        State.judge_calls.append((project.slug, str(role)))
        if State.fail_judge:
            raise State.fail_judge
        return Judge()

    def fake_grade(case_, session, judge, run_id, store_):
        State.executed.append(case_.title)
        return (RawResult(case_id=case_.id, outcome=Outcome.COMPLETED),
                Verdict(run_id=run_id, case_id=case_.id, result=Result.PASS,
                        grader_provider="mock"))

    orig_init = BrowserSession.__init__

    def counting_init(self, *a, **kw):
        State.sessions += 1
        orig_init(self, *a, **kw)

    BrowserSession.__init__ = counting_init
    BrowserSession.start = lambda self: self
    BrowserSession.close = lambda self: None
    routes_runs.for_role = for_role
    run_execution.run_and_grade_case_resilient = fake_grade
    # head only: the launcher's own default judge looks for_role up in run_launcher
    try:
        from autotester.stages import run_launcher
        run_launcher.for_role = for_role
    except ImportError:
        pass

    def spawn(job):
        if State.defer:
            State.deferred.append(job)
        else:
            job()

    run_queue._QUEUE = run_queue.RunQueue(spawn=spawn, runner=run_queue._registered_runner)


def fresh(cases=("p0", "p1", "p2", "pin"), approve=True):
    root = Path(tempfile.mkdtemp(prefix="rt-", dir=os.environ["PROBE_TMP"]))
    os.environ["AUTOTESTER_ROOT"] = str(root)
    install([])
    c = TestClient(app, raise_server_exceptions=False)
    c.post("/onboard", data={"slug": "demo", "name": "Demo", "base_url": "https://demo.test",
                             "allowed_domains": "demo.test"})
    store = ProjectStore("demo", root)
    for name in cases:
        store.add_case(Case(project="demo", flow_id=name, kind=CaseKind.BEST,
                            case_class=CaseClass.HAPPY, title=name,
                            priority="p3" if name == "pin" else name, pinned=name == "pin"))
    if approve:
        from run_approval_fixture import grant_live_case_approval
        grant_live_case_approval(store)
    return root, store, c


def tree(root: Path) -> list:
    out = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and ".work" not in p.parts:
            out.append(norm(p.relative_to(root).as_posix()) + f" {p.stat().st_size if p.suffix not in ('.json', '.jsonl') else 'j'}")
    return sorted(out)


def runs_json(store):
    out = []
    for d in sorted(store.paths.runs_dir.iterdir()) if store.paths.runs_dir.exists() else []:
        f = d / "run.json"
        if f.exists():
            out.append(norm(f.read_text(encoding="utf-8")))
    return out


def snap(c, store, root, resp):
    return {
        "status": resp.status_code, "location": resp.headers.get("location"),
        "body": norm(resp.text)[:600],
        "executed": list(State.executed), "judge_calls": list(State.judge_calls),
        "sessions": State.sessions, "run_json": runs_json(store),
        "tree": tree(root),
    }


def post(c, qs=""):
    return c.post("/projects/demo/run" + qs, follow_redirects=False)


rows = OUT["rows"]
for label, qs in [("none", ""), ("p0", "?priority=p0"), ("p1", "?priority=p1"), ("p2", "?priority=p2"),
                  ("p3", "?priority=p3"), ("p0+p1", "?priority=p0&priority=p1"),
                  ("p1+p1dup", "?priority=p1&priority=p1"),
                  ("unknown p9", "?priority=p9"), ("empty str", "?priority="),
                  ("upper P1", "?priority=P1"), ("p1+p9", "?priority=p1&priority=p9")]:
    root, store, c = fresh()
    rows[f"priority[{label}]"] = snap(c, store, root, post(c, qs))

# select nothing: only p2 cases, no pinned; priority=p0 -> zero cases
root, store, c = fresh(cases=("p2",))
rows["zero-selection p2-only, priority=p0"] = snap(c, store, root, post(c, "?priority=p0"))
root, store, c = fresh(cases=())
rows["no cases, no priority"] = snap(c, store, root, post(c))
root, store, c = fresh(cases=())
rows["no cases, priority=p1"] = snap(c, store, root, post(c, "?priority=p1"))

# gates
root, store, c = fresh(approve=False)
rows["no approval"] = snap(c, store, root, post(c))
root, store, c = fresh(approve=False)
rows["no approval, priority=p1"] = snap(c, store, root, post(c, "?priority=p1"))
root, store, c = fresh()
State.available = False
State.unavailable_reason = "set PROBE_KEY"
rows["provider unavailable (reason)"] = snap(c, store, root, post(c))
root, store, c = fresh()
State.available = False
rows["provider unavailable (no reason)"] = snap(c, store, root, post(c, "?priority=p1"))
root, store, c = fresh()
State.fail_judge = ProviderError("model X needs variable PROBE_VAR")
rows["ProviderError from factory"] = snap(c, store, root, post(c))
root, store, c = fresh()
State.fail_judge = RuntimeError("boom")
rows["unexpected error from factory"] = snap(c, store, root, post(c))

# slug doors
root, store, c = fresh()
for slug in ["NOPE", "nope", "../etc", "a b", "demo%0A", "9lives", "demo-"]:
    State.executed.clear(); State.judge_calls.clear()
    r = c.post(f"/projects/{slug}/run", follow_redirects=False)
    rows[f"slug[{slug}]"] = {"status": r.status_code, "body": norm(r.text)[:200], "judge_calls": list(State.judge_calls)}

# missing credential value
root, store, c = fresh()
p = store.load_project()
from autotester.schema.flowspec import Step  # noqa: E402
from autotester.schema.enums import Action  # noqa: E402
cs = store.list_cases()
cred = Case(project="demo", flow_id="cred", kind=CaseKind.BEST, case_class=CaseClass.HAPPY, title="cred",
            steps=[Step(order=1, action=Action.FILL, target="#pw", value="{{SECRET:PROBE_PW}}")])
store.add_case(cred)
rows["placeholder with no value"] = snap(c, store, root, post(c))

# queued path: press, then world changes, then the worker starts
root, store, c = fresh()
State.defer = True
r = post(c, "?priority=p1")
q = run_queue.get_queue()
rows["queued: press"] = {"status": r.status_code, "deferred": len(State.deferred),
                         "stored_priorities": [e.priorities for e in q.snapshot()],
                         "executed": list(State.executed)}
# a new p1 and a new p2 arrive after the press (the re-check must use the stored priorities)
store.add_case(Case(project="demo", flow_id="late1", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                    title="late-p1", priority="p1"))
store.add_case(Case(project="demo", flow_id="late2", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                    title="late-p2", priority="p2"))
for job in list(State.deferred):
    job()
rows["queued: start"] = {"executed": list(State.executed), "judge_calls": list(State.judge_calls),
                         "entries": [(str(e.status), e.reason, e.priorities) for e in q.snapshot()],
                         "run_json": runs_json(store), "sessions": State.sessions}

# queued, approval removed before start -> refused
root, store, c = fresh()
State.defer = True
post(c)
q = run_queue.get_queue()
(store.paths.root / "approvals.jsonl").write_text("") if hasattr(store.paths, "root") else None
ap = store.paths.approvals if hasattr(store.paths, "approvals") else None
if ap is not None and Path(ap).exists():
    Path(ap).write_text("")
for job in list(State.deferred):
    job()
rows["queued: approval gone"] = {"entries": [(str(e.status), norm(e.reason or "")) for e in q.snapshot()],
                                 "executed": list(State.executed), "sessions": State.sessions,
                                 "runs": runs_json(store)}

# queued, provider gone at start
root, store, c = fresh()
State.defer = True
post(c, "?priority=p0")
q = run_queue.get_queue()
State.available = False
State.unavailable_reason = "gone"
for job in list(State.deferred):
    job()
rows["queued: provider gone"] = {"entries": [(str(e.status), norm(e.reason or "")) for e in q.snapshot()],
                                 "executed": list(State.executed), "sessions": State.sessions,
                                 "runs": runs_json(store)}

# queued, cases removed -> refused no cases
root, store, c = fresh()
State.defer = True
post(c, "?priority=p1")
q = run_queue.get_queue()
for case in store.list_cases():
    if not case.pinned:
        store.delete_case(case.id)
# pinned remain; so remove pinned by rewriting the file
store.paths.cases.write_text("")
for job in list(State.deferred):
    job()
rows["queued: cases gone"] = {"entries": [(str(e.status), norm(e.reason or "")) for e in q.snapshot()],
                              "executed": list(State.executed), "sessions": State.sessions}

# executor failure inside the run
root, store, c = fresh()
def boom(case_, session, judge, run_id, store_):
    raise RuntimeError("executor exploded")
run_execution.run_and_grade_case_resilient = boom
rows["executor raises"] = snap(c, store, root, post(c))

Path(sys.argv[1]).write_text(json.dumps(OUT, indent=1, sort_keys=True, default=str), encoding="utf-8")
print("rows", len(rows))
