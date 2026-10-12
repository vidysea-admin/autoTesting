import shutil, subprocess, sys, os
from pathlib import Path
S = Path(os.environ["S"]); SRC = S / "b-copy"; WORK = S / "b-at890"
PY = str(S / "venv-b2" / "Scripts" / "python.exe")
GUARD = "prompt = guard_expand_prompt(build_expand_prompt(flow, proposal.case_class, docs), secrets)"
M = {
 "F6": ("_expand_reviewed_flow", GUARD, "prompt = build_expand_prompt(flow, proposal.case_class, docs)"),
 "F7": ("build_expand_prompt", '.replace("{{ORIGINAL_STEPS}}", mask_pii(steps_text))', '.replace("{{ORIGINAL_STEPS}}", steps_text)'),
 "F8": ("guard_expand_prompt", "return secrets.guard_prompt(secrets.redactor().scrub(prompt))",
        "return __import__('re').sub(r'\{\{SECRET:[A-Z0-9_]+\}\}', '[REDACTED]', secrets.guard_prompt(secrets.redactor().scrub(prompt)))"),
 "F9": ("_expand_reviewed_flow", GUARD,
        "prompt = guard_expand_prompt(build_expand_prompt(flow.model_copy(update={'name': 'FLOWNAMEX'}), proposal.case_class, docs), secrets).replace('FLOWNAMEX', mask_pii(flow.name))"),
}
fid = sys.argv[1]
d = WORK / f"fz-{fid}"
shutil.rmtree(d, ignore_errors=True); d.mkdir()
shutil.copytree(SRC / "src", d / "src", ignore=shutil.ignore_patterns("__pycache__"))
shutil.copytree(SRC / "tests", d / "tests", ignore=shutil.ignore_patterns("__pycache__"))
shutil.copy(SRC / "pyproject.toml", d / "pyproject.toml")
(d / "scripts").mkdir(); shutil.copy(SRC / "scripts" / "regression_proof.py", d / "scripts" / "regression_proof.py")
env = dict(os.environ, PYTHONPATH=str(d / "src"), UV_PROJECT_ENVIRONMENT="")
def pyt(label, args):
    r = subprocess.run([PY, "-m", "pytest", "-p", "no:xdist", "-o", "addopts=", "-q", "--tb=line", "tests/test_expand_redaction.py"] + args,
                       cwd=d, env=env, capture_output=True, text=True, timeout=420)
    tail = [l for l in r.stdout.splitlines() if l.startswith(("FAILED", "E ", "/")) or "passed" in l or "failed" in l or "assert" in l.lower()]
    print(f"[{fid}] {label} rc={r.returncode}"); r.returncode and print(r.stdout[-600:], r.stderr[-300:]); print("\n".join(tail[-14:]), flush=True)
fn, old, new = M[fid]
r = subprocess.run([PY, "-c", "import autotester;print(autotester.__file__)"], cwd=d, env=env, capture_output=True, text=True)
print(f"[{fid}] autotester.__file__ =", r.stdout.strip())
pyt("BASELINE", [])
p = d / "src/autotester/stages/expand.py"; t = p.read_text(encoding="utf-8")
assert t.count(old) == 1, t.count(old)
p.write_text(t.replace(old, new), encoding="utf-8")
print(f"[{fid}] mutated function={fn}; hunk old=`{old}` new=`{new}`")
pyt("MUTATED", [])
shutil.rmtree(d, ignore_errors=True)
