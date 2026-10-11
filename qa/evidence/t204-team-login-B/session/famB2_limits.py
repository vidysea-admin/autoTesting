"""Child: one request of one kind/size in a fresh process; prints elapsed and memory. Parent: runs the matrix."""
import os, sys, json, time, subprocess, ctypes
from ctypes import wintypes

if len(sys.argv) > 1 and sys.argv[1] == "child":
    kind, field, size = sys.argv[2], sys.argv[3], int(sys.argv[4])
    sys.path.insert(0, os.environ["T204B_SRC"])
    from fastapi.testclient import TestClient
    import tracemalloc

    class PMC(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

    def peak():
        k = ctypes.windll.kernel32
        k.GetCurrentProcess.restype = wintypes.HANDLE
        pm = PMC(); pm.cb = ctypes.sizeof(pm)
        ctypes.windll.psapi.GetProcessMemoryInfo(wintypes.HANDLE(k.GetCurrentProcess()), ctypes.byref(pm), pm.cb)
        return pm.PeakWorkingSetSize / 1e6, pm.WorkingSetSize / 1e6

    from autotester.ui.app import app
    from autotester.auth import accounts
    accounts.signup("known@team.test", "Zq7-canary-warm0000")
    c = TestClient(app, follow_redirects=False, raise_server_exceptions=False)
    c.post("/auth/login", data={"email": "known@team.test", "password": "wrong-password-1"})   # warm argon2 + sqlite
    big = "a" * size
    email = "known@team.test"
    pw = "Zq7-canary-warm0000"
    if field == "password":
        pw = big
    else:
        email = big + "@team.test"
    path = {"login": "/auth/login", "signup": "/auth/signup", "control": "/auth/logout"}[kind]
    if kind == "signup":
        email = email if field == "email" else "newuser@team.test"
    from urllib.parse import urlencode
    body = urlencode({"email": email, "password": pw}).encode()
    del big
    peak0, ws0 = peak()
    tracemalloc.start()
    t = time.perf_counter()
    r = c.post(path, content=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    dt = time.perf_counter() - t
    _, tm_peak = tracemalloc.get_traced_memory()
    peak1, ws1 = peak()
    print(json.dumps({"kind": kind, "field": field, "size": size, "status": r.status_code, "seconds": round(dt, 2), "body_mb": round(len(body) / 1e6, 1),
                      "peakWS_delta_mb": round(peak1 - peak0, 0), "tracemalloc_peak_mb": round(tm_peak / 1e6, 0)}))
    sys.exit(0)

# ---- parent
BASE = os.environ["T204B_BASE"]
SRC = "D:/autoTesting/.worktrees/t204-team-login/src"
PY = "D:/autoTesting/.worktrees/t204-team-login/.venv/Scripts/python.exe"
n = 0
for kind, field in [("control", "password"), ("login", "password"), ("login", "email"), ("signup", "password"), ("signup", "email")]:
    for size in (129, 10**6, 50 * 10**6):
        n += 1
        root = os.path.join(BASE, f"famB2_{n}")
        os.makedirs(root, exist_ok=True)
        env = {k: os.environ[k] for k in ("SYSTEMROOT", "PATH", "TEMP", "TMP", "USERPROFILE") if k in os.environ}
        env.update({"AUTOTESTER_ROOT": root, "AUTOTESTER_ALLOWED_HOSTS": "testserver", "T204B_SRC": SRC, "PYTHONUTF8": "1"})
        try:
            r = subprocess.run([PY, __file__, "child", kind, field, str(size)], capture_output=True, text=True, env=env, timeout=170)
            print(r.stdout.strip() or ("ERR " + r.stderr.strip()[-200:]), flush=True)
        except subprocess.TimeoutExpired:
            print({"kind": kind, "field": field, "size": size, "status": "TIMEOUT>170s"}, flush=True)
