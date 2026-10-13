import json, os, socket, subprocess, sys, time, re, urllib.request, pathlib
from playwright.sync_api import sync_playwright
WT = pathlib.Path(r"C:/Users/product/Desktop/autoTesting/.claude/worktrees/t204-au26")
EV = WT/"qa/evidence/browser-t204-au26-r2-checker"
EV.mkdir(parents=True, exist_ok=True)
SCR = pathlib.Path(sys.argv[1])
root = SCR/"root"; root.mkdir(exist_ok=True)
s = socket.socket(); s.bind(("127.0.0.1",0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, AUTOTESTER_ROOT=str(root))
for k in list(env):
    if k.startswith("AUTOTESTER_") and k != "AUTOTESTER_ROOT": env.pop(k)
srv = subprocess.Popen(["uv","run","uvicorn","autotester.ui.app:app","--host","127.0.0.1","--port",str(port)],
    cwd=WT, env=env, stdout=open(SCR/"server.log","w"), stderr=subprocess.STDOUT)
base = f"http://127.0.0.1:{port}"
for _ in range(60):
    try: urllib.request.urlopen(base+"/auth/login", timeout=2); break
    except Exception: time.sleep(1)
PW = "Scratch-Pass-12345"
R = {"base": base, "steps": {}}; errs = []
def rec(k, ok, note): R["steps"][k] = {"result": "pass" if ok else "FAIL", "note": note}; print(k, ok, note, flush=True)
def mk(b, name):
    c = b.new_context(viewport={"width":1100,"height":800}); p = c.new_page()
    p.on("console", lambda m, n=name, pg=p: errs.append((n, m.text, pg.url)) if m.type=="error" else None)
    p.on("pageerror", lambda e, n=name, pg=p: errs.append((n, str(e), pg.url)))
    return c, p
def shot(p, n): p.screenshot(path=str(EV/f"{n}.png"), full_page=True)
def signup(p, email):
    p.goto(base+"/auth/signup"); p.get_by_label("Email").fill(email)
    p.get_by_label(re.compile("^Password")).fill(PW); p.get_by_role("button", name="Create account").click()
    p.wait_for_load_state()
def login(p, email):
    p.goto(base+"/auth/login"); p.get_by_label("Email").fill(email)
    p.get_by_label("Password").fill(PW); p.get_by_role("button", name="Sign in").click(); p.wait_for_load_state()
def unlabeled(p):
    return p.evaluate("""()=>[...document.querySelectorAll('input:not([type=hidden]),select,textarea')].filter(e=>{
      if(e.getAttribute('aria-label')) return false;
      if(e.labels && e.labels.length) return false;
      if(e.closest('label')) return false; return true}).map(e=>e.outerHTML.slice(0,90))""")
def relogin(p, email):
    p.get_by_role("button", name="Sign out").click(); p.wait_for_load_state(); login(p, email)
with sync_playwright() as pw:
    b = pw.chromium.launch(headless=False)
    try:
        ca, a = mk(b,"admin"); cu, u = mk(b,"user2")
        signup(a,"admin@example.test"); shot(a,"s1-admin-home")
        adm_links = a.get_by_role("link", name=re.compile("Users|Groups")).count()
        rec("1a", a.url.rstrip("/")==base and adm_links>=1, f"first signup lands {a.url}; admin links={adm_links}")
        signup(u,"user2@example.test"); shot(u,"s1-user2-waiting")
        rec("1b", "/auth/waiting" in u.url and "no access" in u.content().lower(), f"second signup lands {u.url}")
        a.goto(base+"/admin/users"); shot(a,"s2-admin-users")
        row = a.locator("tr", has_text="user2@example.test")
        row.get_by_label("Tester").check(); row.get_by_role("button", name="Save groups").click(); a.wait_for_load_state()
        shot(a,"s2-admin-after-group")
        u.goto(base+"/"); shot(u,"s2-user2-after-group")
        rec("2", u.url.rstrip("/")==base and "/auth/" not in u.url, f"user2 next request -> {u.url} title={u.title()}")
        row = a.locator("tr", has_text="user2@example.test"); row.get_by_role("button", name="Disable").click(); a.wait_for_load_state()
        shot(a,"s3-admin-disabled")
        u.goto(base+"/"); shot(u,"s3-user2-after-disable")
        rec("3a", "/auth/login" in u.url, f"disabled user2 next click -> {u.url}")
        a.locator("tr", has_text="user2@example.test").get_by_role("button", name="Delete").click(); a.wait_for_load_state()
        shot(a,"s3-admin-after-delete")
        gone = a.locator("tr", has_text="user2@example.test").count()==0
        login(u,"user2@example.test"); shot(u,"s3-user2-login-after-delete")
        rec("3b", gone and "/auth/login" in u.url, f"row gone={gone}; deleted user login stays at {u.url}")
        ctx = {}
        for n in ("tester","dev","lead"):
            c,p = mk(b,n); ctx[n]=(c,p); signup(p,f"{n}@example.test")
        a.goto(base+"/admin/users")
        for n,g in (("tester","Tester"),("dev","Developer"),("lead","Sub-admin")):
            r = a.locator("tr", has_text=f"{n}@example.test")
            r.get_by_label(g).check(); r.get_by_role("button", name="Save groups").click(); a.wait_for_load_state()
            a.goto(base+"/admin/users")
        def newproj(p, slug):
            p.goto(base+"/onboard"); p.locator("input[name=slug]").fill(slug); p.locator("input[name=name]").fill(slug.title())
            p.locator("input[name=base_url]").fill("https://app.example.test/"); p.locator("input[name=allowed_domains]").fill("app.example.test")
            p.get_by_role("button", name="Create project").click(); p.wait_for_load_state()
        newproj(a,"alpha")
        for n,rel in (("tester","shared with"),("lead","assigned to (sub-admin)")):
            a.goto(base+"/projects/alpha/access"); a.get_by_label("Account email").fill(f"{n}@example.test")
            a.get_by_label("Relation").select_option(label=rel); a.get_by_role("button", name="Save").click(); a.wait_for_load_state()
        shot(a,"p-admin-alpha-access")
        t = ctx["tester"][1]; t.goto(base+"/"); relogin(t,"tester@example.test")
        shot(t,"p-tester-landing")
        link = t.get_by_role("link", name=re.compile("alpha", re.I)).first
        has = link.count()>0; clicks = 0
        if has: link.click(); clicks=1; t.wait_for_load_state()
        shot(t,"p-tester-alpha")
        rec("P-tester", has and clicks<=2 and "alpha" in t.url, f"after login home lists Alpha link={has}; clicks to project={clicks}; url={t.url}")
        d = ctx["dev"][1]; d.goto(base+"/"); relogin(d,"dev@example.test")
        newproj(d,"devproj"); d.goto(base+"/"); shot(d,"p-dev-home")
        dl = d.get_by_role("link", name=re.compile("devproj", re.I)).count()>0
        d.get_by_role("link", name=re.compile("devproj", re.I)).first.click(); d.wait_for_load_state(); shot(d,"p-dev-own-project")
        dadm = d.get_by_role("link", name=re.compile("^(Users|Groups)$")).count()
        rec("P-dev", dl and "devproj" in d.url, f"dev reaches own project {d.url}; admin links={dadm}")
        l = ctx["lead"][1]; l.goto(base+"/"); relogin(l,"lead@example.test")
        shot(l,"p-lead-home")
        la = l.get_by_role("link", name=re.compile("^(Users|Groups)$")).count()
        st = l.goto(base+"/admin/users").status; shot(l,"p-lead-admin-users-refused")
        l.goto(base+"/"); alink = l.get_by_role("link", name=re.compile("alpha", re.I)).count()>0
        rec("P-lead", la==0 and st==403, f"admin nav links={la}; GET /admin/users status={st}; sees assigned alpha={alink}")
        un = {}
        for name,path in (("login","/auth/login"),("signup","/auth/signup")):
            pg2 = mk(b,"anon")[1]; pg2.goto(base+path); un[name]=unlabeled(pg2)
        a.goto(base+"/admin/groups"); a.get_by_role("link", name="Tester").first.click(); a.wait_for_load_state(); gp=a.url
        for path in ("/admin/users","/admin/groups",gp.replace(base,""),"/projects/alpha/access","/onboard"):
            a.goto(base+path); un[path]=unlabeled(a)
        rec("labels", all(not v for v in un.values()), json.dumps(un)[:1500])
        k = mk(b,"kbd")[1]; k.goto(base+"/auth/login")
        order=[]
        for _ in range(6):
            k.keyboard.press("Tab"); order.append(k.evaluate("document.activeElement.id||document.activeElement.textContent.trim()||document.activeElement.tagName"))
            if order[-1]=="email": break
        k.keyboard.type("admin@example.test"); k.keyboard.press("Tab"); k.keyboard.type(PW); k.keyboard.press("Enter"); k.wait_for_load_state()
        shot(k,"k-keyboard-login")
        rec("keyboard", k.url.rstrip("/")==base, f"keyboard-only sign-in (Tab,type,Tab,type,Enter) lands {k.url}; tab order to email: {order}")
        kc,kp = mk(b,"kbuser"); signup(kp,"kb@example.test")
        a.goto(base+"/admin/users"); r = a.locator("tr", has_text="kb@example.test")
        r.get_by_label("Developer").focus(); a.keyboard.press("Space")
        r.get_by_role("button", name="Save groups").focus(); a.keyboard.press("Enter"); a.wait_for_load_state(); shot(a,"k-admin-keyboard-group")
        kp.goto(base+"/"); rec("keyboard-admin", "/auth/" not in kp.url, f"group ticked with Space, saved with Enter; kb user next click -> {kp.url}")
        a.goto(base+"/admin/users")
        a.get_by_role("button", name="Sign out").focus(); fo = a.evaluate("document.activeElement.textContent.trim()")
        rec("keyboard-focus", fo=="Sign out", f"sign-out button focusable by keyboard: {fo}")
    finally:
        b.close()
R["console_errors"] = errs
json.dump(R, open(EV/"report.json","w"), indent=1)
srv.terminate()
try: srv.wait(10)
except Exception: srv.kill()
print("errs", errs)
