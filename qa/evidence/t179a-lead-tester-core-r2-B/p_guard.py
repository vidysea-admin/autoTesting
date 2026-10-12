"""Checker B: write_policy_refusal decision table. Run under a copy; prints JSON. Offline, no browser."""
import sys, json, itertools
root = sys.argv[1]
sys.path[:0] = [root + "/src", root + "/tests"]
import autotester
assert autotester.__file__.startswith(root.replace("/", "\\")) or root in autotester.__file__.replace("\\", "/"), autotester.__file__
from autotester.agents import guards
from autotester.browser.session import NavigationRefused, check_destination
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, WritePolicy
from autotester.schema.flowspec import Step
from autotester.schema.project import Project, SecretRef

def proj(policy, login=None):
    return Project(slug="demo", name="Demo", base_url="https://app.test", allowed_domains=["app.test"],
                   write_policy=policy, login_case_id=login, secrets=[SecretRef(key="APP_PASS", domains=["app.test"])])

def case(steps, cid="c1"):
    c = Case(project="demo", flow_id="f", kind=CaseKind.BEST, case_class=CaseClass.HAPPY, title="t", steps=steps)
    return c

T = ["https://app.test/x", "http://app.test/x", "https://sub.app.test/x", "https://APP.TEST/x", "https://app.test./x", "https://app.test:8443/x",
     "//app.test/x", "//evil.test/x", "https://evil.test/x", "https://app.test.evil.test/x", "https://evilapp.test/x", "https://user@app.test/x",
     "https://app.test" + chr(92) + "@evil.test/x", "https://app.test" + chr(92) + "x", "ftp://app.test/", "ws://app.test/", "wss://app.test/", "javascript:alert(1)", "data:text/html,hi", "file:///etc/passwd",
     "about:blank", "/dashboard", "dashboard", "the pricing page", "", " ", "https://[::1]/x", "https://127.0.0.1/x", "https://аpp.test/x", "https://app.test/x?next=https://evil.test",
     "https://app.test/delete-account", "https://app.test/x#logout", "https://app.test/x?a=1",
     "https://{{SECRET:HOST}}/x", "https://app.test/{{SECRET:APP_PASS}}", "https://evil.test/{{SECRET:APP_PASS}}", "{{SECRET:HOST}}", "https://app.test/?p={{SECRET:APP_PASS}}", "https://evil.test/?p={{SECRET:APP_PASS}}"]
ctrl = ["\t", "\r", "\n", "\x00", "\x7f", "\x0b", "\x0c", "\x1f", " ", " ", "​"]
for c in ctrl:
    T += [f"{c}https://app.test/x", f"https://app.test/x{c}", f"https://app{c}.test/x", f"https://app.test/{c}x", f"htt{c}ps://app.test/x", f"{c}//evil.test/x"]
T = list(dict.fromkeys(T))
out = {}
for pol in WritePolicy:
    for t in T:
        p = proj(pol)
        r = guards.write_policy_refusal(case([Step(order=1, action=Action.NAVIGATE, target=t)]), p)
        out[f"{pol.value}|NAV|{t!r}"] = [r[0].value, r[1]] if r else None
        # seam oracle
        try:
            check_destination(p, t); o = None
        except NavigationRefused:
            o = "refused"
        out[f"{pol.value}|ORACLE|{t!r}"] = o
# READ_ONLY step matrix incl. login carve-out
vals = [None, "", "  ", "\t", "{{SECRET:APP_PASS}}", " {{SECRET:APP_PASS}} ", "{{SECRET:OTHER}}", "{{SECRET:APP_PASS}}x", "x{{SECRET:APP_PASS}}", "{{SECRET:APP_PASS}}{{SECRET:APP_PASS}}", "hello", "Enter", "Tab"]
tg = ["Email", "Sign in", "Delete account", "Submit", "Log out", "x", "https://app.test/a", "#id"]
for pol in WritePolicy:
    for login in (False, True):
        for a in Action:
            for v in vals:
                for t in tg:
                    cs = case([Step(order=1, action=Action.FILL, target="Email", value="{{SECRET:APP_PASS}}"),
                               Step(order=2, action=a, target=t, value=v)])
                    p = proj(pol, login=cs.id if login else None)
                    r = guards.write_policy_refusal(cs, p)
                    out[f"{pol.value}|login={login}|{a.value}|{v!r}|{t!r}"] = [r[0].value, r[1]] if r else None
                    cs2 = case([Step(order=1, action=a, target=t, value=v), Step(order=2, action=Action.CLICK, target="Sign in")])
                    p2 = proj(pol, login=cs2.id if login else None)
                    r2 = guards.write_policy_refusal(cs2, p2)
                    out[f"{pol.value}|login={login}|first|{a.value}|{v!r}|{t!r}"] = [r2[0].value, r2[1]] if r2 else None
json.dump(out, open(sys.argv[2], "w"), indent=0, sort_keys=True)
print(len(out), "rows")
