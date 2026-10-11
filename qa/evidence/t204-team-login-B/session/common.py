"""Shared setup for the blind security check scripts (read-only against the worktree)."""
import os, sys, json, sqlite3, secrets, time, shutil
BASE = os.environ["T204B_BASE"]
SRC = "D:/autoTesting/.worktrees/t204-team-login/src"
CLEAR = ["AUTOTESTER_AUTH_DIR", "AUTOTESTER_AUTH_DISABLED", "AUTOTESTER_HOSTED",
         "AUTOTESTER_FIRST_ADMIN_EMAIL", "AUTOTESTER_COOKIE_SECURE", "AUTOTESTER_ALLOWED_ORIGINS",
         "AUTOTESTER_SESSION_HOURS", "UVICORN_HOST", "AUTOTESTER_ALLOWED_HOSTS"]
PW = "Zq7-canary-" + secrets.token_hex(4)
PW2 = "Zq7-canary-" + secrets.token_hex(4)

def setup(name, **env):
    root = os.path.join(BASE, name)
    shutil.rmtree(root, ignore_errors=True)
    os.makedirs(root)
    for k in CLEAR:
        os.environ.pop(k, None)
    os.environ["AUTOTESTER_ROOT"] = root
    os.environ["AUTOTESTER_ALLOWED_HOSTS"] = "testserver"
    for k, v in env.items():
        os.environ[k] = v
    sys.path.insert(0, SRC)
    return root

def db_path(root): return os.path.join(root, ".auth", "auth.sqlite3")
def audit_lines(root):
    p = os.path.join(root, ".work", "audit.jsonl")
    return open(p, encoding="utf-8").read().splitlines() if os.path.exists(p) else []
def q(root, sql, args=()):
    c = sqlite3.connect(db_path(root)); c.row_factory = sqlite3.Row
    try: return [dict(r) for r in c.execute(sql, args)]
    finally: c.close()
def snapshot(root):
    """store contents excluding sessions (audit is a file, separate)."""
    c = sqlite3.connect(db_path(root))
    try:
        out = {}
        for t in ("users","groups","group_permissions","memberships","project_grants","meta"):
            out[t] = sorted(map(tuple, c.execute(f"select * from {t}")))
        return out
    finally: c.close()
def p(*a): print(*a, flush=True)
