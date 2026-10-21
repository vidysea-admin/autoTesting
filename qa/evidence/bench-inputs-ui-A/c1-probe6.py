# C1 repair: 60 distinct keys marked by 60 simultaneous editor POSTs while 20 readers hammer the crawl, run and bench pages;
# then 40 simultaneous undo (clear) of half. Every acknowledged ruling must be stored; no 5xx on writers or readers.
import httpx, json, threading, time, glob
B = "http://127.0.0.1:8771"; PW = "correct-horse-battery"; H = {"Origin": B}
MF = r"D:\autoTesting\.work\tmp\bi-A1\root\projects\demo\bench\demo-acceptance.marks.json"
def login():
    c = httpx.Client(base_url=B, follow_redirects=False, timeout=120)
    assert c.post("/auth/login", data={"email":"editor@team.test","password":PW}, headers=H).status_code == 303; return c
base = json.load(open(MF))["marks"]
for k in list(base):
    login().post("/projects/demo/bench/marks", data={"finding":k,"verdict":"clear"}, headers=H)
assert json.load(open(MF))["marks"] == {}
keys = [f"{i+0xa000:016x}" for i in range(60)]
res, rd, stop = [], [], [False]
def reader():
    c = login()
    while not stop[0]:
        for p in ("/projects/demo/crawls/crawl_1", "/projects/demo/runs/run_1", "/projects/demo/bench"):
            rd.append(c.get(p).status_code)
def writer(k, v):
    c = login(); res.append((k, v, c.post("/projects/demo/bench/marks", data={"finding":k,"verdict":v}, headers=H).status_code))
rs = [threading.Thread(target=reader) for _ in range(20)]; [t.start() for t in rs]
ws = [threading.Thread(target=writer, args=(k, "real" if i % 2 else "false_positive")) for i, k in enumerate(keys)]
[t.start() for t in ws]; [t.join() for t in ws]
m = json.load(open(MF))["marks"]
acked = [k for k, v, s in res if s == 303]
print("phase1 writers:", len(res), "status set", sorted({s for _,_,s in res}), "acked", len(acked), "stored", len(m), "acked-but-missing", [k for k in acked if k not in m])
print("verdict mismatches", [k for k, v, s in res if s == 303 and m.get(k, {}).get("verdict") != v])
res.clear()
cl = [threading.Thread(target=writer, args=(k, "clear")) for k in keys[::2]]; [t.start() for t in cl]; [t.join() for t in cl]
stop[0] = True; [t.join() for t in rs]
m2 = json.load(open(MF))["marks"]
print("phase2 undo:", len(res), "status set", sorted({s for _,_,s in res}), "remaining", len(m2), "expected 30; cleared-keys-still-present", [k for k in keys[::2] if k in m2], "kept-keys-missing", [k for k in keys[1::2] if k not in m2])
from collections import Counter
print("reader statuses", Counter(rd))
print("stray files in bench dir:", [p for p in glob.glob(MF.rsplit("\\",1)[0] + "\*") if not p.endswith((".json",".lock"))])
