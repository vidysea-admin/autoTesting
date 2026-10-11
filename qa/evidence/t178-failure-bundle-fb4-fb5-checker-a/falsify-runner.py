import shutil, subprocess, sys, os, pathlib, re
S = pathlib.Path(sys.argv[1]); BASE = S/"base"
PY = "D:/autoTesting/.venv/Scripts/python.exe"
M = [
 ("FB4-selection-ignored", "src/autotester/store/project_store.py",
  "        if priorities is None:\n            return rows", "        if True:\n            return rows",
  "tests/test_store.py::test_priority_selection_adds_pinned_p0_once_and_preserves_default_order"),
 ("FB5-prune-ignored", "src/autotester/store/../schema/case.py",
  "return [p for p in batch if p.status == \"approved\"]", "return [p for p in batch]",
  "tests/test_expand.py::test_five_nonhappy_proposals_prune_before_spend"),
 ("CONTAIN-check-removed", "src/autotester/stages/failure_bundle.py",
  "        if not target.is_relative_to(root):\n            raise PartialBundleError(\"bundle file escapes the bundle directory\")\n", "",
  "tests/test_failure_bundle.py::test_loader_refuses_real_directory_link_escape_before_hashing"),
 ("QUEUE-priorities-dropped", "src/autotester/ui/routes_runs.py",
  "_prepare_run(entry.project, entry.priorities)", "_prepare_run(entry.project)",
  "tests/test_ui_runs.py::test_trigger_runs_exact_selected_priority_plus_pinned_once"),
]
only = sys.argv[2:] 
def run(d, node):
    env = dict(os.environ, PYTHONPATH=str(d/"src"))
    r = subprocess.run([PY,"-m","pytest","-p","no:xdist","--rootdir",str(d),"-c",str(d/"pyproject.toml"),str(d/node.split("::")[0])+"::"+node.split("::",1)[1]],
        capture_output=True, text=True, env=env)
    return r.returncode, r.stdout
for name, f, a, b, node in M:
    if only and name not in only: continue
    d = S/("fals"+"/"+name)
    if d.exists(): shutil.rmtree(d, ignore_errors=True)
    shutil.copytree(BASE, d, ignore=shutil.ignore_patterns(".git"))
    rc, out = run(d, node); print(f"## {name}: green-before rc={rc}", out.strip().splitlines()[-1])
    p = d/f; t = p.read_text(encoding="utf-8"); assert a in t, "mutation target missing"
    p.write_text(t.replace(a,b,1), encoding="utf-8")
    rc2, out2 = run(d, node)
    fails = [l for l in out2.splitlines() if l.startswith(("E ","FAILED"))][:6]
    print(f"## {name}: red-after rc={rc2}"); print("\n".join(fails)); print(out2.strip().splitlines()[-1])
    p.write_text(t, encoding="utf-8")
