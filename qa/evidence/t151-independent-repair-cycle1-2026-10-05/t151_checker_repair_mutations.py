"""Scoped, attributed repair falsification in a fresh cache-free source copy."""
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

candidate = Path(__file__).resolve().parents[1]
scratch = candidate / ".work/t151-checker-repair-copy"
assert not scratch.exists()
scratch.mkdir()
shutil.copytree(candidate / "src", scratch / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
(scratch / "tests").mkdir()
for source, target in [(candidate / "tests/test_discover.py", "test_discover.py"),
                       (candidate / ".work/t151_checker_probe.py", "test_original_checker.py"),
                       (candidate / ".work/t151_checker_repair_probe.py", "test_repair_checker.py")]:
    shutil.copy2(source, scratch / "tests" / target)
shutil.copy2(candidate / "pyproject.toml", scratch / "pyproject.toml")
env = os.environ.copy()
env.update(PYTHONPATH=str(scratch / "src"), PYTHONDONTWRITEBYTECODE="1",
           PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTEST_CURRENT_TEST="checker-repair-no-env",
           AUTOTESTER_APPROVAL_KEY="checker-synthetic-signing-key")
frozen = {str(p.relative_to(scratch)): hashlib.sha256(p.read_bytes()).hexdigest()
          for p in (scratch / "src").rglob("*") if p.is_file()}

def run(label):
    command = [sys.executable, "-B", "-m", "pytest", "tests", "-o", "addopts=", "-p", "no:cacheprovider",
               "--basetemp=" + str(scratch / (label + "-temp")), "--junitxml=" + str(scratch / (label + ".xml"))]
    process = subprocess.run(command, cwd=scratch, env=env, capture_output=True, text=True, timeout=45)
    (scratch / (label + ".txt")).write_text(process.stdout + process.stderr, encoding="utf-8")
    tree = ET.parse(scratch / (label + ".xml"))
    return {"label": label, "command": command, "exit": process.returncode,
            "tests": len(tree.findall(".//testcase")), "errors": len(tree.findall(".//error")),
            "failed": [c.attrib["name"] for c in tree.findall(".//testcase") if c.find("failure") is not None]}

baseline = run("repair-baseline")
assert baseline["exit"] == 0 and baseline["errors"] == 0
records = [baseline]
changes = [
 ("scan-output", "stages/discover.py", "scan", '    redactor.assert_clean(result.model_dump_json())', '    pass', "test_encoded_evidence_path_is_guarded"),
 ("context-output", "stages/read_context.py", "read_context", '    redactor.assert_clean(result.model_dump_json())', '    pass', "test_encoded_context_output_is_guarded"),
 ("project-preflight", "stages/discover.py", "approved_roots", '    redactor.assert_clean(scope.project)', '    pass', "test_dirty_project_rejected_before_filesystem"),
 ("approval-exception", "stages/discover.py", "approved_roots", '                raise ApprovalRequired("refusing to start a read run: approval required") from None', '                raise', "test_denial_class_and_formatted_chain_are_safe"),
 ("root-filesystem", "stages/discover.py", "approved_roots", '        raise category("filesystem access refused") from None', '        raise', "test_filesystem_subclass_and_diagnostics[checker-repair-secret-longvalue-missing]"),
 ("scan-filesystem", "stages/discover.py", "scan", '        raise category("filesystem access refused") from None', '        raise', "test_filesystem_subclass_and_diagnostics[checker-repair-secret-longvalue-scan_open]"),
 ("context-filesystem", "stages/read_context.py", "read_context", '        raise category("filesystem access refused") from None', '        raise', "test_filesystem_subclass_and_diagnostics[checker-repair-secret-longvalue-context_open]"),
]
for label, relative, function, before, after, defender in changes:
    path = scratch / "src/autotester" / relative
    original = path.read_bytes()
    text = original.decode()
    nodes = [node for node in ast.parse(text).body if isinstance(node, ast.FunctionDef) and node.name == function]
    assert len(nodes) == 1, (label, "function anchor")
    lines = text.splitlines(keepends=True)
    node = nodes[0]
    section = "".join(lines[node.lineno-1:node.end_lineno])
    assert section.count(before) == 1
    assert text.count(section) == 1
    changed_section = section.replace(before, after)
    changed = text.replace(section, changed_section).encode()
    assert changed != original
    try:
        path.write_bytes(changed)
        assert path.read_bytes() == changed
        row = run(label)
        row.update(function=function, anchor_count=1, defends=defender,
                   before_sha256=hashlib.sha256(original).hexdigest(), mutation_sha256=hashlib.sha256(changed).hexdigest())
        row["attributed"] = defender in row["failed"]
        row["result"] = "KILLED" if row["exit"] == 1 and row["errors"] == 0 and row["attributed"] else "INCONCLUSIVE"
        records.append(row)
    finally:
        path.write_bytes(original)
        assert path.read_bytes() == original
    (scratch / "repair-results.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
restored = run("repair-restored")
records.append(restored)
assert restored["exit"] == 0 and restored["errors"] == 0
assert all(hashlib.sha256((scratch / p).read_bytes()).hexdigest() == h for p, h in frozen.items())
(scratch / "repair-results.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
print(json.dumps({"baseline": baseline, "mutations": records[1:-1], "restored": restored,
                  "frozen_source_files": len(frozen), "hash_mismatches": 0}, indent=2))
