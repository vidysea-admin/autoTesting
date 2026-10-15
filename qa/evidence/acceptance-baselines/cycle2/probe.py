"""One resolved-source containment fix: contemporary byte seal and focused guard proof."""

import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
WORK = ROOT / ".work" / "baseline-proofs-cycle2"
OLD = ROOT / "qa/evidence/acceptance-baselines/risk-proofs"
STAGE = "src/autotester/stages/acceptance_baseline.py"
TEST = "tests/test_acceptance_baseline.py"
BEFORE = "8d793363a2d0d3098ce4172eec8cf096036855c6"
FAIL = "93d9ad143937fbf4b5353441da4a2a0e930e5259"
NEW_TEST = TEST + "::test_resolved_source_project_stays_in_supplied_root"
NODES = [TEST+"::test_same_build_scoped_refs_and_input_only_isolation",
         NEW_TEST+"[inside]", NEW_TEST+"[outside]"]
GUARD = ('    if (not source_dir.is_relative_to(source_root)\n'
         '            or not config_path.is_relative_to(source_root)):\n'
         '        raise ValueError("source project must remain within the supplied source root")\n')


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def dump(name, value):
    path = OUT / name
    if path.exists():
        assert json.loads(path.read_bytes()) == value, name
    else:
        path.write_bytes(json.dumps(value, indent=2).encode())


def git_blob(commit, path):
    return subprocess.check_output(["git", "show", commit+":"+path], cwd=ROOT)


def inventory(root):
    return {p.relative_to(root).as_posix(): sha(p.read_bytes()) for part in ("src", "tests", "scripts")
            for p in (root/part).rglob("*") if p.is_file() and "__pycache__" not in p.parts
            and p.suffix != ".pyc"}


