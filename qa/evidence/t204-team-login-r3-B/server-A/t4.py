import json, sqlite3, os, re, time
from common import *
port = 22103; root = os.path.join(B, "run3")
ck = json.load(open(EV + r"\t3-ck.json"))["ck"]
db = os.path.join(root, ".auth", "auth.sqlite3")
def q(sql):
    c = sqlite3.connect("file:" + db.replace("\\", "/") + "?mode=ro", uri=True)
    try: return c.execute(sql).fetchall()
    finally: c.close()
print("tables", q("select name from sqlite_master where type='table'"))
def nsess(): return q("select count(*) from sessions")[0][0]
# ---- drive valid-shaped link (gws not on PATH -> no network)
LINK = "https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUvWxYz0123456"
for grp, slug in [("sub-admin","qa-proj"),("developer","qa-proj"),("developer","dev-proj")]:
    b, h = form({"link": LINK}); s, hd, d = req(port, "POST", f"/projects/{slug}/sources/drive", h, b, cookie=ck[grp])
    loc = dict(hd).get("Location", ""); print("DRIVE", grp, slug, s, loc)
    if loc:
        time.sleep(1.5); s2, _, d2 = req(port, "GET", loc, cookie=ck[grp]); t = re.sub(r"<[^>]+>", " ", d2.decode()); print("  job page", s2, " ".join(t.split())[-200:])
# ---- env masking
b, h = form({"key":"QA_PROJ_FAKEKEY","value":"CANARY-fake-secret-7788","domains":"127.0.0.1","description":"fake"})
s, hd, d = req(port, "POST", "/projects/qa-proj/env/add", h, b, cookie=ck["admin"]); print("env add", s, d[:100])
for grp in ["admin","sub-admin","developer","tester"]:
    s, hd, d = req(port, "GET", "/projects/qa-proj/env", cookie=ck[grp]); print("ENV", grp, s, "value-visible=", b"CANARY-fake-secret-7788" in d, "key-visible=", b"QA_PROJ_FAKEKEY" in d)
# ---- T4
print("--- T4")
s, c, hd = login(port, *ADMIN); sc = [v for k, v in hd if k.lower()=="set-cookie"]; print("login ok", s, sc, dict(hd).get("Location"))
OLD = c
s1, hd1, d1 = login(port, ADMIN[0], "wrong-password-xx")[0], None, None
b, h = form({"email":ADMIN[0],"password":"wrong-password-xx","next":"/"}); sA, hdA, dA = req(port, "POST", "/auth/login", h, b)
b, h = form({"email":"nobody@test.example","password":"wrong-password-xx","next":"/"}); sB, hdB, dB = req(port, "POST", "/auth/login", h, b)
print("wrong pw", sA, "unknown", sB, "bodies identical:", dA == dB, len(dA), "set-cookie:", cookie_of(hdA), cookie_of(hdB))
b, h = form({"email":"DISABLED?@test.example","password":""}); 
s, hd, d = req(port, "GET", "/", {"Accept":"text/html"}, cookie=OLD); print("pre-logout GET /", s)
s, hd, d = req(port, "POST", "/auth/logout", cookie=OLD); print("logout", s, [v for k,v in hd if k.lower()=="set-cookie"])
for path in ["/", "/projects/qa-proj", "/admin/users"]:
    s, hd, d = req(port, "GET", path, {"Accept":"text/html"}, cookie=OLD); print("replay", path, s, dict(hd).get("Location"))
s, hd, d = req(port, "POST", "/projects/qa-proj/sources/drive", *reversed(form({"link":LINK})), cookie=OLD); print("replay POST drive", s)
print("sessions rows now", nsess())
n0 = nsess()
for label, origin in [("evil", "http://evil.example"), ("null", "null"), ("none", None), ("match", f"http://127.0.0.1:{port}")]:
    b, h = form({"email":ADMIN[0],"password":ADMIN[1]})
    s, hd, d = req(port, "POST", "/auth/login", h, b, origin=origin)
    print("LOGIN origin=", label, s, "set-cookie:", bool(cookie_of(hd)), "loc:", dict(hd).get("Location"), "body:", d[:90], "rows", nsess())
    if label == "match": newc = cookie_of(hd)
# multiple Origin headers + bad port
c = http.client.HTTPConnection("127.0.0.1", port); c.putrequest("POST","/auth/login", skip_host=True, skip_accept_encoding=True)
b, h = form({"email":ADMIN[0],"password":ADMIN[1]})
for k, v in [("Host",f"127.0.0.1:{port}"),("Origin",f"http://127.0.0.1:{port}"),("Origin","http://evil.example"),("Content-Type",h["Content-Type"]),("Content-Length",str(len(b)))]: c.putheader(k, v)
c.endheaders(b); r = c.getresponse(); print("double-Origin", r.status, r.getheader("Set-Cookie")); r.read(); c.close()
s, hd, d = req(port, "POST", "/auth/login", {**h}, b, origin=f"http://127.0.0.1:{port}.evil.com"); print("bad-port Origin", s, bool(cookie_of(hd)))
print("sessions rows end", nsess(), "tokens stored plaintext?", q("select * from sessions limit 1") and [len(str(x)) for x in q("select * from sessions limit 1")[0]])
print("cols", q("select sql from sqlite_master where name='sessions'"))
# cookie flags raw
