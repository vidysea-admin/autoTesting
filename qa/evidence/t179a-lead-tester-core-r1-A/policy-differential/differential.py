"""Policy differential: identical script run on BASE and HEAD copies.
usage: python differential.py <label> <out.csv>
Drives agents.tools.dispatch(ctx,"run_case",...) with spies on the session factory and on
execute.run_case, so the same code works whatever guards.write_policy_refusal returns."""
from __future__ import annotations

import csv
import os
import sys
import tempfile
from pathlib import Path

import autotester
from autotester.agents import tools
from autotester.agents.context import AgentContext
from autotester.browser.secrets import SecretStore, host_of
from autotester.browser.session import check_destination
from autotester.core.redact import PLACEHOLDER_RE
from autotester.providers.mock import MockProvider
from autotester.schema.approval import RunApproval
from autotester.schema.case import Case
from autotester.schema.enums import (
    Action, ApprovalKind, CaseClass, CaseKind, Outcome, WritePolicy)
from autotester.schema.flowspec import Step
from autotester.schema.project import Project, SecretRef
from autotester.schema.run import RawResult
from autotester.store.project_store import ProjectStore

os.environ.setdefault("AUTOTESTER_APPROVAL_KEY", "fake-differential-key-0000")
label, out = sys.argv[1], sys.argv[2]
print(label, "autotester.__file__ =", autotester.__file__, flush=True)

CANARY = "CANARY-pw-7f3a9c"
A = Action
APP = "https://app.example.test"


def S(action, target, value=None, order=1):
    return Step(order=order, action=action, target=target, value=value)


# ---------------- rows -----------------
def common_rows():
    r = []
    for t in ["Save", "Save changes", "Place order", "Confirm", "Apply now", "Register", "Sign up",
              "Add to cart", "Sign in", "हटाएं",
              "खाता हटाएं",
              "Delete account", "Log out", "Sign out", "Remove", "Cancel subscription"]:
        r.append((f"CLICK:{t}", [S(A.CLICK, t)]))
    for v in ["Enter", None, "Delete", "Tab"]:
        r.append((f"PRESS_KEY:{v}", [S(A.PRESS_KEY, "body", v)]))
    for v in ["", "   ", None, "x", "{{SECRET:APP_PASS}}"]:
        r.append((f"FILL:{v!r}", [S(A.FILL, "Name", v)]))
    r.append(("SELECT:pro", [S(A.SELECT, "Plan", "pro")]))
    r.append(("UPLOAD:cv", [S(A.UPLOAD, "Resume", "cv.pdf")]))
    r.append(("WAIT", [S(A.WAIT, "body")]))
    r.append(("ASSERT", [S(A.ASSERT, "Heading")]))
    return r


