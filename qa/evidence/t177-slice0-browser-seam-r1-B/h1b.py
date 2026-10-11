import os, sys, json, time, threading, socket
sys.argv=[sys.argv[0]]
import importlib.util
spec = importlib.util.spec_from_file_location("h1", os.path.join(os.path.dirname(__file__), "h1.py")); h1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(h1)
class Drip(h1.Hostile):
    def serve(self, c):
        self.hits += 1; self.t_first = time.monotonic()
        try:
            c.settimeout(3); buf=b""
            while b"\r\n\r\n" not in buf: buf += c.recv(4096)
            c.sendall(b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n")
            while time.monotonic() - self.t_first < 25:   # one byte per second, well inside the probe's 2 s per-read timeout
                c.sendall(b" "); time.sleep(1)
        except OSError: pass
        finally: c.close()
d = Drip(b""); root = h1.WORK/"drip"; root.mkdir(parents=True, exist_ok=True); profile = root/"profiles"/"pathlynks"
orig = h1.launch._published; st={}
def patched(pd, dl):
    port, path = orig(pd, dl); st["real_port"]=port; return d.port, path
h1.launch._published = patched
s = h1.fresh_session(root); t0=time.monotonic(); exc=None
def watch():
    time.sleep(12); print(json.dumps({"at_12s": "start() still running", "real_port_accepts": h1.accepts("127.0.0.1", st.get("real_port",0)), "procs": h1.procs_for(profile)}), flush=True)
threading.Thread(target=watch, daemon=True).start()
try: s.start()
except BaseException as e: exc=e
print(json.dumps({"case":"drip","start_returned_after_s": round(time.monotonic()-t0,1), "raised": repr(exc)[:150], "procs_after": h1.procs_for(profile), "port_file": (profile/"DevToolsActivePort").exists()}), flush=True)
