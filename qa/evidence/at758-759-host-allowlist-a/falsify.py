"""Checker A falsification runner: one isolated copy per row, green before, red after."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

S = Path(os.environ["SCRATCH"])
BASE = S / "base"
PY = r"D:\autoTesting\.venv\Scripts\python.exe"
H = "src/autotester/ui/helpers.py"
E = "src/autotester/stages/explore_consent.py"
T_GUARD = "tests/test_ui_origin_guard.py"
T_APPR = "tests/test_credential_run_approval.py"

ROWS = [
    ("C1a", H, 'or not _host_allowed(headers["host"])', "or False",
     f"{T_GUARD}::test_the_rebinding_repro_cannot_read_a_saved_credential_but_loopback_can"),
    ("C1b", H, "parts.username is not None", "False",
     f"{T_GUARD}::test_a_host_outside_the_allow_list_gets_an_empty_403_on_every_method"),
    ("C1c", H, 'return host in _listed("AUTOTESTER_ALLOWED_HOSTS") | set(origins)',
     'return True', f"{T_GUARD}::test_hosts_of_the_allowed_origins_and_the_hosts_variable_are_added_exactly"),
    ("C2", H, "_ = parts.port  # AT-760", "_ = None  # AT-760",
     f"{T_GUARD}::test_an_origin_with_an_unparsable_port_is_refused"),
    ("C3a", H, 'names.count("origin") > 1', 'names.count("origin") > 99',
     f"{T_GUARD}::test_more_than_one_origin_or_host_header_is_refused"),
    ("C3b", H, 'names.count("host") != 1', 'names.count("host") == 0',
     f"{T_GUARD}::test_more_than_one_origin_or_host_header_is_refused"),
    ("C3c", H, 'names.count("host") != 1', 'False',
     f"{T_GUARD}::test_a_request_with_no_host_header_is_refused"),
    ("C4a", E, "            return _require(human, project, kind, bounds)\n        except ApprovalRequired as human_refusal",
     "            return _require(rows, project, kind, bounds)\n        except ApprovalRequired as human_refusal",
     f"{T_APPR}::test_an_account_row_stops_covering_when_its_credential_is_gone"),
    ("C4b", E, "        return _require(human, project, kind, bounds)\n    try:",
     "        return _require(rows, project, kind, bounds)\n    try:",
     f"{T_APPR}"),
]


def run(tree: Path, node: str) -> str:
    env = dict(os.environ, PYTHONPATH=str(tree / "src"))
    p = subprocess.run([PY, "-m", "pytest", "-p", "no:xdist", "-p", "no:cacheprovider", "-o", "addopts=",
                        "-q", node], cwd=tree, env=env, capture_output=True, text=True, timeout=300)
    tail = [ln for ln in p.stdout.splitlines() if ln.strip()][-1] if p.stdout.strip() else p.stderr[-200:]
    return f"rc={p.returncode} {tail}"


only = set(sys.argv[1:])
for rid, rel, old, new, node in ROWS:
    if only and rid not in only:
        continue
    tree = S / f"fals-{rid}"
    if tree.exists():
        shutil.rmtree(tree)
    shutil.copytree(BASE, tree, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    before = run(tree, node)
    f = tree / rel
    src = f.read_text(encoding="utf-8")
    n = src.count(old)
    assert n >= 1, (rid, "pattern missing")
    f.write_text(src.replace(old, new, 1), encoding="utf-8", newline="")
    after = run(tree, node)
    f.write_text(src, encoding="utf-8", newline="")
    restored = run(tree, node)
    print(f"{rid} [{n} match] {node.split('::')[-1] if '::' in node else node}\n   before: {before}\n   after:  {after}\n   restored: {restored}", flush=True)
