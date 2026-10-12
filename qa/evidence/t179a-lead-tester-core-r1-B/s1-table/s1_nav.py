"""S1(b) NAVIGATE probe. Run under a copy's venv:
  <copy>/.venv/Scripts/python -I s1_nav.py <copy-root> <out.json> <targets.json>
targets.json = list of target strings (from the diff). Also runs the fixed placeholder targets.
Per (policy, target): head/base dispatch (single-step NAVIGATE case) AND the REAL BrowserSession.goto
from THIS copy (L.goto_would_refuse) under three secret modes."""
from __future__ import annotations

import json
import shutil
import sys

sys.path.insert(0, "D:/autoTesting/qa/evidence/t179a-lead-tester-core-r1-B")
import probe_lib as L  # noqa: E402

COPY, OUT, TJ = sys.argv[1], sys.argv[2], sys.argv[3]
print("COPY", L.confirm_copy(COPY))
A = L.Action


def goto_would_refuse(project, secrets, url):
    """L.goto_would_refuse equivalent: probe_lib's sets `s.page` (a read-only property on
    BrowserSession -> AttributeError); this sets `s._page`. Same REAL BrowserSession.goto."""
    from autotester.browser.session import BrowserSession

    class Page:
        url = "about:blank"

        def goto(self, real, **kw):
            self.url = real

    s = object.__new__(BrowserSession)
    s.project, s.secrets, s._page, s.budget = project, secrets, Page(), None
    s._record = lambda *a, **k: None
    try:
        s.goto(url)
    except Exception as e:  # noqa: BLE001
        return type(e).__name__
    return None


FIXED = [
    "https://{{SECRET:APP_PASS}}/", "//{{SECRET:APP_USER}}/x", "{{SECRET:APP_PASS}}",
    "{{SECRET:APP_USER}}", "https://{{SECRET:APP_USER}}", "https://app.test/{{SECRET:APP_PASS}}",
    "https://app.test/?t={{SECRET:APP_PASS}}", "https://{{SECRET:NOPE}}/", "{{SECRET:NOPE}}",
    "https://app.test/home", "https://evil.test/", "javascript:alert(1)", "/reports",
    "Admin portal URL", "", "   ", "home",
]
targets = list(dict.fromkeys(FIXED + json.load(open(TJ))))
MODES = {
    "canary": dict(declared=("APP_PASS", "APP_USER"), values=dict(L.CANARY)),
    "hostvals": dict(declared=("APP_PASS", "APP_USER"),
                     values={"APP_PASS": "app.test", "APP_USER": "https://app.test/login"}),
    "undeclared": dict(declared=(), values=dict(L.CANARY)),
}
rows = []
for pol in L.POLICIES:
    for t in targets:
        try:
            steps = [L.Step(order=1, action=A.NAVIGATE, target=t, value=None)]
        except Exception as e:  # noqa: BLE001
            rows.append({"policy": pol.value, "target": L.label(t), "step_rejected": type(e).__name__})
            continue
        row = {"policy": pol.value, "target": L.label(t)[:80], "dispatch": {}, "goto": {}}
        for mode, m in MODES.items():
            env = L.make_env(pol, [steps], declared=m["declared"], secret_values=m["values"])
            r = L.run_case_row(env)
            row["dispatch"][mode] = {"executed": r["executed"], "refusal": r["refusal"],
                                     "raised": r["raised"], "summary": (r["summary"] or "")[:90]}
            # real goto from this copy with a fake page: would the SESSION refuse it?
            proj = L.make_project(pol, None, m["declared"])
            row["goto"][mode] = goto_would_refuse(proj, L.SecretStore(proj, dict(m["values"])), t)
            shutil.rmtree(env.root, ignore_errors=True)
        rows.append(row)
L.dump(OUT, {"copy": COPY, "rows": rows})
print("rows", len(rows))
