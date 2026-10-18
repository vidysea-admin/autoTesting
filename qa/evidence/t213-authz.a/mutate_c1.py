"""Checker-A cycle-1 floor: one falsification per repaired criterion, each in its OWN copy outside the worktree."""
import os, shutil, subprocess
WT = "D:/autoTesting/.worktrees/t213-authz"
OUT = "D:/autoTesting/.work/tmp/t213a/copies-c1"
PY = WT + "/.venv/Scripts/python.exe"
T = "tests/test_oracle_tenant.py::"; P = "tests/test_oracle_privilege.py::"; G = "tests/test_authz_gate.py::"
A5a = G + "test_a5_an_approval_for_one_platform_cannot_be_spent_on_a_sibling_platforms_host"
A5b = G + "test_a5_a_platform_pinned_to_exact_hosts_refuses_its_own_subdomain"
MUTS = [
 ("A5-sibling-host", "src/autotester/stages/authz_probe.py",
  "for d in (*platform.allowed_domains, base) if d]", "for d in (*platform.allowed_domains, base, 'other.test') if d]", [A5a]),
 ("A5-subdomain-flag", "src/autotester/stages/authz_probe.py",
  "host == d or (platform.include_subdomains and host.endswith(f\".{d}\"))", "host == d or host.endswith(f\".{d}\")", [A5b]),
 ("MP18-list-status", "src/autotester/stages/oracle_tenant.py",
  "    if not reply.ok:  # a 401/403/5xx is not \"no rows\": the view was not probed, and says so\n        unprobed += _unprobed(probe, rest, StopReason.LIST_STATUS)\n        return None\n    return list(reply.rows)",
  "    return list(reply.rows) if reply.ok else []",
  [T + "test_mp18_an_owner_list_that_returns_401_names_the_view_unprobed_never_clean",
   T + "test_mp18_a_viewer_list_that_returns_403_names_the_view_unprobed"]),
 ("MP19-raise-record", "src/autotester/stages/oracle_privilege.py",
  "        prep.budget.extra()\n        _record_revert(probe, control, prep, fid, reverted)\n        return None",
  "        prep.budget.extra()\n        return None",
  [P + "test_mp19_an_assign_that_raises_and_whose_revert_failed_is_recorded_for_the_operator"]),
]
def mk(name):
    d = f"{OUT}/{name}"; shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    for item in ("src", "tests", "scripts", "pyproject.toml"):
        s = f"{WT}/{item}"
        (shutil.copytree(s, f"{d}/{item}", ignore=shutil.ignore_patterns("__pycache__")) if os.path.isdir(s) else shutil.copy(s, d))
    return d
def run(d, nodes):
    env = dict(os.environ, PYTHONPATH=f"{d}/src", TMP="D:/autoTesting/.work/tmp", TEMP="D:/autoTesting/.work/tmp", AUTOTESTER_APPROVAL_KEY="synthetic-checker-key-not-real")
    where = subprocess.run([PY, "-c", "import autotester;print(autotester.__file__)"], cwd=d, env=env, capture_output=True, text=True).stdout.strip()
    r = subprocess.run([PY, "-m", "pytest", *nodes, "-p", "no:cacheprovider"], cwd=d, env=env, capture_output=True, text=True)
    return where, r.returncode, r.stdout
for name, f, old, new, nodes in MUTS:
    d = mk(name)
    where, rc, out = run(d, nodes)
    print(f"[{name}] GREEN-BEFORE rc={rc} pkg_in_copy={where.replace(chr(92),'/').startswith(d)} :: {[l for l in out.splitlines() if 'passed' in l or 'failed' in l][-1:]}")
    path = f"{d}/{f}"; src = open(path, encoding="utf-8").read()
    assert src.count(old) == 1, (name, src.count(old))
    open(path, "w", encoding="utf-8").write(src.replace(old, new))
    where, rc, out = run(d, nodes)
    red = [l for l in out.splitlines() if l.startswith("FAILED")]
    print(f"[{name}] RED-AFTER rc={rc} :: {[l for l in out.splitlines() if 'passed' in l or 'failed' in l][-1:]}\n    {red}")
