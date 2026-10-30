"""mongo-store M9 follow-ups from both U1 checkers: no exception CHAIN carries the URI.

`raise X from None` hides the driver exception from the traceback but leaves it in `__context__`
when raised inside the `except` block, and a driver message may quote the connection string. The
guard therefore picks its verdict inside `except` and raises outside it. These tests walk the whole
chain (`__context__`, `__cause__`, args, str, repr) of every guard-raised error.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from fake_mongo import CANARY, FakeMongoServer, assert_no_canary, open_store
from pymongo.errors import AutoReconnect, DuplicateKeyError

from autotester.store.mongo_guard import (
    StoreConfigError,
    StoreDuplicateKey,
    StoreNotFound,
    StoreUnavailable,
)

URI = f"mongodb://u:{CANARY}@h/x"


def assert_chain_clean(exc: BaseException) -> None:
    """Nothing reachable from `exc` is a driver exception or mentions the canary."""
    seen: list[BaseException] = []
    link: BaseException | None = exc
    while link is not None and link not in seen:
        seen.append(link)
        assert CANARY not in str(link) + repr(link) + repr(link.args)
        assert type(link).__module__.split(".")[0] not in {"pymongo", "gridfs"}
        link = link.__cause__ or link.__context__
    assert exc.__context__ is None and exc.__cause__ is None


def test_constructor_error_branch_is_reached_and_clean() -> None:
    """Checker warning (b): the client factory itself raises (the `cannot open` branch)."""
    def boom(uri: str) -> Any:
        raise ValueError(f"cannot parse {uri}")

    with pytest.raises(StoreUnavailable) as caught:
        open_store(URI, client_factory=boom)
    assert str(caught.value) == "cannot open the state store (ValueError)"
    assert_chain_clean(caught.value)


def test_constructor_error_when_selecting_the_database_is_clean() -> None:
    class Exploding:
        def __getitem__(self, name: str) -> Any:
            raise RuntimeError(f"driver says {URI}")

    with pytest.raises(StoreUnavailable) as caught:
        open_store(URI, client_factory=lambda uri: Exploding())
    assert "RuntimeError" in str(caught.value)
    assert_chain_clean(caught.value)


def _down_actions(store: Any) -> list[Callable[[], Any]]:
    return [store.ping, lambda: store.collection("projects").find({}),
            lambda: store.collection("projects").insert_one({"_id": "a"}),
            lambda: store.bucket().upload("f", b"x", metadata={})]


def test_unavailable_errors_from_a_driver_failure_carry_no_chain() -> None:
    server = FakeMongoServer(down_message=f"connect failed for {URI}")
    store = open_store(URI, server.client())
    server.down = True
    for action in _down_actions(store):
        with pytest.raises(StoreUnavailable) as caught:
            action()
        assert "AutoReconnect" in str(caught.value)
        assert_chain_clean(caught.value)


def test_duplicate_key_and_missing_blob_carry_no_chain() -> None:
    store = open_store(URI, FakeMongoServer().client())
    store.collection("projects").insert_one({"_id": "a"})
    with pytest.raises(StoreDuplicateKey) as dup:
        store.collection("projects").insert_one({"_id": "a"})
    assert_chain_clean(dup.value)
    with pytest.raises(StoreNotFound) as missing:
        store.bucket().download("absent")
    assert_chain_clean(missing.value)


def test_translate_maps_each_driver_error_without_chaining() -> None:
    from autotester.store.mongo_guard import _translate

    def fail(error: BaseException) -> Callable[[], Any]:
        def call() -> Any:
            raise error
        return call

    for error, expected in ((DuplicateKeyError(URI), StoreDuplicateKey),
                            (AutoReconnect(URI), StoreUnavailable)):
        with pytest.raises(expected) as caught:
            _translate(fail(error))
        assert_chain_clean(caught.value)


def test_a_lazy_cursor_that_dies_mid_iteration_is_translated_and_clean(
        capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture) -> None:
    """U2 checker-B W3: `find` iterates the cursor INSIDE `_translate`, so a network error that
    surfaces mid-iteration is a clean `StoreUnavailable`, not a raw driver error quoting the URI."""
    server = FakeMongoServer(down_message=f"connect failed for {URI}")
    store = open_store(URI, server.client())
    for name in ("projects", "approvals"):  # a guarded and an insert-only collection
        for i in range(3):
            store.collection(name).insert_one({"_id": f"d{i}", "p": "x"})
    server.cursor_error = f"cursor lost on {URI}"
    for name in ("projects", "approvals"):
        with pytest.raises(StoreUnavailable) as caught:
            store.collection(name).find({"p": "x"})
        assert str(caught.value) == "state store unavailable (AutoReconnect)"
        assert_chain_clean(caught.value)
        assert_no_canary(caught.value, capsys, caplog)


@pytest.mark.parametrize("uri", [
    f"notmongo://u:{CANARY}@h/", f"u:{CANARY}@h/", f"mongodb://u:{CANARY}@h:notaport/",
    f"mongodb://u:{CANARY}@/"])
def test_the_invalid_uri_branch_raises_one_fixed_error_with_no_chain(
        uri: str, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture) -> None:
    """U2 checker-B W4: `_uri_path_database` fails -> `StoreConfigError`, raised outside `except`,
    so neither the URI nor the parser's own exception is reachable from the chain."""
    server = FakeMongoServer()
    with pytest.raises(StoreConfigError) as caught:
        open_store(uri, server.client())
    assert str(caught.value) == "the store connection string is not a valid mongodb:// URI"
    assert_chain_clean(caught.value)
    assert_no_canary(caught.value, capsys, caplog)
    assert server.log == [] and server.databases == {}


def test_a_fake_bucket_never_reuses_a_file_id_after_a_delete() -> None:
    """Dispatcher note (U5a): upload, delete, upload must hand out two different ids."""
    bucket = open_store(client=FakeMongoServer().client()).bucket()
    first = bucket.upload("a.bin", b"1", metadata={})
    bucket.delete(first)
    second = bucket.upload("a.bin", b"2", metadata={})
    assert first != second
    assert [r["id"] for r in bucket.revisions("a.bin")] == [second]
