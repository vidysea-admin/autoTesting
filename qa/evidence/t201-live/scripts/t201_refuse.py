import pathlib, json
from playwright.sync_api import sync_playwright
B="http://127.0.0.1:59025"; EV=pathlib.Path("qa/evidence/t201-live")
q=pathlib.Path(".work/t201-root/.work/run_queue.json"); runs=pathlib.Path(".work/t201-root/projects/livefix/runs")
before=(q.exists() and q.read_text(), sorted(p.name for p in runs.glob("*")) if runs.exists() else [])
with sync_playwright() as p:
    br=p.chromium.launch(headless=True); c=br.new_context(viewport={"width":1200,"height":700}); pg=c.new_page()
    pg.goto(B+"/auth/login"); pg.fill("input[name=email]","dev@live.test"); pg.fill("input[name=password]","correct-horse-battery"); pg.click("button[type=submit]"); pg.wait_for_load_state()
    pg.goto(B+"/projects/livefix"); pg.click("form[action='/projects/livefix/test'] button"); pg.wait_for_load_state()
    pg.screenshot(path=str(EV/"00-TT6-refused-no-approval.png")); print(pg.inner_text("main")[:400])
after=(q.exists() and q.read_text(), sorted(p.name for p in runs.glob("*")) if runs.exists() else [])
print("queue/run dirs unchanged:", before==after, after[1])