MAIN_NAV = [
    "https://app.example.test/account/delete?id=1&confirm=1", "https://app.example.test/logout",
    "https://app.example.test/reports", "https://app.example.test/reports?page=2",
    "/reports", "/home", "Admin portal URL", "{{SECRET:APP_PASS}}",
    "https://app.example.test/{{SECRET:APP_PASS}}", "https://api.app.example.test/x",
    "https://other.example.test/x", "http://app.example.test/x", "https://app.example.test:8443/x",
    "https://APP.EXAMPLE.TEST/x", "HTTPS://app.example.test/x", "https://app.example.test./x",
    "https://app.example.test:443/x", "https://user:pw@app.example.test/x",
    "https://app.example.test\\x", "https://evil.test\\@app.example.test/x",
    " https://app.example.test/x", "https://app.example.test/x ", "\thttps://app.example.test/x",
    "//app.example.test/x", "//evil.test/x", "https://bücher.example.test/x",
    "https://xn--bcher-kva.example.test/x", "https://аpp.example.test/x",
    "javascript:alert(1)", "javascript://app.example.test/%0aalert(1)", "data:text/html,<b>x</b>",
    "file:///etc/passwd", "file://app.example.test/x", "about:blank", "ftp://app.example.test/x",
    "ws://app.example.test/x", "https://evil.test/x", "https://evil.test/app.example.test",
    "https://app.example.test.evil.test/x", "https://evilapp.example.test/x",
    "https://app.example.test/x\ny", "https://app.exa\tmple.test/x", "https://app.example.test/x\x00",
    "https://app.example.test/x\x7f", "https://[invalid/x", "https://app.example.test:99999/x",
    "https://app.example.test:abc/x", "https://app.example.test@evil.test/x",
    "https://@app.example.test/x", "https://app.example.test?x=1", "https://app.example.test#frag",
    "app.example.test/x", "app.example.test", "evil.test/x", "localhost:3000/",
    "mailto:a@app.example.test",
    # placeholder-bearing URLs (resolution happens in session.goto, after the guard)
    "{{SECRET:BASE}}/x", "https://{{SECRET:HOST}}/x", "{{SECRET:LOGINURL}}", "{{SECRET:BASE}}",
    "https://{{SECRET:HOST}}",
    "//{{SECRET:HOST}}/x", "https://{{SECRET:HOST}}:8443/x",
    "https://user:{{SECRET:APP_PASS}}@app.example.test/x",
]


def main_rows():
    rows = common_rows()
    for t in MAIN_NAV:
        rows.append((f"NAVIGATE:{t!r}", [S(A.NAVIGATE, t)]))
    rows.append(("MULTI:form", [S(A.NAVIGATE, f"{APP}/form", None, 1), S(A.FILL, "Name", "Eve", 2),
                                S(A.SELECT, "Plan", "pro", 3), S(A.CLICK, "Save", None, 4),
                                S(A.ASSERT, "Saved", None, 5)]))
    rows.append(("MULTI:form-barepath", [S(A.NAVIGATE, "/form", None, 1),
                                         S(A.FILL, "Name", "Eve", 2),
                                         S(A.SELECT, "Plan", "pro", 3), S(A.CLICK, "Save", None, 4),
                                         S(A.ASSERT, "Saved", None, 5)]))
    return rows


def local_rows(urls):
    rows = [(f"NAVIGATE:{u!r}", [S(A.NAVIGATE, u)]) for u in urls]
    rows.append(("MULTI:form", [S(A.NAVIGATE, urls[0], None, 1), S(A.FILL, "Name", "Eve", 2),
                                S(A.SELECT, "Plan", "pro", 3), S(A.CLICK, "Save", None, 4),
                                S(A.ASSERT, "Saved", None, 5)]))
    return rows


SECRETS = {"APP_PASS": CANARY, "BASE": APP, "HOST": "app.example.test",
           "LOGINURL": f"{APP}/login"}
SECREFS = [SecretRef(key=k, domains=["app.example.test", "other.example.test"]) for k in SECRETS]
PROJECTS = [
    dict(slug="demo", base_url=APP,
         domains=["app.example.test", "other.example.test", "bücher.example.test"],
         secrets=SECREFS, secvals=SECRETS, rows=main_rows),
    dict(slug="lhost", base_url="http://localhost:3000", domains=["localhost"], secrets=[],
         secvals={},
         rows=lambda: local_rows(["http://localhost:3000/", "http://localhost:3000/app/x?y=1",
                                  "https://localhost:3000/", "http://localhost/",
                                  "http://LOCALHOST:3000/x", "http://127.0.0.1:3000/", "/app",
                                  "http://localhost.evil.test/", "http://sub.localhost:3000/x"])),
    dict(slug="ip4", base_url="http://127.0.0.1:8080", domains=["127.0.0.1"], secrets=[],
         secvals={},
         rows=lambda: local_rows(["http://127.0.0.1:8080/", "http://127.0.0.1/x?y=1",
                                  "https://127.0.0.1:8443/x", "http://localhost:8080/",
                                  "http://127.0.0.2/"])),
    dict(slug="ip6", base_url="http://[::1]:8080", domains=["::1"], secrets=[], secvals={},
         rows=lambda: local_rows(["http://[::1]:8080/", "http://[::1]/x?y=1",
                                  "https://[::1]:8443/x", "http://[::2]:8080/"])),
    dict(slug="ip6b", base_url="http://[::1]:8080", domains=["[::1]"], secrets=[], secvals={},
         rows=lambda: local_rows(["http://[::1]:8080/", "http://[::1]/x?y=1"])),
]


