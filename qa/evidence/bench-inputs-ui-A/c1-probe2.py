import httpx, re, json, hashlib, os, time, threading, glob
B = "http://127.0.0.1:8771"; PW = "correct-horse-battery"; H = {"Origin": B}
ROOT = r"D:\autoTesting\.work\tmp\bi-A1\root"
def login(email):
    c = httpx.Client(base_url=B, follow_redirects=False, timeout=300)
    assert c.post("/auth/login", data={"email": email, "password": PW}, headers=H).status_code == 303
    return c
ed = login("editor@team.test"); vw = login("viewer@team.test")
def up(c, body, name="a.json", field="atomic_list", ctype="application/json"):
    return c.post("/projects/demo/bench/atomic-list", files={field:(name, body, ctype)}, headers=H)
def show(n, r): print(f"{n}: {r.status_code} {r.headers.get('location','')} {r.text[:160]!r}" if r.status_code>=400 else f"{n}: {r.status_code} {r.headers.get('location','')}")
good = {"items":[{"id":"CEO-SECRET-1","priority":"P0","technique":"inbox"},{"id":"CEO-SECRET-2","priority":"P1","technique":"state_after","needs_seeded_data":True}]}
gb = json.dumps(good).encode()
print("== bad uploads (nothing may be stored)")
cases = {
 "empty": b"", "not json": b"hello", "binary": os.urandom(2000), "html": b"<html><script>alert(1)</script></html>",
 "array": b"[1,2]", "no items": b"{}", "extra key": b'{"items":[{"id":"A","priority":"P0","technique":"inbox","text":"secret finding text"}]}',
 "dup ids": b'{"items":[{"id":"A","priority":"P0","technique":"inbox"},{"id":"A","priority":"P1","technique":"inbox"}]}',
 "bad priority": b'{"items":[{"id":"A","priority":"PX","technique":"inbox"}]}',
 "deep nest": b"[" * 200000 + b"]" * 200000,
 "bigint": b'{"items":[{"id":' + b"9"*5000 + b',"priority":"P0","technique":"inbox"}]}',
 "NaN": b'{"items":[{"id":"A","priority":"P0","technique":"inbox","needs_seeded_data":NaN}]}',
 "utf16 bom": '\ufeff{"items":[]}'.encode("utf-16"),
 "exact cap+1": b" " * (256*1024+1),
 "255KiB spaces valid json?": b'{"items":[]}' + b" " * (256*1024 - 12),
 "id huge": json.dumps({"items":[{"id":"X"*100000,"priority":"P0","technique":"inbox"}]}).encode(),
}
for n, b in cases.items():
    r = up(ed, b); show(n, r)
print("pin after bad uploads:", glob.glob(ROOT + r"\.work\ceo-bench\**\*", recursive=True))
print("== missing / wrong field / traversal filename / multiple")
show("wrong field name", up(ed, gb, field="file"))
r = ed.post("/projects/demo/bench/atomic-list", data={"atomic_list":"text-not-file"}, headers=H); show("text field not file", r)
r = ed.post("/projects/demo/bench/atomic-list", headers=H); show("no body", r)
r = ed.post("/projects/demo/bench/atomic-list", content=gb, headers={**H,"content-type":"application/json"}); show("json body not multipart", r)
print("== valid upload with hostile filename")
r = up(ed, gb, name="../../../../evil.json"); show("traversal filename", r)
files = glob.glob(ROOT + r"\.work\ceo-bench\**\*", recursive=True); print("stored:", files)
print("outside root evil.json exists?", os.path.exists(r"D:\autoTesting\.work\tmp\bi-A1\evil.json"), os.path.exists(r"D:\autoTesting\.work\evil.json"), os.path.exists(r"D:\evil.json"))
pin = json.load(open(ROOT + r"\.work\ceo-bench\demo\atomic-list.pin.json")); print("pin", pin)
print("sha matches:", pin["sha256"] == hashlib.sha256(gb).hexdigest(), "stored bytes equal:", open(ROOT + r"\.work\ceo-bench\demo\atomic-list.json","rb").read() == gb)
print("== page / never served")
pg = ed.get("/projects/demo/bench").text
print("page shows sha:", pin["sha256"] in pg, "| contains CEO-SECRET:", "CEO-SECRET" in pg, "| contains 'atomic-list.json' href:", "atomic-list.json" in pg)
for p in ["/.work/ceo-bench/demo/atomic-list.json","/projects/demo/atomic-list.json","/projects/demo/bench/atomic-list","/projects/demo/bench/atomic-list.json","/projects/demo/bench/list","/static/../.work/ceo-bench/demo/atomic-list.json","/static/..%2f.work/ceo-bench/demo/atomic-list.json","/ceo-bench/demo/atomic-list.json", "/projects/demo/files/.work/ceo-bench/demo/atomic-list.json", "/projects/demo/bench/../../../.work/ceo-bench/demo/atomic-list.json"]:
    r = ed.get(p); print("GET", p, r.status_code, "SECRET" in r.text)
r = ed.get("/projects/demo/bench/atomic-list"); print("GET on POST-only route:", r.status_code)
print("viewer page has secret:", "CEO-SECRET" in vw.get("/projects/demo/bench").text)
print("== replace with different list -> replaced hash")
g2 = json.dumps({"items":[{"id":"CEO-SECRET-9","priority":"P2","technique":"inbox"}]}).encode()
show("replace", up(ed, g2)); pin2 = json.load(open(ROOT + r"\.work\ceo-bench\demo\atomic-list.pin.json")); print("replaced:", pin2["replaced_sha256"] == [pin["sha256"]], pin2["sha256"] == hashlib.sha256(g2).hexdigest())
show("same again", up(ed, g2)); pin3 = json.load(open(ROOT + r"\.work\ceo-bench\demo\atomic-list.pin.json")); print("replaced after same:", pin3["replaced_sha256"] == [pin["sha256"]])
print("tmp leftovers:", glob.glob(ROOT + r"\.work\ceo-bench\demo\*.tmp"))
print("git-ignored .work:", os.popen("git -C D:/autoTesting/.worktrees/bench-inputs-ui check-ignore -v .work/ceo-bench/demo/atomic-list.json").read().strip())
