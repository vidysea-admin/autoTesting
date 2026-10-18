"""Checker B falsification runner: isolated copy per mutant, outside D:/autoTesting."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

WT = Path("D:/autoTesting/.worktrees/t213-authz")
OUT = Path("C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/e46c0e51-15e9-4a31-a0b0-cf49de9d445f/scratchpad/mut_b")
PY = WT / ".venv/Scripts/python.exe"
FILES = ["tests/test_oracle_tenant.py", "tests/test_oracle_privilege.py", "tests/test_authz_gate.py",
         "tests/test_authz_probe_schema.py"]

MUTANTS = {
    "control": None,
    "M18a_swap_ignores_status": ("src/autotester/stages/oracle_tenant.py",
        "elif reply.ok and reply.rows:", "elif reply.rows:"),
    "M18b_list_ignores_status": ("src/autotester/stages/oracle_tenant.py",
        "return list(reply.rows) if reply.ok else []", "return list(reply.rows)"),
    "M19a_4xx_counts_as_success": ("src/autotester/stages/oracle_privilege.py",
        "elif reply.ok:  #", "elif reply.status < 500:  #"),
    "M19b_revert_always_recorded_true": ("src/autotester/stages/oracle_privilege.py",
        "role_id=probe.lower_role_id, reverted=reverted,", "role_id=probe.lower_role_id, reverted=True,"),
    "M19c_write_guard_only_read_only": ("src/autotester/stages/oracle_privilege.py",
        "is not WritePolicy.ALLOW_WRITES:", "is WritePolicy.READ_ONLY:"),
    "M20a_ceiling_ge": ("src/autotester/stages/authz_probe.py",
        "if planned > PROBE_CEILING:", "if planned >= PROBE_CEILING:"),
    "A5a_probes_minus_one": ("src/autotester/stages/authz_probe.py",
        "probes=planned, wall_clock_s=plan.wall_clock_s", "probes=planned - 1, wall_clock_s=plan.wall_clock_s"),
    "M20b_no_ceiling_clamp_on_cap": ("src/autotester/stages/authz_probe.py",
        "cap=min(plan.request_cap, PROBE_CEILING)", "cap=plan.request_cap"),
    "MPI1a_reply_rows_dumped": ("src/autotester/schema/authz_probe.py",
        "Field(default_factory=list, exclude=True, repr=False)", "Field(default_factory=list, repr=False)"),
    "A5b_wall_clock_not_checked": ("src/autotester/stages/authz_probe.py",
        "probes=planned, wall_clock_s=plan.wall_clock_s", "probes=planned, wall_clock_s=0.0"),
    "M18c_owner_filter_inverted": ("src/autotester/stages/oracle_tenant.py",
        "and str(r[probe.id_field]) in owner_ids]", "and str(r[probe.id_field]) not in owner_ids]"),
    "M18d_count_mode_offset": ("src/autotester/stages/oracle_tenant.py",
        "rows[probe.declared_own_count or 0:]", "rows[(probe.declared_own_count or 0) + 1:]"),
    "M20c_swap_limit_4": ("src/autotester/stages/authz_probe.py",
        "MAX_SWAPS_PER_ENDPOINT = 3", "MAX_SWAPS_PER_ENDPOINT = 4"),
    "M20d_cap_boundary_ge": ("src/autotester/stages/authz_probe.py",
        "self.sent + reserve > self.cap", "self.sent + reserve >= self.cap"),
    "M20e_revert_reserve_1": ("src/autotester/stages/oracle_privilege.py",
        "prep.budget.take(reserve=2)", "prep.budget.take(reserve=1)"),
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
