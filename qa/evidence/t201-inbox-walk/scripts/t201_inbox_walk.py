import json, time, pathlib
from playwright.sync_api import sync_playwright
B="http://127.0.0.1:59025"; EV=pathlib.Path("qa/evidence/t201-inbox-walk"); PW="correct-horse-battery"; log={}
def login(br,email):
    c=br.new_context(viewport={"width":1200,"height":800}); p=c.new_page()
    p.goto(f"{B}/auth/login"); p.fill("input[name=email]",email); p.fill("input[name=password]",PW)
    p.click("button[type=submit]"); p.wait_for_load_state(); return c,p
with sync_playwright() as pw:
    br=pw.chromium.launch(headless=True)
    a=br.new_context(); r=a.request.get(f"{B}/inbox",max_redirects=0,headers={"Accept":"text/html"}); log["anon_inbox"]=(r.status,r.headers.get("location"))
    c,p=login(br,"dev@live.test")
    p.goto(f"{B}/projects/livefix")
    with p.expect_navigation(): p.click("form[action='/projects/livefix/test'] button")
    log["status_url"]=p.url; url=p.url
    p.goto(f"{B}/inbox"); log["inbox_while_active"]=p.inner_text("body")[:600]; p.screenshot(path=str(EV/"01-dev-inbox-active.png"))
    end=time.time()+240
    while time.time()<end:
        p.goto(url); t=p.inner_text("body")
        if any(w in t for w in ("Open the report","stopped on an error","A gate said no","server stopped")): break
        time.sleep(2)
    p.goto(f"{B}/inbox"); log["dev_inbox_done"]=p.inner_text("body")[:800]; p.screenshot(path=str(EV/"02-dev-inbox-done.png"))
    link=p.locator("a[href*='/projects/livefix/']").first
    log["dev_links"]=[l.get_attribute("href") for l in p.locator("table a").all()]
    c2,p2=login(br,"tester@live.test")
    p2.goto(f"{B}/inbox"); log["tester_inbox"]=p2.inner_text("body")[:600]; p2.screenshot(path=str(EV/"03-tester-inbox.png"))
    rid=[h for h in log["dev_links"] if "/runs/" in h or "/test/" in h]
    for h in rid[:2]:
        r=c2.request.get(B+h,max_redirects=0); log["tester_direct_"+h]=r.status
    r=c2.request.get(f"{B}/projects/livefix/runs/run-doesnotexist00000000000000",max_redirects=0); log["tester_missing"]=r.status
    c3,p3=login(br,"admin@live.test"); p3.goto(f"{B}/inbox"); log["admin_inbox"]=p3.inner_text("body")[:600]; p3.screenshot(path=str(EV/"04-admin-inbox.png"))
    br.close()
json.dump(log,open(EV/"walk-log.json","w"),indent=1,default=str)
for k,v in log.items(): print(k,"=>",v)
