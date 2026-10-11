"""login-carve-out abuse harness. Offline: spies replace execute.run_case + session factory."""
from __future__ import annotations

import csv
import hashlib
import sys
import tempfile
from pathlib import Path
from typing import Any

import autotester
from autotester.agents import tools
from autotester.agents.context import AgentContext
from autotester.browser.secrets import SecretStore
from autotester.providers.mock import MockProvider
from autotester.schema.approval import RunApproval
from autotester.schema.case import Case
from autotester.schema.enums import Action as A
from autotester.schema.enums import ApprovalKind, CaseClass, CaseKind, Outcome, WritePolicy
from autotester.schema.flowspec import Step
from autotester.schema.project import Project, SecretRef
from autotester.schema.run import RawResult
from autotester.store.project_store import ProjectStore

import os
os.environ["AUTOTESTER_APPROVAL_KEY"] = "fake-test-approval-key-not-real-0001"
OUT = Path(sys.argv[1])
BASE = "https://app.example.test"
RAW_U, RAW_P = "CANARY-user-7f3a9c", "CANARY-pw-7f3a9c"
print("autotester.__file__ =", autotester.__file__)

calls = {"run_case": 0, "sessions": 0}
tools.execute.run_case = lambda case, session: (
    calls.__setitem__("run_case", calls["run_case"] + 1),
    RawResult(case_id=case.id, outcome=Outcome.COMPLETED))[1]


class _S:
    def __enter__(self):
        return self

    def __exit__(self, *e):
        return None


def snap(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(root)).encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def S(*items):
    return [Step(order=i + 1, action=a, target=t, value=v) for i, (a, t, v) in enumerate(items)]


NAV = (A.NAVIGATE, f"{BASE}/login?next=%2Fhome", None)
U = (A.FILL, "Email", "{{SECRET:APP_USER}}")
P = (A.FILL, "Password", "{{SECRET:APP_PASS}}")
CL = (A.CLICK, "Sign in", None)
EN = (A.PRESS_KEY, "", "Enter")
LOGIN = [NAV, U, P, CL]


def run_row(rid, desc, items, mode="self", case_id=None, expect="refused", note=""):
    tmp = Path(tempfile.mkdtemp(prefix="lco-"))
    project = Project(slug="demo", name="Demo", base_url=BASE, allowed_domains=["app.example.test"],
                      write_policy=WritePolicy.READ_ONLY,
                      secrets=[SecretRef(key="APP_USER", domains=["app.example.test"]),
                               SecretRef(key="APP_PASS", domains=["app.example.test"])])
    store = ProjectStore("demo", tmp)
    store.paths.ensure()
    store.save_project(project)
    steps = S(*items)
    kw: dict[str, Any] = {"id": case_id} if case_id else {}
    case = store.add_case(Case(project="demo", flow_id="f1", kind=CaseKind.BEST,
                               case_class=CaseClass.HAPPY, title="case", steps=steps, **kw))
    decoy = store.add_case(Case(project="demo", flow_id="decoy", kind=CaseKind.BEST,
                                case_class=CaseClass.HAPPY, title="decoy",
                                steps=S((A.WAIT, "x", None))))
    store.add_approval(RunApproval(project="demo", run_kind=ApprovalKind.LIVE_CASE, target=BASE,
                                   scope="fixture", max_actions=50, wall_clock_s=900.0,
                                   granted_by="umesh", granted_at="2026-10-01",
                                   expires_at="2099-01-01").sign())
    login_id = {"self": case.id, "other": decoy.id, "none": None,
                "missing": "no-such-case"}.get(mode, mode)
    project = project.model_copy(update={"login_case_id": login_id})
    calls.update(run_case=0, sessions=0)

    def open_session(obs):
        calls["sessions"] += 1
        return _S()
    ctx = AgentContext(project=project, store=store,
                       secrets=SecretStore(project, {"APP_USER": RAW_U, "APP_PASS": RAW_P}),
                       judge=MockProvider(), run_id="run-1", open_session=open_session)
    before = snap(tmp)
    out = tools.dispatch(ctx, "run_case", {"case_id": case.id})
    changed = snap(tmp) != before
    row = dict(id=rid, desc=desc, login_mode=mode, case_id=case.id[:24], ok=out.ok,
               refusal=out.refusal.value if out.refusal else "",
               summary=out.summary[:230], sessions=calls["sessions"],
               run_case_calls=calls["run_case"], data_changed=changed, expected=expect,
               result="as-expected" if (out.ok == (expect == "ok")) else "UNEXPECTED", note=note)
    assert RAW_U not in out.model_dump_json() and RAW_P not in out.model_dump_json()
    if not out.ok:
        assert out.refusal is not None and calls["sessions"] == 0 and calls["run_case"] == 0, row
    return row


