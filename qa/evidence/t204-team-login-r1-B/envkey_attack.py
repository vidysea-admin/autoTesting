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


# operator lines (server keys) in the shared .env, plus operator non-server keys
(root / "projects").mkdir(exist_ok=True)
ENV.write_text("ANTHROPIC_API_KEY=sk-dummy-op\nAUTOTESTER_APPROVAL_KEY=dummy-approval\n"
               "PLAYWRIGHT_BROWSERS_PATH=/opt/pw-op\nHTTP_PROXY=http://op-proxy:3128\n",
               encoding="utf-8")
BASE = restart()  # reference: what a restart exports with only operator lines
print("baseline restart exports:", BASE)
EXPECTED_OK = set(BASE)

# ---- A: onboard route, slugs x dangerous keys ---------------------------------------------
ATT = [("http", "HTTP_PROXY"), ("node", "NODE_OPTIONS"), ("ld", "LD_PRELOAD"), ("ssl", "SSL_CERT_FILE"),
       ("requests", "REQUESTS_CA_BUNDLE"), ("no", "NO_PROXY"), ("all", "ALL_PROXY"),
       ("git", "GIT_SSH_COMMAND"), ("uv", "UV_INDEX_URL"), ("litellm", "LITELLM_API_BASE"),
       ("openai", "OPENAI_BASE_URL"), ("gemini", "GEMINI_BASE_URL"), ("google", "GOOGLE_API_KEY"),
       ("ollama", "OLLAMA_HOST"), ("anthropic", "ANTHROPIC_BASE_URL"),
       ("anthropic-base", "ANTHROPIC_BASE_URL"), ("a", "A_X"), ("a1", "A1_X"), ("b-", "B_X"),
       ("c--d", "C_D_X"), ("bash", "BASH_ENV"), ("pythonpath", "PYTHONPATH_X"),
       ("autotester", "AUTOTESTER_X"), ("autotester-x", "AUTOTESTER_X_Y"),
       ("auto", "AUTO_X"), ("autotest", "AUTOTEST_X"), ("playwright", "PLAYWRIGHT_BROWSERS_PATH"),
       ("uvicorn", "UVICORN_HOST"), ("sslkeylog", "SSLKEYLOG_FILE"), ("proxy", "PROXY_X")]
for slug, key in ATT:
    code = onboard(slug, key)
    bad = [k for k in restart() if k not in EXPECTED_OK]
    rec(f"A onboard {slug}/{key}", f"http {code}", bad)

# ---- B: value injection through the real write route -------------------------------------
VALS = {"vt": "a\x0bLD_PRELOAD=/tmp/e.so", "ff": "a\x0cLD_PRELOAD=/tmp/e.so",
        "fs": "a\x1cLD_PRELOAD=/tmp/e.so", "gs": "a\x1dLD_PRELOAD=/tmp/e.so",
        "rs": "a\x1eLD_PRELOAD=/tmp/e.so", "nel": "a\x85LD_PRELOAD=/tmp/e.so",
        "ls": "a\u2028LD_PRELOAD=/tmp/e.so", "ps": "a\u2029LD_PRELOAD=/tmp/e.so",
        "bs": "x\\", "bsq": '"\\', "eq": "a=b", "interp": "${ANTHROPIC_API_KEY}", "exp": "export LD_PRELOAD=1",
        "nul": "a\x00LD_PRELOAD=1", "hash": "#LD_PRELOAD=1", "sp": "a #b", "q1": "'", "q2": '"',
        "q1q2": "'\"", "q3": "x'\"LD_PRELOAD=1"}
n = 0
for tag, val in VALS.items():
    n += 1
    slug = f"inj{tag}"
    code = onboard(slug, f"{slug.upper()}_K", val)
    # a second write by someone else, to force the splitlines() rewrite path
    code2 = onboard(f"zz{tag}", f"ZZ{tag.upper()}_K", "second")
    bad = [k for k in restart() if k not in EXPECTED_OK]
    from dotenv import dotenv_values
    dkeys = [k for k, v in dotenv_values(ENV).items() if v and "e.so" in v]
    rec(f"B value {tag}", f"http {code}/{code2} dotenv_LD={dkeys}", bad)
# did any backslash/quote value swallow the operator provider key lines?
exp = restart()
print("B after all values, ANTHROPIC_API_KEY still exported?:", "ANTHROPIC_API_KEY" in exp or "ANTHROPIC_API_KEY" in os.environ)
fresh = subprocess.run([sys.executable, "-c",
    "import os,sys;sys.path.insert(0,r'%s');from dotenv import dotenv_values;"
    "d=dotenv_values(r'%s');print(json.dumps(sorted(d)) if False else sorted(d))" % (WT / "src", ENV)],
    capture_output=True, text=True)
print("dotenv keys now:", fresh.stdout.strip()[:600])

# ---- C: project deleted / project.json corrupt or unreadable --------------------------------
import shutil  # noqa: E402

onboard("orph", "ORPH_PROXY")
ok_before = [k for k in restart() if k not in EXPECTED_OK]
pj = root / "projects" / "orph" / "project.json"
saved = pj.read_text(encoding="utf-8")
pj.write_text("{ not json", encoding="utf-8")
rec("C corrupt project.json", "namespace by dirname", [k for k in restart() if k not in EXPECTED_OK])
pj.write_text(saved, encoding="utf-8")
pj.rename(pj.with_name("project.json.bak"))
rec("C project.json renamed away (dir kept)", "no glob hit", [k for k in restart() if k not in EXPECTED_OK])
pj.with_name("project.json.bak").rename(pj)
shutil.move(str(root / "projects" / "orph"), str(scratch / "orph-moved"))
rec("C project dir deleted (operator action)", "orphan key", [k for k in restart() if k not in EXPECTED_OK])
shutil.move(str(scratch / "orph-moved"), str(root / "projects" / "orph"))

