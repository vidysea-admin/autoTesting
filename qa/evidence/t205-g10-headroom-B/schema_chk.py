import json, sys, ast
from pathlib import Path
from pydantic import ValidationError
from autotester.schema.project import Project
from autotester.schema.run import Run
import autotester.schema.team_enums as te
import autotester.schema.schedule as sc

MASTER = Path(sys.argv[1])
ok = bad = 0
for pj in sorted(MASTER.glob("projects/*/project.json")):
    try:
        p = Project.model_validate_json(pj.read_text(encoding="utf-8"))
        rt = Project.model_validate_json(p.model_dump_json())
        assert rt == p
        ok += 1
    except Exception as e:
        bad += 1; print("LOAD FAIL", pj, str(e)[:150])
print("master project.json files loaded:", ok, "failed:", bad)
runs = sorted(MASTER.glob("projects/*/runs/*/run.json")) + sorted(MASTER.glob("projects/*/run*.json"))
r_ok = r_bad = 0
for rj in runs:
    try:
        Run.model_validate_json(rj.read_text(encoding="utf-8")); r_ok += 1
    except Exception as e:
        r_bad += 1; print("RUN FAIL", rj, str(e)[:150])
print("master run records loaded:", r_ok, "failed:", r_bad)

base = json.loads(next(MASTER.glob("projects/*/project.json")).read_text(encoding="utf-8"))
def tryload(label, mutate):
    d = json.loads(json.dumps(base)); mutate(d)
    try:
        Project.model_validate(d); print(f"{label:55s} ACCEPTED")
    except ValidationError as e:
        print(f"{label:55s} refused ({e.errors()[0]['type']})")
tryload("unknown top-level key", lambda d: d.update(evil=1))
tryload("unknown key __proto__", lambda d: d.update({"__proto__": {}}))
tryload("schedule: unknown nested key", lambda d: d.update(schedule={"mode": "manual", "evil": 1}))
tryload("tracker: unknown nested key", lambda d: d.update(tracker={"evil": 1}))
tryload("schedule: null (explicit)", lambda d: d.update(schedule=None))
tryload("tracker: bare dict", lambda d: d.update(tracker={}))
tryload("schedule: mode outside enum", lambda d: d.update(schedule={"mode": "hourly"}))
tryload("secrets entry unknown key", lambda d: d.update(secrets=[{"key": "A_B", "value": "leak"}]))
for cls_name in ("ScheduleMode", "ScheduleZone", "SlotOutcome", "SchedulerHealth"):
    print(cls_name, "same object in schedule and team_enums:", getattr(sc, cls_name) is getattr(te, cls_name),
          [m.value for m in getattr(te, cls_name)])
# duplicate definitions anywhere in src
import re
src = Path(sys.argv[2])
names = {}
for f in src.rglob("*.py"):
    for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
        if isinstance(n, ast.ClassDef):
            names.setdefault(n.name, []).append(f.name)
print("classes defined in >1 module:", {k: v for k, v in names.items() if len(v) > 1 and k in {"ScheduleMode","ScheduleZone","SlotOutcome","SchedulerHealth","RunVia","TrackerConfig"}})
