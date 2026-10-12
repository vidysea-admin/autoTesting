import json, sys, threading
for name, b in [("[x30000", b"["*30000), ("{a:x13000", b'{"a":'*13000), ("[xcap", b"["*65536), ("{a:xcap", (b'{"a":'*13107).ljust(65536, b"[")), ("[xcap in 1MB-thread", None)]:
    if b is None: continue
    try: json.loads(b); print(name, "parsed")
    except BaseException as e: print(name, type(e).__name__)
# raised recursion limit scenario
lim = int(sys.argv[1]) if len(sys.argv) > 1 else 0
if lim:
    sys.setrecursionlimit(lim)
    def run():
        try: json.loads(b"["*65536); print("lim", lim, "parsed")
        except BaseException as e: print("lim", lim, type(e).__name__)
    if len(sys.argv) > 2:
        t = threading.Thread(target=run); t.start(); t.join()
    else: run()
