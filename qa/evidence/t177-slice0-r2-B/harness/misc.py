import json, socket, time, sys
import h
import attacks as A
from autotester.browser import launch as L
out = {}
# 1) race: right identity, length-less, never closes. Does the watchdog firing a hair early turn truncation into success?
L.PROBE_DEADLINE_S = 0.2
res = {"returned_body": 0, "raised": {}, "answers_true": 0}
GUID = "/devtools/browser/abc"
lst = A.Listener(A.right_then_hold, {"guid": GUID, "real_port": 0, "other": None})
N = 300
for _ in range(N):
    try:
        b = L._fetch_version(lst.port); res["returned_body"] += 1
    except BaseException as e:
        k = type(e).__name__; res["raised"][k] = res["raised"].get(k, 0) + 1
    if L._answers_as(lst.port, GUID): res["answers_true"] += 1
out["race_lengthless_hold_N300_deadline0.2"] = res
lst.stop = True
# 1b) same with the real 2.0 s deadline, 6 trials via _answers_as
L.PROBE_DEADLINE_S = 2.0
lst2 = A.Listener(A.right_then_hold, {"guid": GUID, "real_port": 0, "other": None})
t = []; ans = []
for _ in range(6):
    t0 = time.monotonic(); ans.append(L._answers_as(lst2.port, GUID)); t.append(round(time.monotonic() - t0, 3))
out["race_real_deadline_6"] = {"answers": ans, "durations": t}
lst2.stop = True

# 2) _reaches_past_loopback
def timed(port):
    t0 = time.monotonic(); r = L._reaches_past_loopback(port); return r, round(time.monotonic() - t0, 2)
s1 = socket.socket(); s1.bind(("127.0.0.1", 0)); s1.listen(5)
out["bound_127.0.0.1_only"] = timed(s1.getsockname()[1])
s2 = socket.socket(); s2.bind(("127.0.0.2", 0)); s2.listen(5)
out["bound_127.0.0.2 (accepts on the alias, stand-in for a wildcard bind)"] = timed(s2.getsockname()[1])
s3 = socket.socket(); s3.bind(("127.0.0.2", 0)); s3.listen(0)
fill = []
for _ in range(8):
    f = socket.socket(); f.setblocking(False); f.connect_ex(("127.0.0.2", s3.getsockname()[1])); fill.append(f)
time.sleep(0.3)
out["bound_127.0.0.2_full_backlog (probe times out)"] = timed(s3.getsockname()[1])
out["closed_port"] = timed(1)
print(json.dumps(out, indent=1))
