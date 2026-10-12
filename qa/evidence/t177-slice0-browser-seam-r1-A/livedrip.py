import os, sys, threading, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hostile as h, live as L
from autotester.browser import launch
root, s = L.mk("drip")
conns = []
def drip(c):
    conns.append(c); h.readreq(c); c.sendall(b"HTTP/1.0 200 OK\r\n\r\n")
    try:
        while True:
            c.sendall(b" "); time.sleep(0.5)
    except OSError:
        pass
port, stop0 = h.serve(drip)
def stop():
    stop0()
    for c in conns:
        try: c.close()
        except OSError: pass
launch._published = lambda pd, dl: (port, h.GUID)   # port file "points" at the dripping listener
def midway():
    time.sleep(10)
    pf = s.paths.profile_dir / "DevToolsActivePort"
    real = int(pf.read_text().splitlines()[0]) if pf.exists() else None
    n = len([d for d in L.descendants() if "chrome" in d[1].lower() or "headless" in d[1].lower()])
    print("after 10s, start() has NOT returned: real chromium port", real, "open =", L.accepts(real) if real else None,
          "| chromium descendants =", n, flush=True)
    stop()
threading.Thread(target=midway, daemon=True).start()
t0 = time.time()
try:
    s.start(); print("start() returned")
except BaseException as e:
    print("start() raised", type(e).__name__, "after", round(time.time() - t0, 1), "s")
L.after("post", s, None)
s.close()
