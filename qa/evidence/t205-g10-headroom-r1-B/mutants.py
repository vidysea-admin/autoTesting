import shutil, subprocess, sys, pathlib, os, json
S = pathlib.Path(sys.argv[1]); head = S/"head"
PY = r"D:/autoTesting/.worktrees/check-t205-r1-b/.venv/Scripts/python.exe"
def edit(root, rel, old, new, count=1):
    p = root/rel; t = p.read_text(encoding="utf-8")
    assert t.count(old) == count, (rel, old, t.count(old))
    p.write_text(t.replace(old, new), encoding="utf-8")
def append(root, rel, text):
    p = root/rel; p.write_text(p.read_text(encoding="utf-8") + text, encoding="utf-8")
SAFE = ["tests/test_safe_names_windows.py", "tests/test_team_store.py", "-k", "not ignored_by_git"]
GUARD = ["tests/test_run_launcher.py", "tests/test_run_launcher_approval.py"]
SCHEMA = ["tests/test_project_schema_team.py"]
M = {}
M["M1_TF6_drop_uploaded_by"] = (lambda r: edit(r,"src/autotester/schema/project.py",'    uploaded_by: str | None = Field(default=None, description="user id of who added it (Group 10)")\n',""), SCHEMA)
M["M2_TF6_origin_free_str"] = (lambda r: edit(r,"src/autotester/schema/project.py","origin: SourceOriginKind | None","origin: str | None"), SCHEMA)
M["M3_safe_forbidden_off"] = (lambda r: edit(r,"src/autotester/core/safe_names.py","if _FORBIDDEN.search(name):","if False and _FORBIDDEN.search(name):"), SAFE)
M["M4_safe_no_conin"] = (lambda r: edit(r,"src/autotester/core/safe_names.py",'"conin$", "conout$",',""), SAFE)
M["M4b_safe_no_rstrip"] = (lambda r: edit(r,"src/autotester/core/safe_names.py",'split(".", 1)[0].rstrip(" ").lower()','split(".", 1)[0].lower()'), SAFE)
M["M5a_getattr_importlib_executor"] = (lambda r: append(r,"src/autotester/ui/helpers.py",
 "\n\ndef _bypass(*a):\n    import importlib\n    return getattr(importlib.import_module('autotester.stages.run_launcher'), 'run_cases_' + 'traced')(*a)\n"), GUARD)
M["M5b_getattr_literal_executor"] = (lambda r: append(r,"src/autotester/ui/helpers.py",
 "\n\ndef _bypass2(*a):\n    from autotester.stages import run_launcher as _m\n    return getattr(_m, 'run_cases_traced')(*a)\n"), GUARD)
M["M5c_aliased_Run"] = (lambda r: append(r,"src/autotester/ui/helpers.py",
 "\n\nfrom autotester.schema.run import Run as _R\n\n\ndef _bypass3():\n    return _R(id='x')\n"), GUARD)
M["M5d_alias_executor_partial"] = (lambda r: append(r,"src/autotester/ui/helpers.py",
 "\n\nimport functools as _ft\nfrom autotester.stages.run_launcher import run_cases_traced as _go\n_p = _ft.partial(_go, 1)\n"), GUARD)
M["M6a_seams_field_added"] = (lambda r: edit(r,"src/autotester/stages/run_launcher.py","    ledger: PlanningLedger | None = None\n","    ledger: PlanningLedger | None = None\n    skip_approval: bool = False\n"), GUARD)
def m6b(r):
    edit(r,"src/autotester/stages/run_launcher.py","    ledger: PlanningLedger | None = None\n","    ledger: PlanningLedger | None = None\n    approval_override: object = None\n")
    edit(r,"src/autotester/stages/run_launcher.py","    approval = require_live_case_approval(project, store, cases, secrets, account_keys)\n",
         "    approval = seams.approval_override if isinstance(seams.approval_override, RunApproval) else require_live_case_approval(project, store, cases, secrets, account_keys)\n")
M["M6b_seams_field_honoured_only_for_real_RunApproval"] = (m6b, ["tests/test_run_launcher_approval.py","-k","no_seam_value"])
def m6c(r):
    edit(r,"src/autotester/stages/run_launcher.py","    ledger: PlanningLedger | None = None\n","    ledger: PlanningLedger | None = None\n    skip_approval: bool = False\n")
    edit(r,"src/autotester/stages/run_launcher.py","    approval = require_live_case_approval(project, store, cases, secrets, account_keys)\n",
         "    approval = RunApproval(project=slug, run_kind=ApprovalKind.LIVE_CASE, target=project.base_url, scope='x', granted_by='x', granted_at='2026-01-01', expires_at='2099-01-01', max_actions=10**6, max_probes=10**6, wall_clock_s=1e9) if seams.skip_approval else require_live_case_approval(project, store, cases, secrets, account_keys)\n")
M["M6c_seams_field_honoured_truthy"] = (m6c, ["tests/test_run_launcher_approval.py","-k","no_seam_value"])
def run(root, args):
    env = dict(os.environ, PYTHONPATH=str(root/"src"))
    chk = subprocess.run([PY,"-c","import autotester,sys;print(autotester.__file__)"],cwd=root,env=env,capture_output=True,text=True).stdout.strip()
    assert str(root).replace("\\","/").lower() in chk.replace("\\","/").lower(), chk
    p = subprocess.run([PY,"-m","pytest","-p","no:xdist","-o","addopts=","-q","--no-header","-x" if False else "-p","no:cacheprovider",*args],cwd=root,env=env,capture_output=True,text=True)
    tail = [l for l in p.stdout.splitlines() if l.strip()][-1] if p.stdout.strip() else p.stderr[-200:]
    fails = [l for l in p.stdout.splitlines() if l.startswith("FAILED")]
    return p.returncode, tail, fails
sel = sys.argv[2:] or list(M)
out = {}
for name in sel:
    fn, args = M[name]
    root = S/("mut_"+name)
    shutil.rmtree(root, ignore_errors=True); shutil.copytree(head, root, ignore=shutil.ignore_patterns("qa",".goal"))
    g = run(root, args)
    fn(root)
    r = run(root, args)
    out[name] = {"green_before": g[:2], "after": r[:2], "failed_tests": r[2][:6]}
    print(name, "| BEFORE rc", g[0], g[1], "| AFTER rc", r[0], r[1]); 
    for f in r[2][:4]: print("    ", f[:170])
    sys.stdout.flush()
    shutil.rmtree(root, ignore_errors=True)
json.dump(out, open(S/"mutants.json","w"), indent=1)
