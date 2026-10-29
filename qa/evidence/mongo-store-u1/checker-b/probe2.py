import sys
W = "D:/autoTesting/.claude/worktrees/mongo-u1"
sys.path[:0] = [W + "/src", W + "/tests"]
from pymongo import uri_parser
import autotester.store.mongo_guard as g
import fake_mongo as fm
for u in ["mongodb://u:p#x@h/autotester", "mongodb://h/autotester.x", "mongodb://h/AUTOTESTER.coll", "mongodb://h/autotester.",
          "mongodb://h/%61utotester.%78"]:
    try:
        r = uri_parser.parse_uri(u)
        d, c = r["database"], r["collection"]
    except Exception as e:
        d = c = "ERR " + type(e).__name__
    srv = fm.FakeMongoServer(); cl = srv.client()
    try:
        with fm.seams(client_factory=lambda _u: cl):
            g.GuardedStore(u)
        o = "CONSTRUCTED"
    except Exception as e:
        o = "refused:" + type(e).__name__
    print(f"{u!r:36} parse_uri(default validate) db={d!r} coll={c!r} guard={g._uri_path_database(u)!r} -> {o}")
