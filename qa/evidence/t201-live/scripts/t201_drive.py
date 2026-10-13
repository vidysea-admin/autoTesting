import json, time, pathlib, re
from playwright.sync_api import sync_playwright
B = "http://127.0.0.1:59025"; EV = pathlib.Path("qa/evidence/t201-live"); EV.mkdir(parents=True, exist_ok=True)
PW = "correct-horse-battery"; log = []
def note(k, v): log.append((k, v)); print(k, "=>", v, flush=True)
with sync_playwright() as p:
    br = p.chromium.launch(headless=True)
    # S1 anonymous + cross-origin
    anon = br.new_context(); 
    r = anon.request.post(f"{B}/projects/livefix/test", max_redirects=0, headers={"Origin": B, "Accept": "text/html"})
    note("S1_anon_post", (r.status, r.headers.get("location")))
    ctx = br.new_context(viewport={"width": 1200, "height": 800}); pg = ctx.new_page()
    pg.goto(f"{B}/auth/login"); pg.fill("input[name=email]", "dev@live.test"); pg.fill("input[name=password]", PW)
    pg.click("button[type=submit]"); pg.wait_for_load_state()
    note("login_url", pg.url)
    r = ctx.request.post(f"{B}/projects/livefix/test", max_redirects=0, headers={"Origin": "http://evil.example"})
    note("S1_cross_origin_with_session", r.status)
    pg.goto(f"{B}/projects/livefix"); pg.screenshot(path=str(EV / "01-project-page-test-button.png"))
    note("button_visible", pg.locator("form[action='/projects/livefix/test'] button").count())
    t0 = time.perf_counter()
    with pg.expect_navigation():
        pg.click("form[action='/projects/livefix/test'] button")
    note("press_to_status_s", round(time.perf_counter() - t0, 2)); note("status_url", pg.url)
    note("press_body", pg.inner_text("body")[:300])
    if "/test/" not in pg.url: raise SystemExit("press did not reach a status page")
    entry_id = pg.url.rsplit("/", 1)[1]
    pg.screenshot(path=str(EV / "02-status-after-press.png"))
    # second press while active
    r2 = ctx.request.post(f"{B}/projects/livefix/test", max_redirects=0, headers={"Origin": B})
    note("S5_second_press", (r2.status, r2.headers.get("location")))
    seen = []; end = time.time() + 240
    while time.time() < end:
        pg.goto(pg.url.split("#")[0] if "/test/" in pg.url else f"{B}/projects/livefix/test/{entry_id}")
        txt = pg.inner_text("body"); 
        st = next((w for w in ("Position in the line", "The run is in progress", "Open the report", "stopped on an error", "A gate said no", "server stopped") if w in txt), "?")
        if not seen or seen[-1] != st:
            seen.append(st); pg.screenshot(path=str(EV / f"03-status-{len(seen)}-{re.sub('[^a-z]','',st.lower())[:12]}.png"))
        if st in ("Open the report", "stopped on an error", "A gate said no", "server stopped"): break
        time.sleep(1.5)
    note("status_sequence", seen); note("status_body", pg.inner_text("body")[:1500])
    link = pg.locator("a", has_text="Open the report")
    if link.count():
        link.first.click(); pg.wait_for_load_state(); note("report_url", pg.url)
        pg.screenshot(path=str(EV / "04-report.png"), full_page=True); note("report_body", pg.inner_text("body")[:2500])
    # inbox? and queue file
    br.close()
q = pathlib.Path(".work/t201-root/.work/run_queue.json"); note("queue_file", q.read_text()[:2000] if q.exists() else "missing")
json.dump(log, open(EV / "drive-log.json", "w"), indent=1, default=str)
