# wildcard HTTP listener under CPU load: how often does _reaches_past_loopback say False (= "passes as loopback-only")?
import os, socket, sys, time, json, threading, multiprocessing as mp
SRC = os.environ["R1B_SRC"]; sys.path.insert(0, SRC + "/src")
def burn(stop):
    while not stop.is_set(): sum(i*i for i in range(10000))
if __name__ == "__main__":
    from autotester.browser import launch
    from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            b=b"{}"; self.send_response(200); self.send_header("Content-Length","2"); self.end_headers(); self.wfile.write(b)
        def log_message(self,*a): pass
    srv = ThreadingHTTPServer(("0.0.0.0",0),H); port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever,daemon=True).start()
    N = int(os.environ.get("N","100")); res = {}
    def run(label):
        t=[]; falses=0
        for _ in range(N):
            a=time.monotonic(); r=launch._reaches_past_loopback(port); t.append(time.monotonic()-a); falses += (r is False)
        res[label]={"n":N,"false(=passes as loopback-only)":falses,"max_s":round(max(t),3),"mean_s":round(sum(t)/len(t),4)}
    run("idle")
    stop = mp.Event(); ps=[mp.Process(target=burn,args=(stop,)) for _ in range((os.cpu_count() or 4)*3)]
    for p in ps: p.start()
    time.sleep(2); run(f"cpu_load_{len(ps)}_burners")
    stop.set(); [p.join(5) for p in ps]
    print(json.dumps(res), flush=True)
