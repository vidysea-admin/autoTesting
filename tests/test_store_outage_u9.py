"""mongo-store U9: store-outage 503, startup refusal text, /healthz readiness (M9, M26, M27).

Split from test_store_startup_u9.py (300-line cap). Fake Mongo only: no socket, no live server.
"""

from __future__ import annotations

import traceback
from collections.abc import Iterator
from pathlib import Path

import pytest
from fake_mongo import CANARY, FakeMongoServer, seams
from fastapi.testclient import TestClient

import autotester.ui.app as app_module
import autotester.ui.error_pages as error_pages
import autotester.ui.routes_live as routes_live
from autotester.core.env import MONGO_URI_ENV
from autotester.store.filestore import validate_store_env
from autotester.store.mongo_backend import reset_default_backend
from autotester.store.mongo_guard import StoreUnavailable
from autotester.store.mongo_routes import StoreDown, ping_backends
from autotester.ui.app import app

URI = f"mongodb://user:{CANARY}@db.example/"


@pytest.fixture(autouse=True)
def _clean(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    for name in ("AUTOTESTER_STORE", "AUTOTESTER_STORE_AREAS", "AUTOTESTER_MONGO_URI",
                 MONGO_URI_ENV):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path / "root"))
    reset_default_backend()
    yield
    reset_default_backend()


# ---- 503 (M26) --------------------------------------------------------------------------------

FIXED = "State store unavailable, nothing was changed"


def _boom(monkeypatch: pytest.MonkeyPatch, exc: Exception) -> None:
    def raiser() -> list[str]:
        raise exc
    monkeypatch.setattr(app_module, "_project_slugs", raiser)


@pytest.mark.parametrize("accept", ["application/json", "text/html"])
def test_a_store_outage_in_a_route_is_a_503_with_a_fixed_body(
        monkeypatch: pytest.MonkeyPatch, accept: str) -> None:
    _boom(monkeypatch, StoreUnavailable(f"state store unavailable ({URI})"))
    resp = TestClient(app).get("/", headers={"accept": accept})
    assert resp.status_code == 503
    assert FIXED in resp.text
    assert CANARY not in resp.text and "mongodb" not in resp.text


def test_an_unrelated_error_is_not_turned_into_a_503(monkeypatch: pytest.MonkeyPatch) -> None:
    _boom(monkeypatch, ValueError("plain bug"))
    with pytest.raises(ValueError):
        TestClient(app).get("/")


