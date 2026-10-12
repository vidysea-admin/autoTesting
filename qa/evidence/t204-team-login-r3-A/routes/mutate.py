"""Apply one named mutation to a throwaway copy: mutate.py <copy_dir> <name>."""
import sys
from pathlib import Path

copy, name = Path(sys.argv[1]), sys.argv[2]
POL = copy / "src/autotester/auth/policy.py"
TST = copy / "tests/test_ui_auth_escalation.py"

DRIVE_GET = '"/catalog", "/sources/drive/{job_id}")}'
DAMAGE = '"/report.html", "/damage-report")}'
DRIVE_POST = '"/sources/upload", "/sources/drive")},'
ACCESS_ROW = '    ("POST", _P + "/access"): _VIEW,\n'

EDITS = {
    "m1": (POL, [(DRIVE_POST, '"/sources/upload",)},')]),
    "m2": (POL, [(DRIVE_GET, '"/catalog")}')]),
    "m3": (POL, [(DAMAGE, '"/report.html")}')]),
    "m5": (POL, [(DAMAGE, '"/report.html")}'), (DRIVE_GET, '"/catalog", "/sources/drive/{job_id}", "/damage-report")}')]),
    "m6": (POL, [(DRIVE_POST, '"/sources/upload",)},'),
                 (ACCESS_ROW, ACCESS_ROW + '    ("POST", _P + "/sources/drive"): _VIEW,\n')]),
    "m7": (POL, [(DRIVE_GET, '"/catalog")}'),
                 (ACCESS_ROW, ACCESS_ROW + '    ("GET", _P + "/sources/drive/{job_id}"): _project(K.VIDEO_UPLOAD),\n')]),
    "m4a": (TST, [('"/catalog", "/sources/drive/{job_id}")}', '"/catalog")}')]),
    "m4b": (TST, [('"/report.html", "/damage-report")}', '"/report.html")}')]),
    "m4c": (TST, [('for t in ("/sources/upload","/sources/drive")},', 'for t in ("/sources/upload",)},')]),
}
if name == "base":
    print("no change")
    sys.exit(0)
path, edits = EDITS[name]
text = path.read_text(encoding="utf-8")
for old, new in edits:
    assert text.count(old) == 1, (name, old, text.count(old))
    text = text.replace(old, new)
path.write_text(text, encoding="utf-8")
print("mutated", name, path.relative_to(copy))
