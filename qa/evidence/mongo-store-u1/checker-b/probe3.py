import sys, os, tempfile, pathlib
W = "D:/autoTesting/.claude/worktrees/mongo-u1"
sys.path[:0] = [W + "/src", W + "/tests"]
import autotester.store.mongo_guard as g
from autotester.schema.store_config import load_store_config
import fake_mongo as fm

tmp = pathlib.Path(tempfile.mkdtemp())


def cfg(text, raw=None):
    p = tmp / f"c{len(list(tmp.iterdir()))}.toml"
    p.write_bytes(raw if raw is not None else text.encode("utf-8"))
    try:
        return "OK " + load_store_config(p).database
    except Exception as e:
        return "refused " + type(e).__name__


print("== TOML")
H = '[tool.autotester.store]\n'
cases = {
    "ok": H + 'database = "autotester"\n',
    "dupkey": H + 'database = "autotester"\ndatabase = "admin"\n',
    "nested": H + 'database = "autotester"\n[tool.autotester.store.x]\ndatabase="y"\n',
    "int": H + 'database = 5\n',
    "bool": H + 'database = true\n',
    "list": H + 'database = ["a"]\n',
    "inline-table": H + 'database = {a=1}\n',
    "ADMIN": H + 'database = "ADMIN"\n',
    "Config": H + 'database = "Config"\n',
    "fullwidth": H + 'database = "\uff41utotester"\n',
    "trailing-nl": H + 'database = "autotester\\n"\n',
    "trailing-space": H + 'database = "autotester "\n',
    "dot": H + 'database = "auto.tester"\n',
    "pathlynks": H + 'database = "pathlynks"\n',
    "extra-key": H + 'database = "autotester"\nproduct_databases = ["x"]\n',
    "arr-of-tables": '[[tool.autotester.store]]\ndatabase = "autotester"\n',
    "dotted": 'tool.autotester.store.database = "autotester"\n',
    "len38": H + 'database = "' + "a" * 38 + '"\n',
    "len39": H + 'database = "' + "a" * 39 + '"\n',
    "empty-store-table": H,
    "tool-is-str": 'tool = "x"\n',
}
for k, v in cases.items():
    print(f"{k:16}", cfg(v))
print(f"{'bom':16}", cfg("", raw=b"\xef\xbb\xbf" + cases["ok"].encode()))

print("== filter / update / verbs")
srv = fm.FakeMongoServer()
cl = srv.client()
with fm.seams(client_factory=lambda _u: cl):
    s = g.GuardedStore("mongodb://h/")


def t(label, fn):
    try:
        r = fn()
        print(f"  ALLOWED  {label} -> {r!r}")
    except Exception as e:
        print(f"  refused  {label}: {type(e).__name__}: {str(e)[:60]}")


