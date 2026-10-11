import os, subprocess, sys, time, shutil, hashlib, http.client, json, urllib.parse
B = r"C:\Users\Lenovo\AppData\Local\Temp\claude\r3b-43931685"
PY = B + r"\copy\.venv\Scripts\python.exe"
EV = B + r"\ev-A"
ADMIN = ("admin@test.example", "Zx-fake-canary-9317-Aq")
def start(name, port):
    root = os.path.join(B, name)
    if os.path.exists(root): shutil.rmtree(root)
    shutil.copytree(os.path.join(B, "tpl"), root)
    env = {k: os.environ[k] for k in ("SystemRoot", "TEMP", "TMP") if k in os.environ}; env["PATH"] = os.environ["SystemRoot"] + "\System32"
    env.update(PYTHONUTF8="1", AUTOTESTER_ROOT=root)
    log = open(os.path.join(EV, f"{name}-server.log"), "wb")
    p = subprocess.Popen([PY, "-m", "uvicorn", "autotester.ui.app:app", "--host", "127.0.0.1",
        "--port", str(port), "--no-access-log"], cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
    open(os.path.join(EV, f"{name}-pid.txt"), "w").write(str(p.pid))
    for _ in range(60):
        try:
            r = req(port, "GET", "/auth/login"); 
            if r[0] == 200: return p, root
        except Exception: pass
        time.sleep(0.5)
    raise SystemExit("server did not start")
def req(port, method, path, headers=None, body=None, host=None, origin="auto", cookie=None):
    h = {"Host": host or f"127.0.0.1:{port}"}
    if origin == "auto":
        if method in ("POST","PUT","PATCH","DELETE"): h["Origin"] = f"http://127.0.0.1:{port}"
    elif origin is not None: h["Origin"] = origin
    if cookie: h["Cookie"] = cookie
    h.update(headers or {})
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    c.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
    for k, v in h.items(): c.putheader(k, v)
    if body is not None: c.putheader("Content-Length", str(len(body)))
    elif method in ("POST","PUT","PATCH"): c.putheader("Content-Length", "0")
    c.endheaders(body if body is not None else None)
    r = c.getresponse(); data = r.read()
    hd = r.getheaders(); c.close()
    return r.status, hd, data
def form(d): return urllib.parse.urlencode(d).encode(), {"Content-Type": "application/x-www-form-urlencoded"}
def multipart(fields, files):
    bd = "----fakeboundary7731"; parts = []
    for k, v in fields.items():
        parts.append(f'--{bd}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    for k, (fn, content, ct) in files.items():
        parts.append(f'--{bd}\r\nContent-Disposition: form-data; name="{k}"; filename="{fn}"\r\nContent-Type: {ct}\r\n\r\n'.encode() + content + b"\r\n")
    parts.append(f"--{bd}--\r\n".encode())
    return b"".join(parts), {"Content-Type": f"multipart/form-data; boundary={bd}"}
def cookie_of(hd):
    for k, v in hd:
        if k.lower() == "set-cookie": return v.split(";")[0]
def login(port, email, pw):
    b, h = form({"email": email, "password": pw})
    s, hd, d = req(port, "POST", "/auth/login", h, b)
    return s, cookie_of(hd), hd
def treehash(root):
    items = []
    for dp, dn, fn in os.walk(root):
        for f in fn:
            p = os.path.join(dp, f); rel = os.path.relpath(p, root).replace("\\", "/")
            try: items.append((rel, hashlib.sha256(open(p, "rb").read()).hexdigest()))
            except OSError as e: items.append((rel, "ERR"))
    return dict(sorted(items))
def stop(p):
    subprocess.run(["taskkill","/PID",str(p.pid),"/F","/T"],capture_output=True)
    try: p.wait(10)
    except Exception: p.kill()
