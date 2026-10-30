"""mongo-store M15, M17, M19 (File, InMemory and Mongo legs): ONE contract, every backend.

Each test takes the `backend` fixture, which runs it once per entry of `BACKEND_FACTORIES`
(`tests/state_backends.py`): `file`, `memory` and `mongo` (over the hand-written fake). The
semantics asserted are the ones the stores rely on: ordered rows, upsert that keeps position,
`delete_row` returning a bool, `keys(prefix)` ordering, one winner for an exclusive create, a
compare-and-set loser that writes nothing, and keys that cannot escape.
"""

from __future__ import annotations

import json
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from state_backends import BACKEND_FACTORIES

from autotester.core.safe_names import UnsafeName
from autotester.store.mongo_routes import StateBackend, text_sha


@pytest.fixture(params=sorted(BACKEND_FACTORIES))
def backend(request: pytest.FixtureRequest, tmp_path: Path) -> StateBackend:
    return BACKEND_FACTORIES[request.param](tmp_path / "root")


def row(**fields: Any) -> str:
    return json.dumps(fields, sort_keys=True)


def test_put_get_replace_and_delete(backend: StateBackend) -> None:
    assert backend.get("a/b.json") is None and backend.exists("a/b.json") is False
    backend.put("a/b.json", "one")
    backend.put("a/b.json", "two")
    assert backend.get("a/b.json") == "two" and backend.exists("a/b.json") is True
    assert backend.delete("a/b.json") is True
    assert backend.delete("a/b.json") is False and backend.get("a/b.json") is None


def test_put_accepts_bytes_and_returns_the_text(backend: StateBackend) -> None:
    backend.put("a/blob.txt", "héllo".encode())
    assert backend.get("a/blob.txt") == "héllo"


def test_rows_are_ordered_and_a_missing_key_has_none(backend: StateBackend) -> None:
    assert backend.rows("t/rows.jsonl") == []
    for number in (3, 1, 2):
        backend.append_row("t/rows.jsonl", row(id=f"r{number}"))
    assert [json.loads(r)["id"] for r in backend.rows("t/rows.jsonl")] == ["r3", "r1", "r2"]


def test_upsert_keeps_position_and_adding_twice_is_idempotent(backend: StateBackend) -> None:
    for name in ("a", "b", "c"):
        backend.upsert_row("t/rows.jsonl", "id", name, row(id=name, v=1))
    backend.upsert_row("t/rows.jsonl", "id", "b", row(id="b", v=2))
    backend.upsert_row("t/rows.jsonl", "id", "b", row(id="b", v=2))
    seen = [json.loads(r) for r in backend.rows("t/rows.jsonl")]
    assert [(r["id"], r["v"]) for r in seen] == [("a", 1), ("b", 2), ("c", 1)]


def test_upsert_appends_when_nothing_matches_and_a_missing_field_reads_none(
        backend: StateBackend) -> None:
    backend.append_row("t/rows.jsonl", row(other=1))
    backend.upsert_row("t/rows.jsonl", "id", "x", row(id="x"))
    assert len(backend.rows("t/rows.jsonl")) == 2
    backend.upsert_row("t/rows.jsonl", "id", "None", row(id="y"))  # row 0 has no `id`
    assert json.loads(backend.rows("t/rows.jsonl")[0]) == {"id": "y"}


def test_delete_row_returns_a_bool_and_keeps_the_order(backend: StateBackend) -> None:
    for name in ("a", "b", "c"):
        backend.append_row("t/rows.jsonl", row(id=name))
    assert backend.delete_row("t/rows.jsonl", "id", "b") is True
    assert backend.delete_row("t/rows.jsonl", "id", "b") is False
    assert backend.delete_row("t/missing.jsonl", "id", "b") is False
    assert [json.loads(r)["id"] for r in backend.rows("t/rows.jsonl")] == ["a", "c"]


