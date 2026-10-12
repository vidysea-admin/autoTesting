"""S1 extra composed login-case sequences probing the credential-pending credit. Run under a copy's venv:
<copy>/.venv/Scripts/python -I s1_extra.py <copy-root> <out.json>"""
import json, shutil, sys
sys.path.insert(0, "D:/autoTesting/qa/evidence/t179a-lead-tester-core-r1-B")
import probe_lib as L
print("COPY", L.confirm_copy(sys.argv[1]))
A = L.Action; F, C, K, N = A.FILL, A.CLICK, A.PRESS_KEY, A.NAVIGATE
Pw, U = "{{SECRET:APP_PASS}}", "{{SECRET:APP_USER}}"
seqs = {
 "ws-fill+PlaceOrder": [(F, "Note", "   "), (C, "Place order", None)],
 "tab-fill+PlaceOrder": [(F, "Note", "\t"), (C, "Place order", None)],
 "nl-fill+PlaceOrder": [(F, "Note", "\n"), (C, "Place order", None)],
 "empty-fill+PlaceOrder": [(F, "Note", ""), (C, "Place order", None)],
 "None-fill+PlaceOrder": [(F, "Note", None), (C, "Place order", None)],
 "padded-ph+PlaceOrder": [(F, "Pass", Pw + " "), (C, "Place order", None)],
 "ws-fill+Enter": [(F, "Note", "   "), (K, "Note", "Enter")],
 "enter-alone": [(K, "Pass", "Enter")],
 "click-alone-PlaceOrder": [(C, "Place order", None)],
 "p+nav-away+PlaceOrder": [(F, "Pass", Pw), (N, "https://app.test/other", None), (C, "Place order", None)],
 "p+Save+PlaceOrder(1 fill)": [(F, "Pass", Pw), (C, "Save", None), (C, "Place order", None)],
 "u+p+Save+PlaceOrder": [(F, "User", U), (F, "Pass", Pw), (C, "Save", None), (C, "Place order", None)],
 "p+Enter+PlaceOrder(1 fill)": [(F, "Pass", Pw), (K, "Pass", "Enter"), (C, "Place order", None)],
 "p+click-empty-name": [(F, "Pass", Pw), (C, "", None)],
 "p+click-ws-name": [(F, "Pass", Pw), (C, "   ", None)],
 "p+click-Pay": [(F, "Pass", Pw), (C, "Pay", None)],
}
rows = []
for pol in L.POLICIES:
    for name, seq in seqs.items():
        for login in (True, False):
            steps = [L.Step(order=i + 1, action=a, target=t, value=v) for i, (a, t, v) in enumerate(seq)]
            env = L.make_env(pol, [steps], login_index=0 if login else None)
            r = L.run_case_row(env)
            rows.append({"policy": pol.value, "name": name, "login": login, "executed": r["executed"],
                         "refusal": r["refusal"], "summary": (r["summary"] or "")[:100], "raised": r["raised"],
                         "sessions": r["sessions"]})
            shutil.rmtree(env.root, ignore_errors=True)
L.dump(sys.argv[2], {"rows": rows})
print(len(rows))
