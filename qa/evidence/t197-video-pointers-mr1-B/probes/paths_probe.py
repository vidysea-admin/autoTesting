import importlib.util, inspect, json, sys, tempfile
from pathlib import Path
import autotester
print("AT_FILE", autotester.__file__)
def load(name, f):
    spec = importlib.util.spec_from_file_location(name, f); m = importlib.util.module_from_spec(spec); sys.modules[name] = m; spec.loader.exec_module(m); return m
out = {}
for n in ("master", "unit", "head", "variant"):
    m = load("paths_" + n, f"paths_{n}.py")
    root = Path(tempfile.mkdtemp(prefix="pp-"))
    P = m.ProjectPaths("proj", root)
    P.ensure(); P.ensure()
    tree = sorted(p.relative_to(root).as_posix() + ("/" if p.is_dir() else "") for p in root.rglob("*"))
    vals = {}
    for name, obj in inspect.getmembers(m.ProjectPaths):
        if name.startswith("_") or name in ("ensure",): continue
        try:
            if isinstance(obj, property):
                v = getattr(P, name)
            elif callable(obj):
                nparams = len(inspect.signature(obj).parameters) - 1
                v = getattr(P, name)(*(["X"] * nparams))
            else: continue
            vals[name] = str(v).replace(str(root), "<root>").replace("\\", "/") if not isinstance(v, (str, int, float, bool, type(None))) else v
        except Exception as e:
            vals[name] = "ERR " + type(e).__name__
    out[n] = {"tree": tree, "vals": vals, "ensure_src_lines": len(inspect.getsource(m.ProjectPaths.ensure).splitlines())}
json.dump(out, open("paths_out.json", "w"), indent=1, sort_keys=True)
h, v, mm, u = out["head"], out["variant"], out["master"], out["unit"]
print("tree head==variant:", h["tree"] == v["tree"], len(h["tree"]), "dirs")
print("tree head==master:", h["tree"] == mm["tree"], " head==unit:", h["tree"] == u["tree"])
print("vals head==variant:", h["vals"] == v["vals"], len(h["vals"]), "members")
for k in ("review_path", "review_work_dir"): print(k, "head==unit:", h["vals"][k] == u["vals"][k], h["vals"][k])
print("case_proposals head==master:", h["vals"]["case_proposals"] == mm["vals"]["case_proposals"], h["vals"]["case_proposals"])
print("member diff head vs variant:", {k for k in set(h["vals"]) ^ set(v["vals"])}, [k for k in h["vals"] if h["vals"].get(k) != v["vals"].get(k)])
print("members head-master:", sorted(set(h["vals"]) - set(mm["vals"])), "master-head:", sorted(set(mm["vals"]) - set(h["vals"])))
print("members head-unit:", sorted(set(h["vals"]) - set(u["vals"])), "unit-head:", sorted(set(u["vals"]) - set(h["vals"])))
print("others equal master->head:", [k for k in mm["vals"] if mm["vals"][k] != h["vals"].get(k)])
print("ensure tree entries:", h["tree"])
