from common import *
import re, subprocess, threading
from fastapi.testclient import TestClient

VENV = "D:/autoTesting/.worktrees/t204-team-login/.venv/Scripts"
EXE = VENV + "/autotester.exe"
PY = VENV + "/python.exe"


def clean_env(root, **extra):
    env = {k: os.environ[k] for k in ("SYSTEMROOT", "PATH", "TEMP", "TMP", "USERPROFILE", "APPDATA", "LOCALAPPDATA") if k in os.environ}
    env.update({"AUTOTESTER_ROOT": root, "AUTOTESTER_ALLOWED_HOSTS": "testserver", "PYTHONIOENCODING": "utf-8",
                "PYTHONUTF8": "1", "PYTHONPATH": SRC})
    env.update(extra)
    return env


def sub(code, root, **extra):
    return subprocess.run([PY, "-c", code], capture_output=True, text=True, encoding='utf-8', errors='replace', env=clean_env(root, **extra), timeout=100)


root = setup("famE1")
from autotester.ui.app import app
from autotester.auth.ratelimit import login_limiter, signup_limiter
from autotester.auth import accounts, groups, db
def admins():
    return q(root, "select u.email from memberships m join users u on u.id=m.user_id join groups g on g.id=m.group_id where g.seed='admin'")
OWNER = "owner@team.test"
# ---------------- E4 CLI ---------------------------------------------------------------
p("== E4 CLI: autotester auth bootstrap-admin --email X --password-stdin")
root = setup("famE4")
accounts.signup("existing@team.test", PW)
accounts.signup("other@team.test", PW)


def cli(args, stdin, root=root, **extra):
    r = subprocess.run([EXE, "auth", "bootstrap-admin", *args], input=stdin, capture_output=True, text=True, encoding='utf-8', errors='replace',
                       env=clean_env(root, **extra), timeout=100)
    return r


def leak(r):
    t = (r.stdout or '') + (r.stderr or '')
    return {"canary": any(x in t for x in (PW, PW2)), "hash": "argon2" in t, "other_emails": [e for e in ("existing@team.test", "other@team.test") if e in t]}


r = cli(["--email", "New@Team.test", "--password-stdin"], PW + "\n")
p(" create:", r.returncode, r.stdout.strip(), r.stderr.strip()[:100], leak(r))
r = cli(["--email", "new@team.test", "--password-stdin"], PW2 + "\n")
p(" reset same email:", r.returncode, r.stdout.strip(), leak(r))
r = cli(["--email", "existing@team.test", "--password-stdin"], PW + "\n")
p(" promote existing non-admin (ownership of that account is overwritten, pw reset):", r.returncode, r.stdout.strip(), leak(r))
r = cli(["--email", "x@team.test", "--password", PW], "")
p(" argv password flag:", r.returncode, r.stderr.strip().splitlines()[-1][:100] if r.stderr.strip() else "", leak(r))
r = cli(["--email", "x@team.test"], "")
p(" no --password-stdin, piped stdin (non-tty):", r.returncode, r.stderr.strip()[:110], leak(r))
for label, pw in [("9 chars", "a" * 9), ("129 chars", PW + "x" * 130), ("empty line", ""), ("EOF/no stdin", None)]:
    r = cli(["--email", "w@team.test", "--password-stdin"], "" if pw is None else pw + "\n")
    p(f" weak {label}:", r.returncode, (r.stderr.strip() or r.stdout.strip())[:100], leak(r))
for label, em in [("not-an-email", "not-an-email"), ("with space", "a b@x.test"), ("newline", "x@y.test\nz"), ("empty", ""), ("plus", "ad+min@team.test"), ("unicode", "caf\u00e9@team.test")]:
    r = cli(["--email", em, "--password-stdin"], PW + "\n")
    p(f" email {label!r}:", r.returncode, (r.stderr.strip() or r.stdout.strip())[:100].replace("\n", " | "), leak(r))
r = cli(["--password-stdin"], PW + "\n")
p(" missing --email:", r.returncode, r.stderr.strip().splitlines()[-1][:100] if r.stderr.strip() else "")
r = cli(["--email", "nd@team.test", "--password-stdin"], PW + "\n", root=os.path.join(BASE, "famE4_nonexist", "a", "b"))
p(" nonexistent data dir (created?):", r.returncode, r.stdout.strip()[:80], "dir created:", os.path.exists(os.path.join(BASE, "famE4_nonexist", "a", "b", ".auth", "auth.sqlite3")))
# unexpected exception -> does typer print locals (incl. the password)?
bad = os.path.join(BASE, "famE4_file")
open(bad, "w").write("x")
r = cli(["--email", "boom@team.test", "--password-stdin"], PW + "\n", AUTOTESTER_AUTH_DIR=bad)
p(" forced unexpected error (AUTH_DIR is a file): rc", r.returncode, "leak:", leak(r), "| stderr lines:", len(r.stderr.splitlines()), "| shows locals section:", "locals" in r.stderr.lower())
r = subprocess.run([PY, "-c", "import rich;print(rich.__file__)"], capture_output=True, text=True)
p(" rich installed:", r.returncode == 0)
# audit of CLI actions
au = [json.loads(l) for l in audit_lines(root)]
p(" CLI audit lines:", [{k: v for k, v in d.items() if k != 'ts'} for d in au])

