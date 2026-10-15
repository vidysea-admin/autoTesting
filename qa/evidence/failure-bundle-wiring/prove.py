"""Bound each command to source/test/environment fingerprints before execution."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file())
OUT = Path(__file__).resolve().parent
PYTHON = sys.executable
FILES = ["src/autotester/schema/failure_bundle.py", "src/autotester/stages/run_artifacts.py",
         "src/autotester/stages/run_launcher.py", "src/autotester/stages/report_export.py",
         "src/autotester/stages/failure_bundle.py", "src/autotester/core/image_privacy.py",
         "tests/test_run_failure_artifacts.py", "tests/conftest.py", "pyproject.toml", "uv.lock"]

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def run(label, args, source=None):
    source = source or ROOT
    command = [PYTHON, *args]
    env = dict(os.environ, PYTHONPATH=str(source / "src"), PYTHONDONTWRITEBYTECODE="1")
    distributions = sorted(f"{d.metadata['Name']}=={d.version}" for d in importlib.metadata.distributions())
    receipt = {"label": label, "command": command, "python": PYTHON,
               "python_version": sys.version, "import_root": str(source / "src"),
               "dependency_sha256": hashlib.sha256("\n".join(distributions).encode()).hexdigest(),
               "file_sha256": {f: sha(source / f) for f in FILES},
               "started_at": time.time(), "status": "planned-before-command"}
    receipt["environment"] = {k: env.get(k) for k in ["PYTHONPATH", "PYTHONDONTWRITEBYTECODE",
                                                     "PYTEST_ADDOPTS", "OMP_THREAD_LIMIT"]}
    receipt["environment_sha256"] = hashlib.sha256(
        json.dumps(receipt["environment"], sort_keys=True).encode()).hexdigest()
    receipt["harness_sha256"] = {p.name: sha(p) for p in [OUT / "prove.py", OUT / "mutations.py"]
                                 if p.exists()}
    path = OUT / f"{label}.json"
    path.write_text(json.dumps(receipt, indent=2))
    started = time.perf_counter()
    result = subprocess.run(command, cwd=source, env=env, capture_output=True, text=True, timeout=90)
    output = OUT / f"{label}.log"
    output.write_text(result.stdout + result.stderr, encoding="utf-8")
    receipt.update(exit_code=result.returncode, duration_s=time.perf_counter()-started,
                   output_sha256=sha(output), status="finished", finished_at=time.time())
    path.write_text(json.dumps(receipt, indent=2))
    print(label, result.returncode, output, flush=True)
    return result

if __name__ == "__main__":
    label = sys.argv[1] if len(sys.argv) > 1 else "initial-tests"
    result = run(label, ["-m", "pytest", "tests/test_run_failure_artifacts.py",
                                  "--basetemp", str(OUT / f"pytest-{label}")])
    print(result.stdout + result.stderr)
    sys.exit(result.returncode)
