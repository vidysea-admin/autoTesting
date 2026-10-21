import httpx, re, json, os, threading, glob
B = "http://127.0.0.1:8771"; PW = "correct-horse-battery"; H = {"Origin": B}
ROOT = r"D:\autoTesting\.work\tmp\bi-A1\root"
def login(e):
    c = httpx.Client(base_url=B, follow_redirects=False, timeout=60)
    assert c.post("/auth/login", data={"email":e,"password":PW}, headers=H).status_code == 303; return c
ed = login("editor@team.test")
run = ed.get("/projects/demo/runs/run_1").text; crawl = ed.get("/projects/demo/crawls/crawl_1").text
print("script tag raw in run page:", "<script>alert(1)" in run, "| escaped present:", "&lt;script&gt;" in run)
print("raw <b>x</b> in crawl page:", "<b>x</b>" in crawl, "| escaped:", "&lt;b&gt;x&lt;/b&gt;" in crawl)
keys = re.findall(r"name='finding' value='([0-9a-f]{16})'", crawl) ; rk = re.findall(r"name='finding' value='([0-9a-f]{16})'", run)
print("crawl keys", sorted(set(keys)), "run keys", sorted(set(rk)))
# concurrency: 30 distinct synthetic keys marked in parallel by 3 clients
import random
ks = [f"{i:016x}" for i in range(1, 31)]
def go(k): 
    c = login("editor@team.test"); r = c.post("/projects/demo/bench/marks", data={"finding":k,"verdict":"real"}, headers=H); res.append(r.status_code)
res=[]; ts=[threading.Thread(target=go,args=(k,)) for k in ks]
[t.start() for t in ts]; [t.join() for t in ts]
mf = glob.glob(ROOT + r"\projects\demo\bench\*.marks.json"); print("marks file", mf, "statuses", sorted(set(res)))
d = json.load(open(mf[0])); print("stored marks:", len(d["marks"]), "of 30 posted")
print("file head:", json.dumps(d)[:400])
print("contains finding text 'api/status' or 'boom':", any(s in open(mf[0]).read() for s in ["api/status","boom","502"]))
