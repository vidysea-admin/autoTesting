import httpx, json, threading, glob
B = "http://127.0.0.1:8765"; PW = "correct-horse-battery"; H = {"Origin": B}
MF = r"D:\autoTesting\.work\tmp\bi-A\root\projects\demo\bench\demo-acceptance.marks.json"
def login(e):
    c = httpx.Client(base_url=B, follow_redirects=False, timeout=60)
    assert c.post("/auth/login", data={"email":e,"password":PW}, headers=H).status_code == 303; return c
cs = [login("editor@team.test") for _ in range(2)]
# reset: clear the 10 synthetic keys
for k in json.load(open(MF))["marks"]:
    cs[0].post("/projects/demo/bench/marks", data={"finding":k,"verdict":"clear"}, headers=H)
lost = err = 0; N = 25
for i in range(N):
    ka, kb = f"{i*2+100:016x}", f"{i*2+101:016x}"; out = []
    ts = [threading.Thread(target=lambda c=c,k=k: out.append(c.post("/projects/demo/bench/marks", data={"finding":k,"verdict":"real"}, headers=H).status_code)) for c,k in ((cs[0],ka),(cs[1],kb))]
    [t.start() for t in ts]; [t.join() for t in ts]
    m = json.load(open(MF))["marks"]; got = (ka in m) + (kb in m)
    ok = sum(1 for s in out if s == 303); err += sum(1 for s in out if s >= 500)
    if got < ok: lost += 1
print(f"{N} pairs of 2 simultaneous marks: pairs where an acknowledged (303) mark was missing from the file: {lost}; 5xx responses: {err}")
