"""Bind only missing PDF mutation proofs to immutable code, environment and raw outputs."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "scripts"))
import mutation_check as harness

CANDIDATE = "c1f67d93b9ae1c9cab0c0cdbffdb5adadf68fcee"
CODE_PATHS = ["src", "tests", "scripts", "pyproject.toml", "uv.lock"]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dump(name: str, payload: object) -> None:
    (OUT / name).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def source_manifest(root: Path) -> dict[str, str]:
    files = []
    for name in CODE_PATHS:
        path = root / name
        files.extend(path.rglob("*") if path.is_dir() else [path])
    return {p.relative_to(root).as_posix(): digest(p.read_bytes())
            for p in sorted(files) if p.is_file() and "__pycache__" not in p.parts
            and p.suffix != ".pyc"}


def tree_digest(manifest: dict[str, str]) -> str:
    return digest(json.dumps(manifest, sort_keys=True).encode())


def run_probe(work: Path, tests: list[str], label: str) -> tuple[int, set[str]]:
    before = source_manifest(work)
    started = datetime.now(UTC).isoformat()
    tick = time.monotonic()
    code, output = harness._run_pytest(
        work, tests, "--basetemp", str(work / ".work" / label), timeout=180)
    elapsed = time.monotonic() - tick
    logfile = OUT / f"{label}.log"
    logfile.write_text(output, encoding="utf-8")
    after = source_manifest(work)
    assert after == before, "pytest unexpectedly changed source/fixture bytes"
    failures = harness.failed_tests(work)
    dump(f"{label}.receipt.json", {
        "context": "context.json", "label": label, "started_utc": started,
        "ended_utc": datetime.now(UTC).isoformat(), "elapsed_s": elapsed,
        "command": [sys.executable, "-m", "pytest", *tests, "-o", "addopts=", "-q",
                    "--no-header", "-p", "no:cacheprovider", "-p", harness.REPORT_PLUGIN,
                    "--basetemp", str(work / ".work" / label)],
        "before_tree_sha256": tree_digest(before), "after_tree_sha256": tree_digest(after),
        "exit_code": code, "failed_nodeids": sorted(failures),
        "output": logfile.name, "output_sha256": digest(logfile.read_bytes()),
    })
    print(f"{label}: exit={code}, elapsed={elapsed:.3f}s", flush=True)
    return code, failures


def main() -> None:
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", CANDIDATE, "--", *CODE_PATHS], cwd=ROOT, text=True)
    assert not changed.strip(), "feature code must remain exactly the reviewed candidate"
    spec = json.loads((ROOT / "qa/evidence/teaching-pdf/mutations.json").read_text())
    mutations = [m for m in spec["mutations"] if m["name"] != "PDF secret sanitation removed"]
    assert len(mutations) == 21
    tests = sorted({test for m in mutations for test in m["kills"]})
    original = source_manifest(ROOT)
    work, owned = harness._sandbox(ROOT)
    shutil.copy2(ROOT / "uv.lock", work / "uv.lock")
    (work / ".work").mkdir()
    assert source_manifest(work) == original, "sandbox copy differs before its first command"
    assert not list(work.rglob("__pycache__")), "copied caches would invalidate proof identity"
    os.environ["PYTHONPATH"] = str(work / "src")
    os.environ["OMP_THREAD_LIMIT"] = "1"
    tool_receipts = {}
    for name, argument in (("tesseract", "--version"), ("pdftoppm", "-v")):
        executable = shutil.which(name)
        assert executable, f"required local tool unavailable: {name}"
        result = subprocess.run([executable, argument], capture_output=True, text=True,
                                timeout=10, check=True)
        tool_receipts[name] = {"path": executable, "sha256": digest(Path(executable).read_bytes()),
                               "version": (result.stdout + result.stderr).splitlines()[0]}
    dump("context.json", {
        "created_utc": datetime.now(UTC).isoformat(), "feature_candidate": CANDIDATE,
        "base": "abc4a0ef", "fix_cycle": 2, "bound_worktree": str(ROOT), "sandbox": str(work),
        "python": sys.executable, "python_version": sys.version,
        "python_sha256": digest(Path(sys.executable).read_bytes()),
        "dependencies": {m: importlib.metadata.version(m) for m in ("pypdf", "Pillow", "pytest")},
        "lock_sha256": original["uv.lock"], "source_manifest": original,
        "source_tree_sha256": tree_digest(original), "tools": tool_receipts,
        "environment": {"PYTHONPATH": str(work / "src"), "OMP_THREAD_LIMIT": "1",
                        "PATH_sha256": digest(os.environ["PATH"].encode()),
                        "TESSDATA_PREFIX_sha256": digest(os.environ.get("TESSDATA_PREFIX", "").encode())},
        "excluded": "previously independently proven sanitation mutation; no broader test suite",
        "tokens": None, "cost": None,
    })
    helper = Path("C:/Users/product/.agents/skills/checker/scripts/review_budget.py")
    preflight = subprocess.run([sys.executable, str(helper), "preflight", "--root", str(work),
                               "--import-name", "autotester", "--import-root", str(work / "src"),
                               "--temp-parent", str(work / ".work")], capture_output=True, text=True,
                              timeout=30, check=True)
    (OUT / "preflight.log").write_text(preflight.stdout + preflight.stderr, encoding="utf-8")
    code, _ = run_probe(work, tests, "00-green")
    assert code == 0, "baseline not green; no mutation result is valid"
    rows = []
    for index, mutation in enumerate(mutations, 1):
        assert source_manifest(work) == original, "prior mutation was not restored"
        target = harness._inside(work, mutation["file"], mutation["name"])
        before = target.read_bytes()
        text = before.decode("utf-8")
        assert text.count(mutation["old"]) == 1, "anchor must match once"
        altered = text.replace(mutation["old"], mutation["new"], 1).encode("utf-8")
        assert altered != before
        target.write_bytes(altered)
        assert target.read_bytes() == altered
        try:
            code, failures = run_probe(work, mutation["kills"], f"{index:02}-red")
        finally:
            target.write_bytes(before)
        assert target.read_bytes() == before
        assert source_manifest(work) == original
        killed = harness.is_kill(code, set(mutation["kills"]), failures)
        row = {"name": mutation["name"], "file": mutation["file"], "old": mutation["old"],
               "new": mutation["new"], "anchor_matches": 1, "before_sha256": digest(before),
               "mutated_sha256": digest(altered), "restored_sha256": digest(target.read_bytes()),
               "restored_tree_sha256": tree_digest(source_manifest(work)), "expected": mutation["kills"],
               "actual_failed": sorted(failures), "killed": killed, "exit": code,
               "command_receipt": f"{index:02}-red.receipt.json"}
        rows.append(row)
        dump("results.json", rows)
        assert killed, f"missing named failure for {mutation['name']}"
    code, _ = run_probe(work, tests, "99-restored-green")
    assert code == 0 and source_manifest(work) == original
    dump("completion.json", {"ended_utc": datetime.now(UTC).isoformat(), "mutations": len(rows),
                             "all_killed": all(r["killed"] for r in rows),
                             "restored_tree_sha256": tree_digest(source_manifest(work)),
                             "bound_worktree_unchanged": source_manifest(ROOT) == original})
    assert source_manifest(ROOT) == original
    print("Authenticated 21/21 proofs; green and restored-green baseline passed", flush=True)
    harness._discard(owned)


if __name__ == "__main__":
    main()
