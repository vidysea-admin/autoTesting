import json, re, sys, time
from common import *
port = 22101
p, root = start("run1", port)
print("pid", p.pid, "root", root)
routes = {}
for l in open(EV + r"\routes.jsonl"):
    if not l.startswith("{"): continue
    d = json.loads(l)
    if "path" in d: routes.setdefault(d["path"], set()).update(d["methods"])
fill = {"slug":"x","job_id":"x","case_id":"x","run_id":"x","video_path":"a/b.mp4","crawl_id":"x","issue_id":"x","key":"x","source_id":"x","name":"a.png","user_id":"1","action":"disable","group_id":"1"}
def fillp(t): return re.sub(r"\{(\w+)(:path)?\}", lambda m: fill[m.group(1)], t)
PUBLIC = {("GET","/auth/login"),("POST","/auth/login"),("GET","/auth/signup"),("POST","/auth/signup"),("GET","/healthz")}
# warm: serve /auth/login once (done by start)
before = treehash(root)
rows = []; bad = []
mp = multipart({"label":"x"}, {"recording":("fake.mp4", b"\x00\x01fake", "video/mp4")})
for tmpl in sorted(routes):
    path = fillp(tmpl)
    for m in ("GET","POST","PUT","PATCH","DELETE"):
        if (m, tmpl) in PUBLIC: continue
        if m == "POST" and tmpl.endswith("/sources/upload"): body, h = mp
        elif m == "POST" and tmpl.endswith("/sources/drive"): body, h = form({"link":"https://drive.google.com/drive/folders/FAKE"})
        elif m in ("POST","PUT","PATCH","DELETE"): body, h = form({"a":"b"})
        else: body, h = None, {}
        variants = {
          "a-html": dict(headers={**h,"Accept":"text/html"}),
          "a-json": dict(headers=h),
          "b-evilOrigin": dict(headers={**h,"Accept":"text/html"}, origin="http://evil.example"),
          "c-evilHost": dict(headers={**h,"Accept":"text/html"}, host="evil.example"),
        }
        for vn, kw in variants.items():
            try: s, hd, data = req(port, m, path, body=body, **kw)
            except Exception as e: s, hd, data = -1, [], repr(e).encode()
            loc = dict((k.lower(), v) for k, v in hd).get("location", "")
            ok = s in (401, 403) or (s == 302 and loc.startswith("/auth/login")) or (vn=="c-evilHost" and s in (400,))
            # Origin-guard refusal (403) also fine
            rows.append((m, tmpl, vn, s, loc[:60], len(data), ok))
            if not ok: bad.append((m, tmpl, vn, s, loc, data[:200]))
after = treehash(root)
changed = [k for k in set(before)|set(after) if before.get(k)!=after.get(k)]
print("requests", len(rows), "non-refusals", len(bad), "hash changed files", changed)
for b in bad: print("BAD", b)
from collections import Counter
print(Counter((r[2], r[3]) for r in rows))
json.dump(rows, open(EV + r"\t2-rows.json","w"))
json.dump({"before":before,"after":after,"changed":changed}, open(EV + r"\t2-hash.json","w"), indent=1)
# public routes separately
pub = []
for m, path in sorted(PUBLIC):
    for vn, kw in {"a": {}, "b-evilOrigin": dict(origin="http://evil.example"), "c-evilHost": dict(host="evil.example")}.items():
        body, h = (form({}) if m=="POST" else (None, {}))
        s, hd, data = req(port, m, path, headers={**h,"Accept":"text/html"}, body=body, **kw)
        pub.append((m, path, vn, s, data[:80]))
for r in pub: print("PUB", r)
json.dump([(a,b,c,d,e.decode(errors='replace')) for a,b,c,d,e in pub], open(EV + r"\t2-public.json","w"))
open(EV+r"\t2-done.txt","w").write("ok")
# leave server running for T3-T5? stop it; T3 uses a fresh server
stop(p)
