"""Checker B scratch runner: green-before / mutate-in-copy / red-after for four rows."""
import os
import subprocess
import sys
from pathlib import Path

PY = r"D:\autoTesting\.worktrees\t209-leak-severity\.venv\Scripts\python.exe"
S = Path(r"D:/chk-scratch-t209b/r2")
env = {**os.environ, "TMP": r"D:\autoTesting\.work\tmp", "TEMP": r"D:\autoTesting\.work\tmp"}

ROWS = {
    "mp7": ("src/autotester/stages/finding_priority.py",
            "FindingClass.PRIVILEGE_ESCALATION: Priority.P0,",
            "FindingClass.PRIVILEGE_ESCALATION: Priority.P1,",
            "tests/test_finding_priority.py::test_priority_by_class_over_every_class[privilege_escalation]"),
    "mp8": ("src/autotester/stages/report_banner.py",
            "    blocking = _blocking(findings)\n    if not blocking:\n        return \"\"",
            "    blocking = list(findings)\n    if not blocking:\n        return \"\"",
            "tests/test_report_banner.py::test_no_banner_without_a_p0_leak_or_privilege_finding"),
    "mp9": ("src/autotester/stages/leak_evidence.py",
            "shutil.copyfile(batch.paths[0], dest)",
            "shutil.copyfile(raw, dest)",
            "tests/test_leak_evidence.py::test_screenshot_is_masked_before_it_is_written"),
    "mp10": ("src/autotester/stages/leak_evidence.py",
             "write_json(path, finding)",
             "write_json(path, finding.model_copy(update={'steps': finding.steps[:-1]}))",
             "tests/test_leak_repro_replay.py::test_replaying_the_recorded_repro_gives_the_same_count"),
}


def run(row: str, node: str) -> tuple[int, str]:
    e = {**env, "PYTHONPATH": str(S / row / "src")}
    p = subprocess.run([PY, "-m", "pytest", "-p", "no:cacheprovider", node],
                       cwd=S / row, env=e, capture_output=True, text=True)
    tail = [ln for ln in p.stdout.splitlines() if ln.strip()][-6:]
    return p.returncode, "\n".join(tail)


for row, (rel, old, new, node) in ROWS.items():
    f = S / row / rel
    print(f"=== {row} {node}")
    rc, out = run(row, node)
    print("GREEN-BEFORE rc=", rc, "|", out.splitlines()[-1] if out else "")
    text = f.read_text(encoding="utf-8")
    assert text.count(old) == 1, (row, text.count(old))
    f.write_text(text.replace(old, new), encoding="utf-8")
    rc, out = run(row, node)
    print("RED-AFTER rc=", rc)
    print(out)
sys.exit(0)
