"""mongo-store U7 (M19, M20, M53): the path-level coordination verbs, one contract per backend.

`store/filestore_paths.py` hosts what `filestore` (at its line cap) cannot: exclusive create,
compare-and-set, raw reads, rename, delete-tree. The local-scratch fences are in
`test_scratch_fences_u7.py`. Every state verb is
run on the real file backend, the in-memory double and `MongoBackend` over the hand-written fake.
Races use 16 threads released together, so a second winner would show.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Callable
from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict
from state_backends import BACKEND_FACTORIES

import autotester.store.filestore as filestore
from autotester.core.safe_names import UnsafeName
from autotester.store.filestore import exists_path, list_children, read_json, write_text
from autotester.store.filestore_paths import (
    create_exclusive_path,
    delete_tree,
    digest_path,
    is_dir_path,
    put_if_path,
    read_bytes_path,
    read_text_path,
    remove_empty_dir,
    remove_stray_temps,
    rename_path,
    touch_path,
)
from autotester.store.mongo_routes import text_sha


@pytest.fixture(params=["file", "memory", "mongo"])
def root(request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    base = tmp_path / "root"
    base.mkdir()
    monkeypatch.setenv("AUTOTESTER_ROOT", str(base))
    for name in ("AUTOTESTER_STORE", "AUTOTESTER_STORE_AREAS"):
        monkeypatch.delenv(name, raising=False)
    if request.param != "file":
        backend = BACKEND_FACTORIES[request.param](base)
        monkeypatch.setattr(filestore, "_backend", lambda name: backend)
    return base


def _race(count: int, job: Callable[[int], bool]) -> int:
    """How many of `count` threads, released at the same instant, got True from `job`."""
    gate, wins = threading.Barrier(count), []

    def run(number: int) -> None:
        gate.wait()
        wins.append(job(number))

    threads = [threading.Thread(target=run, args=(n,)) for n in range(count)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    return sum(wins)


def test_create_exclusive_has_one_winner_and_keeps_the_winners_text(root: Path) -> None:
    path = root / "projects" / "p" / "claim.json"
    assert create_exclusive_path(path, "first") is True
    assert create_exclusive_path(path, "second") is False
    assert read_text_path(path) == "first"


def test_sixteen_racers_for_one_exclusive_create_yield_exactly_one_winner(root: Path) -> None:
    for attempt in range(25):
        path = root / "projects" / "p" / f"race-{attempt}.json"
        assert _race(16, lambda n, p=path: create_exclusive_path(p, f"racer-{n}")) == 1
        assert (read_text_path(path) or "").startswith("racer-")


def test_an_exclusive_create_never_shows_a_reader_a_half_written_file(root: Path) -> None:
    """A 6 MB body takes milliseconds to write, so an in-place create (O_EXCL, then write) is
    seen empty or partial by at least one of three readers that never stop reading."""
    path = root / "projects" / "p" / "big.json"
    body = "x" * 6_000_000
    seen: list[str | None] = []
    errors: list[BaseException] = []
    stop, started = threading.Event(), threading.Barrier(4)

    def reader() -> None:
        started.wait()
        while not stop.is_set():
            try:
                seen.append(read_text_path(path))
            except OSError as exc:
                errors.append(exc)

    threads = [threading.Thread(target=reader) for _ in range(3)]
    [t.start() for t in threads]
    started.wait()
    assert create_exclusive_path(path, body) is True
    stop.set()
    [t.join() for t in threads]
    assert not errors
    assert all(text in (None, body) for text in seen)
    assert read_text_path(path) == body


class _MidWriteReader:
    """Wraps a write handle: after half of the text is written it reads the claim's path, as a
    reader arriving at that instant would, and records what it saw."""

    def __init__(self, handle, probe: Callable[[], None]) -> None:
        self._handle, self._probe = handle, probe

    def __enter__(self) -> _MidWriteReader:
        self._handle.__enter__()
        return self

    def __exit__(self, *exc: object) -> object:
        return self._handle.__exit__(*exc)

    def write(self, text: str) -> int:
        half = len(text) // 2
        self._handle.write(text[:half])
        self._handle.flush()
        self._probe()
        return self._handle.write(text[half:])


def test_an_exclusive_create_is_invisible_to_a_reader_until_the_whole_text_is_written(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Deterministic: a reader arriving half way through the write sees no file (never a partial
    one). A create written in place (O_EXCL, then write) shows the first half and fails here."""
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    for name in ("AUTOTESTER_STORE", "AUTOTESTER_STORE_AREAS"):
        monkeypatch.delenv(name, raising=False)
    path, body, seen = tmp_path / "projects" / "p" / "mid.json", "y" * 4000, []
    real = os.fdopen

    def spy(fd: int, mode: str = "r", *args: object, **kwargs: object) -> object:
        handle = real(fd, mode, *args, **kwargs)
        if "w" not in mode:
            return handle
        return _MidWriteReader(handle, lambda: seen.append(read_text_path(path)))

    with monkeypatch.context() as patched:
        patched.setattr(os, "fdopen", spy)
        assert create_exclusive_path(path, body) is True
    assert seen, "the spy never ran: the create no longer writes through os.fdopen"
    assert all(text in (None, body) for text in seen)
    assert read_text_path(path) == body


