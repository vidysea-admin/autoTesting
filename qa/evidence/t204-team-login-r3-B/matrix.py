"""Startup matrix driver (checker B, t204 r3). Real uvicorn subprocesses, scrubbed env, fake values."""
import http.client, itertools, json, os, shutil, socket, subprocess, sys, time, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

W = Path(os.environ["R3W"])
PY = str(W / "copy/.venv/Scripts/python.exe")
LAN = "192.168.1.4"
PW = "Zx-fake-canary-9317-Aq"
OUT = W / "ev-matrix"
OUT.mkdir(exist_ok=True)
BASE_ENV = {k: os.environ[k] for k in ("SystemRoot", "PATH", "TEMP", "TMP") if k in os.environ}
BASE_ENV["PYTHONUTF8"] = "1"
_port = itertools.count(int(os.environ.get("R3PORT0", "20000")))
_lock = threading.Lock()


def next_port():
    with _lock:
        return next(_port)


def connect_addr(bind):
    return {"127.0.0.1": "127.0.0.1", "::1": "::1", LAN: LAN, "0.0.0.0": "127.0.0.1", "::": "::1"}[bind]


def req(addr, port, method, path, host, origin=None, form=None, timeout=15):
    fam = socket.AF_INET6 if ":" in addr else socket.AF_INET
    c = http.client.HTTPConnection(addr, port, timeout=timeout)
    c.sock = socket.socket(fam, socket.SOCK_STREAM)
    c.sock.settimeout(timeout)
    c.sock.connect((addr, port, 0, 0) if fam == socket.AF_INET6 else (addr, port))
    hdr = {"Host": host}
    if origin:
        hdr["Origin"] = origin
    body = None
    if form is not None:
        from urllib.parse import urlencode
        body = urlencode(form)
        hdr["Content-Type"] = "application/x-www-form-urlencoded"
    c.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
    for k, v in hdr.items():
        c.putheader(k, v)
    c.putheader("Content-Length", str(len(body.encode()) if body else 0))
    c.endheaders(body.encode() if body else None)
    r = c.getresponse()
    data = r.read()
    c.close()
    return r.status, dict(r.getheaders()), data[:300].decode("utf8", "replace")


def run_row(row):
    rid = row["id"]
    port = next_port()
    root = OUT / f"root-{rid}"
    if root.exists():
        shutil.rmtree(root)
    shutil.copytree(W / "tpl", root)
    lan_origin = f"http://{LAN}:{port}"
    bind = row["bind"]
    # the origin a user of this deployment opens
    po = row["public_origin"]  # None=unset, ''=empty, or a template with {p}
    po_val = None if po is None else po.replace("{p}", str(port))
    if row.get("user_origin"):
        uo = row["user_origin"].replace("{p}", str(port))
    elif po_val and not po_val.startswith(("http://localhost", "https://localhost", "http://127.", "http://[::1]")):
        uo = po_val
    elif bind in ("127.0.0.1",):
        uo = f"http://localhost:{port}"
    elif bind == "::1":
        uo = f"http://[::1]:{port}"
    else:
        uo = lan_origin
    uhost = uo.split("://", 1)[1]
    lists = row["lists"]
    env = dict(BASE_ENV)
    env["AUTOTESTER_ROOT"] = str(root)
    env["AUTOTESTER_FIRST_ADMIN_EMAIL"] = "admin@test.example"
    if row.get("hosted", True):
        env["AUTOTESTER_HOSTED"] = "1"
    if uo.startswith("http://"):
        env["AUTOTESTER_COOKIE_SECURE"] = "0"
    if po_val is not None:
        env["AUTOTESTER_PUBLIC_ORIGIN"] = po_val
    if lists == "both":
        env["AUTOTESTER_ALLOWED_HOSTS"] = uhost
        env["AUTOTESTER_ALLOWED_ORIGINS"] = uo
    elif lists == "hosts":
        env["AUTOTESTER_ALLOWED_HOSTS"] = uhost
    elif lists == "origins":
        env["AUTOTESTER_ALLOWED_ORIGINS"] = uo
    elif lists == "wrong":
        env["AUTOTESTER_ALLOWED_HOSTS"] = f"10.9.9.9:{port}"
        env["AUTOTESTER_ALLOWED_ORIGINS"] = f"http://10.9.9.9:{port}"
    log = OUT / f"{rid}.log"
    host_arg = bind
    with open(log, "wb") as lf:
        p = subprocess.Popen([PY, "-I", "-m", "uvicorn", "autotester.ui.app:app", "--host", host_arg,
                              "--port", str(port), "--no-access-log"], cwd=root, env=env,
                             stdout=lf, stderr=subprocess.STDOUT)
        res = {"id": rid, "bind": bind, "public_origin": po_val, "lists": lists, "hosted": row.get("hosted", True),
               "user_origin": uo, "port": port, "pid": p.pid}
        try:
            addr = connect_addr(bind)
            t0 = time.time()
            up = False
            while time.time() - t0 < 60:
                if p.poll() is not None:
                    break
                try:
                    s = socket.socket(socket.AF_INET6 if ":" in addr else socket.AF_INET)
                    s.settimeout(1)
                    s.connect((addr, port, 0, 0) if ":" in addr else (addr, port))
                    s.close()
                    up = True
                    break
                except OSError:
                    time.sleep(0.4)
            if p.poll() is not None or not up:
                time.sleep(0.5)
                code = p.poll()
                res["started"] = False
                res["exit"] = code
                res["timeout_no_listen"] = (code is None)
            else:
                res["started"] = True
                try:
                    st, h, b = req(addr, port, "GET", "/auth/login", uhost)
                    res["get_login"] = st
                    st2, h2, b2 = req(addr, port, "POST", "/auth/login", uhost, origin=uo,
                                      form={"email": "admin@test.example", "password": PW, "next": "/"})
                    res["post_login"] = st2
                    res["cookie"] = "set-cookie" in {k.lower() for k in h2}
                    st3, _, _ = req(addr, port, "POST", "/auth/login", uhost, origin="http://evil.example",
                                    form={"email": "admin@test.example", "password": PW, "next": "/"})
                    res["post_foreign_origin"] = st3
                except Exception as e:
                    res["req_error"] = repr(e)
        finally:
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(10)
                except Exception:
                    p.kill()
    txt = log.read_text("utf8", "replace")
    lines = [l for l in txt.splitlines() if l.strip()]
    res["tail"] = lines[-2:] if lines else []
    res["traceback"] = "Traceback" in txt
    res["autoerr"] = next((l for l in lines if "AuthConfigError" in l), "")
    shutil.rmtree(root, ignore_errors=True)
    return res


