import hashlib, json, os
from playwright.sync_api import sync_playwright
B = "http://localhost:8791"; EV = r"D:\autoTesting\.worktrees\bench-inputs-ui\qa\evidence\bench-inputs-ui-B\browser-cycle1"
TM = r"D:\autoTesting\.work\tmp\bi-chkB2"
good = os.path.join(TM, "list-good2.json"); bad = os.path.join(TM, "list-bad2.json"); exe = os.path.join(TM, "list.exe")
open(good, "w").write(json.dumps({"items": [{"id": "Q1", "priority": "P0", "technique": "inbox"}, {"id": "Q2", "priority": "P2", "technique": "state_after"}]}))
open(bad, "w").write('{"items": [{"id": "Q1", "priority": "P7", "technique": "x", "text": "SECRET-TEXT"}]}')
open(exe, "w").write(open(good).read())
res = []
with sync_playwright() as p:
    br = p.chromium.launch(headless=True); c = br.new_context(); pg = c.new_page()
    pg.goto(B + "/auth/login"); pg.get_by_label("Email").fill("editor@chk.test"); pg.get_by_label("Password").fill("correct-horse-battery")
    pg.get_by_role("button", name="Sign in").click(); pg.wait_for_load_state()
    pg.goto(B + "/projects/demo/bench")
    lab = pg.get_by_label("Atomic answer list (JSON file)")
    # .exe name: refused
    lab.set_input_files(exe)
    with pg.expect_navigation(): pg.get_by_role("button", name="Upload and pin").click()
    t = pg.inner_text("body"); res.append(("exe refused", "400" in t and "json" in t.lower(), t.replace("\n", " | ")[:160]))
    pg.goto(B + "/projects/demo/bench")
    pg.get_by_label("Atomic answer list (JSON file)").set_input_files(good)
    pg.get_by_role("button", name="Upload and pin").focus()
    with pg.expect_navigation(): pg.keyboard.press("Enter")
    body = pg.inner_text("main"); sha = hashlib.sha256(open(good, "rb").read()).hexdigest()
    res.append(("good upload via keyboard Enter: sha shown, ids not shown", sha in body.lower() and "Q1" not in body and "Q2" not in body, pg.url))
    pg.screenshot(path=os.path.join(EV, "good-upload-waited.png"), full_page=True)
    br.close()
for r in res: print(r)
