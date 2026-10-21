import hashlib, json, os, re, sys
from playwright.sync_api import sync_playwright

B = "http://localhost:8791"
EV = r"D:\autoTesting\.worktrees\bench-inputs-ui\qa\evidence\bench-inputs-ui-B"
TMPD = r"D:\autoTesting\.work\tmp\bi-chkB"
os.makedirs(EV, exist_ok=True)
GOODF = os.path.join(TMPD, "list-good.json")
BADF = os.path.join(TMPD, "list-bad.json")
open(GOODF, "w").write(json.dumps({"items": [{"id": "B1", "priority": "P0", "technique": "inbox"}, {"id": "B2", "priority": "P2", "technique": "state_after"}]}))
open(BADF, "w").write('{"items": [{"id": "B1", "priority": "P7", "technique": "x", "text": "SECRET-TEXT"}]}')
rep = {"console": [], "requests": [], "steps": []}
NL = chr(10)


def flat(s):
    return s.replace(NL, " | ")


def step(name, ok, detail=""):
    rep["steps"].append({"step": name, "ok": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name, detail, flush=True)


def table_text(page):
    return page.locator("table", has_text="Ruling").inner_text().lower()


with sync_playwright() as p:
    br = p.chromium.launch(headless=True)

    def ctx():
        c = br.new_context(viewport={"width": 1200, "height": 900})
        pg = c.new_page()
        pg.on("console", lambda m: rep["console"].append((m.type, m.text, pg.url)) if m.type in ("error", "warning") else None)
        pg.on("pageerror", lambda e: rep["console"].append(("pageerror", str(e), pg.url)))
        pg.on("request", lambda r: rep["requests"].append(r.url))
        return c, pg

    def login(pg, email):
        pg.goto(B + "/auth/login")
        pg.get_by_label("Email").fill(email)
        pg.get_by_label("Password").fill("correct-horse-battery")
        pg.get_by_role("button", name="Sign in").click()
        pg.wait_for_load_state()

    c, pg = ctx()
    login(pg, "editor@chk.test")
    pg.goto(B + "/projects/demo")
    pg.get_by_role("link", name="Benchmark inputs").first.click()
    pg.wait_for_load_state()
    step("project page button -> bench page", pg.url.endswith("/projects/demo/bench"), pg.url)
    pg.goto(B + "/projects/demo")
    side = pg.locator("a.sidebar-sub", has_text="Benchmark inputs")
    step("sidebar sub-link present on open project", side.count() == 1)
    side.click()
    pg.wait_for_load_state()
    step("sidebar link navigates", pg.url.endswith("/projects/demo/bench"), pg.url)
    pg.screenshot(path=os.path.join(EV, "bench-page-editor-initial.png"), full_page=True)

    pg.goto(B + "/projects/demo/crawls/crawl_1")
    t = table_text(pg)
    step("crawl: earlier-marked first finding persisted (false positive)", "false positive" in t and "undo mark" in t, flat(t)[:200])
    while pg.get_by_role("button", name="Undo mark").count():
        pg.get_by_role("button", name="Undo mark").first.click()
        pg.wait_for_load_state()
    t = table_text(pg)
    step("crawl: undo all -> both unadjudicated", t.count("unadjudicated") == 2 and pg.get_by_role("button", name="Mark real bug").count() == 2)
    pg.get_by_role("button", name="Mark false positive").first.click()
    pg.wait_for_load_state()
    t = table_text(pg)
    step("crawl: first false positive, other stays unadjudicated", t.count("false positive") >= 1 and t.count("unadjudicated") == 1, flat(t)[:300])
    pg.screenshot(path=os.path.join(EV, "crawl-after-mark.png"), full_page=True)
    pg.get_by_role("button", name="Mark real bug").first.click()
    pg.wait_for_load_state()
    t = table_text(pg)
    step("crawl: second marked real bug", "real bug" in t and pg.get_by_role("button", name="Undo mark").count() == 2 and "unadjudicated" not in t, flat(t)[:300])
    pg.get_by_role("button", name="Undo mark").first.click()
    pg.wait_for_load_state()
    t = table_text(pg)
    step("crawl: undo returns first to unadjudicated", t.count("unadjudicated") == 1 and pg.get_by_role("button", name="Undo mark").count() == 1, flat(t)[:300])
    pg.get_by_role("button", name="Mark false positive").first.click()
    pg.wait_for_load_state()
    step("crawl: re-marked", pg.get_by_role("button", name="Undo mark").count() == 2)

    pg.goto(B + "/projects/demo/runs/run_1")
    while pg.get_by_role("button", name="Undo mark").count():
        pg.get_by_role("button", name="Undo mark").first.click()
        pg.wait_for_load_state()
    t = table_text(pg)
    step("run: boom finding with controls", "boom" in t and pg.get_by_role("button", name="Mark real bug").count() == 1, flat(t)[:200])
    pg.get_by_role("button", name="Mark false positive").click()
    pg.wait_for_load_state()
    step("run: marked, redirected back to run page", pg.url.endswith("/projects/demo/runs/run_1") and "undo mark" in table_text(pg), pg.url)
    pg.screenshot(path=os.path.join(EV, "run-after-mark.png"), full_page=True)

    pg.goto(B + "/projects/demo/bench")
    body = pg.inner_text("main")
    step("bench summary counts", "ruled real bugs" in body, flat(body)[:250].encode("ascii", "replace").decode())
    lab = pg.get_by_label("Atomic answer list (JSON file)")
    step("file input has visible label", lab.count() == 1)
    lab.set_input_files(BADF)
    pg.get_by_role("button", name="Upload and pin").click()
    pg.wait_for_load_state()
    bt = pg.inner_text("body")
    step("bad upload refused, no echo of content", "SECRET-TEXT" not in bt and "not a valid" in bt, flat(bt)[:200])
    pg.screenshot(path=os.path.join(EV, "bad-upload.png"))
    pg.goto(B + "/projects/demo/bench")
    pg.get_by_label("Atomic answer list (JSON file)").set_input_files(GOODF)
    pg.get_by_role("button", name="Upload and pin").focus()
    pg.keyboard.press("Enter")
    pg.wait_for_load_state()
    body = pg.inner_text("main")
    sha = hashlib.sha256(open(GOODF, "rb").read()).hexdigest()
    step("good upload via keyboard Enter: sha shown, ids not shown", sha in body and "B1" not in body and "B2" not in body, flat(body)[:300].encode("ascii", "replace").decode())
    pg.screenshot(path=os.path.join(EV, "bench-page-after-upload.png"), full_page=True)
    step("no link to the list on the page", pg.locator("a[href*='atomic-list']").count() == 0)

    c2, v = ctx()
    login(v, "viewer@chk.test")
    v.goto(B + "/projects/demo/crawls/crawl_1")
    vt = table_text(v)
    step("viewer crawl: read-only, no buttons", "read-only" in vt and v.get_by_role("button", name=re.compile("Mark|Undo")).count() == 0, flat(vt)[:250])
    v.goto(B + "/projects/demo/bench")
    vb = v.inner_text("main")
    step("viewer bench: sees pin, no upload control", sha in vb and v.get_by_label("Atomic answer list (JSON file)").count() == 0 and "needs permission" in vb)
    v.screenshot(path=os.path.join(EV, "bench-page-viewer.png"), full_page=True)
    js = "async () => { const r = await fetch('/projects/demo/bench/marks', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body:'finding=a4e6f0a7af79d444&verdict=clear'}); return r.status }"
    step("viewer browser fetch POST marks -> 403", v.evaluate(js) == 403)
    br.close()

ext = sorted({u for u in rep["requests"] if not u.startswith(B) and not u.startswith("data:")})
step("no external requests", not ext, str(ext))
errs = [c for c in rep["console"] if c[0] in ("error", "pageerror")]
rep["console_error_count"] = len(errs)
print("console errors:", errs)
json.dump(rep, open(os.path.join(EV, "report.json"), "w"), indent=1)
print("steps ok:", sum(s["ok"] for s in rep["steps"]), "/", len(rep["steps"]))