def rows():
    out = []
    pos = [("unset", None), ("empty", ""), ("lo-http", "http://localhost:{p}"), ("lo-https", "https://localhost"),
           ("lo-127", "http://127.0.0.1:{p}"), ("lan", "http://" + LAN + ":{p}"), ("domain", "https://qa.example.com")]
    binds = ["127.0.0.1", "::1", LAN, "0.0.0.0", "::"]
    n = 0
    for b in binds:
        for pn, pv in pos:
            for l in ["unset", "both", "hosts", "origins", "wrong"]:
                n += 1
                out.append(dict(id=f"M{n:03d}-{b.replace(':','c')}-{pn}-{l}", bind=b, public_origin=pv, lists=l))
    # compose-rendered environments (bind 0.0.0.0) per docker compose config
    comp = [("neither", "", "lan"), ("domain-only", "https://qa.example.com", "domain"),
            ("explicit-origin", "http://" + LAN + ":{p}", "lan")]
    for name, pv, scen in comp:
        for l in ["unset", "both", "hosts", "origins", "wrong"]:
            n += 1
            out.append(dict(id=f"C{n:03d}-compose-{name}-{l}", bind="0.0.0.0", public_origin=pv, lists=l))
    # HOSTED unset on a wildcard bind (operator forgot AUTOTESTER_HOSTED=1)
    for pn, pv in [("unset", None), ("lan", "http://" + LAN + ":{p}")]:
        for l in ["unset", "both", "wrong"]:
            n += 1
            out.append(dict(id=f"H{n:03d}-0.0.0.0-nohosted-{pn}-{l}", bind="0.0.0.0", public_origin=pv, lists=l, hosted=False))
    return out


if __name__ == "__main__":
    allrows = rows()
    sel = sys.argv[1] if len(sys.argv) > 1 else None
    if sel:
        allrows = [r for r in allrows if sel in r["id"]]
    print(len(allrows), "rows", flush=True)
    results = []
    with ThreadPoolExecutor(int(os.environ.get("R3WORKERS", "6"))) as ex:
        for r in ex.map(run_row, allrows):
            results.append(r)
            print(json.dumps(r), flush=True)
    (OUT / ("results-%s.json" % (sel or "all"))).write_text(json.dumps(results, indent=1))
