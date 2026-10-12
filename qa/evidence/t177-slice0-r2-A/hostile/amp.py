"""Deadline-boundary amplifier: PROBE_DEADLINE_S patched to 0.2 s so 600 iterations probe the edge in ~2 min.
usage: amp.py VARIANT N out   (A full reply near deadline | C JSON+CL+40 then silence | E no-CL keepalive JSON then silence | T thread latency)"""
import collections, json, os, random, sys, threading, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hl
from hl import PATH, Listener, good_json, http_head
launch = hl.launch
V, N, OUT = sys.argv[1], int(sys.argv[2]), sys.argv[3]
if V != "T":
    launch.PROBE_DEADLINE_S = 0.2
fetched = []
orig = launch._fetch_version
def rec(p):
    try:
        r = orig(p); fetched.append(len(r)); return r
    except BaseException as e:
        fetched.append(type(e).__name__); raise
launch._fetch_version = rec
base = set(threading.enumerate())
def beh(c):
    c.request(); j = good_json(c.port)
    if V == "A":
        c.wait(random.uniform(0.15, 0.21)); c.send(http_head(len(j)) + j)
    elif V == "C":
        c.send(http_head(len(j) + 40) + j); c.stop.wait()
    elif V == "E":
        c.send(http_head() + j); c.stop.wait()
    elif V == "T":
        c.send(http_head(len(j)) + j); c.wait(0.05)
    c.wait(0.2)
lst = Listener(beh, backlog=128)
res = collections.Counter(); walls = []; lat = []
for i in range(N):
    fetched.clear(); t0 = time.monotonic()
    try: r = launch._answers_as(lst.port, PATH)
    except BaseException as e: r = "EXC:" + repr(e)
    t1 = time.monotonic(); walls.append(t1 - t0)
    declared = len(good_json(lst.port)) + (40 if V == "C" else 0)
    got = fetched[0] if fetched else None
    if V == "T":
        t2 = time.monotonic()
        while hl.foreign_threads(base) and time.monotonic() - t2 < 2: time.sleep(0.001)
        lat.append(time.monotonic() - t1)
    if r is True:
        k = "True-full" if got == declared else f"True-TRUNCATED(got {got} of declared {declared if V in 'AC' else 'n/a'})"
    else:
        k = f"False({got if isinstance(got, str) else 'short:'+str(got)})"
    res[k] += 1
walls.sort()
s = dict(variant=V, n=N, results=dict(res), wall_min=round(walls[0], 3), wall_med=round(walls[len(walls)//2], 3), wall_max=round(walls[-1], 3),
         threads_end=hl.foreign_threads(base), open_socks=sum(x.fileno() != -1 for x in hl.SOCKS))
if lat: s["thread_gone_latency_max_s"] = round(max(lat), 4); s["latency_gt_0.1s"] = sum(l > 0.1 for l in lat)
print(json.dumps(s, indent=1)); json.dump(s, open(OUT, "w"), indent=1); lst.stop()
