import json, os, re, sys, time, hashlib, threading, glob
import httpx
B = "http://127.0.0.1:8791"; OR = {"Origin": B}; PW = "correct-horse-battery"
ROOT = r"D:\autoTesting\.work\tmp\bi-chkB2\root2"
LISTDIR = os.path.join(ROOT, ".work", "ceo-bench", "demo")
def login(email):
    c = httpx.Client(base_url=B, follow_redirects=False, timeout=120)
    r = c.post("/auth/login", data={"email": email, "password": PW}, headers=OR); assert r.status_code == 303
    return c
e = login("editor@chk.test")
def up(data, fname="list.json", name="atomic_list", c=None):
    return (c or e).post("/projects/demo/bench/atomic-list", files={name: (fname, data, "application/json")}, headers=OR)
def pin(): return json.load(open(os.path.join(LISTDIR, "atomic-list.pin.json")))
def mk(nbytes):
    base = b'{"items": [{"id": "A1", "priority": "P0", "technique": "inbox"}], "pad": "'
    tail = b'"}'
    # AtomicList extra=forbid on items only? try pad at top-level
    return base + b"a" * (nbytes - len(base) - len(tail)) + tail
P0 = pin(); print("start pin", P0["sha256"][:12], "replaced", len(P0["replaced_sha256"]))
# exact cap
MAX = 256 * 1024
for n in (MAX, MAX + 1):
    d = mk(n); assert len(d) == n
    t = time.time(); r = up(d); print(f"valid-json-size {n}: status {r.status_code} body {r.text[:90]!r} {time.time()-t:.2f}s; pin sha now {pin()['sha256'][:12]} bytes {pin()['bytes']}")
# 40 MB
big = b"x" * (40 * 1024 * 1024)
t = time.time(); r = up(big); print(f"40MB: status {r.status_code} {time.time()-t:.2f}s; pin sha {pin()['sha256'][:12]}")
# name check
GOOD = json.dumps({"items": [{"id": "A9", "priority": "P0", "technique": "inbox"}]}).encode()
for fname in ["x.exe", "x.json.exe", "x", "x.JSON", r"C:\evil\x.json", "../../x.json", "x.json "]:
    before = pin()["sha256"]
    r = up(GOOD, fname=fname); after = pin()["sha256"]
    print(f"name {fname!r}: {r.status_code} stored_changed={before != after}")
# staging cleanup
up_dirs = glob.glob(os.path.join(ROOT, ".work", "uploads", "demo", "*"))
print("staging leftovers:", up_dirs)
# concurrent uploads of distinct lists
hs = []
def one(i):
    c = login("editor@chk.test")
    d = json.dumps({"items": [{"id": f"U{i}", "priority": "P0", "technique": "inbox"}]}).encode()
    r = up(d, c=c); hs.append((i, r.status_code, hashlib.sha256(d).hexdigest()))
ts = [threading.Thread(target=one, args=(i,)) for i in range(12)]
before = pin(); [t.start() for t in ts]; [t.join() for t in ts]
p = pin(); lst = open(os.path.join(LISTDIR, "atomic-list.json"), "rb").read()
print("concurrent uploads statuses:", sorted(set(s for _, s, _ in hs)), "list matches pin:", hashlib.sha256(lst).hexdigest() == p["sha256"],
      "all 12 hashes recorded (replaced+current):", all(h in p["replaced_sha256"] + [p["sha256"]] for _, _, h in hs),
      "replaced count", len(p["replaced_sha256"]), "(prev", len(before["replaced_sha256"]), ")", "tmp leftovers:", [f for f in os.listdir(LISTDIR) if f.startswith(".tmp")])
# concurrent marks over HTTP with concurrent page GETs
page = e.get("/projects/demo/crawls/crawl_1").text
keys = sorted(set(re.findall(r"name='finding' value='([0-9a-f]{16})'", page)))
print("keys on crawl page:", keys)
mp = os.path.join(ROOT, "projects", "demo", "bench", "demo-acceptance.marks.json")
st = []; 
def mark(i, key, verdict):
    c = login("editor@chk.test")
    r = c.post("/projects/demo/bench/marks", data={"finding": key, "verdict": verdict}, headers=OR); st.append(r.status_code)
def reader():
    c = login("viewer@chk.test")
    for _ in range(15): 
        r = c.get("/projects/demo/bench"); st.append(("GET", r.status_code))
fake = [f"{i:016x}" for i in range(40)]
ts = [threading.Thread(target=mark, args=(i, fake[i], "real")) for i in range(40)] + [threading.Thread(target=reader) for _ in range(3)]
[t.start() for t in ts]; [t.join() for t in ts]
m = json.load(open(mp))["marks"]
print("40 concurrent marks + 3 readers: statuses", sorted(set(map(str, st))), "stored", sum(k in m for k in fake), "of 40")
