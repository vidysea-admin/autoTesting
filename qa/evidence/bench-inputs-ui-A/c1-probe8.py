# C2 repair: boundary, name vet, concurrent uploads over HTTP, staging cleanup.
import httpx, json, hashlib, threading, glob, os
B = "http://127.0.0.1:8771"; PW = "correct-horse-battery"; H = {"Origin": B}
ROOT = r"D:\autoTesting\.work\tmp\bi-A1\root"; D = ROOT + r"\.work\ceo-bench\demo"
def login(e="editor@team.test"):
    c = httpx.Client(base_url=B, follow_redirects=False, timeout=120)
    assert c.post("/auth/login", data={"email": e, "password": PW}, headers=H).status_code == 303; return c
ed = login()
def up(c, body, name="a.json"): return c.post("/projects/demo/bench/atomic-list", files={"atomic_list": (name, body, "application/json")}, headers=H)
def mk(n, pad=0):
    b = json.dumps({"items": [{"id": f"A{n}", "priority": "P0", "technique": "inbox"}]}).encode()
    return b + b" " * pad
MAX = 256 * 1024
r = up(ed, mk(1, MAX - len(mk(1)))); print("exactly MAX bytes valid:", r.status_code, "size", MAX)
r = up(ed, mk(2, MAX + 1 - len(mk(2)))); print("MAX+1:", r.status_code, r.text[:80])
for n in ("a.exe", "a.json.exe", "noext", "a.JSON", "..\\..\\x.json", "a.json "):
    r = up(ed, mk(3), n); print("name", repr(n), "->", r.status_code, r.text[:70] if r.status_code >= 400 else "")
vw = login("viewer@team.test"); print("viewer upload:", up(vw, mk(4)).status_code)
anon = httpx.Client(base_url=B, follow_redirects=False); print("anon upload:", anon.post("/projects/demo/bench/atomic-list", files={"atomic_list": ("a.json", mk(5))}, headers=H).status_code)
print("evil origin:", ed.post("/projects/demo/bench/atomic-list", files={"atomic_list": ("a.json", mk(6))}, headers={"Origin": "https://evil.test"}).status_code)
# concurrent uploads of 12 distinct valid lists
bodies = [mk(100 + i) for i in range(12)]; cs = [login() for _ in bodies]; res = []
ts = [threading.Thread(target=lambda c=c, b=b: res.append(up(c, b).status_code)) for c, b in zip(cs, bodies)]
pre = json.load(open(D + r"\atomic-list.pin.json"))
[t.start() for t in ts]; [t.join() for t in ts]
pin = json.load(open(D + r"\atomic-list.pin.json")); raw = open(D + r"\atomic-list.json", "rb").read()
print("12 concurrent uploads statuses:", sorted(set(res)), "| list sha == pin sha:", hashlib.sha256(raw).hexdigest() == pin["sha256"])
hashes = {hashlib.sha256(b).hexdigest() for b in bodies}; seen = set(pin["replaced_sha256"]) | {pin["sha256"]}
print("every uploaded hash recorded (replaced+current):", hashes <= seen, "missing", len(hashes - seen), "| pre-hash kept:", pre["sha256"] in seen)
print("files in .work/ceo-bench/demo:", sorted(os.listdir(D)))
print("staging leftovers:", glob.glob(ROOT + r"\.work\uploads\demo\*"))
