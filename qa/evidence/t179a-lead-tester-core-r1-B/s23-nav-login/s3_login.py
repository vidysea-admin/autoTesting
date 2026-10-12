"""Section 3: login carve-out abuse rows through dispatch under READ_ONLY. <python> -I s3_login.py <copy> <out>"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import probe_lib as L  # noqa: E402
L.confirm_copy(sys.argv[1])
from autotester.schema.enums import Action as A, WritePolicy  # noqa: E402

U, P_, NOPE = "{{SECRET:APP_USER}}", "{{SECRET:APP_PASS}}", "{{SECRET:NOPE}}"
N = lambda t="https://app.test/login": (A.NAVIGATE, t, None)
fu = (A.FILL, "Email", U); fp = (A.FILL, "Password", P_)
ck = lambda n="Sign in": (A.CLICK, n, None)
en = (A.PRESS_KEY, "", "Enter")
ROWS = {
 "legit: nav,user,pass,Sign in": [N(), fu, fp, ck()],
 "legit: nav,pass,Enter": [N(), fp, en],
 "legit: pass,Enter(value None)": [fp, (A.PRESS_KEY, "", None)],
 "legit: login nav with query": [N("https://app.test/login?next=%2Fhome"), fu, fp, ck()],
 "submit before any fill": [N(), ck(), fu, fp],
 "submit with no fills": [N(), ck()],
 "enter with no fills": [N(), en],
 "fill then two submits": [fp, ck(), ck("Place order")],
 "fill,Enter,Enter": [fp, en, en],
 "fill,click,Enter": [fp, ck(), en],
 "fill-submit-fill-submit (two logins)": [fu, ck(), fp, ck("Continue")],
 "fill-submit-fill-submit-submit": [fu, ck(), fp, ck("Continue"), ck("Place order")],
 "two fills then two clicks": [fu, fp, ck(), ck("Place order")],
 "literal mixed with placeholder": [(A.FILL, "Email", "x" + U), ck()],
 "placeholder with trailing text": [(A.FILL, "Pass", P_ + " extra"), ck()],
 "placeholder with trailing space": [(A.FILL, "Pass", P_ + " "), ck()],
 "undeclared key": [(A.FILL, "Pass", NOPE), ck()],
 "literal value": [(A.FILL, "Email", "eve@x.test"), ck()],
 "fill value empty": [(A.FILL, "Pass", ""), ck()],
 "fill value None": [(A.FILL, "Pass", None), ck()],
 "fill value whitespace then Place order": [(A.FILL, "x", "   "), ck("Place order")],
 "fill value tab then Save": [(A.FILL, "x", "\t"), ck("Save")],
 "two blank fills then two clicks": [(A.FILL, "x", " "), ck("Save"), (A.FILL, "x", " "), ck("Place order")],
 "blank fill, Enter": [(A.FILL, "x", " "), en],
 "fill then Delete key": [fp, (A.PRESS_KEY, "", "Delete")],
 "fill then Tab": [fp, (A.PRESS_KEY, "", "Tab")],
 "fill then Delete account click": [fp, ck("Delete account")],
 "fill then Logout click": [fp, ck("Logout")],
 "fill then Place order click (name-tell-free)": [fp, ck("Place order")],
 "fill then Save click": [fp, ck("Save")],
 "fill then empty-name click": [fp, ck("")],
 "fill then whitespace-name click": [fp, ck("   ")],
 "after login: click Save": [fu, fp, ck(), ck("Save")],
 "after login: fill literal": [fu, fp, ck(), (A.FILL, "Name", "Eve")],
 "after login: navigate with query": [fu, fp, ck(), N("https://app.test/orders?confirm=1")],
 "after login: navigate /account/delete": [fu, fp, ck(), N("https://app.test/account/delete")],
 "after login: select": [fu, fp, ck(), (A.SELECT, "Plan", "pro")],
 "after login: upload": [fu, fp, ck(), (A.UPLOAD, "File", "x.txt")],
 "mutating click BEFORE login fills": [ck("Save"), fu, fp, ck()],
 "literal fill BEFORE login fills": [(A.FILL, "Name", "Eve"), fu, fp, ck()],
 "credential then off-domain navigate": [fp, ck(), N("https://evil.test/")],
 "login nav query to off-domain target": [N("https://app.test/login?next=https://evil.test/"), fu, fp, ck()],
 "login nav query confirm=1": [N("https://app.test/login?confirm=1&action=buy"), fu, fp, ck()],
 "login nav to /account/delete": [N("https://app.test/account/delete"), fu, fp, ck()],
 "login nav to javascript:": [N("javascript:alert(1)"), fu, fp, ck()],
 "login nav with placeholder": [N("{{SECRET:APP_PASS}}"), fu, fp, ck()],
 "SELECT with placeholder": [(A.SELECT, "Pass", P_), ck()],
 "UPLOAD with placeholder": [(A.UPLOAD, "Pass", P_), ck()],
 "hover between fill and submit": [fp, (A.HOVER, "x", None), ck()],
 "wait between fill and submit": [fp, (A.WAIT, "1", None), ck()],
 "many fills then one submit": [fu, fp, fu, fp, ck()],
 "many fills then two submits": [fu, fp, fu, fp, ck(), ck("Place order")],
 "click target equals canary literal": [fp, ck(L.CANARY["APP_PASS"])],
 "fill value is canary literal": [(A.FILL, "Pass", L.CANARY["APP_PASS"]), ck()],
 "scroll/back/hover/wait/assert only": [(A.SCROLL, "", None), (A.BACK, "", None), (A.HOVER, "x", None), (A.WAIT, "1", None), (A.ASSERT, "t", None)],
 "unknown submit-by-key: Control+Enter": [fp, (A.PRESS_KEY, "", "Control+Enter")],
 "Enter lowercase": [fp, (A.PRESS_KEY, "", "enter")],
 "Enter padded": [fp, (A.PRESS_KEY, "", " Enter ")],
 "steps order shuffled (order field): click order1 fill order2": None,
}
MODES = ["login", "other", "unset"]
rows = []
for name, spec in ROWS.items():
    if spec is None:
        continue
    for mode in MODES:
        steps = [L.step(i + 1, a, t, v) for i, (a, t, v) in enumerate(spec)]
        dummy = [L.step(1, A.WAIT, "dummy")]
        cases = [steps, dummy]
        li = {"login": 0, "other": 1, "unset": None}[mode]
        env = L.make_env(WritePolicy.READ_ONLY, cases, login_index=li)
        r = L.run_case_row(env, 0)
        rows.append({"row": name, "mode": mode, "steps": L.label(repr([(a.value, t, v) for a, t, v in spec])),
                     **{k: r[k] for k in ("executed", "refusal", "sessions", "run_case_calls", "n_files_written", "raised")}})
# shuffled order field row
steps = [L.step(2, A.FILL, "Pass", P_), L.step(1, A.CLICK, "Place order"), L.step(3, A.CLICK, "Sign in")]
for mode, li in (("login", 0), ("other", 1)):
    env = L.make_env(WritePolicy.READ_ONLY, [steps, [L.step(1, A.WAIT, "d")]], login_index=li)
    r = L.run_case_row(env, 0)
    rows.append({"row": "order field: click(1) fill(2) click(3)", "mode": mode, "steps": "order 2 fill pass; order 1 click Place order; order 3 click Sign in",
                 **{k: r[k] for k in ("executed", "refusal", "sessions", "run_case_calls", "n_files_written", "raised")}})
L.dump(sys.argv[2], rows)
print("rows", len(rows))
