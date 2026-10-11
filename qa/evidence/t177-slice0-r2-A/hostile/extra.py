"""Extra bounds: header-memory ceiling, 100-Continue byte rate, headers with a valid body after."""
import json, os, sys, time, threading, tracemalloc
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hl
from hl import PATH, Listener, good_json, http_head
launch = hl.launch
rows = []
def run(name, beh, pre=None):
    lst = Listener(beh); hl.reset_client(); base = set(threading.enumerate())
    tracemalloc.start()
    t0 = time.monotonic(); r = launch._answers_as(lst.port, PATH); dt = time.monotonic() - t0
    peak = tracemalloc.get_traced_memory()[1]; tracemalloc.stop()
    row = dict(case=name, ret=r, wall=round(dt, 3), client_bytes=hl.CLIENT_BYTES[0], listener_sent=lst.sent,
               py_peak_alloc_MB=round(peak / 1e6, 1), threads=hl.foreign_threads(base))
    rows.append(row); print(row, flush=True); lst.stop()

def hdr_heavy(n, size):
    def f(c):
        c.request(); j = good_json(c.port)
        extra = "".join(f"X-H{i}: {'a' * size}\r\n" for i in range(n))
        c.send(http_head(len(j), extra) + j); c.wait(0.5)
    return f
run("97 headers x 65000B then VALID good body", hdr_heavy(97, 65000))
run("98 headers x 65000B then VALID good body (101st header total -> too many?)", hdr_heavy(98, 65000))
def cont_heavy(c):  # each 100 response carries 90 x 64000B headers, forever
    c.request(); blob = (b"HTTP/1.1 100 Continue\r\n" + b"".join(b"X: " + b"a" * 64000 + b"\r\n" for _ in range(90)) + b"\r\n")
    while c.send(blob):
        pass
run("100-Continue each with 90x64KB headers, forever", cont_heavy)
json.dump(rows, open(sys.argv[1], "w"), indent=1)
