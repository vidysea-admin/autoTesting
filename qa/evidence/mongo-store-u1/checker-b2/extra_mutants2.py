"""Checker B cycle 2 extra mutants on the NEW code; 3 pytest calls (<=2 files each) per mutant on a scratch copy."""
import os, shutil, subprocess, sys, tempfile, pathlib, json

W = pathlib.Path("D:/autoTesting/.claude/worktrees/mongo-u1")
PY = "D:/autoTesting/.venv/Scripts/python"
G = "src/autotester/store/mongo_guard.py"
C = "src/autotester/schema/store_config.py"
EXC = '    except Exception:\n        pass\n    raise StoreConfigError('
MSG = '"the store connection string is not a valid mongodb:// URI"'
MUT = [
    ("srv scheme not rewritten", G, 'parse_uri("mongodb://" + rest, validate=False)', 'parse_uri(uri, validate=False)'),
    ("parse failure raised inside except", G, EXC, '    except Exception:\n        raise StoreConfigError(' + MSG + ')\n    raise StoreConfigError('),
    ("scheme gate removed", G, '("mongodb", "mongodb+srv").index(scheme)', '0'),
    ("projection unchecked", G, '_check_query([filter or {}, projection or {}])', '_check_query(filter or {})'),
    ("replacement body unchecked", G, '        _check_query(replacement)\n', ''),
    ("replacement _id rule removed", G, 'if "_id" in replacement and replacement["_id"] != filter.get("_id"):', 'if False:'),
    ("update value-shape rule removed", G, 'if not isinstance(fields, Mapping):', 'if False:'),
    ("CI check case-sensitive", G, 'k.upper() == "CI"', 'k == "CI"'),
    ("collection leaks driver in attribute", G, 'self._store, self._name = store, name\n', 'self._store, self._name = store, name\n        self.raw = raw\n'),
    ("ctor from None removed", G, 'raise StoreUnavailable(f"cannot open the state store ({type(exc).__name__})") from None', 'raise StoreUnavailable(f"cannot open the state store ({type(exc).__name__})")'),
    ("ctor echoes driver message", G, 'cannot open the state store ({type(exc).__name__})', 'cannot open the state store ({exc})'),
    ("first write skips marker", G, '        if not self._marked:\n            self.ensure_marker()', '        pass'),
    ("insert-only kind ignored", G, 'kind = InsertOnlyCollection if name in INSERT_ONLY else GuardedCollection', 'kind = GuardedCollection'),
    ("NoFile translation removed", G, '    except NoFile:\n        raise StoreNotFound("no such blob") from None\n', ''),
    ("partition -> rpartition", G, 'uri.partition("://")', 'uri.rpartition("://")'),
    ("clash uses startswith", G, '_uri_path_database(uri).casefold() == cfg.database.casefold()', '_uri_path_database(uri).casefold().startswith(cfg.database.casefold())'),
    ("clash exact case only", G, '_uri_path_database(uri).casefold() == cfg.database.casefold()', '_uri_path_database(uri) == cfg.database'),
    ("find drops projection+sort", G, 'for k, v in (("projection", projection), ("sort", sort), ("limit", limit))', 'for k, v in (("limit", limit),)'),
    ("tool level non-table accepted", C, 'table = table.get(key) if isinstance(table, dict) else None', 'table = table.get(key)'),
    ("delete_one skips before_write", G, '        self._store._before_write(self._name, filter, selects=True)\n        return bool(_translate(_REGISTRY[self].delete_one', '        return bool(_translate(_REGISTRY[self].delete_one'),
    ("update_one skips before_write", G, '        self._store._before_write(self._name, filter, selects=True)\n        result = _translate(_REGISTRY[self].update_one', '        result = _translate(_REGISTRY[self].update_one'),
    ("replace_one skips before_write", G, '        self._store._before_write(self._name, filter, selects=True)\n        result = _translate(_REGISTRY[self].replace_one', '        result = _translate(_REGISTRY[self].replace_one'),
    ("smoke regex unanchored", G, 'SMOKE_COLLECTION.fullmatch(name)', 'SMOKE_COLLECTION.match(name)'),
    ("bucket registry via attribute", G, '        self._store = store\n        _REGISTRY[self] = raw', '        self._store = store\n        self.raw = raw\n        _REGISTRY[self] = raw'),
]
GROUPS = [["tests/test_store_config.py", "tests/test_mongo_guard.py"],
          ["tests/test_mongo_guard_surface.py", "tests/test_mongo_guard_scan.py"],
          ["tests/test_mongo_guard_uri.py"]]
results = []
only = [int(a) for a in sys.argv[1:]]
if not only or only == [-1]:  # control: unmodified copy must be green, else every 'kill' is vacuous
    MUT.insert(0, ("CONTROL no-op", G, "from __future__ import annotations", "from __future__ import annotations"))
for i, (name, rel, old, new) in enumerate(MUT):
    if only and i not in only:
        continue
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="xmut2_"))
    for sub in ("src", "tests", "scripts", "qa/contracts"):
        shutil.copytree(W / sub, tmp / sub, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(W / "pyproject.toml", tmp / "pyproject.toml")
    f = tmp / rel
    text = f.read_bytes().decode("utf-8").replace("\r\n", "\n")
    if text.count(old) != 1:
        results.append((i, name, f"SPEC-ERR count={text.count(old)}"))
        print(results[-1], flush=True)
        shutil.rmtree(tmp, ignore_errors=True)
        continue
    f.write_bytes(text.replace(old, new).encode("utf-8"))
    env = dict(os.environ, PYTHONPATH=str(tmp / "src"))
    env.pop("AUTOTESTER_ROOT", None)
    red = []
    for grp in GROUPS:
        p = subprocess.run([PY, "-m", "pytest", *grp, "-o", "addopts=", "-q", "-x", "-rf", "-p", "no:cacheprovider"],
                           cwd=tmp, env=env, capture_output=True, text=True)
        red.append(p.returncode)
        fails = [l[:150] for l in p.stdout.splitlines() if l.startswith(('FAILED', 'ERROR'))]
        if p.returncode != 0:
            break
    results.append((i, name, "KILLED" if any(red) else "SURVIVED", (fails[:2] if any(red) else [])))
    print(results[-1], flush=True)
    shutil.rmtree(tmp, ignore_errors=True)
print(json.dumps(results))
