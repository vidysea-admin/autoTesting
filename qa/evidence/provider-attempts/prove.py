"""Replay fingerprinted green/red/restored proofs in a disposable, cache-free copy."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
COPY = ROOT / ".work/provider-attempts/proof-copy-2"
PYTHON = Path(sys.executable)
TEST = "tests/test_provider_attempts.py"
COUNT = "test_attempt_count_reserves_before_repair_and_fallback"
TRACE = "test_failed_attempts_trace_unknown_usage_and_preserve_winner"
NESTED = "test_nested_budget_rejects_atomically_and_context_restores"
TIME = "test_deadline_caps_transport_and_exhausts_before_next_request"
MUTATIONS = [
("count", "providers/attempts.py", "if scope.used >= scope.max_calls:", "if False:", COUNT),
("deadline", "providers/attempts.py", "if timeout_s <= 0:", "if False:", TIME),
("remaining", "providers/attempts.py", "timeout_s = min(timeout_s, scope.deadline - time.monotonic())", "timeout_s = timeout_s", TIME),
("nested", "providers/attempts.py", "(*_SCOPES.get(), budget)", "(budget,)", COUNT),
("restore", "providers/attempts.py", "_SCOPES.reset(token)", "_SCOPES.set(())", NESTED),
("max-validation", "providers/attempts.py", "if isinstance(max_calls, bool) or not isinstance(max_calls, int) or max_calls < 0:", "if False:", NESTED),
("time-validation", "providers/attempts.py", "if wall_clock_s is not None and (not math.isfinite(wall_clock_s) or wall_clock_s < 0):", "if False:", TIME),
("failed-account", "providers/litellm_provider.py", "self.record(role, None, None, failed=True, prompt_file=prompt_file,", "self.record(role, 0, 0, failed=False, prompt_file=prompt_file,", TRACE),
("usage-unknown", "providers/litellm_provider.py", 'getattr(usage, "prompt_tokens", None)', 'getattr(usage, "prompt_tokens", 0) or 0', TRACE),
("unknown-total", "providers/base.py", "None if entry.input_tokens is None or input_tokens is None", "0 if entry.input_tokens is None or input_tokens is None", COUNT),
("unknown-cap", "stages/video_review.py", "if any(u.input_tokens is None or u.output_tokens is None for u in provider.usage):", "if False:", TRACE),
("unknown-display", "ui/routes_report.py", '"unknown" if s.cost is None', '"$0.0000" if s.cost is None', TRACE),
("isolation", "providers/isolated.py", "entry.failed_calls += usage.failed_calls", "entry.failed_calls += 0", TRACE),
("strict-shape", "schema/provider_attempt.py", 'ConfigDict(extra="forbid")', 'ConfigDict(extra="ignore")', NESTED),
]

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

if COPY.exists():
    raise RuntimeError("use a fresh proof-copy; never delete a prior receipt")
COPY.mkdir(parents=True)
for folder in ("src", "tests", "scripts"):
    shutil.copytree(ROOT / folder, COPY / folder, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
for name in ("pyproject.toml", "uv.lock"):
    shutil.copy2(ROOT / name, COPY / name)
(COPY / ".work").mkdir()
(COPY / "_attempt_report.py").write_text('import json, os\n_failed=[]\ndef pytest_runtest_logreport(report):\n    if report.when == "call" and report.failed: _failed.append(report.nodeid)\ndef pytest_sessionfinish(session):\n    open(os.environ["ATTEMPT_REPORT"],"w").write(json.dumps(_failed))\n')
env = {**os.environ, "PYTHONPATH": str(COPY / "src") + os.pathsep + str(COPY), "PYTHONDONTWRITEBYTECODE": "1"}
files = sorted(set(["src/autotester/" + m[1] for m in MUTATIONS] + [TEST, "tests/litellm_fake.py", "tests/conftest.py", "tests/tests_mutation_fixtures.py", "pyproject.toml", "uv.lock"]))
deps = sorted((d.metadata["Name"], d.version) for d in importlib.metadata.distributions())
fingerprint = {"python": str(PYTHON), "version": sys.version, "dependencies_sha256": hashlib.sha256(json.dumps(deps).encode()).hexdigest(), "lock": digest(ROOT / "uv.lock")}
(OUT / "environment.json").write_text(json.dumps({**fingerprint, "dependencies": deps}, indent=2))
records=[]

def run(label, node, expected=0):
    report = OUT / (label + ".failures.json")
    before = {f: digest(COPY / f) for f in files}
    started = datetime.now(timezone.utc).isoformat()
    env["ATTEMPT_REPORT"] = str(report)
    command=[str(PYTHON), "-m", "pytest", node, "-p", "_attempt_report", "--basetemp", str(COPY / ".work" / label)]
    tick=time.perf_counter()
    proc=subprocess.run(command,cwd=COPY,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60)
    elapsed=time.perf_counter()-tick
    log=OUT / (label + ".log"); log.write_text(proc.stdout)
    row={"phase":label,"started":started,"duration_s":elapsed,"command":command,"exit":proc.returncode,"output_sha256":digest(log),"source_before":before,"source_after":{f:digest(COPY / f) for f in files},"environment":fingerprint,"failed":json.loads(report.read_text())}
    records.append(row); (OUT / "receipts.json").write_text(json.dumps(records,indent=2))
    assert proc.returncode == expected, (label, proc.returncode, proc.stdout)
    assert row["source_before"] == row["source_after"]
    print(label, proc.returncode, flush=True)
    return row

preflight=[str(PYTHON), r"C:/Users/product/.agents/skills/checker/scripts/review_budget.py", "preflight", "--root", str(COPY), "--import-name", "autotester", "--import-root", str(COPY / "src"), "--temp-parent", str(COPY / ".work")]
probe=subprocess.run(preflight,cwd=COPY,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
(OUT / "preflight.log").write_text(probe.stdout); assert probe.returncode == 0, probe.stdout
run("baseline", TEST)
for name,file,old,new,kills in MUTATIONS:
    path=COPY / "src/autotester" / file
    original=path.read_bytes(); text=path.read_text(); assert text.count(old)==1, name
    changed=text.replace(old,new); path.write_text(changed); assert path.read_bytes()!=original
    try:
        row=run(name+"-red", TEST+"::"+kills, 1)
        assert TEST+"::"+kills in row["failed"], name
    finally:
        path.write_bytes(original); assert path.read_bytes()==original
    run(name+"-restored", TEST+"::"+kills)
(OUT / "mutations.json").write_text(json.dumps({"tests":TEST,"mutations":[{"name":n,"file":"src/autotester/"+f,"old":a,"new":b,"kills":[TEST+"::"+t]} for n,f,a,b,t in MUTATIONS]},indent=2))
print("ALL MUTATIONS ATTRIBUTED AND RESTORED", flush=True)
