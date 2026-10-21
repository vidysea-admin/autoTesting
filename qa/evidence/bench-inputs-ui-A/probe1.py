import httpx, re, json, hashlib, sys
B = "http://127.0.0.1:8765"
PW = "correct-horse-battery"
def login(email):
    c = httpx.Client(base_url=B, follow_redirects=False, timeout=60)
    r = c.post("/auth/login", data={"email": email, "password": PW}, headers={"Origin": B})
    return c, r.status_code
def line(name, r):
    loc = r.headers.get("location", "")
    print(f"{name}: {r.status_code} {loc}")
anon = httpx.Client(base_url=B, follow_redirects=False)
ed, s = login("editor@team.test"); print("editor login", s)
vw, s = login("viewer@team.test"); print("viewer login", s)
ng, s = login("nogroup@team.test"); print("nogroup login", s)
H = {"Origin": B}
pg = ed.get("/projects/demo/crawls/crawl_1").text
keys = re.findall(r"name='finding' value='([0-9a-f]{16})'", pg)
print("crawl keys", set(keys))
key = keys[0]
D = {"finding": key, "verdict": "real", "next": "/projects/demo/crawls/crawl_1"}
print("== anonymous / no-permission")
line("anon GET bench", anon.get("/projects/demo/bench", headers={"accept":"text/html"}))
line("anon POST marks html", anon.post("/projects/demo/bench/marks", data=D, headers={**H,"accept":"text/html"}))
line("anon POST marks json", anon.post("/projects/demo/bench/marks", data=D, headers=H))
line("anon POST upload", anon.post("/projects/demo/bench/atomic-list", files={"atomic_list":("a.json",b"{}")}, headers=H))
line("nogroup POST marks", ng.post("/projects/demo/bench/marks", data=D, headers=H))
line("nogroup GET bench", ng.get("/projects/demo/bench"))
print("== viewer")
vb = vw.get("/projects/demo/bench"); print("viewer GET bench", vb.status_code, "form" in vb.text.lower() and "<form" in vb.text, "Uploading needs permission" in vb.text)
line("viewer POST marks", vw.post("/projects/demo/bench/marks", data=D, headers=H))
line("viewer POST upload", vw.post("/projects/demo/bench/atomic-list", files={"atomic_list":("a.json",b'{"items":[]}')}, headers=H))
vc = vw.get("/projects/demo/crawls/crawl_1").text
print("viewer crawl page has mark buttons:", "Mark real bug" in vc, "read-only" in vc)
print("== CSRF")
line("editor evil Origin", ed.post("/projects/demo/bench/marks", data=D, headers={"Origin":"https://evil.example"}))
line("editor evil Referer", ed.post("/projects/demo/bench/marks", data=D, headers={"Referer":"https://evil.example/x"}))
line("editor Sec-Fetch-Site cross-site", ed.post("/projects/demo/bench/marks", data=D, headers={"Sec-Fetch-Site":"cross-site"}))
line("editor evil Origin upload", ed.post("/projects/demo/bench/atomic-list", files={"atomic_list":("a.json",b"{}")}, headers={"Origin":"https://evil.example"}))
line("editor null Origin", ed.post("/projects/demo/bench/marks", data=D, headers={"Origin":"null"}))
print("marks after CSRF attempts:", ed.get("/projects/demo/crawls/crawl_1").text.count("Undo mark"))
print("== injection in mark route")
for name, data in {
  "finding traversal": {"finding":"../../../x","verdict":"real"},
  "finding 16hex upper": {"finding":"ABCDEF0123456789","verdict":"real"},
  "finding trailing newline": {"finding":key+"\n","verdict":"real"},
  "finding too long": {"finding":key+"0","verdict":"real"},
  "verdict bad": {"finding":key,"verdict":"__proto__"},
  "no fields": {},
}.items():
    line(name, ed.post("/projects/demo/bench/marks", data=data, headers=H))
for nxt in ["//evil.com", "https://evil.com", "/projects/other/bench", "/projects/demo/../other/bench", "/projects/demo/crawls/crawl_1\r\nSet-Cookie: x=1", "\\evil.com", "/projects/demo/", "/projects/demo/../../auth/logout", "/projects/demox/"]:
    try:
        line(f"next={nxt!r}", ed.post("/projects/demo/bench/marks", data={"finding":key,"verdict":"clear","next":nxt}, headers=H))
    except Exception as e: print("next", repr(nxt), "EXC", e)
print("== slug injection")
for slug in ["..", "../other", "..%2fother", "demo%2f..%2fother", "nope", "demo%00", "DEMO", "demo%20", "%2e%2e", "dem%C3%B6", "a"*300, "demo;x", "demo%5c..%5cother"]:
    r = ed.post(f"/projects/{slug}/bench/marks", data=D, headers=H); line(f"POST slug {slug[:30]!r}", r)
    r = ed.post(f"/projects/{slug}/bench/atomic-list", files={"atomic_list":("a.json",b'{"items":[{"id":"Z","priority":"P0","technique":"inbox"}]}')}, headers=H); line(f"UPLOAD slug {slug[:30]!r}", r)
    r = ed.get(f"/projects/{slug}/bench"); line(f"GET slug {slug[:30]!r}", r)
