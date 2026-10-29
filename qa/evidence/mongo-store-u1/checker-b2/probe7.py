"""Checker B cycle 2: URI parity against the driver's own _validate_uri (no DNS, no network)."""
import sys, random, itertools
W = "D:/autoTesting/.claude/worktrees/mongo-u1"
sys.path[:0] = [W + "/src", W + "/tests"]
import autotester.store.mongo_guard as g
import fake_mongo as fm
from pymongo.uri_parser_shared import _validate_uri
from bson.errors import BSONError, InvalidDocument
from pymongo.errors import PyMongoError
print("InvalidDocument is PyMongoError:", issubclass(InvalidDocument, PyMongoError), "| BSONError is:", issubclass(BSONError, PyMongoError))

def drv(u):
    try: return _validate_uri(u, 27017, True, False, False, None)["database"]
    except Exception as e: return "ERR:" + type(e).__name__
def grd(u):
    try: return g._uri_path_database(u)
    except Exception as e: return "ERR:" + type(e).__name__

hand = ["mongodb://%2Ftmp%2Fm.sock/autotester", "mongodb://%2Ftmp%2Fm.sock,h/autotester", "mongodb://", "mongodb:///", "mongodb://h", "mongodb://h/", "mongodb:///autotester",
        "mongodb://h?authSource=autotester", "mongodb://h/?authSource=autotester", "mongodb://[::1]:27017/autotester", "mongodb://[::1]/AutoTester?x=1",
        "mongodb://h1:1,h2:2,h3:3/autotester", "mongodb+srv://c.example.net/autotester?replicaSet=rs0&authSource=admin", "mongodb+srv://u:p@c.example.net/autotester?authSource=admin",
        "mongodb+srv://c.example.net/autotester?srvServiceName=x", "mongodb+srv://c.example.net/autotester?srvMaxHosts=2", "mongodb+srv://c.example.net/autotester?directConnection=true",
        "mongodb+srv://c.example.net:27017/autotester", "mongodb+srv://a,b/autotester", "mongodb://h/autotester%2e", "mongodb://h/%2Fautotester", "mongodb://h/autotester%00",
        "mongodb://h/autotester/x", "mongodb://h//autotester", "mongodb://h/.autotester", "mongodb://h/autotester..x", "mongodb://u@h/autotester", "mongodb://:@h/autotester", "mongodb://u:p@@h/autotester",
        "mongodb://u:p:q@h/autotester", "mongodb://h/autotester?", "mongodb://h/autotester?&", "mongodb://h/autotester?=", "mongodb://h/autotester?appname=a/b", "mongodb://h/AuToTeStEr"]
print("== hand corpus (driver | guard)")
for u in hand:
    d, r = drv(u), grd(u)
    flag = ""
    if isinstance(d, str) and not d.startswith("ERR") and d is not None:
        pass
    # bypass = driver parses fine, db equals store (casefold), guard did not see it
    if d and not str(d).startswith("ERR") and str(d).casefold() == "autotester" and str(r).casefold() != "autotester": flag = "  <<< BYPASS"
    if str(d).startswith("ERR") is False and str(r).startswith("ERR"): flag += "  (guard refuses a URI the driver accepts)"
    print(f"{u!r:78} drv={d!r:22} grd={r!r}{flag}")

print("== fuzz")
toks = ["mongodb://", "mongodb+srv://", "u", ":", "p", "@", "#", "?", "/", ".", "%2F", "%61", "%2e", "%40", "%23", "%3f", "+", "autotester", "AUTOTESTER", "Autotester", "h", ",", "[::1]", "=", "&", "authSource", "x", " ", "\n", "%", "\uff1a", "\uff20", "\u212a", "%00"]
rnd = random.Random(20261029); bypass = []; over = 0; n = 0
for _ in range(400000):
    k = rnd.randint(2, 9)
    body = "".join(rnd.choice(toks) for _ in range(k))
    u = rnd.choice(["mongodb://", "mongodb+srv://"]) + body
    d = drv(u)
    if isinstance(d, str) and d.startswith("ERR"): continue
    n += 1
    r = grd(u)
    if d is not None and d.casefold() == "autotester" and str(r).casefold() != "autotester":
        # a clash the guard misses unless it refused (ERR counts as refused)
        if not str(r).startswith("ERR"): bypass.append((u, d, r))
    if str(r).startswith("ERR"): over += 1
print("driver-valid URIs:", n, "| guard bypasses:", len(bypass), "| guard refuses driver-valid:", over)
for b in bypass[:10]: print("  BYPASS", b)
