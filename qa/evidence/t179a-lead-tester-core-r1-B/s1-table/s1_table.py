"""S1 attack table. Run: <copy>/.venv/Scripts/python -I s1_table.py <copy-root> <out.json> [shard N]
Generates rows over policy x Action x corpus x position x login, drives the REAL
autotester.agents.tools.dispatch(ctx,"run_case",...) and records facts. Offline (probe_lib spies)."""
from __future__ import annotations

import os
import re
import shutil
import sys
import time

sys.path.insert(0, "D:/autoTesting/qa/evidence/t179a-lead-tester-core-r1-B")
import probe_lib as L  # noqa: E402

COPY = sys.argv[1]
OUT = sys.argv[2]
SHARD = int(sys.argv[3]) if len(sys.argv) > 3 else 0
NSHARD = int(sys.argv[4]) if len(sys.argv) > 4 else 1
print("COPY", L.confirm_copy(COPY))

A = L.Action
PW, US = L.CANARY["APP_PASS"], L.CANARY["APP_USER"]
DECLARED = {"APP_PASS", "APP_USER"}
PH = re.compile(r"\{\{SECRET:([A-Z0-9_]+)\}\}")  # independent copy for the oracle


def lab(x):
    if x is None:
        return "None"
    s = L.label(x)
    if len(s) > 60:
        return f"<str len={len(s)}>"
    return repr(s)


TARGETS = [
    ("Home", True), ("Next", True), ("Products", True), ("Dashboard", True), ("Tab", True),
    ("Save", False), ("Place order", False), ("Register", False), ("Add to cart", False),
    ("Sign in", False), ("\u0939\u091f\u093e\u090f\u0902", False),
    ("Delete", False), ("Remove", False), ("Pay", False), ("Send", False), ("Logout", False),
    ("Sign out", False), ("Log-Out", False), ("LOG_OUT", False),
    ("\u5220\u9664", False), ("\u30ed\u30b0\u30a2\u30a6\u30c8", False),
    ("\u062d\u0630\u0641", False), ("\u0423\u0434\u0430\u043b\u0438\u0442\u044c", False),
    ("", False), ("   ", False),
    ("{{SECRET:APP_PASS}}", False), ("{{SECRET:NOPE}}", False),
    ("pre {{SECRET:APP_USER}} post", False), (PW, False), ("a" * 5000, False),
]
VALUES = [
    (None, True), ("hello", True), ("Home", True), ("", False), ("   ", False),
    ("{{SECRET:APP_PASS}}", False), ("{{SECRET:APP_USER}}", False), ("{{SECRET:NOPE}}", False),
    ("{{SECRET:APP_USER}}{{SECRET:APP_PASS}}", False), ("user {{SECRET:APP_USER}}", False),
    ("{{SECRET:APP_PASS}}x", False), (PW, False), (US, False), ("a" * 5000, False),
    ("Delete", False), ("\u5220\u9664", False), ("100", True),
]
PRESS_VALUES = [(None, False), ("Enter", False), ("enter", False), (" Enter ", False),
                ("Delete", False), ("Tab", True), ("Escape", True), ("Control+Enter", False)]
NAV = [
    ("https://app.test/home", True), ("/reports", True), ("Admin portal URL", True),
    ("https://app.test/account/delete?id=1&confirm=1", False),
    ("https://app.test/logout", False), ("https://evil.test/", False),
    ("javascript:alert(1)", False), ("{{SECRET:APP_PASS}}", False),
    ("https://app.test/home?page=2", True),
    ("https://{{SECRET:APP_PASS}}/", False), ("//{{SECRET:APP_USER}}/x", False),
    ("//app.test/x", True), ("//evil.test/x", False), ("https://sub.app.test/home", True),
    ("http://app.test:8080/", True), ("https://app.test.evil.test/", False),
    ("https://app.test\\@evil.test/", False), ("https://user@app.test/", False),
    ("ftp://app.test/", False), ("file:///etc/passwd", False),
    ("https://app.test/home#delete", False), ("https://app.test/Delete", False),
    ("https://app.test/home\n", False), ("https://app.test/ho\tme", False),
    ("", False), ("   ", False), ("home", True), ("HTTPS://APP.TEST/home", True),
    ("https://app.test/search?q=x", False), ("data:text/html,hi", False),
    ("https://app.test/home/%2e%2e/logout", False),
]
MUTATING = {A.CLICK, A.PRESS_KEY, A.FILL, A.SELECT, A.UPLOAD}
FILL3 = [(A.WAIT, "ok", None), (A.ASSERT, "ok", None)]
FILL6 = [(A.NAVIGATE, "https://app.test/home", None), (A.HOVER, "Menu", None),
         (A.SCROLL, "page", "100"), (A.WAIT, "ok", None), (A.ASSERT, "ok", None), (A.BACK, "", None)]
