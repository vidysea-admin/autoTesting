"""Final bounded checks and maker self-audit before the independent checker packet."""
import json
from prove import ROOT, OUT, FILES, run, sha

EXISTING = [
 "tests/test_failure_bundle.py::test_a_write_that_dies_mid_bundle_leaves_only_the_partial_and_the_loader_refuses",
 "tests/test_failure_bundle.py::test_a_verdict_or_trace_span_from_another_run_is_refused",
 "tests/test_failure_bundle.py::test_no_planted_secret_reaches_any_part_of_the_bundle",
 "tests/test_report_export.py::test_export_excel_has_one_row_per_case",
 "tests/test_report_export.py::test_export_html_embeds_the_screenshot_and_is_self_contained",
 "tests/test_run_launcher.py::test_exactly_one_non_test_call_site_builds_a_run",
 "tests/test_run_launcher.py::test_exactly_one_non_test_call_site_executes_the_cases",
]
checks = []
checks.append(run("final-focused-tests", ["-m", "pytest", "tests/test_run_failure_artifacts.py",
                    *EXISTING, "--basetemp", str(OUT / "pytest-final-focused")]))
checks.append(run("final-scoped-lint", ["-m", "ruff", "check", *FILES[:4], FILES[6]]))
checks.append(run("final-source-doctor", ["-c",
    "from pathlib import Path; from autotester.doctor import check_file_sizes, check_function_sizes, "
    "check_file_names, check_duplicate_definitions; r=Path.cwd(); "
    "v=[*check_file_sizes(r),*check_function_sizes(r),*check_file_names(r),"
    "*check_duplicate_definitions(r)]; print(*v,sep='\\n'); assert not v"]))
assert all(c.returncode == 0 for c in checks)

ledger = json.loads((OUT / "v4-mutation-ledger.json").read_text())
assert len(ledger) == 12
fingerprints = {f: sha(ROOT / f) for f in FILES}
for row in ledger:
    for phase, exit_code in [("green",0),("red",1),("restored",0)]:
        label = f"v4-{row['mutation']}-{phase}"
        receipt = json.loads((OUT / f"{label}.json").read_text())
        assert receipt["exit_code"] == exit_code
        assert receipt["output_sha256"] == sha(OUT / f"{label}.log")
        assert receipt["environment_sha256"]
        assert receipt["dependency_sha256"]
        expected = dict(fingerprints)
        if phase == "red":
            expected[row["file"]] = row["mutated_sha256"]
        assert receipt["file_sha256"] == expected, label
        assert row["restored_sha256"] == fingerprints[row["file"]]
summary = {"status":"SELF_AUDIT_OK", "mutations":len(ledger), "fingerprints":fingerprints,
           "selected_existing_nodes":EXISTING, "checker_verdict":None,
           "maker_tokens":None,"maker_cost":None,"maker_active_s":None}
(OUT / "packet-self-audit.json").write_text(json.dumps(summary,indent=2))
print("SELF_AUDIT_OK",len(ledger),"byte-bound guard proofs")
