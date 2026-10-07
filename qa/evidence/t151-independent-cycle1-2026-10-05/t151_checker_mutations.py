"""Asserted green / named RED / exact restore in a cache-free throwaway copy."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

candidate = Path(__file__).resolve().parents[1]
scratch = candidate / ".work" / "t151-checker-mutation-copy"
assert not scratch.exists(), "never overwrite an existing checker copy"
scratch.mkdir()
shutil.copytree(candidate / "src", scratch / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
(scratch / "tests").mkdir()
shutil.copy2(candidate / "tests/test_discover.py", scratch / "tests/test_discover.py")
shutil.copy2(candidate / "pyproject.toml", scratch / "pyproject.toml")
env = os.environ.copy()
env.update(PYTHONPATH=str(scratch / "src"), PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
           PYTEST_CURRENT_TEST="checker-no-env", AUTOTESTER_APPROVAL_KEY="checker-synthetic-signing-key")
env["PYTHONDONTWRITEBYTECODE"] = "1"
frozen = {str(p.relative_to(scratch)): hashlib.sha256(p.read_bytes()).hexdigest()
          for p in (scratch / "src").rglob("*") if p.is_file()}

def run(label):
    xml = scratch / (label + ".xml")
    command = [sys.executable, "-B", "-m", "pytest", "tests/test_discover.py", "-o", "addopts=",
               "-p", "no:cacheprovider", "--basetemp=" + str(scratch / (label + "-temp")),
               "--junitxml=" + str(xml)]
    result = subprocess.run(command, cwd=scratch, env=env, capture_output=True, text=True, timeout=45)
    (scratch / (label + ".txt")).write_text(result.stdout + result.stderr, encoding="utf-8")
    tree = ET.parse(xml)
    failed = [c.attrib["name"] for c in tree.findall(".//testcase") if c.find("failure") is not None]
    errors = len(tree.findall(".//error"))
    return {"label": label, "command": command, "exit": result.returncode,
            "failed": failed, "errors": errors, "tests": len(tree.findall(".//testcase"))}

baseline = run("baseline")
assert baseline["exit"] == 0 and baseline["errors"] == 0, baseline
mutations = [
 ("dirty-signal", "stages/discover.py", "        redactor.assert_clean(signal.model_dump_json())", "        pass", "test_dirty_signal_is_refused_before_provider"),
 ("nonai-root", "stages/discover.py", '    redactor.assert_clean(common["root_path"])', '    pass', "test_non_ai_encoded_root_secret_is_refused"),
 ("scope-preflight", "stages/discover.py", '        if not root.is_relative_to(project):', '        if False and not root.is_relative_to(project):', "test_all_roots_are_preflighted_before_any_open"),
 ("physical-budget", "stages/discover.py", '                total += len(raw)', '                total += 0', "test_rejected_files_still_consume_physical_read_budget"),
 ("scan-final-deadline", "stages/discover.py", '\n    if time.monotonic() - started >= scope.limits.wall_clock_s:', '\n    if False and time.monotonic() - started >= scope.limits.wall_clock_s:', "test_final_parser_overrun_is_not_complete[False]"),
 ("context-final-deadline", "stages/read_context.py", '\n    if time.monotonic() - started >= scope.limits.wall_clock_s:', '\n    if False and time.monotonic() - started >= scope.limits.wall_clock_s:', "test_final_parser_overrun_is_not_complete[True]"),
 ("yaml-alias", "stages/read_context.py", '        if isinstance(event, AliasEvent):', '        if False and isinstance(event, AliasEvent):', "test_unsafe_or_excessively_nested_yaml_is_refused[x: &a [1]\\ny: *a]"),
 ("classifier-strict", "schema/ai_target.py", 'confidence: float = Field(ge=0, le=1, strict=True, allow_inf_nan=False)', 'confidence: float = Field(ge=0, le=1, strict=False, allow_inf_nan=False)', "test_seeded_bad_classifier_output_is_never_overridden[string]"),
 ("provider-error", "stages/discover.py", 'except (ValidationError, ValueError, TypeError, ProviderError):', 'except (ValidationError, ValueError, TypeError):', "test_provider_error_never_echoes_raw_secret"),
 ("metadata-secret", "stages/read_context.py", '        return redactor.scrub(value)', '        return value', "test_context_is_metadata_only_and_secrets_are_scrubbed"),
]
records = [baseline]
for label, relative, before, after, defender in mutations:
    path = scratch / "src/autotester" / relative
    original = path.read_bytes()
    text = original.decode()
    assert text.count(before) == 1, (label, text.count(before))
    mutated = text.replace(before, after).encode()
    assert mutated != original
    try:
        path.write_bytes(mutated)
        assert path.read_bytes() == mutated
        row = run(label)
        row["defends"] = defender
        row["anchor_count"] = 1
        row["source_before"] = hashlib.sha256(original).hexdigest()
        row["source_mutated"] = hashlib.sha256(mutated).hexdigest()
        row["attributed"] = defender in row["failed"]
        row["result"] = "KILLED" if row["exit"] != 0 and row["errors"] == 0 and row["attributed"] else "INCONCLUSIVE"
        records.append(row)
    finally:
        path.write_bytes(original)
        assert path.read_bytes() == original
    (scratch / "results.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
restored = run("restored")
records.append(restored)
assert restored["exit"] == 0 and restored["errors"] == 0
assert all(hashlib.sha256((scratch / p).read_bytes()).hexdigest() == h for p, h in frozen.items())
(scratch / "results.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
print(json.dumps({"scratch": str(scratch), "baseline": baseline, "mutations": records[1:-1],
                  "restored": restored, "frozen_files": len(frozen), "mismatches": 0}, indent=2))
