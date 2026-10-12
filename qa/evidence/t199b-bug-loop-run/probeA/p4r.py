import sys, json, hashlib
import autotester; print("autotester:", autotester.__file__)
from pathlib import Path
from autotester.schema.verdict import Rubric, Criterion, Verdict
from autotester.schema.case import Case
from autotester.schema.tracked_bug import *
d = Path(sys.argv[1])
for name, cls in (("rubric", Rubric), ("case", Case), ("verdict", Verdict), ("tracked", TrackedBug), ("event", BugEvent), ("seed", BugSeed)):
    txt = (d/f"{name}.json").read_text()
    m = cls.model_validate_json(txt)
    rt = json.loads(m.model_dump_json(exclude_none=True)); orig = json.loads(txt)
    print(name, "loads; roundtrip equal (modulo defaults):", {k:v for k,v in rt.items() if k in orig} == orig)
r = Rubric.model_validate_json((d/"rubric.json").read_text())
c = r.criteria[0]
print("model_dump has fingerprint:", "fingerprint" in c.model_dump(), "| rubric json has:", "fingerprint" in r.model_dump_json())
fp = c.fingerprint; print("fp", fp, "len", len(fp))
print("FP", fp)
print("text change", Criterion(id="C1", text="Pay works!").fingerprint != fp)
print("evidence change", Criterion(id="C1", text="Pay works", evidence_required=False).fingerprint != fp)
print("id change", Criterion(id="C9", text="Pay works").fingerprint != fp)
print("whitespace change", Criterion(id="C1", text="Pay works ").fingerprint != fp)
r2 = Rubric(id="rub_x", criteria=list(reversed(r.criteria)))
print("reorder: per-criterion fps unchanged:", {x.id: x.fingerprint for x in r.criteria} == {x.id: x.fingerprint for x in r2.criteria})
