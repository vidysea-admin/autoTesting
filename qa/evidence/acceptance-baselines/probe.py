"""Byte-bound isolated guard proofs; execution requires the coordinator's serial grant."""

import hashlib
import argparse
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
WORK = ROOT / ".work" / "baseline-proofs"
SOURCE = "src/autotester/stages/acceptance_baseline.py"
TEST = "tests/test_acceptance_baseline.py"
POSITIVE = TEST + "::test_same_build_scoped_refs_and_input_only_isolation"
FILES = [SOURCE, TEST, "src/autotester/schema/acceptance_baseline.py",
         "scripts/prepare_acceptance_baselines.py"]


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def dump(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2), encoding="utf-8")


def inventory(root):
    return {str(p.relative_to(root)).replace("\\", "/"): sha(p.read_bytes())
            for part in ("src", "tests", "scripts") for p in (root / part).rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}


def mutations():
    """Each named new behavior/guard has an applied, attributable semantic defect."""
    stale = TEST + "::test_stale_or_existing_plan_refused_without_writes"
    inputs = TEST + "::test_only_explicit_approved_contained_inputs"
    refs = TEST + "::test_credential_reference_scope_never_widens"
    source = (ROOT / SOURCE).read_bytes().decode("utf-8")
    existing_span = source[source.index("    if destination.resolve()"):source.index(
        '    write_json(destination / "baseline-plan.json", plan)')]
    overwritten_span = existing_span.replace(" or destination.exists()", "").replace(
        "destination.mkdir(parents=True, exist_ok=False)",
        "destination.mkdir(parents=True, exist_ok=True)")
    return [
        ("stale-config", "if _digest(config) != plan.source_config_sha256:", "if False:", [stale+"[config]"]),
        ("stale-input", "if _digest(blob) != row.sha256:", "if False:", [stale+"[input]"]),
        ("existing-output", existing_span, overwritten_span, [stale+"[existing]"]),
        ("redirected-output", "destination.resolve() != destination", "False", [stale+"[redirected]"]),
        ("source-overlap", "if destination.is_relative_to(source_dir) or source_dir.is_relative_to(destination):",
         "if False:", [stale+"[overlap]"]),
        ("source-path", "ProjectPaths(safe_slug(plan.source_slug), source_root)",
         "ProjectPaths(plan.source_slug, source_root)", [stale+"[source-escape]"]),
        ("build-required", "if not plan.target_build.strip():", "if False:", [stale+"[empty-build]"]),
        ("contained-inputs", 'if (relative.is_absolute() or ".." in relative.parts\n'
         '                or not path.is_relative_to(input_root) or not relative.parts\n'
         '                or any(part.lower().startswith(".env") for part in path.parts)):',
         "if False:", [inputs+"[escape]", inputs+"[absolute]", inputs+"[env]"]),
        ("owner-input-reference", "if not row.approval_ref.strip():", "if False:", [inputs+"[unapproved]"]),
        ("input-types", "if path.suffix.lower() not in extensions:", "if False:", [inputs+"[historical-json]"]),
        ("rich-inputs", 'if {row.kind for row in plan.teaching_inputs} != {"video", "doc"}:',
         "if False:", [inputs+"[no-doc]"]),
        ("credential-scope", 'if (not keys or len(set(keys)) != len(keys) or len(selected) != len(keys)\n'
         '            or any(not ref.domains or any(not source.allows_domain(d) for d in ref.domains)\n'
         '                   for ref in selected)):', "if False:",
         [refs+f"[{name}]" for name in ("unknown", "duplicate", "unscoped", "foreign-domain", "empty")]),
        ("target-url-safety", 'if (target.scheme not in {"http", "https"} or not target.hostname\n'
         '            or target.username or target.password or target.query or target.fragment\n'
         '            or not source.allows_domain(target.hostname)):', "if False:", [refs+"[url-credentials]"]),
        ("url-only-empty", 'if mode != "teaching":', "if False:", [POSITIVE]),
        ("same-target", "base_url=source.base_url,", 'base_url="https://other.example/",', [POSITIVE]),
        ("scoped-refs-only", "secrets=selected,", "secrets=[],", [POSITIVE]),
        ("provider-config", "providers=source.providers.model_copy(deep=True),", "", [POSITIVE]),
        ("no-truth-copy", "ids = _write_pair(destination, projects, plan, blobs)",
         'ids = _write_pair(destination, projects, plan, blobs)\n'
         '    __import__("shutil").copytree(source_dir, ProjectPaths(projects[0].slug, '
         'destination / "teaching").dir, dirs_exist_ok=True)', [POSITIVE]),
        ("no-env-copy", 'write_json(destination / "baseline-plan.json", plan)',
         'write_json(destination / "baseline-plan.json", plan)\n'
         '    (destination / ".env").write_text("fixture-secret")', [POSITIVE]),
        ("input-provenance", 'note=f"Owner approval reference: {row.approval_ref}"',
         'note="lost"', [POSITIVE]),
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--init-only", action="store_true")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--count", type=int, default=4)
    args = parser.parse_args()
    if not WORK.exists():
        WORK.mkdir(parents=True)
        for part in ("src", "tests", "scripts"):
            shutil.copytree(ROOT / part, WORK / part,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for name in ("pyproject.toml", "uv.lock"):
            shutil.copy2(ROOT / name, WORK / name)
    original_inventory = inventory(ROOT)
    assert inventory(WORK) == original_inventory
    if (OUT / "inventory.json").exists():
        assert json.loads((OUT / "inventory.json").read_bytes()) == original_inventory
    else:
        dump("inventory.json", original_inventory)
    plugin = WORK / "_baseline_reports.py"
    plugin.write_text('import json, os\nfailed=[]\n'
                      'def pytest_runtest_logreport(report):\n'
                      '    if report.failed and report.when == "call": failed.append(report.nodeid)\n'
                      'def pytest_sessionfinish(session):\n'
                      '    open(os.environ["BASELINE_REPORT"], "w").write(json.dumps(failed))\n')
    env = dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1",
               PYTHONPATH=os.pathsep.join(str(p) for p in (WORK / "src", WORK, WORK / "tests", WORK / "scripts")))
    identity = dict(code_sha=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
                    python=sys.executable, python_version=platform.python_version(),
                    source_sha256={f: sha((ROOT / f).read_bytes()) for f in FILES},
                    lock_sha256=sha((ROOT / "uv.lock").read_bytes()),
                    inventory_sha256=sha((OUT / "inventory.json").read_bytes()),
                    harness_sha256=sha(Path(__file__).read_bytes()), plugin_sha256=sha(plugin.read_bytes()),
                    env_fingerprint=sha(json.dumps({k: env[k] for k in sorted(env)
                        if k.startswith(("PYTHON", "AUTOTESTER"))}, sort_keys=True).encode()),
                    versions={d.metadata["Name"]: d.version for d in importlib.metadata.distributions()},
                    import_root=str(WORK / "src"), tokens=None, monetary_cost=None)
    for f in FILES:
        assert subprocess.check_output(["git", "show", identity["code_sha"]+":"+f], cwd=ROOT) == (ROOT/f).read_bytes()
    if (OUT / "identity.json").exists():
        assert json.loads((OUT / "identity.json").read_bytes()) == identity
    else:
        dump("identity.json", identity)
    spec = mutations()
    spec_document = {"tests": TEST, "mutations": [dict(name=name, file=SOURCE, old=old,
                      new=new, kills=nodes) for name, old, new, nodes in spec]}
    if (OUT / "mutations.json").exists():
        assert json.loads((OUT / "mutations.json").read_bytes()) == spec_document
    else:
        dump("mutations.json", spec_document)
    commands = json.loads((OUT / "commands.json").read_bytes()) if (OUT / "commands.json").exists() else []
    proofs = json.loads((OUT / "proofs.json").read_bytes()) if (OUT / "proofs.json").exists() else []

    def run(label, argv):
        started = datetime.now(UTC).isoformat()
        tick = time.monotonic()
        report_path = WORK / "failed.json"
        report_path.unlink(missing_ok=True)
        result = subprocess.run(argv, cwd=WORK, env=env, capture_output=True, timeout=90)
        log = OUT / (label+".log")
        attempt = 1
        while log.exists():
            log = OUT / f"{label}-retry-{attempt}.log"
            attempt += 1
        log.write_bytes(result.stdout+result.stderr)
        report_hash = None
        if report_path.exists():
            report_bytes = report_path.read_bytes()
            log.with_suffix(".report.json").write_bytes(report_bytes)
            report_hash = sha(report_bytes)
        commands.append(dict(label=label, argv=argv, started_at=started, ended_at=datetime.now(UTC).isoformat(),
            duration_s=time.monotonic()-tick, exit_code=result.returncode,
            log=log.name, output_sha256=sha(log.read_bytes()),
            report_sha256=report_hash,
            source_sha256={f: sha((WORK/f).read_bytes()) for f in FILES},
            identity_sha256=sha((OUT/"identity.json").read_bytes()),
            spec_sha256=sha((OUT/"mutations.json").read_bytes())))
        dump("commands.json", commands)
        return result.returncode

    helper = "C:/Users/product/.agents/skills/checker/scripts/review_budget.py"
    phase = "init" if args.init_only else f"batch-{args.start}"
    assert run(f"preflight-{phase}", [sys.executable, helper, "preflight", "--root", str(WORK),
        "--import-name", "autotester", "--import-root", str(WORK/"src"), "--temp-parent", str(WORK)]) == 0
    if args.init_only:
        assert run("shared-green", [sys.executable, "-m", "pytest", TEST,
                   "-p", "no:cacheprovider", "--basetemp", str(WORK / "temp-shared")]) == 0
        assert run("scoped-lint", [sys.executable, "-m", "ruff", "check", *FILES]) == 0
        shape = ('import ast,json,pathlib; paths='+repr(FILES)+'; result={}; '
                 '\nfor name in paths:\n'
                 ' p=pathlib.Path(name); tree=ast.parse(p.read_bytes()); '
                 'assert len(p.read_bytes().splitlines()) <= 300; '
                 'assert ast.get_docstring(tree); '
                 'lengths={n.name:n.end_lineno-n.lineno+1 for n in ast.walk(tree) '
                 'if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}; '
                 'assert all(v<=50 for v in lengths.values()),lengths; result[name]=lengths\n'
                 'print(json.dumps(result,indent=2))')
        assert run("scoped-shape", [sys.executable, "-c", shape]) == 0
        print("Initialized complete byte-bound copy; shared green and lint passed")
        return
    for index, (name, old, new, nodes) in enumerate(spec):
        if not args.start <= index < args.start + args.count:
            continue
        assert name not in {p["name"] for p in proofs}, "Never overwrite an existing proof"
        report = WORK / "failed.json"
        env["BASELINE_REPORT"] = str(report)
        argv = [sys.executable, "-m", "pytest", *nodes, "-p", "no:cacheprovider", "-p", "_baseline_reports"]
        target = WORK / SOURCE
        original = target.read_bytes()
        old_bytes, new_bytes = old.encode(), new.encode()
        assert original.count(old_bytes) == 1, name
        green_receipt = len(commands)
        assert run(name+"-green", [*argv, "--basetemp", str(WORK/f"temp-{index}-g")]) == 0
        assert json.loads(report.read_bytes()) == []
        mutated = original.replace(old_bytes, new_bytes, 1)
        assert mutated != original
        target.write_bytes(mutated)
        assert target.read_bytes() == mutated
        try:
            red_receipt = len(commands)
            red = run(name+"-red", [*argv, "--basetemp", str(WORK/f"temp-{index}-r")])
            failed = json.loads(report.read_bytes())
            assert red == 1 and set(nodes) <= set(failed), (name, red, failed)
        finally:
            target.write_bytes(original)
            assert target.read_bytes() == original
        restored_receipt = len(commands)
        assert run(name+"-restored", [*argv, "--basetemp", str(WORK/f"temp-{index}-s")]) == 0
        proofs.append(dict(name=name, nodes=nodes, original_sha256=sha(original),
                           mutated_sha256=sha(mutated), restored_sha256=sha(target.read_bytes()),
                           anchor_count=1, green=0, red=red, failed=failed, restored=0,
                           command_indexes=[green_receipt, red_receipt, restored_receipt]))
        dump("proofs.json", proofs)
    assert inventory(WORK) == original_inventory
    assert inventory(ROOT) == original_inventory
    dump("summary.json", dict(proofs=len(proofs), command_seconds=sum(c["duration_s"] for c in commands),
                              tokens=None, monetary_cost=None))
    print(f"Completed {len(proofs)} of {len(spec)} guards; no runtime remains active")


if __name__ == "__main__":
    main()