def test_an_outage_raised_below_the_router_is_a_503_too(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """The auth gate is middleware, outside the router's exception handling: a store error there
    must still deny with a 503 and never fall through as allowed."""
    from autotester.ui import auth_middleware

    def down(_request: object) -> None:
        raise StoreUnavailable(f"state store unavailable ({URI})")
    monkeypatch.setattr(auth_middleware, "_principal", down)
    resp = TestClient(app).get("/")
    assert resp.status_code == 503 and FIXED in resp.text and CANARY not in resp.text


class _Down:
    def ping(self) -> None:
        raise StoreDown(f"cannot reach {URI}")


class _Up:
    def ping(self) -> None: ...


def test_the_startup_refusal_never_relays_the_source_message() -> None:
    """W3: a `StoreDown` raiser that quotes the URI must not reach the refusal text."""
    selection = {"runs": "mongo", "projects": "mongo", "settings": "file"}
    with pytest.raises(StoreDown) as info:
        ping_backends(selection, lambda name: _Down() if name == "mongo" else _Up())
    text = "".join(traceback.format_exception(info.value)) + str(info.value) + repr(info.value)
    assert CANARY not in text and "mongodb" not in text and "cannot reach" not in text
    assert "StoreDown" in str(info.value) and "runs, projects" in str(info.value)
    assert "settings" not in str(info.value)
    assert info.value.__cause__ is None and info.value.__suppress_context__


@pytest.mark.parametrize("selection", [{"AUTOTESTER_STORE_AREAS": "projects=mongo"},
                                       {"AUTOTESTER_STORE": "mongo"}])
def test_the_themed_503_renders_without_reading_the_down_store(
        monkeypatch: pytest.MonkeyPatch, selection: dict[str, str]) -> None:
    """F1 (M26): the page chrome lists projects from the store; the outage page must not. Nothing
    on the render path is patched: `/` goes through the real `ui.helpers._project_slugs`."""
    for name, value in selection.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv(MONGO_URI_ENV, URI)
    server = FakeMongoServer(down_message=f"cannot reach {URI}")
    with seams(client_factory=lambda _uri: server.client()):
        validate_store_env()  # the backend opens while the server is up
        server.down = True
        resp = TestClient(app, raise_server_exceptions=False).get(
            "/", headers={"accept": "text/html"})
    assert resp.status_code == 503
    assert resp.headers["content-type"].startswith("text/html")
    assert FIXED in resp.text and "class='card'" in resp.text and "<style" in resp.text
    assert "<aside" not in resp.text.rpartition("</style>")[2]  # the markup, not the CSS
    assert CANARY not in resp.text and "mongodb" not in resp.text


def test_a_failure_while_rendering_the_outage_page_falls_back_to_a_fixed_body(
        monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*_a: object, **_k: object) -> str:
        raise StoreUnavailable("render touched the store")
    monkeypatch.setattr(error_pages.theme, "card", broken)
    _boom(monkeypatch, StoreUnavailable(f"state store unavailable ({URI})"))
    resp = TestClient(app, raise_server_exceptions=False).get(
        "/", headers={"accept": "text/html"})
    assert resp.status_code == 503 and FIXED in resp.text
    assert "render touched" not in resp.text and CANARY not in resp.text


# ---- readiness (M26) ----------------------------------------------------------------------------


def _admin() -> TestClient:
    return TestClient(app)


def test_healthz_stays_200_and_anonymous_learns_nothing_new(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_TEST_NO_AUTO_LOGIN", "1")
    monkeypatch.setenv("AUTOTESTER_STORE", "mongo")
    monkeypatch.setenv(MONGO_URI_ENV, URI)
    resp = TestClient(app).get("/healthz")
    assert resp.status_code == 200 and resp.json() == {"ok": True}


def test_healthz_in_file_mode_reports_every_area_as_file_without_a_reach_probe() -> None:
    body = _admin().get("/healthz").json()
    assert set(body["store"]["areas"].values()) == {"file"}
    assert body["store"]["reachable"] is True
    assert "mongo" not in str(body["store"])


def test_healthz_reports_a_reachable_mongo_area(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_STORE_AREAS", "runs=mongo")
    monkeypatch.setenv(MONGO_URI_ENV, URI)
    server = FakeMongoServer()
    with seams(client_factory=lambda _uri: server.client()):
        body = _admin().get("/healthz").json()
    assert body["store"]["areas"]["runs"] == "mongo"
    assert body["store"]["areas"]["projects"] == "file"
    assert body["store"]["reachable"] is True


def test_healthz_stays_200_while_the_store_is_down_and_leaks_nothing(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_STORE", "mongo")
    monkeypatch.setenv(MONGO_URI_ENV, URI)
    server = FakeMongoServer(down_message=f"cannot reach {URI}")
    with seams(client_factory=lambda _uri: server.client()):
        _admin().get("/healthz")  # opens the backend while up
        server.down = True
        resp = _admin().get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["store"]["reachable"] is False
    assert CANARY not in resp.text and "mongodb" not in resp.text
    assert "database" not in str(body["store"]) and "autotester" not in str(body["store"])


def test_healthz_with_the_store_unconfigured_reports_it_without_failing(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_STORE", "mongo")  # no URI anywhere
    resp = _admin().get("/healthz")
    assert resp.status_code == 200 and resp.json()["store"]["reachable"] is False


def test_the_readiness_helper_is_the_one_in_routes_live() -> None:
    assert callable(routes_live.store_readiness)
