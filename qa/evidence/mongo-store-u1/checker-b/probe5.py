import sys, traceback, io, logging
W = "D:/autoTesting/.claude/worktrees/mongo-u1"
sys.path[:0] = [W + "/src", W + "/tests"]
import autotester.store.mongo_guard as g
import fake_mongo as fm

print(sys.version)
for label, uri in [
    ("fullwidth colon in password", "mongodb://umesh:CANARY\uff1apw@h.example/"),
    ("fullwidth at in password", "mongodb://umesh:CANARY\uff20pw@h.example/"),
    ("bad ipv6", "mongodb://umesh:CANARY-pw@[h/"),
    ("clean", "mongodb://umesh:CANARY-pw@h.example/"),
]:
    srv = fm.FakeMongoServer()
    cl = srv.client()
    try:
        with fm.seams(client_factory=lambda _u: cl):
            g.GuardedStore(uri)
        print(label, "-> constructed")
    except Exception as e:
        text = "".join(traceback.format_exception(e))
        print(label, "->", type(e).__name__, "| canary in str(e):", "CANARY" in str(e), "| in traceback text:", "CANARY" in text)
        print("   msg:", ascii(str(e))[:140])
