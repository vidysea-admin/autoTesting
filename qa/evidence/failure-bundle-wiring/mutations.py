"""Isolated green/red/restored proof, with attributed test failures and immutable receipts."""
import json
from pathlib import Path
import shutil
from prove import ROOT, OUT, run, sha

COPY = OUT / "mutation-tree-4"
shutil.copytree(ROOT / "src", COPY / "src", ignore=shutil.ignore_patterns("__pycache__"))
for name in ["tests/test_run_failure_artifacts.py", "tests/conftest.py",
             "tests/tests_mutation_fixtures.py", "tests/auth_login_fixture.py",
             "scripts/regression_proof.py", "pyproject.toml", "uv.lock"]:
    (COPY / name).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / name, COPY / name)
LAUNCH = "src/autotester/stages/run_launcher.py"
ARTIFACTS = "src/autotester/stages/run_artifacts.py"
TEST = "tests/test_run_failure_artifacts.py::"
T1 = "test_launcher_bundles_sanitized_copies_and_reports"
T2 = "test_bundle_exception_preserves_functional_records"
T3 = "test_containment_and_uncertain_images_are_explicit"
T4 = "test_report_lookup_rejects_partial_corrupt_and_wrong_lineage"
MUTATIONS = [
    ("postsave-hook", LAUNCH, "    assemble_run_bundles(store, run)\n", "", [T1,T2,T3,T4]),
    ("containment", ARTIFACTS,
     "    if resolved != path.absolute() or not resolved.is_relative_to(root.resolve()):",
     "    if False:", [T3]),
    ("privacy-transport", ARTIFACTS,
     "            safe = stack.enter_context(sanitized_images([original]))",
     "            from types import SimpleNamespace\n"
     "            safe = SimpleNamespace(paths=[original], reasons=[], text_unavailable=False)", [T1,T3]),
    ("unmasked-image", ARTIFACTS, "            if not shot.masked or shot.step_order is None:",
     "            if False:", [T3]),
    ("trace-case", ARTIFACTS,
     '        spans = [s for s in spans if not hasattr(s, "fed_id") or s.fed_id == case.id]',
     "        spans = spans", [T1]),
    ("case-membership", ARTIFACTS, "                if verdict.case_id not in run.case_ids:",
     "                if False:", [T3]),
    ("pass-filter", ARTIFACTS,
     "            if verdict.result not in (Result.FAIL, Result.INCONCLUSIVE, Result.BLOCKED):",
     "            if False:", [T4]),
    ("inner-recovery", ARTIFACTS,
     '                entry = BundleAssembly(case_id=verdict.case_id, status="unavailable",',
     '                raise\n                entry = BundleAssembly(case_id=verdict.case_id, status="unavailable",', [T2]),
    ("outer-recovery", ARTIFACTS,
     '        _LOG.warning("failure_bundle_index_unavailable")  # fixed diagnostic, never exception text',
     "        raise", [T2]),
    ("index-run", ARTIFACTS, "        if index.run_id != run_id:", "        if False:", [T4]),
    ("entry-state", ARTIFACTS,
     '        if entry.status != "complete" or entry.bundle_id is None:', "        if False:", [T4]),
    ("manifest-identity", ARTIFACTS,
     '        if (manifest.run_id, manifest.case_id, manifest.bundle_id) != (\n                run_id, case_id, entry.bundle_id):',
     "        if False:", [T4]),
]
ledger = []
preflight = run("v4-mutation-preflight", [
    "C:/Users/product/.agents/skills/checker/scripts/review_budget.py", "preflight",
    "--root", str(COPY), "--import-name", "autotester", "--import-root", str(COPY / "src"),
    "--temp-parent", str(OUT)], COPY)
assert preflight.returncode == 0
for label, file, anchor, replacement, tests in MUTATIONS:
    path = COPY / file
    original = path.read_bytes()
    newline = b"\r\n" if b"\r\n" in original else b"\n"
    anchor_bytes = anchor.encode().replace(b"\n", newline)
    replacement_bytes = replacement.encode().replace(b"\n", newline)
    assert original.count(anchor_bytes) == 1, label
    selected = [TEST + t for t in tests]
    def command(phase):
        return ["-m", "pytest", *selected, "--basetemp", str(OUT / f"pytest-{label}-{phase}")]
    baseline = run(f"v4-{label}-green", command("green"), COPY)
    assert baseline.returncode == 0, label
    changed = original.replace(anchor_bytes, replacement_bytes)
    assert changed != original
    path.write_bytes(changed)
    assert path.read_bytes() == changed
    mutation_sha = sha(path)
    try:
        red = run(f"v4-{label}-red", command("red"), COPY)
        assert red.returncode == 1, label
        failures = [line for line in red.stdout.splitlines() if line.startswith("FAILED ")]
        assert all(any(TEST+t in line for line in failures) for t in tests), (label,failures)
    finally:
        path.write_bytes(original)
    assert path.read_bytes() == original
    restored = run(f"v4-{label}-restored", command("restored"), COPY)
    assert restored.returncode == 0, label
    ledger.append({"mutation":label,"file":file,"anchor_count":1,"mutated_sha256":mutation_sha,
                   "restored_sha256":sha(path),"tests":tests,"attributed_failures":failures})
    (OUT / "v4-mutation-ledger.json").write_text(json.dumps(ledger, indent=2))
print("ALL MUTATIONS ATTRIBUTED", len(ledger))