ROWS: list[dict] = []


def r(*a, **k):
    ROWS.append(run_row(*a, **k))


# ---- positive controls
r("P1", "login: NAV?query, FILL user, FILL pass, CLICK Sign in", LOGIN, expect="ok")
r("P2", "same with PRESS_KEY Enter", [NAV, U, P, EN], expect="ok")
r("P3", "same with PRESS_KEY value None", [NAV, U, P, (A.PRESS_KEY, "", None)], expect="ok")
r("P4", "PRESS_KEY Enter on locator 'Password'", [NAV, U, P, (A.PRESS_KEY, "Password", "Enter")],
  expect="ok")
r("P5", "credential fill with no submit at all", [NAV, U, P], expect="ok",
  note="no submit required")
# ---- a
r("A1", "identical login steps, case id != login_case_id (decoy is login)", LOGIN, mode="other")
r("A2", "identical login steps, login_case_id None", LOGIN, mode="none")
# ---- b
r("B1", "extra CLICK 'Continue' after submit", LOGIN + [(A.CLICK, "Continue", None)])
r("B2", "extra Enter after CLICK submit", LOGIN + [EN])
r("B3", "second submit CLICK after Enter submit, no new fill", [NAV, U, P, EN, CL])
r("B4", "two full sequences: fill,submit,fill,submit (benign names)",
  [NAV, U, P, CL, P, (A.CLICK, "Continue", None)], expect="refused",
  note="credential_pending reset only by a submit; a fresh credential FILL re-arms it")
r("B4b", "three sequences, one per credential fill", [NAV, U, P, CL, P, CL, P, CL],
  expect="refused")
r("B5", "CLICK 'Sign in' BEFORE any credential fill", [NAV, CL, U, P])
r("B6", "Enter BEFORE any credential fill", [NAV, EN, U, P])
r("B7", "submit CLICK 'Delete account' after credential",
  [NAV, U, P, (A.CLICK, "Delete account", None)])
r("B8", "submit CLICK 'Log out' after credential", [NAV, U, P, (A.CLICK, "Log out", None)])
r("B9", "PRESS_KEY Delete after credential", [NAV, U, P, (A.PRESS_KEY, "", "Delete")])
r("B10", "PRESS_KEY Tab after credential", [NAV, U, P, (A.PRESS_KEY, "", "Tab")])
r("B11", "CLICK 'Place order' as the one submit", [NAV, U, P, (A.CLICK, "Place order", None)],
  expect="refused", note="submit CLICK only passes deny_reason; name not required to be sign-in")
r("B12", "CLICK 'Save' as the one submit", [NAV, U, P, (A.CLICK, "Save", None)])
r("B13", "CLICK 'Transfer funds' as the one submit",
  [NAV, U, P, (A.CLICK, "Transfer funds", None)], expect="refused")
r("B14", "Enter on locator 'Search' after credential",
  [NAV, U, P, (A.PRESS_KEY, "Search", "Enter")], expect="refused")
r("B15", "credential, literal FILL 'Name' Eve, then submit",
  [NAV, U, P, (A.FILL, "Name", "Eve"), CL])
