"""Separate alias oracle to distinguish alias refusal from an event-budget refusal."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

scratch = Path(__file__).resolve().parent / "t151-checker-mutation-copy"
test = scratch / "tests/test_checker_yaml.py"
assert not test.exists()
test.write_text('''from autotester.core.redact import Redactor
from autotester.schema.ai_target import ReadScope
from autotester.stages.read_context import read_context

def test_noncyclic_alias_exact_refusal(tmp_path):
    (tmp_path / "note.md").write_text("---\\nx: &a [1]\\ny: *a\\n---\\n", encoding="utf-8")
    result = read_context([tmp_path], scope=ReadScope(project="fixture", project_root=str(tmp_path)), redactor=Redactor({}))
    assert result.documents == []
    assert [r.reason for r in result.refusals] == ["yaml_alias"]
''', encoding="utf-8")
env = os.environ.copy()
env.update(PYTHONPATH=str(scratch / "src"), PYTHONDONTWRITEBYTECODE="1",
           PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTEST_CURRENT_TEST="checker-no-env")
def run(label):
    command = [sys.executable, "-B", "-m", "pytest", "tests/test_checker_yaml.py", "-o", "addopts=",
               "-p", "no:cacheprovider", "--basetemp=" + str(scratch / (label + "-temp")),
               "--junitxml=" + str(scratch / (label + ".xml"))]
    process = subprocess.run(command, cwd=scratch, env=env, capture_output=True, text=True, timeout=30)
    (scratch / (label + ".txt")).write_text(process.stdout + process.stderr, encoding="utf-8")
    tree = ET.parse(scratch / (label + ".xml"))
    return {"command": command, "exit": process.returncode,
            "failed": [c.attrib["name"] for c in tree.findall(".//testcase") if c.find("failure") is not None],
            "errors": len(tree.findall(".//error"))}
path = scratch / "src/autotester/stages/read_context.py"
original = path.read_bytes()
anchor = b"        if isinstance(event, AliasEvent):"
assert original.count(anchor) == 1
baseline = run("alias-independent-baseline")
assert baseline["exit"] == 0 and baseline["errors"] == 0
mutated = original.replace(anchor, b"        if False and isinstance(event, AliasEvent):")
assert mutated != original
try:
    path.write_bytes(mutated)
    assert path.read_bytes() == mutated
    red = run("alias-independent-red")
    assert red["exit"] == 1 and red["errors"] == 0
    assert "test_noncyclic_alias_exact_refusal" in red["failed"]
finally:
    path.write_bytes(original)
    assert path.read_bytes() == original
restored = run("alias-independent-restored")
assert restored["exit"] == 0
result = {"baseline": baseline, "red": red, "restored": restored,
          "original_sha256": hashlib.sha256(original).hexdigest(),
          "mutation_sha256": hashlib.sha256(mutated).hexdigest(), "restored_exact": True}
(scratch / "alias-independent-results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