def main():
    prior = json.loads((OLD/"identity.json").read_bytes())
    old_stage, current = git_blob(BEFORE, STAGE), (ROOT/STAGE).read_bytes()
    anchor = b'    source_dir = ProjectPaths(safe_slug(plan.source_slug), source_root).dir.resolve()\n'
    inserted = anchor + b'    config_path = ProjectPaths(plan.source_slug, source_root).config.resolve()\n' + GUARD.encode()
    old_read = b'config = ProjectPaths(plan.source_slug, source_root).config.read_bytes()'
    assert old_stage.count(anchor) == old_stage.count(old_read) == 1
    assert current == old_stage.replace(anchor, inserted, 1).replace(old_read, b'config = config_path.read_bytes()', 1)
    assert current.count(GUARD.encode()) == 1
    old_test, new_test = git_blob(BEFORE, TEST), (ROOT/TEST).read_bytes()
    assert new_test.startswith(old_test)
    assert new_test[len(old_test):].count(b'def test_resolved_source_project_stays_in_supplied_root(') == 1
    prior_inventory = json.loads((OLD/"inventory.json").read_bytes())
    current_inventory = inventory(ROOT)
    assert prior_inventory.keys() == current_inventory.keys()
    changed = sorted(p for p in current_inventory if current_inventory[p] != prior_inventory[p])
    assert changed == sorted([STAGE, TEST])
    assert sha((ROOT/"uv.lock").read_bytes()) == prior["lock_sha256"]
    versions = {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()}
    assert versions == prior["versions"] and platform.python_version() == prior["python_version"]
    assert Path(sys.executable).resolve() == Path(prior["python"]).resolve()
    if not WORK.exists():
        WORK.mkdir(parents=True)
        for part in ("src", "tests", "scripts"):
            shutil.copytree(ROOT/part, WORK/part, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for part in ("pyproject.toml", "uv.lock"):
            shutil.copy2(ROOT/part, WORK/part)
    assert inventory(WORK) == current_inventory
    dump("inventory.json", current_inventory)
    plugin = WORK/"_source_reports.py"
    plugin.write_bytes(b'import json,os\nfailed=[]\n'
        b'def pytest_runtest_logreport(report):\n'
        b'    if report.failed and report.when=="call": failed.append(report.nodeid)\n'
        b'def pytest_sessionfinish(session):\n'
        b'    open(os.environ["SOURCE_REPORT"],"w").write(json.dumps(failed))\n')
    env = dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1",
               PYTHONPATH=os.pathsep.join(str(p) for p in (WORK/"src", WORK, WORK/"tests", WORK/"scripts")))
    controls = ("PYTHONPATH", "PYTHONUTF8", "PYTHONDONTWRITEBYTECODE", "AUTOTESTER_ROOT",
                "AUTOTESTER_AUTH_DIR", "AUTOTESTER_AUTH_DISABLED", "AUTOTESTER_TEST_AUTO_LOGIN",
                "AUTOTESTER_ALLOWED_ORIGINS")
    old_env = dict(env, PYTHONPATH=os.pathsep.join(str(p) for p in (
        ROOT/".work/baseline-proofs/src", ROOT/".work/baseline-proofs",
        ROOT/".work/baseline-proofs/tests", ROOT/".work/baseline-proofs/scripts")))
    assert sha(json.dumps({k:old_env.get(k) for k in controls}, sort_keys=True).encode()) == prior["env_fingerprint"]
    code = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    for path in (STAGE, TEST):
        assert git_blob(code, path) == (ROOT/path).read_bytes()
    dump("identity.json", dict(code_sha=code, base_fail_sha=FAIL, python=sys.executable,
        python_version=platform.python_version(), versions=versions,
        source_sha256={p:sha((ROOT/p).read_bytes()) for p in (STAGE, TEST)},
        lock_sha256=prior["lock_sha256"], inventory_sha256=sha((OUT/"inventory.json").read_bytes()),
        harness_sha256=sha(Path(__file__).read_bytes()), plugin_sha256=sha(plugin.read_bytes()),
        env_fingerprint=sha(json.dumps({k:env.get(k) for k in controls}, sort_keys=True).encode()),
        import_root=str(WORK/"src"), maker_active_seconds=None, tokens=None, cost=None))
    dump("mutation.json", dict(file=STAGE, old=GUARD, new="", kills=[NODES[-1]]))
    dump("reuse.json", dict(prior_code=BEFORE, prior_wrapper="417b3c011ec92308812a1436eb98a47b0bfb489a",
        authenticated_by=FAIL, prior_identity_sha256=sha((OLD/"identity.json").read_bytes()),
        compatibility_sha256=sha((ROOT/"qa/evidence/acceptance-baselines/checker-cycle1/compatible.json").read_bytes()),
        source_delta_exact_two_hunks=True, original_22_test_bodies_unchanged=True,
        changed_inventory_paths=changed, other_source_entries_unchanged=len(current_inventory)-2,
        interpreter_dependencies_lock_unchanged=True, explicit_import_root_mapping=True,
        prior_13_proofs_are_old_sha_not_relabelled=True,
        reasoning="Only resolved source-root preflight and validated config read changed. All prior fixtures are in-root. Remaining helper bodies, schema/script, original tests and consumers are byte-identical; prior authenticated 13 chains retained. Changed source boundary gets fresh legitimate/escape/no-output execution and guard proof."))
    fail_blob = git_blob(FAIL, "qa/verdicts/acceptance-baselines.md")
    git_verdict = OUT/"cycle1-verdict.git.md"
    if not git_verdict.exists():
        git_verdict.write_bytes(fail_blob)
    assert git_verdict.read_bytes() == fail_blob
    if "--audit-only" in sys.argv:
        print("AUDIT_READY: exact source delta, append-only tests, complete copy and prior environment authenticated")
        return
    assert not (OUT/"commands.json").exists(), "Preserve every previous command attempt"
    commands = []
    report = WORK/"failed.json"
    env["SOURCE_REPORT"] = str(report)

    def run(label, argv):
        tick = time.monotonic()
        report.unlink(missing_ok=True)
        result = subprocess.run(argv, cwd=WORK, env=env, capture_output=True, timeout=90)
        log = OUT/(label+".log")
        assert not log.exists()
        log.write_bytes(result.stdout+result.stderr)
        if report.exists():
            log.with_suffix(".report.json").write_bytes(report.read_bytes())
        commands.append(dict(label=label, argv=argv, exit_code=result.returncode,
            duration_s=time.monotonic()-tick, output_sha256=sha(log.read_bytes()),
            report_sha256=sha(report.read_bytes()) if report.exists() else None,
            source_sha256={p:sha((WORK/p).read_bytes()) for p in (STAGE, TEST)},
            identity_sha256=sha((OUT/"identity.json").read_bytes()),
            spec_sha256=sha((OUT/"mutation.json").read_bytes())))
        (OUT/"commands.json").write_bytes(json.dumps(commands, indent=2).encode())
        return result.returncode

    helper = "C:/Users/product/.agents/skills/checker/scripts/review_budget.py"
    assert run("preflight", [sys.executable, helper, "preflight", "--root", str(WORK),
        "--import-name", "autotester", "--import-root", str(WORK/"src"), "--temp-parent", str(WORK)]) == 0
    argv = [sys.executable, "-m", "pytest", *NODES, "-p", "no:cacheprovider", "-p", "_source_reports"]
    assert run("green", [*argv, "--basetemp", str(WORK/"temp-green")]) == 0
    assert json.loads(report.read_bytes()) == []
    target = WORK/STAGE
    before = target.read_bytes()
    mutated = before.replace(GUARD.encode(), b"", 1)
    assert before.count(GUARD.encode()) == 1 and mutated != before
    target.write_bytes(mutated)
    assert target.read_bytes() == mutated
    try:
        red = [sys.executable, "-m", "pytest", NODES[-1], "-p", "no:cacheprovider", "-p", "_source_reports"]
        assert run("red", [*red, "--basetemp", str(WORK/"temp-red")]) == 1
        failed = json.loads(report.read_bytes())
        assert NODES[-1] in failed
    finally:
        target.write_bytes(before)
        assert target.read_bytes() == before
    assert run("restored", [*argv, "--basetemp", str(WORK/"temp-restored")]) == 0
    assert json.loads(report.read_bytes()) == []
    assert run("lint", [sys.executable, "-m", "ruff", "check", STAGE, TEST]) == 0
    shape = ('import ast,pathlib; paths='+repr([STAGE, TEST])+'\n'
        'for n in paths:\n p=pathlib.Path(n); t=ast.parse(p.read_bytes()); '
        'assert len(p.read_bytes().splitlines())<=300 and ast.get_docstring(t); '
        'assert all(x.end_lineno-x.lineno+1<=50 for x in ast.walk(t) '
        'if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef)))\nprint("shape OK")')
    assert run("shape", [sys.executable, "-c", shape]) == 0
    assert inventory(ROOT) == inventory(WORK) == current_inventory
    dump("proof.json", dict(anchor_count=1, original_sha256=sha(before), mutated_sha256=sha(mutated),
        restored_sha256=sha(target.read_bytes()), failed=failed, green=0, red=1, restored=0,
        guard_proofs=1, focused_cases=3, command_seconds=sum(c["duration_s"] for c in commands),
        maker_active_seconds=None, tokens=None, cost=None))
    print("PROOF_READY: three focused cases, one named guard RED and restored GREEN; lint/shape clean")


if __name__ == "__main__":
    main()
