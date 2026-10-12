"""Group a junit xml by the -k substrings of each criterion (Part 1 grouping)."""
import sys, xml.etree.ElementTree as ET
KEYS = {f"AU{i}": [f"test_au{i}_"] for i in range(1, 24)}
KEYS["AU7"] = ["test_au7_", "test_d074"]
KEYS["AU27"] = ["test_p5"]
KEYS["AU19"] = ["test_au19_", "tests/test_ui_origin_guard.py"]
cases = []
for path in sys.argv[1:]:
    for tc in ET.parse(path).getroot().iter("testcase"):
        status = "passed"
        for ch in tc:
            if ch.tag in ("failure", "error"): status = "FAILED"
            elif ch.tag == "skipped": status = "skipped"
        cls = tc.get("classname", "").replace(".", "/")
        cases.append((cls + "::" + tc.get("name"), tc.get("name"), status))
rows = []
for crit, subs in KEYS.items():
    sel = [c for c in cases if any((s in c[1]) if not s.startswith("tests/") else (s[:-3].replace("/", "/") in c[0]) for s in subs)]
    n = len(sel); p = sum(1 for c in sel if c[2] == "passed"); f = sum(1 for c in sel if c[2] == "FAILED")
    rows.append((crit, n, p, f))
    print(f"{crit}: collected={n} passed={p} failed={f} skipped={n-p-f}")
