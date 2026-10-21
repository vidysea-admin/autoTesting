import json, re, sys, time, hashlib, os
import httpx
B = "http://127.0.0.1:8791"
OR = {"Origin": B}
PW = "correct-horse-battery"
ROOT = r"D:\autoTesting\.work\tmp\bi-chkB\root"
LISTDIR = os.path.join(ROOT, ".work", "ceo-bench", "demo")
OUTP = r"C:\Users\Lenovo\AppData\Local\Temp\claude\d--autoTesting\e46c0e51-15e9-4a31-a0b0-cf49de9d445f\scratchpad\probeB.out"
out = []
def log(*a):
    s = " ".join(str(x) for x in a); out.append(s); print(s, flush=True)
def login(email):
    c = httpx.Client(base_url=B, follow_redirects=False, timeout=60)
    r = c.post("/auth/login", data={"email": email, "password": PW}, headers=OR)
    assert r.status_code == 303, (email, r.status_code, r.text[:200])
    return c
def stored():
    return sorted(os.listdir(LISTDIR)) if os.path.isdir(LISTDIR) else []
GOOD = json.dumps({"items": [{"id": "A1", "priority": "P0", "technique": "inbox"}, {"id": "A2", "priority": "P1", "technique": "state_after"}]}).encode()
def up(c, data, name="atomic_list", fname="list.json", ctype="application/json", headers=OR):
    return c.post("/projects/demo/bench/atomic-list", files={name: (fname, data, ctype)}, headers=headers)

# --- anonymous
a = httpx.Client(base_url=B, follow_redirects=False)
r = a.get("/projects/demo/bench", headers={"Accept": "text/html"}); log("anon GET bench html", r.status_code, r.headers.get("location"))
r = a.get("/projects/demo/bench"); log("anon GET bench json", r.status_code)
r = a.post("/projects/demo/bench/marks", data={"finding": "0123456789abcdef", "verdict": "real"}, headers=OR); log("anon POST marks", r.status_code)
r = up(a, GOOD); log("anon POST upload", r.status_code, "stored:", stored())
# --- pending
p = login("pending@chk.test")
r = p.get("/projects/demo/bench", headers={"Accept": "text/html"}); log("pending GET bench", r.status_code)
r = up(p, GOOD); log("pending POST upload", r.status_code, "stored:", stored())
# --- viewer
v = login("viewer@chk.test")
r = v.get("/projects/demo/bench"); log("viewer GET bench", r.status_code, "form", "<form" in r.text, "file input", "type='file'" in r.text, "mark btn", "Mark real" in r.text, "msg", "needs permission" in r.text)
r = v.get("/projects/demo/crawls/crawl_1"); log("viewer GET crawl", r.status_code, "Mark real bug", "Mark real bug" in r.text, "read-only", "read-only" in r.text)
r = v.get("/projects/demo/runs/run_1"); log("viewer GET run", r.status_code, "Mark real bug", "Mark real bug" in r.text, "read-only", "read-only" in r.text)
r = v.post("/projects/demo/bench/marks", data={"finding": "0123456789abcdef", "verdict": "real"}, headers=OR); log("viewer POST marks", r.status_code, r.text[:80].replace("\n", " "))
r = up(v, GOOD); log("viewer POST upload", r.status_code, "stored:", stored())
mp = os.path.join(ROOT, "projects", "demo", "bench")
log("bench dir after viewer/anon:", sorted(os.listdir(mp)) if os.path.isdir(mp) else "none")
# --- editor
e = login("editor@chk.test")
r = e.get("/projects/demo/bench"); log("editor GET bench", r.status_code, "file input", "type='file'" in r.text, "label", "for='atomic-list-file'" in r.text)
log("bench page title:", re.findall(r"<title>.*?</title>", r.text)[:1], "raw <b>X present (should be False):", "<b>X</b>" in r.text)
page = e.get("/projects/demo/crawls/crawl_1").text
log("crawl page raw onerror tag present (should be False):", "<img src=x" in page, "escaped present:", "&lt;img src=x" in page)
keys = re.findall(r"name='finding' value='([0-9a-f]{16})'", page); log("keys", keys)
# CSRF
r = e.post("/projects/demo/bench/marks", data={"finding": keys[0], "verdict": "real"}, headers={"Origin": "https://evil.test"}); log("editor cross-origin mark", r.status_code)
r = e.post("/projects/demo/bench/marks", data={"finding": keys[0], "verdict": "real"}, headers={"Referer": "https://evil.test/x"}); log("editor cross-referer mark", r.status_code)
r = e.post("/projects/demo/bench/marks", data={"finding": keys[0], "verdict": "real"}, headers={"Sec-Fetch-Site": "cross-site"}); log("editor sec-fetch cross-site mark", r.status_code)
r = up(e, GOOD, headers={"Origin": "https://evil.test"}); log("editor cross-origin upload", r.status_code, "stored:", stored())
r = up(e, GOOD, headers={"Origin": "http://localhost:8791.evil.com"}); log("editor bad-port origin upload", r.status_code, "stored:", stored())
log("marks file after csrf probes exists (should be False):", os.path.exists(os.path.join(mp, "demo-acceptance.marks.json")))
# bad inputs on marks
for label, d in [("short key", {"finding": "abc", "verdict": "real"}), ("upper hex", {"finding": "0123456789ABCDEF", "verdict": "real"}),
                 ("traversal key", {"finding": "../../../etc/pass", "verdict": "real"}), ("newline key", {"finding": "0123456789abcdef\n", "verdict": "real"}),
                 ("17 key", {"finding": "0123456789abcdef0", "verdict": "real"}), ("bad verdict", {"finding": keys[0], "verdict": "maybe"}),
                 ("no fields", {}), ("verdict clear unknown key", {"finding": "ffffffffffffffff", "verdict": "clear"})]:
    r = e.post("/projects/demo/bench/marks", data=d, headers=OR); log("marks bad:", label, r.status_code)
