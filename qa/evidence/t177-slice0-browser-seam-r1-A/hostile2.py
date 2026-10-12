import sys, time, threading, socket, pathlib, tempfile, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hostile as h
from autotester.browser import launch
import tracemalloc; tracemalloc.start()
# huge body
t0=time.time(); m0=tracemalloc.get_traced_memory()[0]
h.run("huge 300MB body", h.huge, limit=60)
print("  peak traced MB", tracemalloc.get_traced_memory()[1]//1_000_000, "elapsed", round(time.time()-t0,1))
# drip
h.run("drip 1 byte/0.5s forever", h.drip, limit=20)
# redirects
good=b'{"webSocketDebuggerUrl":"ws://x'+h.GUID.encode()+b'"}'
hits=[]
def target(c):
    h.readreq(c); hits.append(1); c.sendall(h.http(good)); c.close()
tp,tstop=h.serve(target)
def redir(c):
    h.readreq(c); c.sendall(b"HTTP/1.1 302 Found\r\nLocation: http://127.0.0.1:%d/json/version\r\nContent-Length: 0\r\n\r\n"%tp); c.close()
h.run("redirect to other loopback port (valid json)", redir)
print("  redirect target contacted:", len(hits))
def redir_loop(c):
    h.readreq(c); c.sendall(b"HTTP/1.1 302 Found\r\nLocation: /json/version\r\nContent-Length: 0\r\n\r\n"); c.close()
h.run("redirect loop", redir_loop)
def redir_ext(c):
    h.readreq(c); c.sendall(b"HTTP/1.1 302 Found\r\nLocation: http://192.0.2.1:9/json/version\r\nContent-Length: 0\r\n\r\n"); c.close()
h.run("redirect to non-loopback host (TEST-NET)", redir_ext, limit=30)
def redir_file(c):
    h.readreq(c); c.sendall(b"HTTP/1.1 302 Found\r\nLocation: file:///C:/Windows/win.ini\r\nContent-Length: 0\r\n\r\n"); c.close()
h.run("redirect to file://", redir_file)
