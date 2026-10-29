"""Checker B cycle 2: exhaustive attribute/method/dunder/closure walk for driver objects + operator/verb injection."""
import sys, types, inspect, weakref, warnings
warnings.simplefilter('ignore')
W = "D:/autoTesting/.claude/worktrees/mongo-u1"
sys.path[:0] = [W + "/src", W + "/tests"]
import autotester.store.mongo_guard as g
import fake_mongo as fm

def isdrv(o):
    m = type(o).__module__ or ""
    return m.startswith(("fake_mongo", "pymongo", "gridfs"))

srv = fm.FakeMongoServer(); cl = srv.client()
with fm.seams(client_factory=lambda u: cl): st = g.GuardedStore("mongodb://h/")
objs = {"store": st, "gcol": st.collection("projects"), "icol": st.collection("approvals"), "bucket": st.bucket()}
hits, seen = [], set()
def walk(o, path, depth=0):
    if id(o) in seen or depth > 6: return
    seen.add(id(o))
    if isinstance(o, weakref.WeakKeyDictionary): hits.append('REGISTRY via ' + path); return
    if isdrv(o): hits.append(path); return
    if isinstance(o, (str, bytes, int, float, bool, type(None))): return
    if isinstance(o, (list, tuple, set, frozenset)):
        for i, v in enumerate(o): walk(v, f"{path}[{i}]", depth + 1)
        return
    if isinstance(o, dict):
        for k, v in o.items(): walk(v, f"{path}[{k!r}]", depth + 1)
        return
    if isinstance(o, types.ModuleType): return
    if isinstance(o, types.CellType):
        try: walk(o.cell_contents, path + ".cell", depth + 1)
        except ValueError: pass
        return
    if inspect.isclass(o):
        for k, v in vars(o).items():
            if not isinstance(v, (types.FunctionType, staticmethod, classmethod, property, types.WrapperDescriptorType, types.MethodDescriptorType, types.GetSetDescriptorType)) or isinstance(v, property): walk(v, f"{path}.{k}", depth + 1)
        return
    if isinstance(o, (types.FunctionType, types.MethodType)):
        f = o.__func__ if isinstance(o, types.MethodType) else o
        walk(f.__closure__ or (), path + ".__closure__", depth + 1)
        walk(f.__defaults__ or (), path + ".__defaults__", depth + 1)
        walk(f.__kwdefaults__ or {}, path + ".__kwdefaults__", depth + 1)
        if isinstance(o, types.MethodType): walk(o.__self__, path + ".__self__", depth + 1)
        return
    for name in dir(o):
        try: v = getattr(o, name)
        except Exception: continue
        if name in ("__globals__", "__builtins__", "__dict__"): continue
        walk(v, f"{path}.{name}", depth + 1)
        if callable(v) and not inspect.isclass(v):
            try: sig = inspect.signature(v)
            except (ValueError, TypeError): continue
            if all(p.default is not p.empty or p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD) for p in sig.parameters.values()):
                if name in ("ensure_marker", "ping", "bucket", "collection_names", "__init_subclass__", "__class_getitem__"): 
                    if name not in ("ensure_marker", "ping", "bucket", "collection_names"): continue
                try: r = v()
                except BaseException as e: r = None
                walk(r, f"{path}.{name}()", depth + 1)
    if hasattr(o, "__dict__"): walk(vars(o), path + ".__dict__", depth + 1)
for n, o in objs.items(): walk(o, n)
print("driver/fake objects reached by attribute/zero-arg-call/closure/default walk:", hits)
srv = fm.FakeMongoServer(); cl = srv.client()
with fm.seams(client_factory=lambda u: cl): st = g.GuardedStore("mongodb://h/")
print("== operator injection")
col = st.collection("projects")
def t(label, fn):
    try: r = fn(); print("  ALLOWED ", label, "->", repr(r)[:50])
    except Exception as e: print("  refused ", label, type(e).__name__, str(e)[:60])
t("projection $function deep", lambda: col.find({}, projection={"a": {"$cond": [1, {"$function": {"body": "x"}}, 2]}}))
t("projection $where", lambda: col.find({}, projection={"$where": 1}))
t("sort dict $where", lambda: col.find({}, sort=[("a", 1)]))
t("find filter list-of-list function", lambda: col.find({"$or": [[{"$function": 1}]]}))
t("find_one $accumulator", lambda: col.find_one({"a": {"$accumulator": 1}}))
t("count $where in tuple", lambda: col.count_documents({"$and": ({"$where": "1"},)}))
t("update $set value nested $function", lambda: col.update_one({"_id": "a"}, {"$set": {"x": {"$function": 1}}}))
t("update $set ' _id'", lambda: col.update_one({"_id": "a"}, {"$set": {"_id": 1}}))
t("update $set int key", lambda: col.update_one({"_id": "a"}, {"$set": {1: 1}}))
t("update $inc generation.x", lambda: col.update_one({"_id": "a"}, {"$inc": {"generation.x": 1}}))
t("update $set '$[]'", lambda: col.update_one({"_id": "a"}, {"$set": {"a.$[]": 1}}))
t("update list pipeline", lambda: col.update_one({"_id": "a"}, [{"$set": {"a": 1}}]))
t("update empty mapping value", lambda: col.update_one({"_id": "a"}, {"$set": {}}))
print("== replace_one _id edges")
t("rep same _id", lambda: col.replace_one({"_id": "a"}, {"_id": "a", "x": 1}, upsert=True))
t("rep other _id", lambda: col.replace_one({"_id": "a"}, {"_id": "b"}, upsert=True))
t("rep _id with no filter _id", lambda: col.replace_one({"p": "a"}, {"_id": "b"}))
t("rep True vs 1", lambda: col.replace_one({"_id": 1}, {"_id": True}, upsert=True))
t("rep 1.0 vs 1", lambda: col.replace_one({"_id": 1}, {"_id": 1.0}))
t("rep nan", lambda: col.replace_one({"_id": float("nan")}, {"_id": float("nan")}))
t("rep dict _id op", lambda: col.replace_one({"_id": {"$in": ["a"]}}, {"_id": {"$in": ["a"]}}))
t("rep server_state same marker", lambda: st.collection("server_state").replace_one({"_id": "marker"}, {"_id": "marker"}))
t("rep server_state _id x", lambda: st.collection("server_state").replace_one({"_id": "x"}, {"_id": "x", "database": "evil"}, upsert=True))
t("rep server_state filter {_id:'x'} body 'database'", lambda: st.collection("server_state").update_one({"_id": "x"}, {"$set": {"database": "evil"}}, upsert=True))
t("rep list replacement", lambda: col.replace_one({"_id": "a"}, [{"a": 1, "b": 2}]))
print("marker after:", srv.databases["autotester"]["server_state"].docs)
