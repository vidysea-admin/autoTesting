"""Checker-A falsification floor: one mutant per criterion, each in its OWN copy outside the worktree."""
import os, shutil, subprocess, sys
WT = "D:/autoTesting/.worktrees/t213-authz"
OUT = "D:/autoTesting/.work/tmp/t213a/copies"
PY = WT + "/.venv/Scripts/python.exe"
T = "tests/test_oracle_tenant.py::"; P = "tests/test_oracle_privilege.py::"; G = "tests/test_authz_gate.py::"
MUTS = [
 ("MP20b", "src/autotester/stages/oracle_tenant.py",
  "chosen = owner_ids[:MAX_SWAPS_PER_ENDPOINT]", "chosen = owner_ids[:4]",
  T + "test_mp20_at_most_three_swaps_and_the_rest_is_named_unprobed"),
]
def mk(name):
    d = f"{OUT}/{name}"
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    for item in ("src", "tests", "scripts", "pyproject.toml"):
        s = f"{WT}/{item}"
        (shutil.copytree(s, f"{d}/{item}", ignore=shutil.ignore_patterns("__pycache__")) if os.path.isdir(s)
         else shutil.copy(s, d))
    return d
def run(d, node):
    env = dict(os.environ, PYTHONPATH=f"{d}/src", TMP="D:/autoTesting/.work/tmp", TEMP="D:/autoTesting/.work/tmp",
               AUTOTESTER_APPROVAL_KEY="synthetic-checker-key-not-real")
    r = subprocess.run([PY, "-c", "import autotester,sys;print(autotester.__file__)"], cwd=d, env=env, capture_output=True, text=True)
    where = r.stdout.strip()
    r = subprocess.run([PY, "-m", "pytest", node, "-p", "no:cacheprovider"], cwd=d, env=env, capture_output=True, text=True)
    tail = [l for l in r.stdout.splitlines() if l.strip()][-3:]
    return where, r.returncode, tail, r.stdout
for name, f, old, new, node in MUTS:
    d = mk(name)
    where, rc, tail, _ = run(d, node)
    print(f"[{name}] GREEN-BEFORE rc={rc} pkg={where}\n    {tail[-1] if tail else ''}")
    path = f"{d}/{f}"
    src = open(path, encoding="utf-8").read()
    assert src.count(old) == 1, (name, src.count(old))
    open(path, "w", encoding="utf-8").write(src.replace(old, new))
    where, rc, tail, out = run(d, node)
    asserts = [l for l in out.splitlines() if l.startswith("E ")][:2]
    print(f"[{name}] RED-AFTER   rc={rc}\n    {tail[-1] if tail else ''}\n    {asserts}")
