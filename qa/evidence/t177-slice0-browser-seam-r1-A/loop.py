import socket, time, threading
from autotester.browser import launch
def t(label, port):
    t0=time.time(); r=launch._reaches_past_loopback(port); print(f"{label:50s} reaches={r} {time.time()-t0:.2f}s")
def raw(label, host, port):
    t0=time.time()
    try: socket.create_connection((host,port),timeout=1).close(); res="connected"
    except BaseException as e: res=f"{type(e).__name__} errno={getattr(e,'errno',None)}"
    print(f"{label:50s} {res} {time.time()-t0:.2f}s")
# loopback-only listener
a=socket.socket(); a.bind(("127.0.0.1",0)); a.listen(5); pa=a.getsockname()[1]
raw("127.0.0.2 -> loopback-only listener port", "127.0.0.2", pa); t("loopback-only accepting listener", pa)
# wildcard accepting
w=socket.socket(); w.bind(("0.0.0.0",0)); w.listen(5); pw=w.getsockname()[1]
threading.Thread(target=lambda: [w.accept() for _ in range(50)],daemon=True).start()
t("wildcard listener, accepting", pw)
# wildcard with full backlog, never accepts
f=socket.socket(); f.bind(("0.0.0.0",0)); f.listen(1); pf=f.getsockname()[1]
fill=[]
for i in range(8):
    c=socket.socket(); c.setblocking(False)
    try: c.connect_ex(("127.0.0.1",pf))
    except OSError: pass
    fill.append(c)
time.sleep(0.5)
t("wildcard listener, backlog full, not accepting", pf)
# closed port
c=socket.socket(); c.bind(("127.0.0.1",0)); pc=c.getsockname()[1]; c.close()
raw("127.0.0.2 -> CLOSED port", "127.0.0.2", pc)
raw("127.0.0.1 -> CLOSED port", "127.0.0.1", pc)
t("closed port", pc)
# wildcard v6 dual-stack
