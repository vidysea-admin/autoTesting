import sys, shutil, pathlib, subprocess, os
here = pathlib.Path(sys.argv[0]).parent
sroot = sys.argv[1]
sys.argv = [sys.argv[0], sroot, "__none__"]
src = (here / "mutants.py").read_text(encoding="utf-8").split("def run(root, args):")[0]
exec(src)
S = pathlib.Path(sroot); head = S / "head"
root = S / "mut_m6c_debug"; shutil.rmtree(root, ignore_errors=True)
shutil.copytree(head, root, ignore=shutil.ignore_patterns("qa", ".goal"))
M["M6c_seams_field_honoured_truthy"][0](root)
tp = root / "tests/test_run_launcher_approval.py"; t = tp.read_text(encoding="utf-8")
needle = "    if isinstance(raised.value, LaunchRefused):"
assert t.count(needle) == 1
nl = chr(10)
tp.write_text(t.replace(needle, "    print('RAISED', type(raised.value).__name__, str(raised.value)[:300])" + nl + needle), encoding="utf-8")
env = dict(os.environ, PYTHONPATH=str(root / "src"))
p = subprocess.run([PY, "-m", "pytest", "-p", "no:xdist", "-o", "addopts=", "-p", "no:cacheprovider", "--tb=short", "-s",
                    "tests/test_run_launcher_approval.py", "-k", "no_seam_value and skip_approval"],
                   cwd=root, env=env, capture_output=True, text=True)
print(p.stdout[-3000:])
shutil.rmtree(root, ignore_errors=True)
