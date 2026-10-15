"""Run the repository mutation harness with isolated imports and named-test scope."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import mutation_check as harness

spec = json.loads(Path(__file__).with_name("mutations.json").read_text())
original_runner = harness._run_pytest
run_number = 0
evidence = Path(__file__).parent


def isolated_runner(cwd, tests, *extra, timeout=harness.PYTEST_TIMEOUT_S):
    global run_number
    os.environ["PYTHONPATH"] = str(cwd / "src")
    parent = cwd / ".work"
    parent.mkdir(exist_ok=True)
    collecting = "--collect-only" in extra
    targets = tests if collecting or run_number == 0 else spec["mutations"][run_number - 1]["kills"]
    code, output = original_runner(cwd, targets, *extra,
                                   "--basetemp", str(parent / f"pytest-{run_number}"),
                                   timeout=timeout)
    label = "collection" if collecting else f"run-{run_number:02}"
    (evidence / f"{label}.log").write_text(output, encoding="utf-8")
    print(f"{label}: exit={code}", flush=True)
    if not collecting:
        run_number += 1
    return code, output


harness._run_pytest = isolated_runner
results = harness.check(spec, ROOT)
(evidence / "mutation-results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
raise SystemExit(harness.report(results))
