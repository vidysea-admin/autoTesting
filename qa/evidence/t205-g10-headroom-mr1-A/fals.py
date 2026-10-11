"""Falsification driver (checker A): copy the head tree to a fresh dir, run the named tests GREEN,
apply ONE unique-anchor edit, run again (must be RED on an assertion, not import/setup)."""
import json, os, shutil, subprocess, sys, tempfile, pathlib
W = pathlib.Path(sys.argv[1]); spec = json.loads(sys.argv[2])
src = W / "copy"; PY = str(src / ".venv" / "Scripts" / "python.exe")
dst = pathlib.Path(tempfile.mkdtemp(prefix="mr1a-f-", dir=str(W)))
shutil.copytree(src, dst / "t", ignore=shutil.ignore_patterns(".venv", "__pycache__", ".pytest_cache", ".work"))
root = dst / "t"
for extra in spec.get("copy_in", []):
    shutil.copy(extra, root / "tests" / pathlib.Path(extra).name)
env = dict(os.environ, PYTHONPATH=str(root / "src"), MR_COPY=str(root))
def run():
    p = subprocess.run([PY, "-m", "pytest", *spec["tests"], "-p", "no:xdist", "-o", "addopts=", "-p", "no:cacheprovider", "--tb=line", "-q", "-x" if False else "-q"],
                       cwd=root, env=env, capture_output=True, text=True, timeout=900)
    tail = [l for l in p.stdout.splitlines() if l.strip()][-6:]
    return p.returncode, tail
g = run(); print("GREEN-BEFORE rc", g[0], g[1][-1])
f = root / spec["file"]; t = f.read_text(encoding="utf-8"); old = spec["old"]
assert t.count(old) == 1, f"anchor count {t.count(old)}"
f.write_text(t.replace(old, spec["new"]), encoding="utf-8", newline="")
r = run(); print("RED-AFTER rc", r[0]); print("\n".join(r[1]))
shutil.rmtree(dst, ignore_errors=True)