def test_replace_rows_swaps_the_whole_collection(backend: StateBackend) -> None:
    backend.append_row("t/rows.jsonl", row(id="old"))
    backend.replace_rows("t/rows.jsonl", [row(id="n1"), row(id="n2")])
    assert [json.loads(r)["id"] for r in backend.rows("t/rows.jsonl")] == ["n1", "n2"]


def test_keys_are_sorted_filtered_by_prefix_and_suffix(backend: StateBackend) -> None:
    for key in ("p/b/z.json", "p/a/y.jsonl", "p/a/x.json", "p/ab/q.json", "q/r.json"):
        backend.put(key, "x")
    assert backend.keys("p/") == ["p/a/x.json", "p/a/y.jsonl", "p/ab/q.json", "p/b/z.json"]
    assert backend.keys("p/a/") == ["p/a/x.json", "p/a/y.jsonl"]
    assert backend.keys("p/a") == ["p/a/x.json", "p/a/y.jsonl", "p/ab/q.json"]
    assert backend.keys("p/", ".json") == ["p/a/x.json", "p/ab/q.json", "p/b/z.json"]
    assert backend.keys("nothing/") == []


def test_keys_never_list_internal_scratch(backend: StateBackend) -> None:
    backend.put("p/doc.json", "x")
    assert backend.put_if("p/doc.json", "y", text_sha("x")) is True
    assert backend.keys("p/") == ["p/doc.json"]


def test_delete_prefix_counts_and_leaves_the_rest(backend: StateBackend) -> None:
    for key in ("p/1.json", "p/sub/2.json", "q/3.json"):
        backend.put(key, "x")
    assert backend.delete_prefix("p/") == 2
    assert backend.keys("") == ["q/3.json"] and backend.delete_prefix("p/") == 0


def test_delete_prefix_refuses_an_empty_prefix_and_matches_on_a_segment_boundary(
        backend: StateBackend) -> None:
    """U2 checker-B W2: `delete_prefix("")` is never 'delete everything'; `p/a` is not `p/ab`."""
    for key in ("p/a/1.json", "p/a.json", "p/ab/2.json", "q/3.json"):
        backend.put(key, "x")
    for empty in ("", "/"):
        with pytest.raises(UnsafeName):
            backend.delete_prefix(empty)
    assert backend.keys("") == ["p/a.json", "p/a/1.json", "p/ab/2.json", "q/3.json"]
    assert backend.delete_prefix("p/a") == 1  # p/a/1.json only: neither p/a.json nor p/ab/...
    assert backend.keys("") == ["p/a.json", "p/ab/2.json", "q/3.json"]


def test_a_row_set_in_the_catch_all_collection_deletes_like_any_other(
        backend: StateBackend) -> None:  # cycle 1: a `.jsonl` key no family claims still deletes
    for key, ident in (("foo.jsonl", "1"), ("dir/foo.jsonl", "2"), ("dir/foo.jsonl", "3")):
        backend.append_row(key, row(id=ident))
    backend.put("dir/keep.json", "x")
    assert backend.delete("foo.jsonl") is True and backend.delete("foo.jsonl") is False
    assert backend.rows("foo.jsonl") == [] and not backend.exists("foo.jsonl")
    assert backend.delete_prefix("dir/") == 2 and backend.keys("") == []


def test_children_are_the_sorted_immediate_names_with_an_optional_suffix(
        backend: StateBackend) -> None:
    for key in ("d/b.json", "d/a.jsonl", "d/sub/x.json", "d/sub/y/z.json", "e/q.json"):
        backend.put(key, "x")
    assert backend.children("d") == ["a.jsonl", "b.json", "sub"]
    assert backend.children("d", ".json") == ["b.json"]
    assert backend.children("d/sub") == ["x.json", "y"]
    assert backend.children("d/b.json") == [] and backend.children("nope") == []
    assert backend.children("") == ["d", "e"]


