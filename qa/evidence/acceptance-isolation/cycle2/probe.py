"""Rebind seven acceptance guard proofs without repeating unrelated tests."""
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

root = Path.cwd()
out = root / "qa/evidence/acceptance-isolation/cycle2"
out.mkdir(parents=True, exist_ok=True)
work = root / ".work/acceptance-cycle2-sandbox"
assert not work.exists(), "Use a fresh owned sandbox; never overwrite a prior proof"
work.mkdir()
for name in ("src", "tests", "scripts"):
    shutil.copytree(root / name, work / name,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
shutil.copy2(root / "pyproject.toml", work / "pyproject.toml")
assert (work / "tests/tests_mutation_fixtures.py").exists()
plugin = work / "_proof_report.py"
plugin.write_text('''import json, os
failed = []
def pytest_runtest_logreport(report):
    if report.when == "call" and report.failed:
        failed.append(report.nodeid)
def pytest_sessionfinish(session):
    open(os.environ["ACCEPTANCE_PROOF_REPORT"], "w").write(json.dumps(failed))
''')
env = dict(os.environ, PYTHONPATH=os.pathsep.join(
    str(p) for p in (work / "src", work, work / "tests", work / "scripts")),
    PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
code_sha = "7cda16f66dc96514edb3776efd32af64ca5e1791"
files = ["src/autotester/stages/real_acceptance.py",
         "src/autotester/stages/generic_acceptance.py", "scripts/run_real_acceptance.py",
         "tests/test_acceptance_isolation.py"]
def sha(data):
    return hashlib.sha256(data).hexdigest()
identity = dict(code_sha=code_sha, python=sys.executable, python_version=platform.python_version(),
                lock_sha256=sha((root / "uv.lock").read_bytes()),
                source_sha256={f:sha((root/f).read_bytes()) for f in files},
                sandbox_source_sha256={f:sha((work/f).read_bytes()) for f in files},
                import_root=str(work / "src"), sandbox=str(work),
                versions={n:importlib.metadata.version(n) for n in ("pytest", "pydantic", "fastapi", "starlette")},
                env_fingerprint=sha(json.dumps({k:env.get(k) for k in sorted(env)
                    if k.startswith(("PYTHON", "AUTOTESTER"))},sort_keys=True).encode()),
                token_usage=None, active_seconds=None)
assert identity["source_sha256"] == identity["sandbox_source_sha256"]
for f in files:
    blob=subprocess.check_output(["git", "show", code_sha+":"+f],cwd=root)
    assert blob.decode().replace("\r\n", "\n") == (root/f).read_text()
(out/"identity.json").write_text(json.dumps(identity,indent=2))
receipts=[]
def run(name, argv):
    began=datetime.now(timezone.utc).isoformat(); tick=time.monotonic()
    result=subprocess.run(argv,cwd=work,env=env,stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,text=True,timeout=90)
    (out/(name+".log")).write_text(result.stdout,encoding="utf-8")
    receipts.append(dict(name=name,argv=argv,started_at=began,
        ended_at=datetime.now(timezone.utc).isoformat(),duration_s=time.monotonic()-tick,
        exit_code=result.returncode,identity="identity.json"))
    (out/"commands.json").write_text(json.dumps(receipts,indent=2))
    return result
helper=r"C:/Users/product/.agents/skills/checker/scripts/review_budget.py"
assert run("preflight",[sys.executable,helper,"preflight","--root",str(work),
    "--import-name","autotester","--import-root",str(work/"src"),
    "--temp-parent",str(work)]).returncode == 0
spec=json.loads((out.parent/"mutations.json").read_text())
proofs=[]
for index,mutation in enumerate(spec["mutations"][1:],1):
    node="tests/test_acceptance_isolation.py::"+mutation["kills"][0]
    report=work/("report-"+str(index)+".json")
    env["ACCEPTANCE_PROOF_REPORT"]=str(report)
    command=[sys.executable,"-m","pytest",node,"-o","addopts=","-q",
             "-p","no:cacheprovider","-p","_proof_report",
             "--basetemp",str(work/("temp-"+str(index)+"-baseline"))]
    baseline=run(str(index)+"-baseline",command)
    assert baseline.returncode == 0, baseline.stdout
    assert json.loads(report.read_text()) == []
    target=work/mutation["file"]; original=target.read_bytes()
    text=original.decode(); assert text.count(mutation["old"]) == 1
    changed=text.replace(mutation["old"],mutation["new"],1).encode()
    assert changed != original
    target.write_bytes(changed); assert target.read_bytes()==changed
    try:
        command[-1]=str(work/("temp-"+str(index)+"-mutated"))
        red=run(str(index)+"-mutated",command)
        failures=json.loads(report.read_text())
        assert red.returncode==1 and node in failures,(red.returncode,failures,red.stdout)
    finally:
        target.write_bytes(original)
        assert target.read_bytes()==original
    proofs.append(dict(name=mutation["name"],nodeid=node,baseline_exit=0,mutated_exit=1,
        failed=failures,file=mutation["file"],old=mutation["old"],new=mutation["new"],
        original_sha256=sha(original),mutated_sha256=sha(changed),restored_sha256=sha(target.read_bytes()),
        anchor_count=1,identity="identity.json"))
    (out/"proofs.json").write_text(json.dumps(proofs,indent=2))
    print(index,mutation["name"],"KILLED",flush=True)
assert all(sha((work/f).read_bytes())==identity["source_sha256"][f] for f in files)
print("7/7 exact-bound single-defender proofs complete",flush=True)