r("B16", "submit then WAIT/HOVER/SCROLL/BACK/ASSERT",
  LOGIN + [(A.WAIT, "x", None), (A.HOVER, "y", None), (A.SCROLL, "", None), (A.BACK, "", None),
           (A.ASSERT, "", None)], expect="ok", note="reads allowed; BACK is history navigation")
r("B17", "SELECT after submit", LOGIN + [(A.SELECT, "Plan", "pro")])
r("B18", "UPLOAD after submit", LOGIN + [(A.UPLOAD, "CV", "cv.pdf")])
r("B19", "credential, HOVER Delete account, CLICK Sign in",
  [NAV, U, P, (A.HOVER, "Delete account", None), CL], expect="ok")
r("B20", "credential, WAIT, Enter, CLICK (read keeps pending, 2nd submit)",
  [NAV, U, P, (A.WAIT, "x", None), EN, CL])
# ---- c fills
for rid, val, exp, nt in [
    ("C1", "x{{SECRET:APP_PASS}}", "refused", ""),
    ("C2", "{{SECRET:APP_PASS}}x", "refused", ""),
    ("C3", "{{SECRET:APP_PASS}}{{SECRET:APP_PASS}}", "ok", "pure placeholders concatenated"),
    ("C3b", "{{SECRET:APP_USER}}{{SECRET:APP_PASS}}", "ok", "user+pass concatenated"),
    ("C4", " {{SECRET:APP_PASS}} ", "ok", "whitespace residue allowed; typed with the secret"),
    ("C4b", "{{SECRET:APP_PASS}}\n", "ok", "newline residue allowed"),
    ("C4c", "{{SECRET:APP_PASS}} ", "ok", "NBSP residue allowed"),
    ("C4d", "{{SECRET:APP_PASS}}​", "refused", "zero-width space not stripped"),
    ("C5", "", "refused", ""),
    ("C6", None, "refused", ""),
    ("C7", "{{SECRET:OTHER}}", "refused", "undeclared key"),
    ("C7b", "{{SECRET:APP_PASS}}{{SECRET:OTHER}}", "refused", "declared + undeclared"),
    ("C8", "{{SECRET:app_pass}}", "refused", "lower-case key"),
    ("C9", "{{SECRET:APP_PASS}", "refused", "malformed"),
    ("C9b", "{{ SECRET:APP_PASS }}", "refused", "malformed"),
    ("C10", "{{SECRET:{{SECRET:APP_PASS}}}}", "refused", "nested"),
    ("C10b", "{{SECRET:APP_{{SECRET:APP_PASS}}}}", "refused", "nested splice"),
    ("C11", "{{SECRET:APP_PASS}}", "ok", "control"),
    ("C12", "｛｛SECRET:APP_PASS｝｝", "refused", "fullwidth braces"),
    ("C12b", "{{SECRET:APP_PAЅS}}", "refused", "cyrillic lookalike in key"),
    ("C12c", "{{SECRET:APP＿PASS}}", "refused", "fullwidth underscore"),
    ("C13", "{{SECRET:APP_PASS}}\x00", "refused", "NUL residue"),
]:
    r(rid, f"FILL value {val!r}", [NAV, U, (A.FILL, "Password", val), CL], expect=exp, note=nt)
for rid, tgt in [("C14", "Search"), ("C15", "Comment"), ("C16", "Amount"),
                 ("C17", "Delete confirmation")]:
    r(rid, f"declared credential typed into non-credential field {tgt!r}",
      [NAV, (A.FILL, tgt, "{{SECRET:APP_PASS}}")], expect="refused",
      note="guard never inspects step.target for FILL")
r("C18", "after login: NAV /feed, FILL 'Comment' <APP_PASS>, CLICK 'Post comment'",
  [NAV, U, P, CL, (A.NAVIGATE, f"{BASE}/feed", None), (A.FILL, "Comment", "{{SECRET:APP_PASS}}"),
   (A.CLICK, "Post comment", None)], expect="refused",
  note="re-armed credential_pending lets a second state-changing click through")