# ---------------- E5 bind_host / AU17 -------------------------------------------------------
p("== E5 bind_host() reads only sys.argv + UVICORN_HOST")
root = setup("famE5")
from autotester.auth import config
for argv in (["uvicorn", "autotester.ui.app:app"], ["uvicorn", "app", "--host", "0.0.0.0"], ["uvicorn", "app", "--host=0.0.0.0"],
             ["gunicorn", "-b", "0.0.0.0:8000", "-k", "uvicorn.workers.UvicornWorker"], ["hypercorn", "-b", "0.0.0.0:8000"],
             ["fastapi", "run", "app.py"], ["python", "-c", "uvicorn.run(app, host='0.0.0.0')"], ["uvicorn", "app", "--host", "::"],
             ["uvicorn", "app", "--host", "127.0.0.2"], ["uvicorn", "app", "--host", "localhost"]):
    sys.argv = argv
    p(f"  argv={' '.join(argv)[:60]:62s} bind_host={config.bind_host()!r} loopback_treated={config.bind_host() in config._LOOPBACK}")
sys.argv = ["x"]
os.environ["UVICORN_HOST"] = "0.0.0.0"
p("  UVICORN_HOST=0.0.0.0 ->", config.bind_host())
del os.environ["UVICORN_HOST"]
p("== AU17 matrix: AUTH_DISABLED=1 combined with ...")
for label, env, argv in [("(nothing: loopback)", {}, ["uvicorn"]), ("HOSTED=1", {"AUTOTESTER_HOSTED": "1"}, ["uvicorn"]), ("UVICORN_HOST=0.0.0.0", {"UVICORN_HOST": "0.0.0.0"}, ["uvicorn"]),
                         ("argv --host 0.0.0.0", {}, ["uvicorn", "--host", "0.0.0.0"]), ("argv --host=0.0.0.0", {}, ["uvicorn", "--host=0.0.0.0"]),
                         ("gunicorn -b 0.0.0.0 (argv has no --host)", {}, ["gunicorn", "-b", "0.0.0.0:8000"]),
                         ("COOKIE_SECURE unset + https scheme only", {}, ["uvicorn"]), ("AUTH_DISABLED='true'", {"AUTOTESTER_AUTH_DISABLED": "true"}, ["uvicorn"])]:
    for k in ("AUTOTESTER_HOSTED", "UVICORN_HOST", "AUTOTESTER_AUTH_DISABLED"):
        os.environ.pop(k, None)
    os.environ["AUTOTESTER_AUTH_DISABLED"] = "1"
    os.environ.update(env)
    sys.argv = argv
    try:
        config.check_startup()
        res = "STARTS (disabled honoured=%s)" % config.auth_disabled()
    except config.AuthConfigError as e:
        res = "REFUSED: " + str(e)[:70]
    p(f"  {label:44s} -> {res}")
for k in ("AUTOTESTER_HOSTED", "UVICORN_HOST"):
    os.environ.pop(k, None)
sys.argv = ["gunicorn", "-b", "0.0.0.0:8000"]  # server actually bound to 0.0.0.0
os.environ["AUTOTESTER_AUTH_DISABLED"] = "1"
p("== E6 server bound elsewhere but argv has no host: AUTH_DISABLED honoured, nothing asked")
root = setup("famE6")
os.environ["AUTOTESTER_AUTH_DISABLED"] = "1"
login_limiter.reset()
c = TestClient(app, follow_redirects=False, base_url="http://testserver")
for path in ("/", "/admin/users", "/admin/groups", "/settings/providers", "/onboard", "/live", "/healthz", "/docs", "/openapi.json"):
    rr = c.get(path)
    p(f"  anonymous GET {path:22s} -> {rr.status_code}")
rr = c.post("/admin/users/1/delete")
p("  anonymous POST /admin/users/1/delete ->", rr.status_code)
rr = c.post("/auth/signup", data={"email": "ghost@team.test", "password": PW})
p("  anonymous signup while gate disabled ->", rr.status_code)
rr = c.post("/admin/groups", data={"name": "AnonGroup", "permission": "settings.manage"})
p("  anonymous POST /admin/groups with settings.manage ->", rr.status_code, "audit last:", audit_lines(root)[-1:] if audit_lines(root) else None)
# local first-signup admin when the server is in fact public (argv without --host)
os.environ.pop("AUTOTESTER_AUTH_DISABLED", None)
root = setup("famE6b")
sys.argv = ["gunicorn", "-b", "0.0.0.0:8000"]
rr = TestClient(app, follow_redirects=False).post("/auth/signup", data={"email": "stranger@team.test", "password": PW})
p("  bound 0.0.0.0 via gunicorn (argv has no --host), first public signup ->", rr.headers.get("location"), "admins:", [a["email"] for a in admins()])