def act_time(project, secrets, step):
    if step.action is not A.NAVIGATE:
        return ""
    url = step.target
    try:
        real = secrets.resolve_for_navigation(url) if PLACEHOLDER_RE.search(url) else url
        host = check_destination(project, real)
        return f"ACCEPT host={host}"
    except Exception as exc:  # noqa: BLE001
        return f"REFUSE {type(exc).__name__}"


def host_col(step):
    if step.action is not A.NAVIGATE:
        return ""
    try:
        return repr(host_of(step.target))
    except Exception as exc:  # noqa: BLE001
        return f"EXC {type(exc).__name__}"


class Spy:
    sessions = 0
    runs = 0


class _Sess:
    def __enter__(self):
        return self

    def __exit__(self, *e):
        return None


def run_one(spec, policy, rows):
    spy = Spy()
    tools.execute.run_case = lambda case, session: (
        setattr(spy, "runs", spy.runs + 1),
        RawResult(case_id=case.id, outcome=Outcome.COMPLETED))[1]
    project = Project(slug=spec["slug"], name=spec["slug"], base_url=spec["base_url"],
                      allowed_domains=spec["domains"], write_policy=policy, secrets=spec["secrets"])
    store = ProjectStore(spec["slug"], Path(tempfile.mkdtemp()))
    store.paths.ensure()
    store.save_project(project)
    store.add_approval(RunApproval(
        project=spec["slug"], run_kind=ApprovalKind.LIVE_CASE, target=spec["base_url"],
        scope="differential fixture", max_actions=500, wall_clock_s=900.0, granted_by="umesh",
        granted_at="2026-10-01", expires_at="2099-01-01").sign())
    secrets = SecretStore(project, dict(spec["secvals"]))

    def open_session(observer):
        spy.sessions += 1
        return _Sess()
    ctx = AgentContext(project=project, store=store, secrets=secrets, judge=MockProvider(),
                       run_id="run-1", open_session=open_session)
    out_rows = []
    for rid, steps in rows:
        case = store.add_case(Case(project=spec["slug"], flow_id="f1", kind=CaseKind.BEST,
                                   case_class=CaseClass.HAPPY, title=rid, steps=steps))
        spy.sessions = spy.runs = 0
        oc = tools.dispatch(ctx, "run_case", {"case_id": case.id})
        nav = next((s for s in steps if s.action is A.NAVIGATE), None)
        out_rows.append(dict(
            project=spec["slug"], policy=policy.value, row=rid, ok=oc.ok,
            refusal=(oc.refusal.value if oc.refusal else ""), sessions=spy.sessions,
            run_case_calls=spy.runs, act_time=act_time(project, secrets, nav) if nav else "",
            host_of=host_col(nav) if nav else "", summary=oc.summary[:160].replace("\n", " ")))
    return out_rows


allrows = []
for spec in PROJECTS:
    rows = spec["rows"]()
    for policy in (WritePolicy.TEST_ACCOUNT, WritePolicy.ALLOW_WRITES, WritePolicy.READ_ONLY):
        allrows.extend(run_one(spec, policy, rows))
fields = ["project", "policy", "row", "ok", "refusal", "sessions", "run_case_calls", "act_time",
          "host_of", "summary"]
with open(out, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=fields)
    w.writeheader()
    w.writerows(allrows)
print(label, "rows:", len(allrows))
