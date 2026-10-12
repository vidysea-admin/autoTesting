"""Approval-gate door probe (MR1-B). argv[1] = out json. Works on head and master (doors differ by name)."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

os.environ["AUTOTESTER_APPROVAL_KEY"] = "probe-only-signing-key-not-real"
os.environ["AUTOTESTER_ALLOWED_HOSTS"] = "testserver"
os.environ.pop("PYTEST_CURRENT_TEST", None)
sys.path.insert(0, os.path.join(os.getcwd(), "tests"))

import autotester  # noqa: E402
from autotester.browser.session import BrowserSession  # noqa: E402
from autotester.providers.base import ProviderError  # noqa: E402
from autotester.schema.case import Case  # noqa: E402
from autotester.schema.enums import CaseClass, CaseKind, Outcome, Result, Trigger  # noqa: E402
from autotester.schema.project import Project  # noqa: E402
from autotester.schema.run import RawResult  # noqa: E402
from autotester.schema.verdict import Verdict  # noqa: E402
from autotester.store.project_store import ProjectStore  # noqa: E402
from autotester.ui import routes_runs, run_execution, run_queue  # noqa: E402
from autotester.schema.run_queue import QueueEntry  # noqa: E402
from run_approval_fixture import grant_live_case_approval  # noqa: E402

try:
    from autotester.stages import run_launcher as RL
except ImportError:
    RL = None
HEAD = RL is not None and hasattr(RL, "launch_run")

C = {"sessions": 0, "executed": [], "judge": 0, "planner": 0}


class Judge:
    trace = None

    def available(self):
        return True


def for_role(project, role):
    C["judge"] += 1
    return Judge()


def fake_grade(case_, session, judge, run_id, store_):
    C["executed"].append(case_.title)
    return (RawResult(case_id=case_.id, outcome=Outcome.COMPLETED),
            Verdict(run_id=run_id, case_id=case_.id, result=Result.PASS, grader_provider="mock"))


orig_init = BrowserSession.__init__


def counting_init(self, *a, **kw):
    C["sessions"] += 1
    orig_init(self, *a, **kw)


BrowserSession.__init__ = counting_init
BrowserSession.start = lambda self: self
BrowserSession.close = lambda self: None
routes_runs.for_role = for_role
if RL:
    RL.for_role = for_role
run_execution.run_and_grade_case_resilient = fake_grade


def fresh(cases=("p0", "p1", "p2", "pin"), approve=False):
    root = Path(tempfile.mkdtemp(prefix="dr-", dir=os.environ["PROBE_TMP"]))
    os.environ["AUTOTESTER_ROOT"] = str(root)
    C.update(sessions=0, executed=[], judge=0)
    store = ProjectStore("demo", root)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                               allowed_domains=["demo.test"]))
    for n in cases:
        store.add_case(Case(project="demo", flow_id=n, kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                            title=n, priority="p3" if n == "pin" else n, pinned=n == "pin"))
    if approve:
        grant_live_case_approval(store)
    return root, store


def listing(root):
    return sorted((p.relative_to(root).as_posix(), p.stat().st_size) for p in root.rglob("*") if p.is_file())


def attempt(label, fn, rows, cases=("p0", "p1", "p2", "pin"), approve=False):
    root, store = fresh(cases, approve)
    before = listing(root)
    try:
        out = fn()
        res = "returned " + type(out).__name__
    except BaseException as exc:  # noqa: BLE001
        res = f"{type(exc).__name__}: {str(getattr(exc, 'reason', exc))[:90]}" + (
            f" [status {exc.status}]" if hasattr(exc, "status") else "") + (
            f" [status {exc.status_code}]" if hasattr(exc, "status_code") else "")
    rows[label] = {"result": res, "sessions": C["sessions"], "executed": list(C["executed"]),
                   "tree_changed": listing(root) != before,
                   "run_dirs": sorted(p.name[:4] for p in (root / "projects/demo/runs").glob("*")) if (root / "projects/demo/runs").exists() else []}


rows = {}
PRI = {"None": None, "[]": [], "['p1']": ["p1"], "['p0']": ["p0"], "['p9']": ["p9"], "'p1'(str)": "p1", "('p1',)": ("p1",)}
for pl, pv in PRI.items():
    for approve in (False, True):
        tag = "approved" if approve else "NO-APPROVAL"
        if HEAD:
            attempt(f"launch_run priorities={pl} {tag}", lambda pv=pv: RL.launch_run("demo", priorities=pv), rows, approve=approve)
            attempt(f"prepare_run priorities={pl} {tag}", lambda pv=pv: RL.prepare_run("demo", RL.DEFAULT_SEAMS._replace(judge_factory=lambda p: Judge()), pv), rows, approve=approve)
            for trig in ("manual", "schedule", "ci"):
                attempt(f"launch_run trigger={trig} priorities={pl} {tag}",
                        lambda pv=pv, trig=trig: RL.launch_run("demo", trigger=Trigger(trig), requested_by="u", slot_key="s", priorities=pv),
                        rows, approve=approve)
        else:
            # master equivalents
            attempt(f"launch_run priorities={pl} {tag}",
                    lambda pv=pv: routes_runs._execute_and_record(routes_runs._prepare_run("demo", pv), "run-X"), rows, approve=approve)
            attempt(f"prepare_run priorities={pl} {tag}", lambda pv=pv: routes_runs._prepare_run("demo", pv), rows, approve=approve)
        # the queue worker door (both)
        def queued(pv=pv):
            return routes_runs._run_queued(QueueEntry(id="run-QQ", project="demo", priorities=pv))
        attempt(f"_run_queued priorities={pl} {tag}", queued, rows, approve=approve)

# zero-selection with approval present: nothing to run -> refusal, no execution
if HEAD:
    attempt("launch_run zero-selection approved", lambda: RL.launch_run("demo", priorities=["p0"]), rows, cases=("p2",), approve=True)
attempt("_run_queued zero-selection approved", lambda: routes_runs._run_queued(QueueEntry(id="run-QQ", project="demo", priorities=["p0"])), rows, cases=("p2",), approve=True)

# approval granted for ONLY a small case count: a wider selection must not slip through (bounds)
def small_approval(sel):
    root, store = fresh(approve=False)
    grant_live_case_approval(store, max_actions=1)  # covers ~nothing
    return root, store
for label, pv in [("None", None), ("['p1']", ["p1"])]:
    root, store = small_approval(pv)
    before = listing(root)
    C.update(sessions=0, executed=[])
    try:
        if HEAD:
            RL.launch_run("demo", priorities=pv)
        else:
            routes_runs._execute_and_record(routes_runs._prepare_run("demo", pv), "run-X")
        res = "returned"
    except BaseException as exc:  # noqa: BLE001
        res = f"{type(exc).__name__}: {str(getattr(exc, 'reason', exc))[:120]}"
    rows[f"tiny-approval(max_actions=1) priorities={label}"] = {"result": res, "sessions": C["sessions"], "executed": list(C["executed"]), "tree_changed": listing(root) != before}

# unknown keyword doors
if HEAD:
    for kw in ("skip_approval", "approval", "force", "no_gate", "gate"):
        root, store = fresh()
        try:
            RL.launch_run("demo", **{kw: True})
            res = "returned"
        except TypeError as exc:
            res = "TypeError " + str(exc)[:80]
        except BaseException as exc:  # noqa: BLE001
            res = type(exc).__name__
        rows[f"launch_run kw {kw}"] = {"result": res, "sessions": C["sessions"], "executed": list(C["executed"])}
    rows["RunSeams fields"] = list(RL.RunSeams._fields)
    import inspect
    rows["launch_run sig"] = str(inspect.signature(RL.launch_run))
    rows["prepare_run sig"] = str(inspect.signature(RL.prepare_run))
    rows["run_cases_traced sig"] = str(inspect.signature(RL.run_cases_traced))
    rows["__all__"] = RL.__all__

# the public lower door: execute with a fabricated approval (both sides)
from autotester.schema.approval import RunApproval  # noqa: E402
from autotester.schema.enums import ApprovalKind  # noqa: E402
root, store = fresh()
cases = store.list_cases()
project = store.load_project()
from autotester.browser.secrets import SecretStore  # noqa: E402
from autotester.core.paths import ProjectPaths  # noqa: E402
paths = ProjectPaths("demo")
secrets = SecretStore.load(project, paths.env_file, strict=False)
forged = RunApproval(project="demo", run_kind=ApprovalKind.LIVE_CASE, target="https://demo.test", scope="forged",
                     max_actions=10000, max_probes=0, wall_clock_s=100000.0, granted_by="x", granted_at="2026-01-01", expires_at="2099-01-01")
fn = (RL.run_cases_traced if HEAD else routes_runs._execute_with_trace)
try:
    kwargs = dict(seams=RL.DEFAULT_SEAMS._replace(planner=lambda project, **k: __import__("autotester.stages.parallel_run", fromlist=["x"]).ParallelPlan(1, 1, 1, "config", 1000.0, 1))) if HEAD else {}
    fn(store, "run-forged", secrets, project, cases, [False] * len(cases), paths.run_dir("run-forged"), paths, "demo", Judge(), forged, None, **kwargs) if HEAD else fn(store, "run-forged", secrets, project, cases, [False] * len(cases), paths.run_dir("run-forged"), paths, "demo", Judge(), forged)
    res = "returned (executes with whatever approval object it is handed)"
except BaseException as exc:  # noqa: BLE001
    res = f"{type(exc).__name__}: {str(exc)[:100]}"
rows["LOWER DOOR run_cases_traced / _execute_with_trace with forged unsigned approval"] = {"result": res, "executed": list(C["executed"])}

Path(sys.argv[1]).write_text(json.dumps({"file": autotester.__file__, "rows": rows}, indent=1, sort_keys=True), encoding="utf-8")
print(len(rows), "rows")