def test_put_if_a_stale_digest_writes_nothing_and_the_current_one_lands(root: Path) -> None:
    path = root / "projects" / "p" / "cas.json"
    assert put_if_path(path, "v1", None) is True
    assert put_if_path(path, "again", None) is False  # None means "must not exist"
    assert put_if_path(path, "v2", text_sha("stale")) is False
    assert read_text_path(path) == "v1"
    assert digest_path(path) == text_sha("v1")
    assert put_if_path(path, "v2", digest_path(path)) is True
    assert read_text_path(path) == "v2"


def test_sixteen_racers_with_the_same_digest_yield_exactly_one_compare_and_set(root: Path) -> None:
    for attempt in range(25):
        path = root / "projects" / "p" / f"cas-{attempt}.json"
        write_text(path, "base")
        assert _race(16, lambda n, p=path: put_if_path(p, f"w-{n}", text_sha("base"))) == 1


def test_digest_and_reads_are_none_for_a_missing_key(root: Path) -> None:
    path = root / "projects" / "p" / "missing.json"
    assert digest_path(path) is None and read_text_path(path) is None
    assert read_bytes_path(path) is None


def test_read_bytes_returns_exactly_what_was_written(root: Path) -> None:
    path = root / "projects" / "p" / "b.json"
    filestore.write_bytes(path, "héllo\n".encode())
    assert read_bytes_path(path) == "héllo\n".encode()


def test_rename_moves_the_content_and_removes_the_source(root: Path) -> None:
    src, dst = root / "projects" / "p" / "a.json", root / "projects" / "p" / "sub" / "b.json"
    write_text(src, "payload")
    rename_path(src, dst)
    assert read_text_path(dst) == "payload" and not exists_path(src)
    with pytest.raises(FileNotFoundError):
        rename_path(src, dst)


def test_delete_tree_removes_everything_below_and_the_directory_itself(root: Path) -> None:
    base = root / "projects" / "p" / "stage"
    for name in ("0", "manifest.json", "deep/1"):
        write_text(base / name, "x")
    write_text(root / "projects" / "p" / "staged.json", "keep")  # a sibling, not below
    assert delete_tree(base) == 3
    assert not exists_path(base) and not is_dir_path(base)
    assert read_text_path(root / "projects" / "p" / "staged.json") == "keep"
    assert delete_tree(base) == 0


def test_delete_tree_refuses_the_whole_store(root: Path) -> None:
    write_text(root / "projects" / "p" / "a.json", "x")
    with pytest.raises(UnsafeName):
        delete_tree(root)
    assert read_text_path(root / "projects" / "p" / "a.json") == "x"


def test_touch_refreshes_the_mtime_and_a_missing_key_raises(root: Path) -> None:
    path = root / "projects" / "p" / "lock"
    with pytest.raises(FileNotFoundError):
        touch_path(path)
    assert create_exclusive_path(path, "") is True
    before = filestore.mtime_path(path)
    assert before is not None
    touch_path(path)
    after = filestore.mtime_path(path)
    assert after is not None and after >= before and read_text_path(path) == ""


def test_stray_temps_and_empty_directories_are_a_file_backend_concern_only(root: Path) -> None:
    on_files = isinstance(filestore._backend("file"), filestore.FileBackend)
    folder = root / "projects" / "p" / "src1"
    write_text(folder / "keep.txt", "x")
    folder.mkdir(parents=True, exist_ok=True)
    stray = folder / ".tmp-leftover"
    stray.write_text("junk", encoding="utf-8")
    assert remove_stray_temps(folder) == (1 if on_files else 0)
    assert stray.exists() is (not on_files)
    remove_empty_dir(folder)  # holds keep.txt (or is not a file backend): left alone
    assert read_text_path(folder / "keep.txt") == "x"
    empty = root / "projects" / "p" / "empty"
    empty.mkdir(parents=True)
    remove_empty_dir(empty)
    assert empty.exists() is (not on_files)


def test_list_children_still_sees_a_created_key(root: Path) -> None:
    create_exclusive_path(root / "projects" / "p" / "d" / "k.claim", "{}")
    assert list_children(root / "projects" / "p" / "d") == ["k.claim"]
    assert read_json(root / "projects" / "p" / "d" / "k.claim", _Any) is not None


class _Any(BaseModel):
    model_config = ConfigDict(extra="allow")