POSITIONS = ("single", "first", "middle", "last", "s6-first", "s6-mid", "s6-last")


def pairs(action):
    if action is A.NAVIGATE:
        return [(t, None, b) for t, b in NAV] + [("https://app.test/home", "x", True)]
    out = [(t, None, b) for t, b in TARGETS]
    if action is A.PRESS_KEY:
        out += [("Search box", v, b) for v, b in PRESS_VALUES]
        out += [(t, "Enter", False) for t, _ in TARGETS]
    else:
        out += [("Search box", v, b) for v, b in VALUES if v is not None]
    return out


def oracle_mutating_outside_carveout(steps, is_login):
    """INDEPENDENT oracle (no import of code under test): True if the case has a
    CLICK/PRESS_KEY/FILL/SELECT/UPLOAD outside the declared-login carve-out."""
    credit = 0
    for s in sorted(steps, key=lambda s: s.order):
        if s.action not in MUTATING:
            continue
        if not is_login:
            return True
        if s.action is A.FILL:
            v = s.value or ""
            if v and PH.sub("", v).strip() == "" and all(k in DECLARED for k in PH.findall(v)):
                credit += 1
                continue
            return True
        if s.action in (A.CLICK, A.PRESS_KEY):
            if s.action is A.PRESS_KEY and s.value not in (None, "Enter"):
                return True
            if credit > 0:
                credit -= 1
                continue
            return True
        return True
    return False


def build_specs():
    specs = []
    for pol in L.POLICIES:
        for action in sorted(A, key=lambda a: a.value):
            for target, value, benign in pairs(action):
                for pos in POSITIONS:
                    for login in (False, True):
                        specs.append((pol, action, target, value, benign, pos, login))
    return specs


def steps_for(action, target, value, pos):
    tested = (action, target, value)
    if pos == "single":
        seq = [tested]
    elif pos in ("first", "middle", "last"):
        i = {"first": 0, "middle": 1, "last": 2}[pos]
        seq = FILL3[:i] + [tested] + FILL3[i:]
    else:
        i = {"s6-first": 0, "s6-mid": 3, "s6-last": 5}[pos]
        f = list(FILL6)
        del f[i]
        seq = f[:i] + [tested] + f[i:]
    return [L.Step(order=n + 1, action=a, target=t, value=v) for n, (a, t, v) in enumerate(seq)]


def finish(env, steps, login, key, pol, action, target, value, pos, benign):
    h0 = L.tree_hash(env.root)
    r = L.run_case_row(env)
    h1 = L.tree_hash(env.root)
    row = {
        "key": key, "policy": pol.value, "action": action, "target": target, "value": value,
        "pos": pos, "login": login, "benign": benign, "nsteps": len(steps),
        "has_mutating": any(s.action in MUTATING for s in steps),
        "oracle_mut_outside": oracle_mutating_outside_carveout(steps, login),
        "executed": r["executed"], "refusal": r["refusal"], "ok": r["ok"],
        "sessions": r["sessions"], "run_case_calls": r["run_case_calls"],
        "n_files": r["n_files_written"], "tree_changed": h0 != h1, "raised": r["raised"],
        "summary": (r["summary"] or "")[:110],
    }
    shutil.rmtree(env.root, ignore_errors=True)
    return row


def one(pol, action, target, value, benign, pos, login):
    try:
        steps = steps_for(action, target, value, pos)
    except Exception:  # noqa: BLE001 - Step model rejected
        return "step_rejected"
    try:
        env = L.make_env(pol, [steps], login_index=0 if login else None)
    except Exception as e:  # noqa: BLE001
        return f"case_rejected:{type(e).__name__}"
    key = f"{pol.value}|{action.value}|{lab(target)}|{lab(value)}|{pos}|{'login' if login else 'plain'}"
    return finish(env, steps, login, key, pol, action.value, lab(target), lab(value), pos, benign)


