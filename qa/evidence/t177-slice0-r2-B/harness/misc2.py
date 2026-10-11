import json, time, threading
import h
import attacks as A
from autotester.browser import launch as L
out = {}
def hdr_flood(c, l):
    l.send(c, b"HTTP/1.1 200 OK\r\n")
    line = b"X: " + b"a" * 60000 + b"\r\n"
    while not l.stop: l.send(c, line)
def cont_flood(c, l):
    while not l.stop: l.send(c, b"HTTP/1.1 100 Continue\r\n\r\n")
for name, hd in (("header_flood_60KB_lines", hdr_flood), ("100_continue_flood", cont_flood)):
    lst = A.Listener(hd, {"guid": "/devtools/browser/x", "real_port": 0, "other": None})
    t = time.monotonic(); r = L._answers_as(lst.port, "/devtools/browser/x"); d = time.monotonic() - t
    time.sleep(0.3); lst.stop = True
    out[name] = {"answers_as": r, "held_s": round(d, 2), "listener_bytes_sent": lst.sent, "timers": h.timers()}
print(json.dumps(out, indent=1))
