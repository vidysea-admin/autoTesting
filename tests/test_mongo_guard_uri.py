"""mongo-store M4(c), M9: the URI is read the way the driver reads it, and never echoed.

M4(c): a URI whose driver-parsed database is the store database is refused before any client
exists. The corpus includes every shape checker B found where `urlsplit` and the driver disagree
(`db.collection`, a `#` in the userinfo). M9: no exception carries the URI or any part of it,
whatever fails to parse (a fullwidth `:` or `@` makes `urlsplit` quote the whole netloc).
"""

from __future__ import annotations

import logging
import socket
from typing import Any

import pytest
from fake_mongo import CANARY, FakeMongoServer, assert_no_canary, open_store
from pymongo.uri_parser import parse_uri

import autotester.store.mongo_guard as guard_module
from autotester.store.mongo_guard import StoreConfigError

CLASH = [
    "mongodb://h/autotester", "mongodb://h/Autotester", "mongodb://h/AUTOTESTER?x=1",
    f"mongodb://u:{CANARY}@h1,h2/autotester?replicaSet=r",
    f"mongodb+srv://u:{CANARY}@cluster0.example.net/autotester",
    "mongodb://h/%61utotester", "mongodb://h/%41utotester?x=1",
    "mongodb://h/%61%75%74%6f%74%65%73%74%65%72", "mongodb://h/%41UTOTESTER?x=1",
    f"mongodb://u:{CANARY}@h1,h2/%61utotester?replicaSet=r",
    "mongodb://h/autotester.x", "mongodb://h/AUTOTESTER.coll", "mongodb://h/autotester.",
    "mongodb://h/%61utotester.%78", "mongodb://u:p#x@h/autotester",
    f"mongodb://u:{CANARY}#x@h/autotester", "mongodb://u:p?x@h/autotester",
    "mongodb+srv://c.example.net/autotester.x", "mongodb+srv://u:p#x@c.example.net/AUTOTESTER",
]
PARITY = [
    "mongodb://h/", "mongodb://h", "mongodb://h/scratch", "mongodb://h/?authSource=admin",
    "mongodb://h/%2Bx", "mongodb://h/a%2Db", "mongodb://u:p%40ss@h1,h2/db_1?replicaSet=r",
    "mongodb://h/scratch.coll", "mongodb://h/scratch.", "mongodb://u:p#x@h/scratch",
    "mongodb://u:p?x@h/scratch", "mongodb://h/auto+tester", "mongodb://h/a%20b",
    "mongodb://h/a/b", "mongodb://h/a$b", "mongodb://h:notaport/x", "mongodb://[h/x",
    *[u for u in CLASH[:15] if not u.startswith("mongodb+srv")],
]
SRV = [("mongodb+srv://c.example.net/%41utotester.x", "Autotester"),
       ("mongodb+srv://c.example.net/", ""), ("mongodb+srv://u:p#x@c.example.net/x_1?a=b", "x_1"),
       ("mongodb+srv://c.example.net/a.b.c", "a")]
MALFORMED = [
    f"mongodb://umesh:{CANARY}\uff1apw@h.example/", f"mongodb://umesh:{CANARY}\uff20pw@h.example/",
    f"mongodb://umesh:{CANARY}@[h/", f"mongodb://u:{CANARY}@h:notaport/x",
    f"mongodb://u:{CANARY}@h/bad db", f"mongodb://u:{CANARY}@h/a$b", f"mongodb://u:{CANARY}@",
    f"mongodb+srv://u:{CANARY}\uff1a@h.example/", f"mongodb://u:{CANARY}@h/x\x00",
]


def _never(_uri: str) -> Any:
    raise AssertionError("client created")


@pytest.mark.parametrize("uri", CLASH)
def test_a_uri_path_naming_the_store_database_is_refused_before_any_client(uri: str) -> None:
    with pytest.raises(StoreConfigError) as caught:
        open_store(uri, client_factory=_never)
    assert CANARY not in str(caught.value) and caught.value.__context__ is None


@pytest.mark.parametrize("uri", PARITY)
def test_the_database_is_read_exactly_as_the_driver_reads_it(uri: str) -> None:
    try:
        driver = parse_uri(uri, validate=False)["database"] or ""
    except Exception:  # the driver refuses this URI, so the guard must as well
        with pytest.raises(StoreConfigError):
            guard_module._uri_path_database(uri)
        return
    assert guard_module._uri_path_database(uri) == driver


@pytest.mark.parametrize(("uri", "expected"), SRV)
def test_an_srv_uri_is_read_without_dns_and_the_same_way(
        monkeypatch: pytest.MonkeyPatch, uri: str, expected: str) -> None:
    def no_dns(*_a: Any, **_k: Any) -> Any:
        raise AssertionError("DNS lookup")

    monkeypatch.setattr(socket, "getaddrinfo", no_dns)
    assert guard_module._uri_path_database(uri) == expected


def test_a_plus_in_the_path_is_a_space_the_driver_refuses_and_a_percent_2b_is_a_plus() -> None:
    with pytest.raises(StoreConfigError):
        open_store("mongodb://h/auto+tester", FakeMongoServer().client())
    assert guard_module._uri_path_database("mongodb://h/auto%2Btester") == "auto+tester"
    open_store("mongodb://h/auto%2Btester", FakeMongoServer().client())


@pytest.mark.parametrize("uri", ["http://h/x", "h/x", "", "ftp://u:" + CANARY + "@h/x",
                                 "MONGODB://h/x", " mongodb://h/x", "mongodb:/h/x"])
def test_a_non_mongodb_uri_is_refused_without_echoing_it(uri: str) -> None:
    with pytest.raises(StoreConfigError) as caught:
        open_store(uri, client_factory=_never)
    assert CANARY not in str(caught.value) and caught.value.__context__ is None


@pytest.mark.parametrize("uri", MALFORMED)
def test_no_parse_failure_carries_the_uri_or_any_part_of_it(
        uri: str, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        try:
            open_store(uri, FakeMongoServer().client())
        except Exception as exc:
            assert isinstance(exc, StoreConfigError), type(exc).__name__
            assert exc.__context__ is None and exc.__cause__ is None
            assert_no_canary(exc, capsys, caplog)
            for part in ("umesh", "h.example", "notaport", "bad db"):
                assert part not in str(exc), part
