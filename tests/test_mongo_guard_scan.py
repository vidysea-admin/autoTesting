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
DRIVER_ROOTS = {"pymongo", "gridfs"}
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
            if name in {"import_module", "__import__"} and isinstance(first, ast.Constant) \
                    and str(first.value).split(".")[0] in DRIVER_ROOTS:
                reasons.append("dynamic driver import")
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
    assert set(scan(code_root())) == ALLOWED


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
], ids=["from-import", "attr-ctor", "gridfs", "dunder-import", "import_module", "get_database",
        "list_database_names", "drop_database", "get_default_database", "subscript"])
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
