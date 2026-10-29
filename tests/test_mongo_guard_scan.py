"""mongo-store M3, M10: one door found by AST scan, and the read side.

M3 is a static fence: a `MongoClient` anywhere else under `src/` or `scripts/` turns this red.
The scanner is itself sabotaged below (a third file with each pattern must be flagged), so a scan
that quietly matches nothing cannot pass.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, ClassVar

import pytest

from autotester.browser.db import connect_read_only
from autotester.core.paths import code_root

ALLOWED = {"src/autotester/browser/db.py", "src/autotester/store/mongo_guard.py"}
DRIVER_ROOTS = {"pymongo", "gridfs", "motor", "mongoengine", "beanie", "umongo"}
# Resolves schema classes by dotted path; a literal driver import there is still flagged.
NON_LITERAL = "import of a non-literal module name"
NON_LITERAL_OK = {"src/autotester/providers/isolated.py"}
MONGO_CLIS = {"mongosh", "mongo", "mongodump", "mongoexport", "mongoimport", "mongorestore"}
LAUNCHERS = {"run", "Popen", "call", "check_call", "check_output", "system", "popen", "spawn",
             "execv", "execvp", "startfile"}
DOOR_ATTRS = {"get_database", "get_default_database", "list_database_names", "drop_database"}


def _reasons(tree: ast.AST) -> list[str]:
    reasons: list[str] = []
    bound: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import | ast.ImportFrom):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [
                node.module or ""]
            reasons += [f"import {n}" for n in names if n.split(".")[0] in DRIVER_ROOTS]
        elif isinstance(node, ast.Call):
            callee = node.func
            name = callee.id if isinstance(callee, ast.Name) else getattr(callee, "attr", "")
            if name == "MongoClient":
                reasons.append("MongoClient(")
            first = node.args[0] if node.args else None
            if name in {"import_module", "__import__"}:
                if not isinstance(first, ast.Constant):
                    reasons.append(NON_LITERAL)
                elif str(first.value).split(".")[0] in DRIVER_ROOTS:
                    reasons.append("dynamic driver import")
            if name == "getattr" and any(isinstance(a, ast.Constant) and a.value in {
                    "import_module", "__import__"} for a in node.args[1:2]):
                reasons.append("getattr import")
            if name in {"exec", "eval"}:
                reasons.append(name)
            if name in LAUNCHERS and any(
                    isinstance(n, ast.Constant) and str(n.value).lower().removesuffix(".exe")
                    in MONGO_CLIS for a in node.args for n in ast.walk(a)):
                reasons.append("mongo command line tool")
        if isinstance(node, ast.Attribute | ast.Name):
            ident = node.attr if isinstance(node, ast.Attribute) else node.id
            if ident in DOOR_ATTRS:
                reasons.append(ident)
        if isinstance(node, ast.Assign | ast.AnnAssign) and isinstance(node.value, ast.Call):
            callee = node.value.func
            if getattr(callee, "id", getattr(callee, "attr", "")) == "MongoClient":
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                bound |= {t.id for t in targets if isinstance(t, ast.Name)}
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) \
                and node.value.id in bound:
            reasons.append(f"subscript on client {node.value.id}")
    return reasons


def scan(root: Path, folders: tuple[str, ...] = ("src", "scripts")) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for folder in folders:
        for path in sorted((root / folder).rglob("*.py")):
            reasons = _reasons(ast.parse(path.read_text(encoding="utf-8")))
            if reasons:
                found[path.relative_to(root).as_posix()] = reasons
    return found


def test_exactly_two_files_touch_the_driver_and_they_are_the_allowed_two() -> None:
    found = scan(code_root())
    for name in NON_LITERAL_OK:
        found[name] = [r for r in found.get(name, []) if r != NON_LITERAL]
    assert {name for name, reasons in found.items() if reasons} == ALLOWED


@pytest.mark.parametrize("snippet", [
    "from pymongo import MongoClient\nMongoClient('mongodb://h')\n",
    "import pymongo\nc = pymongo.MongoClient('mongodb://h')\n",
    "import gridfs\n",
    "x = __import__('pymongo')\n",
    "import importlib\nimportlib.import_module('gridfs.errors')\n",
    "def f(c):\n    return c.get_database('x')\n",
    "def f(c):\n    return c.list_database_names()\n",
    "def f(c):\n    c.drop_database('x')\n",
    "def f(c):\n    return c.get_default_database()\n",
    "client = MongoClient('mongodb://h')\nrows = client['other']\n",
    "import motor.motor_asyncio\n",
    "import mongoengine\n",
    "import importlib\nimportlib.import_module('py' + 'mongo')\n",
    "import importlib\nname = 'pymongo'\nimportlib.import_module(name)\n",
    "import importlib\ngetattr(importlib, 'import_module')('pymongo')\n",
    "exec('import pymongo')\n",
    "eval(code)\n",
    "import subprocess\nsubprocess.run(['mongosh', '--eval', 'x'])\n",
    "import os\nos.system('x')\nos.popen(['mongodump.exe'])\n",
], ids=["from-import", "attr-ctor", "gridfs", "dunder-import", "import_module", "get_database",
        "list_database_names", "drop_database", "get_default_database", "subscript", "motor",
        "mongoengine", "concat-import", "variable-import", "getattr-import", "exec", "eval",
        "subprocess-mongosh", "popen-mongodump"])
def test_the_scan_flags_a_third_file_with_each_pattern(tmp_path: Path, snippet: str) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "src" / "rogue.py").write_text(snippet, encoding="utf-8")
    assert set(scan(tmp_path)) == {"src/rogue.py"}
    (tmp_path / "src" / "rogue.py").unlink()
    (tmp_path / "scripts" / "rogue.py").write_text(snippet, encoding="utf-8")
    assert set(scan(tmp_path)) == {"scripts/rogue.py"}


def test_the_scan_leaves_innocent_code_alone(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "fine.py").write_text("from pathlib import Path\nx = {}['a']\n",
                                              encoding="utf-8")
    assert scan(tmp_path, ("src",)) == {}


INJECTION = {"config_path", "client_factory", "bucket_factory"}
SEAM_HOME = "src/autotester/store/mongo_guard.py"


def _injections(tree: ast.AST) -> list[str]:
    """Calls that hand the fence a config path or a factory, and any touch of its private seam."""
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            callee = node.func
            name = callee.id if isinstance(callee, ast.Name) else getattr(callee, "attr", "")
            if name == "GuardedStore":
                keys = {k.arg for k in node.keywords}
                if keys & INJECTION or None in keys or len(node.args) > 1 or any(
                        isinstance(a, ast.Starred) for a in node.args):
                    found.append("GuardedStore(...) with an injected argument")
        ident = node.id if isinstance(node, ast.Name) else getattr(node, "attr", "")
        if ident == "_SEAM" or (isinstance(node, ast.alias) and node.name == "_SEAM"):
            found.append("_SEAM")
    return found


def _injection_scan(root: Path) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for folder in ("src", "scripts"):
        for path in sorted((root / folder).rglob("*.py")):
            rel = path.relative_to(root).as_posix()
            found = _injections(ast.parse(path.read_text(encoding="utf-8")))
            if found and rel != SEAM_HOME:
                hits[rel] = found
    return hits


def test_no_src_or_scripts_call_injects_a_config_path_or_factory_into_the_fence() -> None:
    assert _injection_scan(code_root()) == {}


NL = chr(10)
IMPORT = "from autotester.store.mongo_guard import GuardedStore"
AS_G = "import autotester.store.mongo_guard as g"


@pytest.mark.parametrize("snippet", [
    IMPORT + NL + "GuardedStore(u, config_path=p)" + NL,
    AS_G + NL + "g.GuardedStore(u, client_factory=f)" + NL,
    "GuardedStore(u, bucket_factory=f)" + NL,
    "GuardedStore(u, **kw)" + NL,
    "GuardedStore(u, other)" + NL,
    "GuardedStore(*args)" + NL,
    AS_G + NL + "g._SEAM['config_path'] = p" + NL,
    "from autotester.store.mongo_guard import _SEAM" + NL,
], ids=["config_path", "attr-client_factory", "bucket_factory", "kwargs", "positional-2nd",
        "starred", "seam-write", "seam-import"])
def test_the_injection_scan_flags_each_way_in(tmp_path: Path, snippet: str) -> None:
    for folder in ("src", "scripts"):
        (tmp_path / folder).mkdir(exist_ok=True)
    (tmp_path / "src" / "rogue.py").write_text(snippet, encoding="utf-8")
    assert set(_injection_scan(tmp_path)) == {"src/rogue.py"}
    (tmp_path / "src" / "rogue.py").unlink()
    (tmp_path / "scripts" / "rogue.py").write_text(snippet, encoding="utf-8")
    assert set(_injection_scan(tmp_path)) == {"scripts/rogue.py"}


def test_the_injection_scan_leaves_a_plain_construction_alone(tmp_path: Path) -> None:
    for folder in ("src", "scripts"):
        (tmp_path / folder).mkdir()
    (tmp_path / "src" / "fine.py").write_text("GuardedStore(uri)" + NL, encoding="utf-8")
    assert _injection_scan(tmp_path) == {}


class _SpyClient:
    constructed: ClassVar[list[str]] = []

    def __init__(self, uri: str) -> None:
        type(self).constructed.append(uri)

    def __getitem__(self, name: str) -> dict[str, Any]:
        return {"c": object()}


def test_the_read_side_refuses_the_store_database_before_creating_a_client(
        monkeypatch: pytest.MonkeyPatch) -> None:
    import pymongo

    _SpyClient.constructed = []
    monkeypatch.setattr(pymongo, "MongoClient", _SpyClient)
    for name in ("autotester", "Autotester", "AUTOTESTER"):
        with pytest.raises(ValueError):
            connect_read_only("mongodb://h/", name, "auth_users")
    assert _SpyClient.constructed == []
    assert connect_read_only("mongodb://h/", "pathlynks", "c") is not None
    assert _SpyClient.constructed == ["mongodb://h/"]
