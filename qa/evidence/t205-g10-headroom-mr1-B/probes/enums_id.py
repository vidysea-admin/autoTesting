import importlib, pkgutil, json, sys, enum, inspect
import autotester, autotester.schema as sc
print(autotester.__file__, file=sys.stderr)
sched = importlib.import_module("autotester.schema.schedule")
pub = {n: type(getattr(sched, n)).__name__ for n in dir(sched) if not n.startswith("_")}
res = {"schedule_public": pub}
try:
    te = importlib.import_module("autotester.schema.team_enums")
except ImportError:
    te = None
names = ["ScheduleMode","ScheduleZone","SlotOutcome","SchedulerHealth","CredentialState"]
ident = {}
for n in names:
    a = getattr(sched, n)
    ident[n] = {"from schedule": a.__module__}
    if te: ident[n]["is team_enums.%s" % n] = (getattr(te, n) is a)
    ident[n]["members"] = [m.value for m in a]
# every class of that name anywhere in the package
mods = {}
for m in pkgutil.walk_packages(autotester.__path__, "autotester."):
    try: mod = importlib.import_module(m.name)
    except Exception as e: continue
    for n in names + ["RunVia","SourceOriginKind"]:
        c = getattr(mod, n, None)
        if inspect.isclass(c): mods.setdefault(n, {}).setdefault(c.__module__ + "." + c.__qualname__, []).append(m.name)
res["identity"] = ident
res["definitions"] = {n: {k: len(v) for k, v in d.items()} for n, d in mods.items()}
res["distinct_classes_per_name"] = {n: len(d) for n, d in mods.items()}
# every import path used by tests/src of master/head
from pathlib import Path
paths = {}
for n in names:
    objs = {}
    for modname in ("autotester.schema.schedule","autotester.schema.team_enums","autotester.schema.enums","autotester.schema","autotester.stages.schedule_gate","autotester.stages.scheduler"):
        try: mod = importlib.import_module(modname)
        except Exception: continue
        if hasattr(mod, n): objs[modname] = id(getattr(mod, n))
    paths[n] = {"paths": sorted(objs), "one_object": len(set(objs.values())) == 1}
res["paths"] = paths
json.dump(res, open(sys.argv[1], "w"), indent=1, sort_keys=True)
