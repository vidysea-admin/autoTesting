"""Does the repo's own gates notice the JSON-escaped planted secret in case_proposals.jsonl / cases.jsonl?"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import S, ROOTS
sys.path.insert(0, r"C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/236a59b4-e0ec-4b2d-b22e-73d3059dd7f6/scratchpad/t178a/base/scripts")
import check_no_secrets as cns
from autotester.core.redact import Redactor
red = Redactor({"ZZ_PROBE_PW": S})
for name, rel in (("p1b_name", "projects/demo/case_proposals.jsonl"), ("p1b_name", "projects/demo/cases.jsonl")):
    f = ROOTS / name / rel
    if not f.exists(): print(name, rel, "missing"); continue
    t = f.read_text(encoding="utf-8")
    vals = cns.real_values(ROOTS / name)
    clean = cns.scan([f], vals)[f]
    print(f"{rel}: raw S in text={S in t} | json-recoverable={any(S in json.loads(l)['title'] for l in t.splitlines())} | check_no_secrets.scan says clean={clean} | Redactor.is_clean={red.is_clean(t)} | Redactor.contains_folded={red.contains_folded(t)}")
