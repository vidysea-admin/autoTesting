import json, os, httpx
B = "http://127.0.0.1:8791"; OR = {"Origin": B}
c = httpx.Client(base_url=B, follow_redirects=False, timeout=60)
assert c.post("/auth/login", data={"email": "editor@chk.test", "password": "correct-horse-battery"}, headers=OR).status_code == 303
LD = r"D:\autoTesting\.work\tmp\bi-chkB2\root2\.work\ceo-bench\demo\atomic-list.pin.json"
base = json.dumps({"items": [{"id": "C1", "priority": "P0", "technique": "inbox"}]}).encode()
MAX = 256 * 1024
for n in (MAX - 1, MAX, MAX + 1):
    d = base + b" " * (n - len(base)); assert len(d) == n
    r = c.post("/projects/demo/bench/atomic-list", files={"atomic_list": ("l.json", d, "application/json")}, headers=OR)
    p = json.load(open(LD)); print(n, r.status_code, "pinned bytes", p["bytes"])
