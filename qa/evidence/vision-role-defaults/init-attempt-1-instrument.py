"""Byte-exact risk-based role/migration proof with complete isolated test inventory."""
import ast
import hashlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/".work/role-proof"
COPY = OUT/"subject"
TESTS = ["tests/test_vision_roles.py", "tests/test_provider_migration.py",
         "tests/test_provider_factory.py::test_the_factory_resolves_the_receipt_bound_visual_role",
         "tests/test_schema.py::test_vision_ensemble_splits_the_config_and_deduplicates",
         "tests/test_schema.py::test_vision_ensemble_empty_config_uses_visual_policy",
         "tests/test_schema.py::test_vision_ensemble_defaulted_distinguishes_empty_from_explicit_gemini",
         "tests/test_ensemble_honesty.py::test_analyze_route_records_the_default_when_vision_config_is_empty"]
SPEC = ROOT/"qa/evidence/vision-role-defaults/spec.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(name, nodes):
    env = dict(os.environ, PYTHONPATH=str(COPY/"src"), PYTHONDONTWRITEBYTECODE="1")
    command = [sys.executable, "-B", "-m", "pytest", *nodes, "--tb=short",
               "--junitxml="+str(OUT/(name+".xml")), "--basetemp="+str(OUT/("tmp-"+name))]
    start, timestamp = time.monotonic(), datetime.now(UTC).isoformat()
    proc = subprocess.run(command, cwd=COPY, env=env, capture_output=True, timeout=100)
    log = OUT/(name+".log")
    log.write_bytes(proc.stdout+proc.stderr)
    return {"phase":name,"command":command,"exit":proc.returncode,
            "started_at":timestamp,"ended_at":datetime.now(UTC).isoformat(),
            "duration_s":time.monotonic()-start,"log_sha256":digest(log)}


def init():
    assert not OUT.exists(), "preserve failed setup and choose fresh output"
    spec = json.loads(SPEC.read_bytes())
    assert len({r["name"] for r in spec["mutations"]}) == len(spec["mutations"])
    for name in spec["python_paths"]:
        text = (ROOT/name).read_bytes().decode()
        assert len(text.splitlines()) <= 300, name
        assert all(n.end_lineno-n.lineno <= 50 for n in ast.walk(ast.parse(text))
                   if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))), name
    COPY.mkdir(parents=True)
    for name in ("src","tests","scripts"):
        shutil.copytree(ROOT/name,COPY/name,
                        ignore=shutil.ignore_patterns("__pycache__",".pytest_cache"))
    for name in ("pyproject.toml","uv.lock",".gitattributes"):
        (COPY/name).write_bytes((ROOT/name).read_bytes())
    (COPY/".work").mkdir()
    assert (COPY/"tests/tests_mutation_fixtures.py").is_file()
    files = {p.relative_to(COPY).as_posix():digest(p) for p in COPY.rglob("*") if p.is_file()}
    expected = {p.relative_to(ROOT).as_posix():digest(p)
                for name in ("src","tests","scripts") for p in (ROOT/name).rglob("*")
                if p.is_file() and "__pycache__" not in p.parts and ".pytest_cache" not in p.parts}
    assert all(files[name] == value for name,value in expected.items())
    command = [sys.executable,"C:/Users/product/.agents/skills/checker/scripts/review_budget.py",
               "preflight","--root",str(COPY),"--import-name","autotester",
               "--import-root",str(COPY/"src"),"--temp-parent",str(COPY/".work")]
    proc = subprocess.run(command,cwd=COPY,capture_output=True,timeout=30,
                          env=dict(os.environ,PYTHONPATH=str(COPY/"src")))
    (OUT/"preflight.log").write_bytes(proc.stdout+proc.stderr)
    assert proc.returncode == 0
    lint = [sys.executable,"-m","ruff","check",*spec["python_paths"]]
    proc = subprocess.run(lint,cwd=COPY,capture_output=True,timeout=60)
    (OUT/"lint.log").write_bytes(proc.stdout+proc.stderr)
    assert proc.returncode == 0, (proc.stdout+proc.stderr).decode()
    data = {"root":str(ROOT),"python":sys.executable,"version":sys.version,"files":files,
            "instrument_sha256":digest(Path(__file__)),"spec_sha256":digest(SPEC),
            "preflight_sha256":digest(OUT/"preflight.log"),"lint_sha256":digest(OUT/"lint.log"),
            "lint_command":lint,"mutations":[],"bursts":[],
            "dependencies":{n:importlib.metadata.version(n) for n in
                            ("pydantic","pytest","Pillow","litellm","python-dotenv")},
            "fixtures":"Normal global conftest retained. Both new modules apply actual litellm_fake.no_network; selected existing factory consumer retains its original security fixtures.",
            "baseline":run("baseline",TESTS)}
    (OUT/"receipts.json").write_bytes(json.dumps(data,indent=2).encode())
    assert data["baseline"]["exit"] == 0
    print("BASELINE_GREEN",len(spec["mutations"]),flush=True)


def burst(count):
    data = json.loads((OUT/"receipts.json").read_bytes())
    spec = json.loads(SPEC.read_bytes())
    assert data["instrument_sha256"] == digest(Path(__file__))
    assert data["spec_sha256"] == digest(SPEC) and data["baseline"]["exit"] == 0
    assert all(digest(COPY/path) == value for path,value in data["files"].items())
    start = len(data["mutations"])
    for mutation in spec["mutations"][start:start+count]:
        path, name = COPY/mutation["file"],mutation["name"]
        original = path.read_bytes()
        old,new = mutation["old"].encode(),mutation["new"].encode()
        if original.count(old) == 0 and b"\r\n" in original:
            old,new = old.replace(b"\n",b"\r\n"),new.replace(b"\n",b"\r\n")
        assert original.count(old) == 1, name
        changed = original.replace(old,new)
        assert changed != original
        path.write_bytes(changed)
        assert path.read_bytes() == changed
        try:
            row = run(name,mutation["kills"])
            failures = [n.attrib["name"] for n in ET.parse(OUT/(name+".xml")).iter("testcase")
                        if n.find("failure") is not None]
            expected = {node.split("::")[-1] for node in mutation["kills"]}
            assert row["exit"] == 1 and expected <= set(failures), name
            data["mutations"].append({**row,**mutation,"source_sha256":digest(ROOT/mutation["file"]),
                                      "mutated_sha256":digest(path),"failures":failures})
        finally:
            path.write_bytes(original)
            assert path.read_bytes() == original
        (OUT/"receipts.json").write_bytes(json.dumps(data,indent=2).encode())
        print(name,"KILLED",flush=True)
    restored = run("restored-"+str(len(data["mutations"])),TESTS)
    data["bursts"].append({"start":start,"end":len(data["mutations"]),"restored":restored})
    (OUT/"receipts.json").write_bytes(json.dumps(data,indent=2).encode())
    assert restored["exit"] == 0
    assert all(digest(COPY/path) == value for path,value in data["files"].items())
    print("RESTORED_GREEN",len(data["mutations"]),"of",len(spec["mutations"]),flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "init":
        init()
    else:
        burst(int(sys.argv[2]))
