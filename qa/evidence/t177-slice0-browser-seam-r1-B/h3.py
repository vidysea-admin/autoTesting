import os, socket, sys, time, json, threading, multiprocessing as mp, errno
SRC = os.environ["R1B_SRC"]; sys.path.insert(0, SRC + "/src")
from autotester.browser import launch
def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try: s.connect(("192.0.2.1", 9)); return s.getsockname()[0]
    finally: s.close()
LAN = lan_ip()
def free_closed_port():
    s = socket.socket(); s.bind(("127.0.0.1",0)); p = s.getsockname()[1]; s.close(); return p
def conn(host, port, timeout):
    t=time.monotonic()
    try:
        socket.create_connection((host,port),timeout=timeout).close(); r="CONNECTED"
    except BaseException as e:
        r=f"{type(e).__name__}(errno={getattr(e,'errno',None)},winerr={getattr(e,'winerror',None)})"
    return r, round(time.monotonic()-t,2)
out = {"lan": LAN, "closed_port_measure": {}}
cp = free_closed_port()
for host in ("127.0.0.1","127.0.0.2",LAN):
    out["closed_port_measure"][host] = {"timeout=1": conn(host,cp,1), "timeout=6": conn(host,cp,6)}
# listener on 127.0.0.1 only (legit): probe 127.0.0.2 and LAN
lis = socket.socket(); lis.bind(("127.0.0.1",0)); lis.listen(128); lp = lis.getsockname()[1]
out["loopback_only_listener"] = {h: {"timeout=1": conn(h,lp,1)} for h in ("127.0.0.2",LAN)}
out["func_on_loopback_only_listener"] = launch._reaches_past_loopback(lp)
# wildcard listener, idle
w = socket.socket(); w.bind(("0.0.0.0",0)); w.listen(128); wp = w.getsockname()[1]
out["wildcard_idle"] = {"127.0.0.2": conn("127.0.0.2",wp,1), "func": launch._reaches_past_loopback(wp)}
w.close(); lis.close()
# wildcard listener whose accept queue is full (backlog 1, never accept), then probe
w = socket.socket(); w.bind(("0.0.0.0",0)); w.listen(1); wp = w.getsockname()[1]
fill=[]
for i in range(6):
    s=socket.socket(); s.settimeout(0.5)
    try: s.connect(("127.0.0.1",wp)); fill.append(s)
    except OSError: s.close()
out["wildcard_backlog_full"] = {"filled": len(fill), "127.0.0.1 probe": conn("127.0.0.1",wp,1), "127.0.0.2 probe": conn("127.0.0.2",wp,1), "func": launch._reaches_past_loopback(wp)}
for s in fill: s.close()
w.close()
print(json.dumps(out), flush=True)
