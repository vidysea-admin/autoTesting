"""Checker B extra mutants: run the 4 U1 test files (two calls of two files) on a scratch copy."""
import os, shutil, subprocess, sys, tempfile, pathlib, json

W = pathlib.Path("D:/autoTesting/.claude/worktrees/mongo-u1")
PY = "D:/autoTesting/.venv/Scripts/python"
G = "src/autotester/store/mongo_guard.py"
C = "src/autotester/schema/store_config.py"
D = "src/autotester/browser/db.py"
MUT = [
    ("accumulator removed from forbidden", G, '"$where", "$function", "$accumulator"', '"$where", "$function"'),
    ("function removed from forbidden", G, '"$where", "$function", "$accumulator"', '"$where", "$accumulator"'),
    ("_check_query ignores tuples", G, "isinstance(value, list | tuple)", "isinstance(value, list)"),
    ("_scoped: accept any non-empty value", G, "if value and all(isinstance(v, str) and v for v in listed):", "if value:"),
    ("delete_many skips _scoped", G, "        _scoped(filter)\n", "        pass\n"),
    ("marker: selects branch removed", G, "ident == MARKER_ID or (selects and not isinstance(ident, str))", "ident == MARKER_ID"),
    ("marker: id check removed", G, "ident == MARKER_ID or (selects and", "False or (selects and"),
    ("smoke ignores CI", G, ' and "CI" not in os.environ', ""),
    ("smoke ignores flag", G, 'os.environ.get("AUTOTESTER_LIVE_MONGO_TEST") == "1" and ', ""),
    ("smoke regex unanchored (match)", G, "SMOKE_COLLECTION.fullmatch(name)", "SMOKE_COLLECTION.match(name)"),
    ("generation not immutable", G, 'frozenset({"_id", "generation"})', 'frozenset({"_id"})'),
    ("dotted immutable split removed", G, 'str(name).split(".")[0] in IMMUTABLE_FIELDS', "str(name) in IMMUTABLE_FIELDS"),
    ("$unset allowed", G, 'frozenset({"$set", "$setOnInsert", "$inc"})', 'frozenset({"$set", "$setOnInsert", "$inc", "$unset"})'),
    ("approvals not insert-only", G, '"approvals", "approval_revocations", "bug_events", "delivery_records"}) \nUPDATE', 'X'),
    ("bug_events not insert-only", G, '"approval_revocations", "bug_events", "delivery_records"})', '"approval_revocations", "delivery_records"})'),
    ("delivery_records not insert-only", G, '"bug_events", "delivery_records"})', '"bug_events"})'),
    ("marker casefold dropped", G, 'str(marker.get("database", "")).casefold() != self._cfg.database.casefold()', 'str(marker.get("database", "")) != self._cfg.database'),
    ("clash casefold dropped", G, "_uri_path_database(uri).casefold() == cfg.database.casefold()", "_uri_path_database(uri) == cfg.database"),
    ("unmarked-nonempty check removed", G, "elif _translate(handle.list_collection_names):", "elif False:"),
    ("marker ensure skipped on bucket", G, '        self._store._before_write("fs", {})\n        return _translate(_REGISTRY[self].upload_from_stream', '        return _translate(_REGISTRY[self].upload_from_stream'),
    ("bucket delete skips marker", G, '        self._store._before_write("fs", {})\n        _translate(_REGISTRY[self].delete', '        _translate(_REGISTRY[self].delete'),
    ("create_index skips marker", G, '        self._store._before_write(self._name, {})\n        extra', '        extra'),
    ("insert_one skips before_write", G, "        self._store._before_write(self._name, document)\n", ""),
    ("scheme check removed", G, 'if parts.scheme not in ("mongodb", "mongodb+srv"):', "if False:"),
    ("bucket name fixed->param", G, 'BUCKET_NAME = "blobs"', 'BUCKET_NAME = "fs"'),
    ("db name from lower-case cfg", G, "[cfg.database]", "[cfg.database.lower()]"),
    ("pattern ignorecase-less length", C, "{0,37}", "{0,300}"),
    ("pattern fullmatch -> match", C, "DATABASE_PATTERN.fullmatch(value) is None", "DATABASE_PATTERN.match(value) is None"),
    ("forbidden casefold removed", C, "value.casefold() in FORBIDDEN_DATABASES", "value in FORBIDDEN_DATABASES"),
    ("frozen removed", C, 'ConfigDict(extra="forbid", frozen=True)', 'ConfigDict(extra="forbid")'),
    ("cache removed", C, "@functools.cache\n", ""),
    ("table type check removed", C, "if not isinstance(table, dict):", "if table is None:"),
    ("M10 casefold dropped", D, "db_name.casefold() == load_store_config().database.casefold()", "db_name == load_store_config().database"),
    ("M10 after client", D, 'if db_name.casefold() == load_store_config().database.casefold():\n        raise ValueError("the AutoTester store database cannot be the target of a DB assertion")\n    from pymongo import MongoClient\n\n    client: Any = MongoClient(uri)', 'from pymongo import MongoClient\n\n    client: Any = MongoClient(uri)\n    if db_name.casefold() == load_store_config().database.casefold():\n        raise ValueError("x")'),
]
GROUPS = [["tests/test_store_config.py", "tests/test_mongo_guard.py"],
          ["tests/test_mongo_guard_surface.py", "tests/test_mongo_guard_scan.py"]]
results = []
only = sys.argv[1:] and [int(a) for a in sys.argv[1:]]
for i, (name, rel, old, new) in enumerate(MUT):
    if only and i not in only:
        continue
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="xmut_"))
    for sub in ("src", "tests", "qa/contracts"):
        shutil.copytree(W / sub, tmp / sub, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(W / "pyproject.toml", tmp / "pyproject.toml")
    f = tmp / rel
    text = f.read_bytes().decode("utf-8").replace("\r\n", "\n")
    if text.count(old) != 1:
        results.append((i, name, f"SPEC-ERR count={text.count(old)}"))
        shutil.rmtree(tmp, ignore_errors=True)
        continue
    f.write_bytes(text.replace(old, new).encode("utf-8"))
    env = dict(os.environ, PYTHONPATH=str(tmp / "src"), AUTOTESTER_ROOT="")
    env.pop("AUTOTESTER_ROOT")
    red = []
    for grp in GROUPS:
        p = subprocess.run([PY, "-m", "pytest", *grp, "-o", "addopts=", "-q", "-x", "-p", "no:cacheprovider"],
                           cwd=tmp, env=env, capture_output=True, text=True)
        red.append(p.returncode)
        if p.returncode != 0:
            break
    results.append((i, name, "KILLED" if any(red) else "SURVIVED"))
    print(results[-1], flush=True)
    shutil.rmtree(tmp, ignore_errors=True)
print(json.dumps(results, indent=0))