# ---- D: the other routes -----------------------------------------------------------------------
onboard("rt", "RT_BASE")
def post(path, **data):
    return dev.post(path, data=data).status_code
r = {}
r["env/add ok"] = post("/projects/rt/env/add", key="RT_NEW", value="v", domains="rt.test", description="")
r["env/add HTTP_PROXY"] = post("/projects/rt/env/add", key="HTTP_PROXY", value="EVIL", domains="rt.test", description="")
r["env/add AUTOTESTER_X"] = post("/projects/rt/env/add", key="AUTOTESTER_X", value="EVIL", domains="rt.test", description="")
r["env/add ANTHROPIC_API_KEY"] = post("/projects/rt/env/add", key="ANTHROPIC_API_KEY", value="EVIL", domains="rt.test", description="")
r["secrets decl HTTP_PROXY"] = post("/projects/rt/secrets", key="HTTP_PROXY", domains="rt.test")
r["secrets decl RT_Z"] = post("/projects/rt/secrets", key="RT_Z", domains="rt.test")
r["env set RT_Z"] = post("/projects/rt/env", key="RT_Z", value="vz")
r["env set undeclared HTTP_PROXY"] = post("/projects/rt/env", key="HTTP_PROXY", value="EVIL")
r["secrets del RT_Z"] = dev.post("/projects/rt/secrets/RT_Z/delete").status_code
r["settings provider as dev"] = post("/settings/providers", key="ANTHROPIC_API_KEY", value="EVIL")
for lbl, k in (("lower", "rt_proxy"), ("fullwidth", "\uff32T_X"), ("nl", "RT_X\nLD_PRELOAD"), ("eq", "RT_X=1"),
               ("nul", "RT_X\x00"), ("sp", " RT_X"), ("export", "export RT_X"), ("bare", "RT_"), ("bare-noul", "RT")):
    r[f"env/add key {lbl}"] = post("/projects/rt/env/add", key=k, value="v", domains="rt.test", description="")
for k, v in r.items():
    print(f"D {k:40s} http {v}")
rec("D after all route attempts", "", [k for k in restart() if k not in EXPECTED_OK])
print("D .env keys:", env_keys())

# ---- E: nested namespaces, orphan/legacy declaration -------------------------------------------
onboard("alpha", "ALPHA_ONE")
print("E alpha-beta key from alpha:", post("/projects/alpha/env/add", key="ALPHA_BETA_X", value="v", domains="alpha.test", description=""))
onboard("alpha-beta", "ALPHA_BETA_Y")
print("E alpha claims ALPHA_BETA_X after alpha-beta exists:", post("/projects/alpha/env/add", key="ALPHA_BETA_Z", value="v", domains="alpha.test", description=""))
print("E alpha-beta onboard with alpha's ALPHA_BETA_X (alpha has it):", onboard("alpha-beta2", "ALPHA_BETA_X"))
# legacy: hand-written project.json declaring an out-of-namespace key; dev undeclares it
lp = root / "projects" / "legacy"
lp.mkdir(parents=True, exist_ok=True)
(lp / "project.json").write_text(json.dumps({"slug": "legacy", "name": "Legacy", "base_url": "https://legacy.test",
    "allowed_domains": ["legacy.test"], "secrets": [{"key": "HTTP_PROXY", "domains": ["legacy.test"]}]}), encoding="utf-8")
from autotester.auth.access import set_owner  # noqa: E402
from autotester.auth.accounts import list_users  # noqa: E402

uid = next(u.id for u in list_users() if u.email == "dev@team.test")
set_owner("legacy", uid)
print("E legacy declared HTTP_PROXY: set via /env:", post("/projects/legacy/env", key="HTTP_PROXY", value="EVIL"),
      "exported:", [k for k in restart() if k not in EXPECTED_OK])
print("E legacy undeclare:", dev.post("/projects/legacy/secrets/HTTP_PROXY/delete").status_code,
      "exported:", [k for k in restart() if k not in EXPECTED_OK])

# ---- F: reverse harm: operator variable added AFTER start, developer slug covers it ---------
with ENV.open("a", encoding="utf-8") as fh:
    fh.write("LITELLM_OP_KEY=op-dummy\nSSL_OP_CERT=op-cert\n")
_r = dev.post("/onboard", data={"slug": "litellm-op", "name": "L", "base_url": "https://l.test", "allowed_domains": "l.test",
    "credential_key": "LITELLM_OP_KEY", "credential_value": "EVIL", "credential_domains": "l.test", "credential_description": ""})
print("F litellm-op onboard:", _r.status_code, _r.text[:200].replace(chr(10), " "))
print("F op-dummy line overwritten by dev?:", "LITELLM_OP_KEY" in env_keys())
exp = restart()
print("F LITELLM_OP_KEY exported at restart?:", "LITELLM_OP_KEY" in exp, " SSL_OP_CERT exported?:", "SSL_OP_CERT" in exp)
print("F provider keys exported:", [k for k in exp if k in ("ANTHROPIC_API_KEY", "AUTOTESTER_APPROVAL_KEY")])
json.dump(RESULTS, open(scratch / "results.json", "w"), indent=1)
print("TOTAL unexpected exports across attack rows:", sum(len(x["exported_unexpected"]) for x in RESULTS))
