"""Supplementary byte-bound local-cap and finite-timeout guard mutations."""
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

root = Path(__file__).resolve().parents[3]
copy = root / ".work/gemini-mutation"
out = root / "qa/evidence/gemini-media-guard"
for name in ("src", "tests", "scripts"):
    shutil.copytree(root / name, copy / name, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__"))
env = dict(os.environ, PYTHONPATH=str(copy / "src"))
rows = []
node = "tests/test_gemini_request_limits.py"
source = copy / "src/autotester/providers/gemini.py"
original = source.read_bytes()


def check(label, expected):
    start = time.monotonic()
    args = ["-m", "pytest", node, "--basetemp", ".work/"+label]
    result = subprocess.run([sys.executable, *args], cwd=copy, env=env,
                            capture_output=True, timeout=60)
    log = out / (label+".log")
    log.write_bytes(result.stdout+result.stderr)
    rows.append(dict(label=label, command=args, exit=result.returncode,
        duration_s=time.monotonic()-start, log=str(log),
        log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
    (out/"limits-results.json").write_bytes(json.dumps(rows,indent=2).encode())
    assert result.returncode == expected
    return result.stdout


check("limits-green", 0)
for label, old, new, named in [
    ("limits-cap-red", b"with attempt_budget(32, timeout):", b"with attempt_budget(33, timeout):",
     b"test_gemini_provider_owned_cap_exists_without_outer_cap"),
    ("limits-timeout-red", b"if not math.isfinite(timeout) or not 0 < timeout <= 120:", b"if False:",
     b"test_gemini_nonfinite_or_excessive_timeout_is_local_refusal"),
]:
    assert old in original
    changed = original.replace(old,new)
    ast.parse(changed)
    source.write_bytes(changed)
    assert source.read_bytes() == changed
    output = check(label, 1)
    rows[-1].update(mutation_old=old.decode(), mutation_new=new.decode(),
        original_sha256=hashlib.sha256(original).hexdigest(),
        attributable=b"FAILED" in output and named in output)
    source.write_bytes(original)
    assert source.read_bytes() == original and rows[-1]["attributable"]
    (out/"limits-results.json").write_bytes(json.dumps(rows,indent=2).encode())
check("limits-restored-green", 0)
print("2 named-red limit guards, restored green")
