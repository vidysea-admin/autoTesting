"""Checker B cycle-1 falsification runner: isolated copy per mutant, outside D:/autoTesting."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

WT = Path("D:/autoTesting/.worktrees/t213-authz")
OUT = Path("C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/e46c0e51-15e9-4a31-a0b0-cf49de9d445f/scratchpad/mut_b_c1")
PY = WT / ".venv/Scripts/python.exe"
FILES = ["tests/test_oracle_tenant.py", "tests/test_oracle_privilege.py", "tests/test_authz_gate.py",
         "tests/test_authz_probe_schema.py"]

MUTANTS = {
    "control": None,
    "C1_MP18_list_status_check_removed": ("src/autotester/stages/oracle_tenant.py",
        "    if not reply.ok:  # a 401", "    if False:  # a 401"),
    "C1_MP19_raise_path_record_removed": ("src/autotester/stages/oracle_privilege.py",
        "        prep.budget.extra()\n        _record_revert(probe, control, prep, fid, reverted)\n        return None\n    if not accepted:",
        "        prep.budget.extra()\n        return None\n    if not accepted:"),
    "C1_A5_scope_widened_to_sibling_host": ("src/autotester/stages/authz_probe.py",
        "for d in _platform_hosts(platform))", "for d in (*_platform_hosts(platform), 'other.test'))"),
    "C1_A5_include_subdomains_ignored": ("src/autotester/stages/authz_probe.py",
        "(platform.include_subdomains and host.endswith(f\".{d}\"))", "(host.endswith(f\".{d}\"))"),
}


import sys as _s
if len(_s.argv) > 1:
    MUTANTS = {k: v for k, v in MUTANTS.items() if k in _s.argv[1:]}


def run(name, spec):
    d = OUT / name
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    shutil.copytree(WT / "src", d / "src", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(WT / "tests", d / "tests", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(WT / "scripts", d / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(WT / "pyproject.toml", d / "pyproject.toml")
    if spec:
        f, old, new = spec
        p = d / f
        t = p.read_text("utf-8")
        assert t.count(old) == 1, (name, t.count(old))
        p.write_text(t.replace(old, new), "utf-8")
    env = dict(os.environ, PYTHONPATH=str(d / "src") + os.pathsep + str(d / "scripts"), TMP=str(d / "tmp"), TEMP=str(d / "tmp"))
    (d / "tmp").mkdir()
    r = subprocess.run([str(PY), "-m", "pytest", "-p", "no:cacheprovider", *FILES, "-rf", "--tb=no"],
                       cwd=d, env=env, capture_output=True, text=True)
    lines = [ln for ln in r.stdout.splitlines() if ln.startswith("FAILED") or " passed" in ln or " failed" in ln]
    return {"mutant": name, "rc": r.returncode, "result": lines}


if __name__ == "__main__":
    chk = subprocess.run([str(PY), "-c", "import autotester;print(autotester.__file__)"],
                         env=dict(os.environ, PYTHONPATH=str(OUT / "control/src")), capture_output=True, text=True)
    res = [run(n, s) for n, s in MUTANTS.items()]
    print(json.dumps(res, indent=1))