# ---- d
r("D1", "login + CLICK 'Save'", LOGIN + [(A.CLICK, "Save", None)])
r("D2", "login + FILL 'Name' Eve", LOGIN + [(A.FILL, "Name", "Eve")])
r("D3", "login + NAV /x?id=1 (2nd navigate with query)",
  LOGIN + [(A.NAVIGATE, f"{BASE}/x?id=1", None)], expect="refused",
  note="query allowed for EVERY navigate in the login case")
r("D4", "login + NAV /account/delete?id=1&confirm=1",
  LOGIN + [(A.NAVIGATE, f"{BASE}/account/delete?id=1&confirm=1", None)])
r("D5", "login + NAV /logout?x=1", LOGIN + [(A.NAVIGATE, f"{BASE}/logout?x=1", None)])
r("D5b", "login + NAV /account?action=delete&confirm=1 (deny word only in query)",
  LOGIN + [(A.NAVIGATE, f"{BASE}/account?action=delete&confirm=1", None)], expect="refused",
  note="deny_reason sees path+fragment only, never the query")
r("D5c", "login + NAV /transfer?to=eve&amount=100",
  LOGIN + [(A.NAVIGATE, f"{BASE}/transfer?to=eve&amount=100", None)], expect="refused")
r("D5d", "login + NAV /login#delete (fragment deny word)",
  LOGIN + [(A.NAVIGATE, f"{BASE}/login#delete", None)])
r("D6", "login + NAV https://evil.test/login?x=1",
  LOGIN + [(A.NAVIGATE, "https://evil.test/login?x=1", None)])
r("D6b", "login + NAV https://evil.test\\@app.example.test/?x=1",
  LOGIN + [(A.NAVIGATE, "https://evil.test\\@app.example.test/?x=1", None)])
r("D6c", "login + NAV https://app.example.test@evil.test/?x=1",
  LOGIN + [(A.NAVIGATE, "https://app.example.test@evil.test/?x=1", None)])
r("D7", "login + NAV javascript:alert(1)", LOGIN + [(A.NAVIGATE, "javascript:alert(1)", None)])
r("D7b", "login NAV with placeholder in query",
  [(A.NAVIGATE, f"{BASE}/login?pw={{{{SECRET:APP_PASS}}}}", None), U, P, CL])
r("D8", "login + NAV //evil.test/x?y=1", LOGIN + [(A.NAVIGATE, "//evil.test/x?y=1", None)])
r("D9", "login + NAV bare path /x?y=1", LOGIN + [(A.NAVIGATE, "/x?y=1", None)])
r("D10", "login + NAV http://app.example.test/x (http scheme)",
  LOGIN + [(A.NAVIGATE, "http://app.example.test/x", None)], expect="ok",
  note="http inside domain allowed")
# ---- e
r("E1", "login_case_id None, case id literally 'login'", LOGIN, mode="none", case_id="login")
r("E2", "login_case_id = nonexistent id", LOGIN, mode="missing")
r("E3", "login_case_id 'Login', case id 'login'", LOGIN, mode="Login", case_id="login")
r("E4", "login_case_id 'login', case id 'Login'", LOGIN, mode="login", case_id="Login")
r("E5", "login_case_id 'login ', case id 'login'", LOGIN, mode="login ", case_id="login")
r("E6", "login_case_id 'login', case id 'login '", LOGIN, mode="login", case_id="login ")
r("E7", "login_case_id 'login' == case id 'login' (control)", LOGIN, mode="login",
  case_id="login", expect="ok")
r("E8", "login_case_id '' (empty), generated case id", LOGIN, mode="")

with open(OUT / "rows.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(ROWS[0]))
    w.writeheader()
    w.writerows(ROWS)
for x in ROWS:
    print(f"{x['id']:5} {'OK ' if x['ok'] else 'REF'} {x['result']:12} s={x['sessions']} "
          f"rc={x['run_case_calls']} chg={x['data_changed']} | {x['desc'][:62]} | "
          f"{x['summary'][:100]}")
print("UNEXPECTED:", [x['id'] for x in ROWS if x['result'] == 'UNEXPECTED'])
