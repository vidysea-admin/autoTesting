"""B-seat falsifications of TF2 in throwaway copies (deleted at the end). argv: none."""
import os, shutil, subprocess, sys, tarfile, io
from pathlib import Path

WT = "D:/autoTesting/.worktrees/t205-g10-headroom"
PY = WT + "/.venv/Scripts/python.exe"
BASE = Path("C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/236a59b4-e0ec-4b2d-b22e-73d3059dd7f6/scratchpad/b/falsify")
shutil.rmtree(BASE, ignore_errors=True)
BASE.mkdir(parents=True)


def make_copy(name):
    dest = BASE / name
    dest.mkdir()
    data = subprocess.run(["git", "-C", WT, "archive", "HEAD"], capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(dest)
    return dest


def run(copy, tests):
    env = dict(os.environ, PYTHONPATH=str(copy / "src"))
    env.pop("VIRTUAL_ENV", None)
    p = subprocess.run([PY, "-m", "pytest", *tests, "-p", "no:xdist", "-o", "addopts=", "-q", "--no-header", "-x" if False else "-rf"],
                       cwd=copy, env=env, capture_output=True, text=True)
    tail = [l for l in p.stdout.splitlines() if l.strip()][-8:]
    return p.returncode, "\n".join(tail)


def edit(copy, rel, old, new):
    f = copy / rel
    s = f.read_text(encoding="utf-8")
    assert s.count(old) == 1, (rel, s.count(old))
    f.write_text(s.replace(old, new), encoding="utf-8")
    assert f.read_text(encoding="utf-8") != s


TESTS = ["tests/test_run_launcher_approval.py", "tests/test_run_launcher.py", "tests/test_ui_runs_live_case_approval.py"]

# ---- F1: the gate is skipped for ONE entry point (trigger == schedule) --------------------------
c1 = make_copy("f1")
print("F1 green before:", run(c1, TESTS))
edit(c1, "src/autotester/stages/run_launcher.py",
     "    store, project, cases, judge, paths, secrets, approval, entry_flags, cat = prepare_run(\n        slug, seams)\n",
     "    if trigger is Trigger.SCHEDULE:\n"
     "        global require_live_case_approval\n"
     "        _real = require_live_case_approval\n"
     "        require_live_case_approval = lambda p, s, c, secrets=None, account_keys=None: RunApproval(\n"
     "            project=p.slug, run_kind=ApprovalKind.LIVE_CASE, target=p.base_url, scope='x',\n"
     "            max_actions=10**6, max_probes=0, wall_clock_s=1e6, granted_by='x',\n"
     "            granted_at='2026-01-01', expires_at='2099-01-01')\n"
     "        try:\n"
     "            prepared = prepare_run(slug, seams)\n"
     "        finally:\n"
     "            require_live_case_approval = _real\n"
     "    else:\n"
     "        prepared = prepare_run(slug, seams)\n"
     "    store, project, cases, judge, paths, secrets, approval, entry_flags, cat = prepared\n")
print("F1 red after (schedule entry point un-gated):", run(c1, TESTS))

# ---- F2: cross-project case check dropped --------------------------------------------------------
c2 = make_copy("f2")
print("F2 green before:", run(c2, TESTS))
edit(c2, "src/autotester/stages/run_launcher.py",
     "        if any(case.project != project.slug for case in cases):\n            raise ApprovalRequired(\"case project differs from the requested project\")\n",
     "")
print("F2 red after (cross-project case check removed):", run(c2, TESTS))

# ---- F3: the AST test's blind spot: aliased import of the executor + Run, in a new module --------
c3 = make_copy("f3")
print("F3 green before:", run(c3, ["tests/test_run_launcher.py", "tests/test_run_launcher_approval.py"]))
(c3 / "src/autotester/stages/sneaky.py").write_text(
    '"""Throwaway: a second launcher that runs cases with NO gate."""\n'
    "from autotester.stages.run_launcher import run_cases_traced as go\n"
    "from autotester.schema.run import Run as R\n"
    "def launch_ungated(store, run_id, secrets, project, cases, flags, run_dir, paths, slug, judge, approval, cat):\n"
    "    plan = go(store, run_id, secrets, project, cases, flags, run_dir, paths, slug, judge, approval, cat)\n"
    "    return R(id=run_id, project=slug, case_ids=[c.id for c in cases])\n",
    encoding="utf-8")
print("F3 after adding sneaky.py (should be RED if the AST test were sound; green = test blind):",
      run(c3, ["tests/test_run_launcher.py", "tests/test_run_launcher_approval.py"]))
# F3b: same through functools.partial and an attribute alias on the module
(c3 / "src/autotester/stages/sneaky2.py").write_text(
    '"""Throwaway."""\nimport functools\nfrom autotester.stages import run_launcher as rl\n'
    "go2 = functools.partial(rl.run_cases_traced)\n"
    "def f(*a, **k):\n    return go2(*a, **k)\n", encoding="utf-8")
print("F3b after adding partial wrapper:", run(c3, ["tests/test_run_launcher.py", "tests/test_run_launcher_approval.py"]))
# F3c: an escape hatch as a RunSeams FIELD (the 'no skip/bypass parameter' AST test only scans function args)
c4 = make_copy("f3c")
rl = "src/autotester/stages/run_launcher.py"
NL = chr(10)
edit(c4, rl, "    ledger: PlanningLedger | None = None" + NL,
     "    ledger: PlanningLedger | None = None" + NL + "    skip_approval: bool = False" + NL)
edit(c4, rl, "    approval = require_live_case_approval(project, store, cases, secrets, account_keys)" + NL,
     "    approval = (RunApproval(project=slug, run_kind=ApprovalKind.LIVE_CASE, target=project.base_url, scope='x'," + NL
     + "                max_actions=10**6, max_probes=0, wall_clock_s=1e6, granted_by='x', granted_at='2026-01-01'," + NL
     + "                expires_at='2099-01-01') if seams.skip_approval else" + NL
     + "                require_live_case_approval(project, store, cases, secrets, account_keys))" + NL)
(c4 / "tests/test_b_probe.py").write_text(NL.join([
    "from test_run_launcher_approval import world, Counters",
    "from autotester.stages.run_launcher import launch_run",
    "def test_seam_field_skips_the_gate(world):",
    "    store, seams = world",
    "    run = launch_run('demo', seams=seams._replace(skip_approval=True))",
    "    assert Counters.sessions >= 1 and run.bounds is not None", ""]), encoding="utf-8")
print("F3c: builder TF1/TF2 tests with the seam-field escape hatch present (green = the AST test is blind):",
      run(c4, ["tests/test_run_launcher.py", "tests/test_run_launcher_approval.py"]))
print("F3c: probe - launch_run with no approval and skip_approval=True:", run(c4, ["tests/test_b_probe.py"]))

shutil.rmtree(BASE, ignore_errors=True)
print("copies deleted:", not BASE.exists())
