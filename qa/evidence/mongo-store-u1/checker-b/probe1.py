import sys, os
W = "D:/autoTesting/.claude/worktrees/mongo-u1"
sys.path[:0] = [W + "/src", W + "/tests"]
from pymongo import uri_parser
import autotester.store.mongo_guard as g
from autotester.store.mongo_guard import GuardedStore, StoreConfigError
import fake_mongo as fm

print("== A. URI differential: driver database vs guard's decode")
uris = ["mongodb://u:p#x@h/autotester", "mongodb://u:p?x@h/autotester", "mongodb://h/autotester#f",
        "mongodb://h/autotester?authSource=admin", "mongodb://h/%61utotester", "mongodb://u:p%23x@h/autotester",
        "mongodb://h/autotester\n", "mongodb://h/auto\ttester", "MONGODB://h/autotester", " mongodb://h/autotester",
        "mongodb://h/Autotester", "mongodb://h/autotester.", "mongodb://h,h2:2/AUTOTESTER", "mongodb://h/%2561utotester"]
for u in uris:
    try:
        d = uri_parser.parse_uri(u, validate=False)["database"]
    except Exception as e:
        d = "PARSE-ERR " + type(e).__name__
    try:
        gd = g._uri_path_database(u)
    except Exception as e:
        gd = "GUARD-ERR " + type(e).__name__
    srv = fm.FakeMongoServer()
    cl = srv.client()
    try:
        with fm.seams(client_factory=lambda _u: cl):
            GuardedStore(u)
        outcome = "CONSTRUCTED"
    except Exception as e:
        outcome = "refused:" + type(e).__name__
    print(f"{u!r:45} driver={d!r:22} guard={gd!r:22} -> {outcome}")

print("== B. _raw() leaks the driver-level collection")
srv = fm.FakeMongoServer(); cl = srv.client()
with fm.seams(client_factory=lambda _u: cl):
    s = GuardedStore("mongodb://h/")
c = s.collection("projects")
raw = c._raw()
print(type(raw), "has .name", raw.name)
# write to a foreign db through the leaked handle
raw._db.server.database("pathlynks")["users"].docs.append({"_id": "pwned"})
print("foreign db now:", srv.databases["pathlynks"]["users"].docs)
print("spy accessed:", cl.accessed[:5])
print("callable zero-arg private methods on store/collection/bucket returning non-primitive:")
b = s.bucket()
for obj in (s, c, s.collection("approvals"), b):
    for n in dir(obj):
        if n.startswith("_") and not n.startswith("__"):
            v = getattr(obj, n)
            if callable(v):
                try:
                    r = v()
                except TypeError:
                    continue
                except Exception as e:
                    r = f"raised {type(e).__name__}"
                print(f"  {type(obj).__name__}.{n}() -> {type(r).__name__}")
