"""Own probe: a wildcard-bound listener (0.0.0.0) with a full accept queue; does launch._reaches_past_loopback say 'beyond loopback'?"""
import socket, time, sys
sys.path.insert(0, sys.argv[1] + "/src")
import autotester
from autotester.browser import launch
print("autotester:", autotester.__file__)
def run(label, bind, fill):
    ls = socket.socket(); ls.bind((bind, 0)); ls.listen(1); port = ls.getsockname()[1]
    held = []
    if fill:
        for _ in range(8):
            c = socket.socket(); c.setblocking(False)
            try: c.connect_ex(("127.0.0.1", port))
            except OSError: pass
            held.append(c)
        time.sleep(0.3)
    t = time.monotonic(); r = launch._reaches_past_loopback(port); dt = time.monotonic() - t
    raw_t = time.monotonic()
    try:
        socket.create_connection(("127.0.0.2", port), timeout=1).close(); raw = "connected"
    except Exception as e: raw = type(e).__name__
    print(f"{label:46s} reaches_past_loopback={r!s:5s} took={dt:.2f}s  raw 127.0.0.2 connect: {raw} ({time.monotonic()-raw_t:.2f}s)")
    for c in held: c.close()
    ls.close()
run("wildcard bind, empty queue", "0.0.0.0", False)
run("wildcard bind, accept queue FULL", "0.0.0.0", True)
run("loopback-only bind (127.0.0.1)", "127.0.0.1", False)
run("loopback-only bind, queue full", "127.0.0.1", True)
