"""TF7 (team-foundation.md): the team store and path helpers are portable and safe.

Hostile names are refused before any IO; a writer killed mid-write leaves the old content; the
new modules import nothing POSIX-only; the team data root is ignored by git and docker.
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict

from autotester.core import paths, safe_names
from autotester.core.safe_names import UnsafeName
from autotester.store import team_store

REPO = Path(__file__).resolve().parents[1]
NEW_MODULES = ("core/safe_names.py", "store/team_store.py")
FORBIDDEN = {"fcntl", "pwd", "grp", "resource"}
HOSTILE = [
    "", ".", "..", "..\\x", "../x", "a/../../x", "a\\..\\..\\x", "C:\\x", "c:x", "/abs", "\\abs",
    "CON", "nul", "Aux.txt", "com1", "LPT9.log", "trailing.", "trailing ", "x" * 121,
    "has\x00nul", "has\nnewline",
]


LEGAL_ENCODED = {"c:x", "trailing "}


class Note(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str


@pytest.mark.parametrize("name", HOSTILE)
def test_hostile_names_are_refused_everywhere(name: str, tmp_path: Path) -> None:
    sentinel = tmp_path / "outside.txt"
    sentinel.write_text("keep", encoding="utf-8")
    root = tmp_path / "root"
    with pytest.raises(UnsafeName):
        safe_names.safe_name(name)
    with pytest.raises(UnsafeName):
        paths.team_path(name, root=root)
    with pytest.raises(UnsafeName):
        team_store.write_model(root, Note(text="x"), name, "x.json")
    with pytest.raises(UnsafeName):
        team_store.create_marker(root, name, "m")
    assert sentinel.read_text(encoding="utf-8") == "keep"
    assert not root.exists()  # refused before any directory was made


@pytest.mark.parametrize("key", [n for n in HOSTILE if n not in LEGAL_ENCODED])
def test_hostile_slot_keys_are_refused(key: str) -> None:
    """`c:x` and a trailing space are legal slot keys: encoding turns `:` and ` ` into
    `%3A` and `%20`, so neither can read as a drive letter or a trailing space."""
    with pytest.raises(UnsafeName):
        safe_names.encode_slot_key(key)


def test_a_real_slot_key_encodes_to_a_path_safe_name() -> None:
    key = "a:fixed:2026-10-11T09:30Z"  # one-letter project: a raw drive-letter shape
    name = safe_names.encode_slot_key(key)
    assert name == "a%3Afixed%3A2026-10-11T09%3A30Z"
    assert ":" not in name and "/" not in name and "\\" not in name


@pytest.mark.parametrize("slug", ["demo", "pathlynks", "a", "a-b-c1"])
def test_good_slugs_pass_and_bad_ones_do_not(slug: str) -> None:
    assert safe_names.safe_slug(slug) == slug
    for bad in ("Demo", "1demo", "de mo", "con", "nul", "a.b", "-x", "x" * 121):
        with pytest.raises(UnsafeName):
            safe_names.safe_slug(bad)


def test_write_then_read_round_trips_under_the_team_root(tmp_path: Path) -> None:
    where = team_store.write_model(tmp_path, Note(text="hello"), "prefs", "u1.json")
    assert where == tmp_path / ".work" / "team" / "prefs" / "u1.json"
    assert team_store.read_model(tmp_path, Note, "prefs", "u1.json") == Note(text="hello")
    assert team_store.read_model(tmp_path, Note, "prefs", "absent.json") is None


def test_writer_killed_mid_write_keeps_the_old_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    where = team_store.write_model(tmp_path, Note(text="old"), "prefs", "u1.json")

    def die(*_a: object, **_k: object) -> None:
        raise KeyboardInterrupt("killed between temp write and replace")

    monkeypatch.setattr("os.replace", die)
    with pytest.raises(KeyboardInterrupt):
        team_store.write_model(tmp_path, Note(text="new"), "prefs", "u1.json")
    monkeypatch.undo()
    assert team_store.read_model(tmp_path, Note, "prefs", "u1.json") == Note(text="old")
    assert [p.name for p in where.parent.iterdir()] == ["u1.json"]  # no temp litter


def test_marker_is_created_once_and_only_once(tmp_path: Path) -> None:
    assert team_store.create_marker(tmp_path, "markers", "slot-1", body="first") is True
    assert team_store.create_marker(tmp_path, "markers", "slot-1", body="second") is False
    marker = paths.team_path("markers", "slot-1", root=tmp_path)
    assert marker.read_text(encoding="utf-8") == "first"


def test_new_modules_import_nothing_posix_only_and_never_fork() -> None:
    for rel in NEW_MODULES:
        tree = ast.parse((REPO / "src" / "autotester" / rel).read_text(encoding="utf-8"))
        imported = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import)
                    for a in n.names}
        imported |= {n.module.split(".")[0] for n in ast.walk(tree)
                     if isinstance(n, ast.ImportFrom) and n.module}
        assert not imported & FORBIDDEN, rel
        calls = {f"{n.func.value.id}.{n.func.attr}" for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and isinstance(n.func.value, ast.Name)}
        assert "os.fork" not in calls, rel


def test_team_data_root_is_ignored_by_git_and_docker() -> None:
    probe = paths.team_path("prefs", "u1.json", root=REPO).relative_to(REPO).as_posix()
    found = subprocess.run(["git", "check-ignore", "-q", probe], cwd=REPO, check=False)
    assert found.returncode == 0, f"{probe} is not covered by .gitignore"
    docker = (REPO / ".dockerignore").read_text(encoding="utf-8").splitlines()
    assert ".work/" in [line.strip() for line in docker]
