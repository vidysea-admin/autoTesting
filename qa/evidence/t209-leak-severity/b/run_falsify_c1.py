"""Checker B cycle 1: green-before / mutate-in-copy / red-after for MP9 (predicate) and MP10, copies outside the worktree."""
import os
import subprocess
from pathlib import Path

PY = r"D:\autoTesting\.worktrees\t209-leak-severity\.venv\Scripts\python.exe"
S = Path(r"D:/chk-scratch-t209b/c1")
env = {**os.environ, "TMP": r"D:\autoTesting\.work\tmp", "TEMP": r"D:\autoTesting\.work\tmp"}
OLD_RE = 'bool(re.search(r"^\d+$|\d{4,}|[0-9a-fA-F]{16,}|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-|[%@]", segment))'
ROWS = {
    "mp9": ("src/autotester/schema/leak_evidence.py",
            "segment.lower() not in ROUTE_WORDS",
            OLD_RE,
            ["tests/test_leak_url_ids.py::test_templatise_turns_every_id_format_into_a_placeholder[nanoid-21]",
             "tests/test_leak_url_ids.py::test_no_id_format_reaches_the_file_write_finding_writes[stripe-like]"]),
    "mp10": ("src/autotester/stages/leak_evidence.py",
             "write_json(path, finding)",
             "write_json(path, finding.model_copy(update={'steps': finding.steps[:-1]}))",
             ["tests/test_leak_repro_replay.py::test_replaying_the_recorded_repro_gives_the_same_count"]),
}


def run(row, nodes):
    e = {**env, "PYTHONPATH": str(S / row / "src")}
    p = subprocess.run([PY, "-m", "pytest", "-p", "no:cacheprovider", *nodes], cwd=S / row, env=e,
                       capture_output=True, text=True)
    lines = [ln for ln in p.stdout.splitlines() if ln.strip()]
    return p.returncode, lines


for row, (rel, old, new, nodes) in ROWS.items():
    f = S / row / rel
    print(f"=== {row}")
    rc, lines = run(row, nodes)
    print("GREEN-BEFORE rc=", rc, "|", lines[-1])
    text = f.read_text(encoding="utf-8")
    assert text.count(old) == 1, (row, text.count(old))
    if row == "mp9" and "import re\n" not in text:
        text = text.replace("from __future__ import annotations\n", "from __future__ import annotations\n", 1)
    f.write_text(text.replace(old, new), encoding="utf-8")
    rc, lines = run(row, nodes)
    print("RED-AFTER rc=", rc)
    print("\n".join(ln for ln in lines if ln.startswith(("FAILED", "E  ", ">")) or "passed" in ln or "failed" in ln)[:2500])