def composed_specs():
    U, Pw = "{{SECRET:APP_USER}}", "{{SECRET:APP_PASS}}"
    F, C, K = A.FILL, A.CLICK, A.PRESS_KEY
    seqs = {
        "u+p+signin": [(F, "User", U), (F, "Pass", Pw), (C, "Sign in", None)],
        "p+enter": [(F, "Pass", Pw), (K, "Pass", "Enter")],
        "p+enterNone": [(F, "Pass", Pw), (K, "Pass", None)],
        "p+enter-lower": [(F, "Pass", Pw), (K, "Pass", "enter")],
        "p+2submits": [(F, "Pass", Pw), (C, "Sign in", None), (C, "Sign in", None)],
        "submit-before-fill": [(C, "Sign in", None), (F, "Pass", Pw)],
        "p+click-Delete": [(F, "Pass", Pw), (C, "Delete", None)],
        "p+click-Save": [(F, "Pass", Pw), (C, "Save", None)],
        "p+click-Logout": [(F, "Pass", Pw), (C, "Logout", None)],
        "p+click-Signin+Save": [(F, "Pass", Pw), (C, "Sign in", None), (C, "Save", None)],
        "u+p+signin+PlaceOrder": [(F, "User", U), (F, "Pass", Pw), (C, "Sign in", None),
                                  (C, "Place order", None)],
        "u+p+signin+hindi-delete": [(F, "User", U), (F, "Pass", Pw), (C, "Sign in", None),
                                    (C, "\u0939\u091f\u093e\u090f\u0902", None)],
        "p+literal-fill": [(F, "Pass", Pw), (F, "Note", "hello")],
        "mixed-ph-literal": [(F, "Pass", Pw + "hunter2")],
        "undeclared-ph": [(F, "Pass", "{{SECRET:NOPE}}"), (C, "Sign in", None)],
        "p+select": [(F, "Pass", Pw), (A.SELECT, "Country", "IN")],
        "p+upload": [(F, "Pass", Pw), (A.UPLOAD, "File", "x.txt")],
        "p+nav-query": [(F, "Pass", Pw), (A.NAVIGATE, "https://app.test/home?action=buy&id=1", None)],
        "nav-query-then-p": [(A.NAVIGATE, "https://app.test/home?a=1", None), (F, "Pass", Pw)],
        "p+nav-placeholder": [(F, "Pass", Pw), (A.NAVIGATE, "https://app.test/?t=" + Pw, None)],
        "2fills+2submits+Next": [(F, "Pass", Pw), (F, "Pass2", Pw), (C, "Sign in", None),
                                 (C, "Next", None)],
        "p+enter+enter": [(F, "Pass", Pw), (K, "Pass", "Enter"), (K, "Pass", "Enter")],
        "p+enter+click-Home": [(F, "Pass", Pw), (K, "Pass", "Enter"), (C, "Home", None)],
        "p+hover+click": [(F, "Pass", Pw), (A.HOVER, "Menu", None), (C, "Sign in", None)],
        "p+empty-click": [(F, "Pass", Pw), (C, "", None)],
        "p+click-canary-literal": [(F, "Pass", Pw), (C, PW, None)],
    }
    return [(pol, n, s, lg) for pol in L.POLICIES for n, s in seqs.items() for lg in (True, False)]


def one_composed(pol, name, seq, login):
    steps = [L.Step(order=n + 1, action=a, target=t, value=v) for n, (a, t, v) in enumerate(seq)]
    env = L.make_env(pol, [steps], login_index=0 if login else None)
    row = finish(env, steps, login, f"{pol.value}|COMPOSED:{name}|{'login' if login else 'plain'}",
                 pol, "composed", name, "", "composed", False)
    row["steps"] = [[s.action.value, lab(s.target), lab(s.value)] for s in steps]
    return row


def main():
    t0 = time.perf_counter()
    specs = build_specs()
    out_rows, rejected = [], {}
    for i, spec in enumerate(specs):
        if i % NSHARD != SHARD:
            continue
        res = one(*spec)
        if isinstance(res, str):
            rejected[res] = rejected.get(res, 0) + 1
        else:
            out_rows.append(res)
    if SHARD == 0:
        out_rows += [one_composed(*c) for c in composed_specs()]
    L.dump(OUT, {"copy": COPY, "shard": SHARD, "nshard": NSHARD, "specs_total": len(specs),
                 "rejected": rejected, "wall_s": round(time.perf_counter() - t0, 1), "rows": out_rows})
    print("rows", len(out_rows), "rejected", rejected, "wall", round(time.perf_counter() - t0, 1))


main()