P = s.collection("projects")
SS = s.collection("server_state")
JS = {"body": "x", "args": [], "lang": "js"}
t("where", lambda: P.delete_one({"$where": "1"}))
t("expr-function", lambda: P.find({"$expr": {"$function": JS}}))
t("nested and/where", lambda: P.update_one({"$and": [{"$or": [{"$where": "1"}]}]}, {"$set": {"a": 1}}))
t("tuple-nested accumulator", lambda: P.find_one({"a": ({"$accumulator": {}},)}))
t("count with where", lambda: P.count_documents({"$where": "1"}))
t("projection function (unchecked?)", lambda: P.find({"p": "x"}, projection={"z": {"$function": JS}}))
t("delete_many empty", lambda: P.delete_many({}))
t("delete_many p ne", lambda: P.delete_many({"p": {"$ne": "zz"}}))
t("delete_many p regex", lambda: P.delete_many({"p": {"$regex": ".*"}}))
t("delete_many p in []", lambda: P.delete_many({"p": {"$in": []}}))
t("delete_many p exists", lambda: P.delete_many({"p": {"$exists": True}}))
t("delete_many p ''", lambda: P.delete_many({"p": ""}))
t("delete_many k null", lambda: P.delete_many({"k": None}))
t("delete_many p list nested", lambda: P.delete_many({"p": [{"$ne": 1}]}))
t("delete_many p+or-all", lambda: P.delete_many({"p": "a", "$or": [{}]}))
t("delete_many p valid", lambda: P.delete_many({"p": "a"}))
t("delete_many p in valid", lambda: P.delete_many({"p": {"$in": ["a", "b"]}}))
t("delete_many p in + extra op", lambda: P.delete_many({"p": {"$in": ["a"], "$ne": "x"}}))
t("update pipeline merge", lambda: P.update_one({"_id": "x"}, [{"$merge": {"into": {"db": "other", "coll": "c"}}}]))
t("update pipeline set", lambda: P.update_one({"_id": "x"}, [{"$set": {"a": 1}}]))
t("update $unset", lambda: P.update_one({"_id": "x"}, {"$unset": {"a": 1}}))
t("update $rename", lambda: P.update_one({"_id": "x"}, {"$rename": {"a": "b"}}))
t("update generation", lambda: P.update_one({"_id": "x"}, {"$set": {"generation": 2}}))
t("update generation.x", lambda: P.update_one({"_id": "x"}, {"$inc": {"generation.x": 2}}))
t("update _id", lambda: P.update_one({"_id": "x"}, {"$setOnInsert": {"_id": "y"}}))
t("update $set non-dict", lambda: P.update_one({"_id": "x"}, {"$set": "abc"}))
t("replace empty filter", lambda: P.replace_one({}, {"a": 1}))
t("aggregate", lambda: P.aggregate([{"$out": "x"}]))
t("bulk_write", lambda: P.bulk_write([]))
t("coll dotted", lambda: s.collection("projects.x"))
t("coll fs.files", lambda: s.collection("fs.files"))
t("coll system.profile", lambda: s.collection("system.profile"))
t("coll $cmd", lambda: s.collection("$cmd"))
t("coll t_x without flag", lambda: s.collection("t_x"))
os.environ["AUTOTESTER_LIVE_MONGO_TEST"] = "1"
t("coll t_x with flag", lambda: type(s.collection("t_x")).__name__)
t("coll t_x\\n with flag", lambda: s.collection("t_x\n"))
t("coll T_X with flag", lambda: s.collection("T_X"))
t("coll t_ with flag", lambda: s.collection("t_"))
t("coll t_x.y with flag", lambda: s.collection("t_x.y"))
t("coll t_ 31 chars", lambda: s.collection("t_" + "a" * 31))
os.environ["ci"] = "1"
t("coll t_x with lowercase ci env", lambda: type(s.collection("t_x")).__name__)
del os.environ["ci"]
os.environ["CI"] = "true"
t("coll t_x with CI", lambda: s.collection("t_x"))
del os.environ["CI"]
del os.environ["AUTOTESTER_LIVE_MONGO_TEST"]

print("== marker")
s.collection("projects").insert_one({"_id": "a"})
print("marker doc:", srv.databases["autotester"]["server_state"].docs)
for label, fn in [
    ("insert marker", lambda: SS.insert_one({"_id": "marker"})),
    ("update marker", lambda: SS.update_one({"_id": "marker"}, {"$set": {"database": "x"}})),
    ("update marker upsert", lambda: SS.update_one({"_id": "marker"}, {"$set": {"database": "x"}}, upsert=True)),
    ("replace marker", lambda: SS.replace_one({"_id": "marker"}, {"database": "x"})),
    ("delete marker", lambda: SS.delete_one({"_id": "marker"})),
    ("delete ne", lambda: SS.delete_one({"_id": {"$ne": "z"}})),
    ("delete in", lambda: SS.delete_one({"_id": {"$in": ["marker"]}})),
    ("delete and", lambda: SS.delete_one({"$and": [{"_id": "marker"}]})),
    ("delete_many p", lambda: SS.delete_many({"p": "x"})),
    ("delete_many k", lambda: SS.delete_many({"k": "x"})),
    ("delete by database field", lambda: SS.delete_one({"database": "autotester"})),
    ("update by schema_version", lambda: SS.update_one({"schema_version": 1}, {"$set": {"database": "q"}})),
    ("replace other _id upsert w/ _id marker in replacement",
     lambda: SS.replace_one({"_id": "other"}, {"_id": "marker", "database": "evil"}, upsert=True)),
    ("delete Marker casing", lambda: SS.delete_one({"_id": "Marker"})),
    ("index on server_state", lambda: SS.create_index([("a", 1)])),
]:
    t(label, fn)
print("marker doc after:", srv.databases["autotester"]["server_state"].docs)
print("spy accessed:", set(cl.accessed), "dbs:", list(srv.databases))