log("marks file after bad inputs:", os.path.exists(os.path.join(mp, "demo-acceptance.marks.json")))
# next redirect
for nx in ["//evil.com", "/\\evil.com", "https://evil.com", "/projects/demo/../../evil", "/projects/demo/crawls/crawl_1", "/projects/demox/evil", "/projects/demo/bench\r\nSet-Cookie: a=b", "/projects/demo/" + "a" * 3000, ""]:
    try:
        r = e.post("/projects/demo/bench/marks", data={"finding": keys[0], "verdict": "clear", "next": nx}, headers=OR); log("next", repr(nx[:40]), r.status_code, r.headers.get("location"))
    except Exception as ex: log("next", repr(nx[:40]), "EXC", ex)
# slug injection
for path in ["/projects/..%2f..%2fx/bench/marks", "/projects/demo%00/bench/marks", "/projects/Demo/bench/marks", "/projects/nonexistent/bench/marks", "/projects/..%5c..%5cx/bench/atomic-list", "/projects/demo%2f..%2fdemo/bench/marks"]:
    r = e.post(path, data={"finding": keys[0], "verdict": "real"}, headers=OR); log("slug inj POST", path, r.status_code)
r = e.get("/projects/nonexistent/bench"); log("GET unknown project bench", r.status_code)
r = e.post("/projects/nonexistent/bench/atomic-list", files={"atomic_list": ("l.json", GOOD, "application/json")}, headers=OR)
cb = os.path.join(ROOT, ".work", "ceo-bench")
log("upload unknown project", r.status_code, "ceo-bench dirs:", os.listdir(cb) if os.path.isdir(cb) else "none")
# upload bad
r = e.post("/projects/demo/bench/atomic-list", data={"atomic_list": "text-not-file"}, headers=OR); log("upload text field not file", r.status_code)
r = e.post("/projects/demo/bench/atomic-list", data={}, headers=OR); log("upload urlencoded none", r.status_code)
r = up(e, GOOD, name="other"); log("upload wrong field name", r.status_code)
bads = {"empty": b"", "notjson": b"hello", "noitems": b"{}", "extra text key": json.dumps({"items": [{"id": "A1", "priority": "P0", "technique": "inbox", "text": "SECRET-FINDING-TEXT"}]}).encode(),
        "bad priority": json.dumps({"items": [{"id": "A1", "priority": "P9", "technique": "inbox"}]}).encode(),
        "dup ids": json.dumps({"items": [{"id": "A1", "priority": "P0", "technique": "inbox"}] * 2}).encode(),
        "nan": b'{"items": NaN}', "bom": b"\xef\xbb\xbf" + GOOD, "deep nest": b'{"items":' + b"[" * 100000 + b"]" * 100000 + b"}",
        "toplevel list": b"[1,2,3]", "bad utf8": b'{"items": "\xff\xfe"}', "string SECRET input": b'{"items": "SECRET-VALUE-XYZ"}',
        "over cap": b"x" * (256 * 1024 + 10), "257KiB json": (b'{"items": [], "pad": "' + b"a" * (257 * 1024) + b'"}')}
