# C1 repair, flakiness measure: R rounds of W simultaneous editor mark POSTs (distinct keys), optional page readers.
import httpx, json, threading, sys
from collections import Counter
B = "http://127.0.0.1:8771"; PW = "correct-horse-battery"; H = {"Origin": B}
MF = r"D:\autoTesting\.work\tmp\bi-A1\root\projects\demo\bench\demo-acceptance.marks.json"
W, R, READERS = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
def login():
    c = httpx.Client(base_url=B, follow_redirects=False, timeout=120)
    assert c.post("/auth/login", data={"email":"editor@team.test","password":PW}, headers=H).status_code == 303; return c
clients = [login() for _ in range(W)]
st, lost, rd = Counter(), 0, Counter()
for r in range(R):
    for k in list(json.load(open(MF))["marks"]): clients[0].post("/projects/demo/bench/marks", data={"finding":k,"verdict":"clear"}, headers=H)
    keys = [f"{r*1000+i+0xb000:016x}" for i in range(W)]; res = []; stop = [False]
    def reader():
        c = login()
        while not stop[0]:
            for p in ("/projects/demo/crawls/crawl_1", "/projects/demo/bench"): rd[c.get(p).status_code] += 1
    rs = [threading.Thread(target=reader) for _ in range(READERS)]; [t.start() for t in rs]
    ws = [threading.Thread(target=lambda c=c,k=k: res.append((k, c.post("/projects/demo/bench/marks", data={"finding":k,"verdict":"real"}, headers=H).status_code))) for c,k in zip(clients, keys)]
    [t.start() for t in ws]; [t.join() for t in ws]; stop[0] = True; [t.join() for t in rs]
    m = json.load(open(MF))["marks"]; st.update(s for _, s in res)
    lost += sum(1 for k, s in res if s == 303 and k not in m)
print(f"W={W} R={R} readers={READERS}: write statuses {dict(st)}; acknowledged-but-missing {lost}; reader statuses {dict(rd)}")
