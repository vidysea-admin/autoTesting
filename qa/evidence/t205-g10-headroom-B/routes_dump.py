import os, sys, tempfile, json
os.environ["AUTOTESTER_ROOT"] = tempfile.mkdtemp(prefix="b-routes-")
from autotester.ui.app import app
rows = []
def flat(routes):
    for route in routes:
        inner = getattr(route, "original_router", None)
        yield from flat(inner.routes) if inner is not None else [route]
ALL = list(flat(app.routes))
for r in ALL:
    methods = sorted(getattr(r, "methods", None) or [])
    ep = getattr(r, "endpoint", None)
    rows.append(f"{','.join(methods)} {r.path} {getattr(ep, '__module__', '')}.{getattr(ep, '__qualname__', '')} dep={len(getattr(r, 'dependencies', []) or [])} name={r.name}")
print(len(rows))
print("\n".join(rows))
print("middleware:", [m.cls.__name__ for m in app.user_middleware])
print("exc handlers:", sorted(str(k) for k in app.exception_handlers))
print("catchalls:", [getattr(r,"path","") for r in ALL if ":path}" in getattr(r,"path","")])
