import httpx, re, json, os, time, threading, glob
B = "http://127.0.0.1:8765"; PW = "correct-horse-battery"; H = {"Origin": B}
ROOT = r"D:\autoTesting\.work\tmp\bi-A\root"
c = httpx.Client(base_url=B, follow_redirects=False, timeout=600)
assert c.post("/auth/login", data={"email":"editor@team.test","password":PW}, headers=H).status_code == 303
print("== deep nesting inside cap")
r = c.post("/projects/demo/bench/atomic-list", files={"atomic_list":("a.json", b"["*100000 + b"]"*100000)}, headers=H); print(r.status_code, r.text[:140])
r = c.post("/projects/demo/bench/atomic-list", files={"atomic_list":("a.json", b'{"items":'+b"["*100000 + b"]"*100000+b"}")}, headers=H); print(r.status_code, r.text[:140])
print("== large body: 120 MB streamed; watch spool in TMP")
SIZE = 120*1024*1024
peak = [0]; stop = [False]
def watch():
    while not stop[0]:
        tot = 0
        for f in glob.glob(r"D:\autoTesting\.work\tmp\*"):
            try:
                if os.path.isfile(f): tot = max(tot, os.path.getsize(f)) if os.path.basename(f).startswith("tmp") else tot
            except OSError: pass
        peak[0] = max(peak[0], tot); time.sleep(0.05)
threading.Thread(target=watch, daemon=True).start()
boundary = "XBOUNDARYX"
head = (f'--{boundary}\r\nContent-Disposition: form-data; name="atomic_list"; filename="a.json"\r\nContent-Type: application/json\r\n\r\n').encode()
tail = f"\r\n--{boundary}--\r\n".encode()
def gen():
    yield head
    chunk = b" " * (1024*1024)
    for _ in range(SIZE//len(chunk)): yield chunk
    yield tail
t0 = time.time()
r = c.post("/projects/demo/bench/atomic-list", content=gen(), headers={**H, "content-type": f"multipart/form-data; boundary={boundary}"})
stop[0] = True
print("status", r.status_code, r.text[:120], "secs", round(time.time()-t0,1), "peak spool file bytes seen in TMP:", peak[0])