for label, data in bads.items():
    try:
        r = up(e, data); body = r.text
        log("upload bad:", label, r.status_code, "echo SECRET:", ("SECRET" in body), "stored:", stored())
        if label in ("string SECRET input", "extra text key", "bad utf8", "deep nest"): log("   body:", body[:300].replace("\n", " "))
    except Exception as ex: log("upload bad:", label, "EXC", repr(ex)[:150])
# many form fields
r = e.post("/projects/demo/bench/atomic-list", data={f"f{i}": "x" for i in range(1500)}, headers=OR); log("upload 1500 fields", r.status_code)
# Valid upload
r = up(e, GOOD, fname="../../evil.json"); log("valid upload (traversal filename)", r.status_code, r.headers.get("location"), "stored:", stored())
pin = json.load(open(os.path.join(LISTDIR, "atomic-list.pin.json")))
log("pin:", pin, "sha matches file:", hashlib.sha256(open(os.path.join(LISTDIR, "atomic-list.json"), "rb").read()).hexdigest() == pin["sha256"], "expected", hashlib.sha256(GOOD).hexdigest())
# HTTP exposure
page = e.get("/projects/demo/bench").text
log("page shows sha:", pin["sha256"] in page, "page contains item id A1:", "A1" in page, "technique inbox:", "inbox" in page, "pinned by:", pin["pinned_by"] in page)
for path in ["/.work/ceo-bench/demo/atomic-list.json", "/projects/demo/bench/atomic-list", "/static/ceo-bench/demo/atomic-list.json", "/projects/demo/runs/run_1/videos/..%2f..%2f..%2f.work%2fceo-bench%2fdemo%2fatomic-list.json", "/projects/demo/runs/run_1/videos/../../../../.work/ceo-bench/demo/atomic-list.json", "/projects/demo/bench/atomic-list.json", "/projects/demo/bench/../../.work/ceo-bench/demo/atomic-list.json", "/work/ceo-bench/demo/atomic-list.json"]:
    for cl, nm in ((e, "editor"), (a, "anon")):
        r = cl.get(path, headers={"Accept": "text/html"}); leak = (b"A1" in r.content and b"priority" in r.content)
        log("GET", nm, path[:70], r.status_code, "LEAK" if leak else "no-leak")
# replace
r = up(e, GOOD.replace(b"A2", b"A3")); log("replace upload", r.status_code)
pin2 = json.load(open(os.path.join(LISTDIR, "atomic-list.pin.json"))); log("replaced list records old hash:", pin2["replaced_sha256"] == [pin["sha256"]], "files:", stored())
open(OUTP, "w").write("\n".join(out))
