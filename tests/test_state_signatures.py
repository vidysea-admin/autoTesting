"""mongo-store M14: the public store surface is unchanged, so its importers do not change.

`tests/state_signatures.json` is a frozen snapshot of every public `filestore` function and of the
public methods of `ProjectStore`, `CrawlStoreMixin` and `RunStoreMixin`, taken from commit
`4de46d52` (the contract's baseline; `filestore` from `git show`, the classes were untouched
since). A signature drift fails here. The second test is the importer side: every name any file in
`src/`, `scripts/` or `tests/` imports from `filestore` still exists.
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
from typing import Any

import pytest

import autotester.store as store_package
import autotester.store.filestore as filestore
from autotester.core.paths import code_root
from autotester.store.crawl_store import CrawlStoreMixin
from autotester.store.project_store import ProjectStore
from autotester.store.run_store import RunStoreMixin

SNAPSHOT: dict[str, Any] = json.loads(
    (Path(__file__).parent / "state_signatures.json").read_text(encoding="utf-8"))
CLASSES = {"ProjectStore": ProjectStore, "CrawlStoreMixin": CrawlStoreMixin,
           "RunStoreMixin": RunStoreMixin}


@pytest.mark.parametrize("name", sorted(SNAPSHOT["filestore"]))
def test_every_filestore_function_keeps_its_signature(name: str) -> None:
    assert str(inspect.signature(getattr(filestore, name))) == SNAPSHOT["filestore"][name]


@pytest.mark.parametrize("class_name", sorted(CLASSES))
def test_the_store_classes_keep_every_public_method_and_signature(class_name: str) -> None:
    cls = CLASSES[class_name]
    for method, signature in SNAPSHOT[class_name].items():
        assert str(inspect.signature(getattr(cls, method))) == signature, f"{class_name}.{method}"
    assert "__init__" not in vars(cls) or (
        str(inspect.signature(cls.__init__)) == SNAPSHOT[f"{class_name}__init__"])


def test_the_package_exports_are_unchanged() -> None:
    assert sorted(store_package.__all__) == [
        "ProjectStore", "append_jsonl", "read_json", "read_jsonl", "upsert_jsonl", "write_json"]


def _imported_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "autotester.store.filestore":
            names |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module == "autotester.store":
            names |= {a.name for a in node.names if a.name == "filestore"}
    return names


def test_every_name_the_importers_use_still_exists() -> None:
    root, users = code_root(), {}
    for folder in ("src", "scripts", "tests"):
        for path in (root / folder).rglob("*.py"):
            names = _imported_names(ast.parse(path.read_text(encoding="utf-8-sig")))
            if names:
                users[path.relative_to(root).as_posix()] = names
    assert len(users) >= 25, "the scan found too few importers to mean anything"
    missing = {f: sorted(n for n in names if n != "filestore" and not hasattr(filestore, n))
               for f, names in users.items()}
    assert {f: n for f, n in missing.items() if n} == {}
