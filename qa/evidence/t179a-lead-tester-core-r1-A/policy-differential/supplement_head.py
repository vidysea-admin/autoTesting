"""HEAD only: call guards._destination(target, project) directly and compare with the act-time
path (resolve_for_navigation + check_destination) for placeholder-bearing and other URLs."""
import os

os.environ.setdefault("AUTOTESTER_APPROVAL_KEY", "fake-differential-key-0000")
import autotester
from autotester.agents import guards
from autotester.browser.secrets import SecretStore
from autotester.browser.session import check_destination
from autotester.core.redact import PLACEHOLDER_RE
from autotester.schema.project import Project, SecretRef

print("autotester.__file__ =", autotester.__file__)
vals = {"APP_PASS": "CANARY-pw-7f3a9c", "BASE": "https://app.example.test", "HOST": "app.example.test",
        "LOGINURL": "https://app.example.test/login", "PORT": "8443", "SUB": "api"}
refs = [SecretRef(key=k, domains=["app.example.test"]) for k in vals]
p = Project(slug="demo", name="d", base_url="https://app.example.test",
            allowed_domains=["app.example.test", "other.example.test"], secrets=refs)
ss = SecretStore(p, dict(vals))
targets = [
    "{{SECRET:BASE}}/x", "{{SECRET:BASE}}", "{{SECRET:LOGINURL}}", "{{SECRET:HOST}}/x",
    "https://{{SECRET:HOST}}/x", "https://{{SECRET:HOST}}", "//{{SECRET:HOST}}/x",
    "https://{{SECRET:HOST}}:8443/x", "https://{{SECRET:SUB}}.app.example.test/x",
    "https://{{SECRET:SUB}}.{{SECRET:HOST}}/x", "https://app.example.test:{{SECRET:PORT}}/x",
    "https://app.example.test/{{SECRET:APP_PASS}}", "http{{SECRET:PORT}}://app.example.test/x",
    "https://app.example.test/x\n", "https://app.example.test/x\r\n", "https://app.example.test/x\t",
    "https://app.example.test/x ", "{{SECRET:NOSUCH}}/x", "/reports", "/home", "Admin portal URL",
    "reports", "app.example.test/x",
]
print("target | HEAD guard._destination | act-time (resolve_for_navigation+check_destination)")
for t in targets:
    why, _ = guards._destination(t, p)
    g = "REFUSE" if why else "ACCEPT"
    try:
        real = ss.resolve_for_navigation(t) if PLACEHOLDER_RE.search(t) else t
        a = "ACCEPT host=" + check_destination(p, real)
    except Exception as exc:
        a = "REFUSE " + type(exc).__name__
    flag = ""
    if g == "REFUSE" and a.startswith("ACCEPT"):
        flag = "   <== NARROWS (guard refuses, act-time accepts)"
    elif g == "ACCEPT" and a.startswith("REFUSE"):
        flag = "   (guard accepts, act-time refuses: harmless)"
    print(f"{t!r} | {g} | {a}{flag}")
