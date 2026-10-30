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
from fake_mongo import CANARY, FakeMongoServer, open_store
from pymongo.errors import AutoReconnect, DuplicateKeyError

from autotester.store.mongo_guard import (
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
