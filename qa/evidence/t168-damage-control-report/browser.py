import json, re, sys
from playwright.sync_api import sync_playwright
EV = r"D:\autoTesting\qa\evidence\browser-t168-2026-10-11-checker"
B = "http://127.0.0.1:8765"
rep = {"pages": []}
with sync_playwright() as p:
    br = p.chromium.launch(headless=True)
    ctx = br.new_context(viewport={"width": 1280, "height": 900}); pg = ctx.new_page()
    errs = []; dialogs = []
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errs.append("pageerror:" + str(e)))
    pg.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
    # path: project list -> project page -> button
    pg.goto(B + "/"); pg.screenshot(path=EV + r"\01-project-list.png")
    pg.goto(B + "/projects/demo"); pg.screenshot(path=EV + r"\02-project-page.png")
    btn = pg.get_by_role("link", name=re.compile("Damage-control report"))
    rep["button_count"] = btn.count()
    btn.click(); pg.wait_for_load_state()
    rep["after_click_url"] = pg.url
    pg.screenshot(path=EV + r"\03-demo-report.png", full_page=True)
    txt = pg.inner_text("body")
    rep["demo"] = {
      "xss_flag": pg.evaluate("window.__xss"), "dialogs": dialogs[:], "scripts_in_dom": pg.evaluate("document.querySelectorAll('script').length"),
      "img_onerror_in_dom": pg.evaluate("document.querySelectorAll('img').length"),
      "sections": pg.evaluate("[...document.querySelectorAll('section')].map(s=>s.id)"),
      "xss_text_visible_literally": "<script>window.__xss=1</script>" in txt,
      "has_baseline_rel0": "rel0" in txt, "has_regressed": "Regressed" in txt, "c1_regressed_listed": bool(re.search(r"Regressed[^\n]*c1", txt)),
      "unavailable_count": txt.count("Unavailable"), "not_run_present": "not run" in txt,
      "incomplete_banner": "Incomplete: this crawl" in txt, "not_visited": "not_visited" in txt,
      "plain_secret_in_text": "Zq9-plainChecker7" in txt,
      "hscroll_1280": pg.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth"),
    }
    # explicit run query
    pg.goto(B + "/projects/demo/damage-report?run=rel0"); t0 = pg.inner_text("body")
    rep["demo_rel0"] = {"no_baseline_banner": "No trusted baseline" in t0, "url_ok": True}
    pg.screenshot(path=EV + r"\04-demo-rel0.png", full_page=True)
    # no baseline project
    pg.goto(B + "/projects/nobase"); pg.get_by_role("link", name=re.compile("Damage-control report")).click(); pg.wait_for_load_state()
    t1 = pg.inner_text("body"); pg.screenshot(path=EV + r"\05-nobase-report.png", full_page=True)
    rep["nobase"] = {"no_claim_banner": "No trusted baseline, so no regression claim" in t1, "regressed_word": "Regressed" in t1, "fixed_word": "Fixed:" in t1}
    # empty project
    pg.goto(B + "/projects/empty"); pg.get_by_role("link", name=re.compile("Damage-control report")).click(); pg.wait_for_load_state()
    t2 = pg.inner_text("body"); pg.screenshot(path=EV + r"\06-empty-state.png", full_page=True)
    rep["empty"] = {"empty_state": "no runs" in t2.lower(), "pass_word": "PASS" in t2, "sections": pg.evaluate("document.querySelectorAll('section').length")}
    # bad ids
    r = pg.goto(B + "/projects/demo/damage-report?run=../../etc"); rep["bad_run_status"] = r.status
    r = pg.goto(B + "/projects/nope/damage-report"); rep["bad_project_status"] = r.status
    # phone width
    ctx2 = br.new_context(viewport={"width": 390, "height": 800}); p2 = ctx2.new_page(); p2.goto(B + "/projects/demo/damage-report")
    rep["hscroll_390"] = p2.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
    p2.screenshot(path=EV + r"\07-demo-390.png", full_page=True)
    rep["console_errors"] = errs
    br.close()
json.dump(rep, open(EV + r"\report.json", "w"), indent=1)
print(json.dumps(rep, indent=1))