def test_is_dir_is_true_for_a_directory_that_holds_state_only(backend: StateBackend) -> None:
    backend.put("d/sub/x.json", "x")
    assert backend.is_dir("d") and backend.is_dir("d/sub") and backend.is_dir("")
    assert not backend.is_dir("d/sub/x.json") and not backend.is_dir("nope")


def test_mtime_is_none_when_absent_and_moves_forward_on_every_write(
        backend: StateBackend) -> None:
    assert backend.mtime("m/doc.json") is None and backend.mtime("m/rows.jsonl") is None
    backend.put("m/doc.json", "1")
    first = backend.mtime("m/doc.json")
    assert isinstance(first, float) and first > 1_000_000_000
    time.sleep(0.03)
    backend.put("m/doc.json", "2")
    assert (backend.mtime("m/doc.json") or 0) > first
    backend.append_row("m/rows.jsonl", row(id="a"))
    stamp = backend.mtime("m/rows.jsonl")
    time.sleep(0.03)
    backend.append_row("m/rows.jsonl", row(id="b"))
    assert stamp is not None and (backend.mtime("m/rows.jsonl") or 0) > stamp
    backend.delete("m/doc.json")
    assert backend.mtime("m/doc.json") is None


def _race(workers: int, task: Callable[[int], Any]) -> list[Any]:
    gate, results = threading.Barrier(workers), [None] * workers

    def run(index: int) -> None:
        gate.wait()
        results[index] = task(index)

    threads = [threading.Thread(target=run, args=(i,)) for i in range(workers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return results


def test_create_exclusive_has_exactly_one_winner_among_16_callers(backend: StateBackend) -> None:
    for attempt in range(200):
        key = f"claims/c{attempt}.json"
        won = _race(16, lambda i, key=key: backend.create_exclusive(key, f"worker-{i}"))
        assert won.count(True) == 1, f"{won.count(True)} winners on attempt {attempt}"
        assert backend.get(key) == f"worker-{won.index(True)}"


def test_create_exclusive_never_overwrites(backend: StateBackend) -> None:
    assert backend.create_exclusive("c/x.json", "first") is True
    assert backend.create_exclusive("c/x.json", "second") is False
    assert backend.get("c/x.json") == "first"


def test_put_if_a_stale_sha_loses_and_writes_nothing(backend: StateBackend) -> None:
    assert backend.put_if("q/state.json", "v1", None) is True
    assert backend.put_if("q/state.json", "again", None) is False
    assert backend.put_if("q/state.json", "v2", "0" * 64) is False
    assert backend.get("q/state.json") == "v1"
    assert backend.put_if("q/state.json", "v2", text_sha("v1")) is True
    assert backend.put_if("q/state.json", "v3", text_sha("v1")) is False  # now stale
    assert backend.get("q/state.json") == "v2"


def test_put_if_on_a_missing_key_with_an_expected_sha_loses(backend: StateBackend) -> None:
    assert backend.put_if("q/none.json", "x", text_sha("anything")) is False
    assert backend.get("q/none.json") is None


def test_put_if_has_one_winner_among_16_callers_holding_the_same_sha(
        backend: StateBackend) -> None:
    backend.put("q/cas.json", "base")
    won = _race(16, lambda i: backend.put_if("q/cas.json", f"worker-{i}", text_sha("base")))
    assert won.count(True) == 1 and backend.get("q/cas.json") == f"worker-{won.index(True)}"


def test_append_text_creates_then_extends_and_keeps_every_byte(backend: StateBackend) -> None:
    backend.append_text("logs/trace.log", "one\n")
    backend.append_text("logs/trace.log", "two\n")
    assert backend.get("logs/trace.log") == "one\ntwo\n"
    backend.put("logs/other.json", "head,")
    backend.append_text("logs/other.json", "tail")
    assert backend.get("logs/other.json") == "head,tail"  # a plain document: bytes, no newline


def test_append_text_to_a_row_set_adds_one_row_per_line(backend: StateBackend) -> None:
    backend.append_row("logs/a.jsonl", row(id="1"))
    backend.append_text("logs/a.jsonl", row(id="2") + "\n" + row(id="3") + "\n")
    assert backend.rows("logs/a.jsonl") == [row(id="1"), row(id="2"), row(id="3")]


def test_append_text_to_a_row_set_with_blank_lines_adds_only_the_real_rows(
        backend: StateBackend) -> None:
    backend.append_text("logs/b.jsonl", row(id="1") + "\n\n   \n" + row(id="2") + "\n")
    assert backend.rows("logs/b.jsonl") == [row(id="1"), row(id="2")]


def test_append_text_loses_no_append_among_16_callers(backend: StateBackend) -> None:
    if type(backend).__name__ == "FileBackend" and sys.platform == "win32":
        pytest.skip("Windows `open('a')` can interleave; atomic append is the Memory/Mongo promise")
    _race(16, lambda i: backend.append_text("logs/race.log", f"line-{i}\n"))
    assert sorted((backend.get("logs/race.log") or "").splitlines()) == sorted(
        f"line-{i}" for i in range(16))


WHOLE_SEGMENT_ONLY = ["a/CON", "a/nul.txt", "a/COM1.json", "a/lpt9", "a/x.", "a/x ", "a/aux .x",
                      "a/CONIN$", "a/COM0", "a/lpt0.txt", "a/CLOCK$", "a/com¹", "a/COM²"]
ALIASED = [*WHOLE_SEGMENT_ONLY, "a/b:c", "a/y\x7f", "a/q?", "a/s*", "a/<x>", 'a/"q"', "a/p|q"]
UNSAFE = ["../x", "a/../b", "/x", "C:/x", "c:x", "a/C:/y", "a\\b", "a//b", "a/./b", "", "x\x00y",
          "a/", "..", ".", *ALIASED]


def _calls(backend: StateBackend, key: str) -> list[Callable[[], Any]]:
    return [lambda: backend.get(key), lambda: backend.put(key, "x"),
            lambda: backend.put_if(key, "x", None), lambda: backend.create_exclusive(key, "x"),
            lambda: backend.delete(key), lambda: backend.exists(key), lambda: backend.rows(key),
            lambda: backend.append_row(key, "{}"), lambda: backend.replace_rows(key, ["{}"]),
            lambda: backend.upsert_row(key, "id", "1", "{}"),
            lambda: backend.delete_row(key, "id", "1"), lambda: backend.mtime(key),
            lambda: backend.append_text(key, "x\n")]


@pytest.mark.parametrize("key", UNSAFE)
def test_an_unsafe_key_is_refused_by_every_method_before_any_io(
        backend: StateBackend, key: str, tmp_path: Path) -> None:
    backend.put("keep/me.json", "x")
    before = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))
    for call in _calls(backend, key):
        with pytest.raises(UnsafeName):
            call()
    assert sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*")) == before
    assert backend.keys("") == ["keep/me.json"]


@pytest.mark.parametrize("prefix", [p for p in UNSAFE
                                    if p not in {"", "a/", *WHOLE_SEGMENT_ONLY}])
def test_an_unsafe_prefix_is_refused_by_the_listing_methods(
        backend: StateBackend, prefix: str) -> None:
    with pytest.raises(UnsafeName):
        backend.keys(prefix)
    with pytest.raises(UnsafeName):
        backend.delete_prefix(prefix)


@pytest.mark.parametrize("key", [k for k in UNSAFE if k != ""])
def test_an_unsafe_directory_key_is_refused_by_children_and_is_dir(
        backend: StateBackend, key: str) -> None:
    with pytest.raises(UnsafeName):
        backend.children(key)
    with pytest.raises(UnsafeName):
        backend.is_dir(key)


def test_ping_succeeds_on_a_reachable_backend(backend: StateBackend) -> None:
    backend.ping()
