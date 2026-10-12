import json, sqlite3, os, re, time, hashlib, glob
from common import *
port = 22103; root = os.path.join(B, "run3")
ck = json.load(open(EV + r"\t3-ck.json"))["ck"]
LINK = "https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUvWxYz0123456"
for grp, slug in [("sub-admin","qa-proj"),("developer","dev-proj"),("admin","qa-proj")]:
    b, h = form({"link": LINK}); s, hd, d = req(port, "POST", f"/projects/{slug}/sources/drive", h, b, cookie=ck[grp])
    loc = dict((k.lower(), v) for k, v in hd).get("location", ""); print("DRIVE", grp, slug, s, loc)
    if loc:
        time.sleep(2); s2, _, d2 = req(port, "GET", loc, cookie=ck[grp]); t = re.sub(r"<[^>]+>", " ", d2.decode()); print("  job page", s2, " ".join(t.split())[-160:])
        # other user polling the job
        o = "tester" if grp != "tester" else "admin"
        s3, _, _ = req(port, "GET", loc, cookie=ck[o]); print("  tester sees job page (qa-proj shared view):", s3)
# logout removed the row?
c = sqlite3.connect("file:" + (root + "/.auth/auth.sqlite3").replace("\\", "/") + "?mode=ro", uri=True)
s, c1, hd = login(port, *ADMIN); tok = c1.split("=", 1)[1]
h1 = hashlib.sha256(tok.encode()).hexdigest()
print("row present after login:", c.execute("select count(*) from sessions where token_hash=?", (h1,)).fetchone()[0])
s, hd, d = req(port, "POST", "/auth/logout", cookie=c1); print("logout", s)
print("row present after logout:", c.execute("select count(*) from sessions where token_hash=?", (h1,)).fetchone()[0])
# odd anonymous paths
for m, pth in [("GET","/nonexistent"),("GET","//evil.example"),("GET","/auth/login/"),("GET","/AUTH/login"),("GET","/projects/x/../../etc/passwd"),("GET","/static/x"),("GET","/projects/x/sources/upload"),("HEAD","/"),("OPTIONS","/projects/x"),("GET","/auth/login?next=//evil.example"),("GET","/auth/login?next=javascript:alert(1)")]:
    s, hd, d = req(port, m, pth, {"Accept":"text/html"}); print("ANON", m, pth, s, dict((k.lower(), v) for k, v in hd).get("location"), len(d))
