import json
from autotester.ui.app import app
import autotester
print("FILE", autotester.__file__)
seen=set()
def walk(routes, prefix=""):
    for r in routes:
        cls = type(r).__name__
        if cls == "_IncludedRouter":
            sub = getattr(r, "router", None) or getattr(r, "original_router", None)
            pf = getattr(r, "prefix", "") or ""
            if sub is None: print(json.dumps({"unwalked": cls, "attrs": [a for a in dir(r) if not a.startswith('__')]})); continue
            walk(sub.routes, prefix + pf); continue
        path = prefix + getattr(r, "path", "")
        meth = sorted(getattr(r, "methods", None) or [])
        if cls == "Mount":
            print(json.dumps({"mount": path})); walk(r.routes, path); continue
        print(json.dumps({"path": path, "methods": meth, "cls": cls}))
walk(app.routes)
