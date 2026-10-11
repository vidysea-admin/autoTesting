import socket, threading, sys, tempfile, time, pathlib, json
from autotester.browser import launch
GUID="/devtools/browser/aaaa-bbbb"
def serve(handler):
    s=socket.socket(); s.bind(("127.0.0.1",0)); s.listen(5); port=s.getsockname()[1]
    stop=threading.Event()
    def loop():
        s.settimeout(0.2)
        while not stop.is_set():
            try: c,_=s.accept()
            except OSError: continue
            threading.Thread(target=handler,args=(c,),daemon=True).start()
    threading.Thread(target=loop,daemon=True).start()
    return port,(lambda:(stop.set(),s.close()))
def readreq(c):
    c.settimeout(2)
    try: c.recv(4096)
    except OSError: pass
def http(body,status=b"200 OK",extra=b""):
    return b"HTTP/1.0 "+status+b"\r\n"+extra+b"Content-Type: application/json\r\n\r\n"+body
def raw(b):
    def h(c): readreq(c); c.sendall(b); c.close()
    return h
def nothing(c): readreq(c); time.sleep(30)
def drip(c):
    readreq(c); c.sendall(b"HTTP/1.0 200 OK\r\n\r\n")
    try:
        while True: c.sendall(b" "); time.sleep(0.5)
    except OSError: pass
def huge(c):
    readreq(c); c.sendall(b"HTTP/1.0 200 OK\r\n\r\n")
    try:
        chunk=b" "*1_000_000
        for _ in range(300): c.sendall(chunk)   # 300 MB
    except OSError: pass
    c.close()
def reset(c):
    readreq(c); c.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,b"\x01\0\0\0\0\0\0\0"); c.close()
def trunc(c):
    readreq(c); c.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 500\r\n\r\n{\"webSocketDebuggerUrl\":"); c.close()
cases={
 "non-http bytes":raw(b"garbage\r\n"),
 "json list":raw(http(b"[]")),"json str":raw(http(b'"x"')),"json null":raw(http(b"null")),"json num":raw(http(b"7")),
 "json dict ws=list":raw(http(b'{"webSocketDebuggerUrl":["x"]}')),
 "deep nesting 200k":raw(http(b"["*200000)),
 "deep nesting 200k closed":raw(http(b"["*200000+b"]"*200000)),
 "deep obj":raw(http(b'{"a":'*100000)),
 "bad utf8":raw(http(b"\xff\xfe\xfa{")),
 "bigint digits":raw(http(b"1"*50000)),
 "http 500":raw(http(b"{}",b"500 ERR")),
 "reset":reset,"truncated body":trunc,
 "empty reply":raw(b""),
 "accept never reply (timeout)":nothing,
}
def run(name,handler,limit=25):
    port,stop=serve(handler)
    d=pathlib.Path(tempfile.mkdtemp()); (d/launch.PORT_FILE).write_text(f"{port}\n{GUID}\n")
    res={}
    def t():
        t0=time.time()
        try: res["r"]=("returned",launch.verified_cdp_url(d))
        except BaseException as e: res["r"]=(type(e).__name__,str(e)[:70])
        res["s"]=time.time()-t0
    th=threading.Thread(target=t,daemon=True); th.start(); th.join(limit)
    if th.is_alive(): print(f"{name:34s} HANG >{limit}s (no exception)")
    else: print(f"{name:34s} {res['r'][0]:18s} {res['s']:.1f}s {res['r'][1]}")
    stop()
if __name__=="__main__":
    sel=sys.argv[1:]
    for n,h in cases.items(): 
        if not sel or n in sel: run(n,h)
