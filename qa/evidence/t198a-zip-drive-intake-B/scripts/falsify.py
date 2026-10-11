"""Seat B falsification runner: one named falsification per criterion, each in its own copy.
Run with the worktree venv python: python falsify.py <scratch>"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

W = Path("D:/autoTesting/.worktrees/t198a-zip-drive-intake")
PY = str(W / ".venv/Scripts/python.exe")
scr = Path(sys.argv[1])
fal = scr / "fals"
shutil.rmtree(fal, ignore_errors=True)
fal.mkdir()

S = "src/autotester/"
ROWS = [
    ("TI1", S + "sources/zip_names.py", 'unified = raw.replace("\\\\", "/")', "unified = raw",
     ["tests/test_zip_intake_names.py"]),
    ("TI2", S + "sources/zip_intake.py",
     "if info.file_size > limits.ratio_min_bytes and ratio > limits.max_ratio:", "if False:",
     ["tests/test_zip_intake_limits.py"]),
    ("TI3", S + "sources/zip_intake.py",
     'return plan(_S, f"not a recording ({ext}); only video files are registered")',
     'return plan(None, None, ".mp4")', ["tests/test_zip_intake_register.py", "tests/test_cli_intake.py"]),
    ("TI4", S + "sources/intake_commit.py",
     'target = ensure_inside(store.paths.source_dir(draft.id) / f"{RECORDING_STEM}{suffix}",',
     'target = ensure_inside(store.paths.source_dir(draft.id) / (label or f"{RECORDING_STEM}{suffix}"),',
     ["tests/test_zip_intake_register.py", "tests/test_zip_intake_atomic.py", "tests/test_drive_intake.py"]),
    ("TI5", S + "sources/zip_intake.py",
     "return IntakeStatus.PARTIAL if any(r.outcome in good for r in results) else IntakeStatus.FAILED",
     "return IntakeStatus.OK if any(r.outcome in good for r in results) else IntakeStatus.FAILED",
     ["tests/test_zip_intake_register.py", "tests/test_cli_intake.py"]),
    ("TI6", S + "sources/intake_commit.py",
     '        _place(staged, target, digest)\n        store.add_source(draft.model_copy(update={"path": str(target)}))',
     '        store.add_source(draft.model_copy(update={"path": str(target)}))\n        _place(staged, target, digest)',
     ["tests/test_zip_intake_atomic.py"]),
    ("TI7", S + "sources/drive_verify.py",
     "if download.md5 is not None and md5.lower() != download.md5.strip().lower():", "if False:",
     ["tests/test_drive_verify.py", "tests/test_drive_intake.py"]),
    ("TI8", S + "sources/drive_errors.py",
     "    code, text = _error_fields(stderr.strip() or stdout.strip())",
     "    return DriveFailure.NETWORK_ERROR\n    code, text = _error_fields(stderr.strip() or stdout.strip())",
     ["tests/test_gws_drive.py"]),
    ("TI9", S + "sources/gws_drive.py",
     "self._limit = limit_bytes or (lambda: read_max_upload_bytes().bytes)",
     "self._limit = lambda: 2 * 1024**3", ["tests/test_gws_drive.py", "tests/test_drive_intake.py"]),
    ("TI10-seam", S + "ui/routes_intake.py", "            get_gate().recheck(actor, slug)", "            pass",
     ["tests/test_ui_intake_drive.py"]),
    ("TI11", S + "ui/intake_upload.py", "uploaded_by=actor.email,\n                     uploaded_at=datetime.now(UTC),",
     'uploaded_by=staged.fields.get("uploaded_by", actor.email),\n                     uploaded_at=datetime.now(UTC),',
     ["tests/test_ui_intake.py"]),
    ("HO30", S + "ui/upload_stream.py", "if self.size + len(piece) > self.limit:", "if False:",
     ["tests/test_ui_intake.py"]),
    ("HO32", S + "sources/drive_link.py", "if host not in DRIVE_HOSTS:",
     'if not host.startswith("drive.google.com"):', ["tests/test_drive_link.py"]),
    ("HO33", S + "sources/gws_runner.py", "if written > max_bytes:", "if written > max_bytes * 10_000:",
     ["tests/test_gws_runner.py"]),
]


def pytest(copy, files, tag):
    env = {**os.environ, "PYTHONPATH": str(copy / "src")}
    r = subprocess.run([PY, "-m", "pytest", "-p", "no:xdist", "-p", "no:cacheprovider",
                        f"--basetemp={copy / 'bt'}", "-c", str(copy / "pyproject.toml"), *files],
                       cwd=copy, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = r.stdout
    failed = re.findall(r"^FAILED (\S+)", out, re.M)
    summ = out.strip().splitlines()[-1] if out.strip() else ""
    return r.returncode, summ, failed


res = {}
for rid, rel, old, new, files in ROWS:
    copy = fal / rid
    copy.mkdir()
    shutil.copytree(W / "src", copy / "src", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(W / "tests", copy / "tests", ignore=shutil.ignore_patterns("__pycache__"))
    for f in ("pyproject.toml",):
        shutil.copy(W / f, copy / f)
    for d in ("docs", "scripts"):
        if (W / d).exists():
            shutil.copytree(W / d, copy / d, ignore=shutil.ignore_patterns("__pycache__"))
    where = subprocess.run([PY, "-c", "import autotester;print(autotester.__file__)"], cwd=copy,
                           env={**os.environ, "PYTHONPATH": str(copy / "src")}, capture_output=True, text=True).stdout.strip()
    target = copy / rel
    text = target.read_text(encoding="utf-8")
    entry = dict(file=rel, copy_import=where.replace("\\", "/").split("/.")[-1][-60:], anchor_found=text.count(old))
    if text.count(old) != 1:
        res[rid] = {**entry, "error": "anchor not unique"}
        continue
    g = pytest(copy, files, "green")
    entry["green"] = dict(rc=g[0], summary=g[1])
    target.write_text(text.replace(old, new), encoding="utf-8")
    r = pytest(copy, files, "red")
    entry["red"] = dict(rc=r[0], summary=r[1], failed=[x.split("::", 1)[-1] for x in r[2]][:4])
    res[rid] = entry
    shutil.rmtree(copy, ignore_errors=True)
    print(rid, entry["green"]["summary"], "|", entry["red"]["summary"], flush=True)
print(json.dumps(res, indent=1))
