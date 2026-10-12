import re, json, sys, os
from common import *
port = 22103
p, root = start("run3", port)
out = {}
try:
    s, ADM, _ = login(port, *ADMIN); assert s == 303
    def post(path, d, ck, **kw):
        b, h = form(d); return req(port, "POST", path, h, b, cookie=ck, **kw)
    # create project as admin
    s, hd, d = post("/onboard", {"slug":"qa-proj","name":"QA Proj","base_url":"http://127.0.0.1:22103","allowed_domains":"127.0.0.1"}, ADM)
    print("onboard", s, dict(hd).get("Location"))
    # users
    PW = "Zx-fake-user-pw-5521-Qr"
    users = {"sub-admin":"subadmin@test.example","developer":"dev@test.example","tester":"tester@test.example","none":"nogroup@test.example"}
    for g, em in users.items():
        b, h = form({"email":em,"password":PW}); s, hd, d = req(port, "POST", "/auth/signup", h, b)
        print("signup", em, s, dict(hd).get("Location"), "cookie" , bool(cookie_of(hd)))
    s, hd, d = req(port, "GET", "/admin/users", cookie=ADM); html = d.decode("utf-8")
    ids = {}
    for em in users.values():
        m = re.search(re.escape(em) + r".*?/admin/users/(\d+)/groups", html, re.S); ids[em] = int(m.group(1))
    print("ids", ids)
    gid = {"sub-admin":2,"developer":3,"tester":4}
    for g, em in users.items():
        if g in gid:
            s, hd, d = post(f"/admin/users/{ids[em]}/groups", {"group_id": str(gid[g])}, ADM); print("assign", g, s)
    # sessions
    ck = {}
    for g, em in users.items():
        s, c, _ = login(port, em, PW); ck[g] = c; print("login", g, s, bool(c))
    ck["admin"] = ADM
    out["ck_users"] = list(ck)
    # developer creates own project
    s, hd, d = post("/onboard", {"slug":"dev-proj","name":"Dev Proj","base_url":"http://127.0.0.1:22103","allowed_domains":"127.0.0.1"}, ck["developer"]); print("dev onboard", s)
    mp = multipart({"label":"t3"}, {"recording":("fake.mp4", b"\x00\x00\x00\x18ftypmp42fakebytes", "video/mp4")})
    def cells(slug, state):
        res = {}
        reqs = [("POST", f"/projects/{slug}/sources/upload", mp),
                ("POST", f"/projects/{slug}/sources/drive", form({"link":"https://drive.google.com/drive/folders/FAKE"})),
                ("GET", f"/projects/{slug}/sources/drive/jobx", None),
                ("GET", f"/projects/{slug}/damage-report", None),
                ("GET", f"/projects/{slug}/env", None), ("GET", "/settings/providers", None), ("GET", "/admin/users", None),
                ("GET", f"/projects/{slug}/access", None), ("GET", f"/projects/{slug}/sources", None), ("GET", f"/projects/{slug}/report", None),
                ("GET", "/onboard", None), ("POST", f"/projects/{slug}/run", form({}))]
        for grp in ["admin","sub-admin","developer","tester","none"]:
            for m, path, bh in reqs:
                body, h = bh if bh else (None, {})
                s, hd, d = req(port, m, path, {**h, "Accept":"text/html"}, body, cookie=ck[grp])
                res[(slug, state, grp, m, path)] = (s, dict(hd).get("Location",""), d[:80].decode(errors="replace").replace("\n"," "))
        return res
    allres = {}
    allres.update(cells("qa-proj", "no-relation"))
    # grant: sub-admin assigned, developer + tester shared
    for em, rel in [(users["sub-admin"],"assigned"),(users["developer"],"shared"),(users["tester"],"shared")]:
        s, hd, d = post("/projects/qa-proj/access", {"email":em,"relation":rel,"change":"add"}, ADM); print("grant", em, rel, s)
    allres.update(cells("qa-proj", "granted"))
    allres.update(cells("dev-proj", "dev-owns"))
    json.dump([[*k, *v] for k, v in allres.items()], open(EV + r"\t3-cells.json","w"), indent=0)
    json.dump({"ck": {k: v for k, v in ck.items()}}, open(EV + r"\t3-ck.json","w"))
    json.dump(ids, open(EV + r"\t3-ids.json","w"))
    # list drive job state, intake outcomes on disk
    print("done")
finally:
    open(EV+r"\t3-pid.txt","w").write(str(p.pid))
    # keep server running for T5/T4: script t5 expects it; here we stop later
