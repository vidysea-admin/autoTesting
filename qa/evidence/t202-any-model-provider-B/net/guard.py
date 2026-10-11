import socket, sys, traceback
ATT = []
def _rec(kind, args):
    st = [f"{f.filename.split('site-packages')[-1].split('src')[-1]}:{f.lineno}" for f in traceback.extract_stack()[-6:-2]]
    ATT.append((kind, repr(args)[:100], st))
    raise OSError(f"BLOCKED {kind} {args!r}")
def install():
    socket.socket.connect = lambda s, a: _rec("connect", a)
    socket.socket.connect_ex = lambda s, a: _rec("connect_ex", a)
    socket.socket.sendto = lambda s, *a: _rec("sendto", a[-1])
    socket.getaddrinfo = lambda *a, **k: _rec("getaddrinfo", a[:2])
    socket.gethostbyname = lambda *a: _rec("gethostbyname", a)
    socket.gethostbyname_ex = lambda *a: _rec("gethostbyname_ex", a)
    socket.create_connection = lambda a, *x, **k: _rec("create_connection", a)
    import _socket
    _socket.getaddrinfo = lambda *a, **k: _rec("_getaddrinfo", a[:2])
def report(tag):
    print(f"[{tag}] socket attempts: {len(ATT)}")
    for a in ATT: print("   ", a)
