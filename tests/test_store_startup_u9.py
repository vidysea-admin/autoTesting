"""mongo-store U9: URI resolution, startup ping, 503 mapping, readiness (M9, M11, M13, M26, M27).

All against the hand-written fake (tests/fake_mongo.py): no socket, no live server.
"""

from __future__ import annotations

import asyncio
import hashlib
import traceback
from collections.abc import Iterator
from pathlib import Path

import pytest
from fake_mongo import CANARY, FakeMongoServer, seams
from fastapi.testclient import TestClient

import autotester.core.paths as paths
import autotester.ui.app as app_module
import autotester.ui.routes_live as routes_live
from autotester.core.env import MONGO_URI_ENV, mongo_uri
from autotester.store.filestore import validate_store_env
from autotester.store.mongo_backend import reset_default_backend
from autotester.store.mongo_guard import StoreUnavailable
from autotester.store.mongo_routes import StoreSelectionError
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


def _tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")) if root.exists() else []:
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes() if path.is_file() else b"")
    return digest.hexdigest()


# ---- core/env.py::mongo_uri (one name, one place) -------------------------------------------


def test_the_process_environment_wins_over_the_dotenv(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "root").mkdir()
    (tmp_path / "root" / ".env").write_text(f"{MONGO_URI_ENV}=mongodb://from-file/\n", "utf-8")
    assert mongo_uri() == "mongodb://from-file/"
    monkeypatch.setenv(MONGO_URI_ENV, "  mongodb://from-env/ ")
    assert mongo_uri() == "mongodb://from-env/"


def test_a_blank_environment_value_counts_as_unset_and_a_missing_one_is_empty(
        monkeypatch: pytest.MonkeyPatch) -> None:
    assert mongo_uri() == ""
    monkeypatch.setenv(MONGO_URI_ENV, "   ")
    assert mongo_uri() == ""


def test_a_value_is_read_literally_not_interpolated(tmp_path: Path) -> None:
    (tmp_path / "root").mkdir()
    (tmp_path / "root" / ".env").write_text(f"{MONGO_URI_ENV}=mongodb://u:p${{X}}w@h/\n", "utf-8")
    assert mongo_uri() == "mongodb://u:p${X}w@h/"


def test_a_test_process_never_reads_the_real_code_tree_dotenv(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """With no `AUTOTESTER_ROOT` the data root is the code tree; a unit test must not pick up a
    developer's live URI from there."""
    code = tmp_path / "code"
    code.mkdir()
    (code / ".env").write_text(f"{MONGO_URI_ENV}=mongodb://real-server/\n", "utf-8")
    monkeypatch.delenv("AUTOTESTER_ROOT", raising=False)
    monkeypatch.setattr(paths, "code_root", lambda: code)
    assert mongo_uri() == ""


def test_the_provisional_name_is_gone_from_the_source() -> None:
    src = Path(paths.__file__).resolve().parents[1]
    hits = [p.relative_to(src).as_posix() for p in src.rglob("*.py")
            if "AUTOTESTER_MONGO_URI" in p.read_text(encoding="utf-8")]
    assert hits == []


def test_the_old_name_is_ignored_and_the_new_one_is_named_in_the_refusal(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_STORE", "mongo")
    monkeypatch.setenv("AUTOTESTER_MONGO_URI", URI)
    with pytest.raises(StoreSelectionError, match=f"{MONGO_URI_ENV} is not set") as info:
        validate_store_env()
    assert CANARY not in str(info.value)


def test_a_dotenv_uri_opens_the_store_and_is_never_echoed(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture) -> None:
    (tmp_path / "root").mkdir()
    (tmp_path / "root" / ".env").write_text(f"{MONGO_URI_ENV}={URI}\n", "utf-8")
    monkeypatch.setenv("AUTOTESTER_STORE", "mongo")
    server, seen = FakeMongoServer(), []
    with seams(client_factory=lambda uri: seen.append(uri) or server.client()):
        assert validate_store_env()["projects"] == "mongo"
    assert seen == [URI]
    out = capsys.readouterr()
    assert CANARY not in out.out + out.err + caplog.text


# ---- startup ping (M27) ---------------------------------------------------------------------


def test_startup_pings_the_server_once_per_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_STORE", "mongo")
    monkeypatch.setenv(MONGO_URI_ENV, URI)
    server = FakeMongoServer()
    with seams(client_factory=lambda _uri: server.client()):
        validate_store_env()
    assert [e for e in server.log if e[1] == "command:ping"] == [("autotester", "command:ping")]


def test_a_mixed_selection_pings_only_the_chosen_backends(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_STORE_AREAS", "runs=mongo")
    monkeypatch.setenv(MONGO_URI_ENV, URI)
    server = FakeMongoServer()
    with seams(client_factory=lambda _uri: server.client()):
        chosen = validate_store_env()
    assert (chosen["runs"], chosen["projects"]) == ("mongo", "file")
    assert sum(e[1] == "command:ping" for e in server.log) == 1


def test_an_unreachable_server_stops_startup_naming_the_area_and_class_only(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture) -> None:
    monkeypatch.setenv("AUTOTESTER_STORE_AREAS", "runs=mongo")
    monkeypatch.setenv(MONGO_URI_ENV, URI)
    server = FakeMongoServer(down_message=f"cannot reach {URI}")
    server.down = True
    before = _tree(tmp_path / "root")
    with (seams(client_factory=lambda _uri: server.client()),
          pytest.raises(StoreUnavailable) as info):
        validate_store_env()
    text = "".join(traceback.format_exception(info.value)) + str(info.value)
    out = capsys.readouterr()
    assert CANARY not in text + out.out + out.err + caplog.text
    assert "runs" in str(info.value) and "AutoReconnect" in str(info.value)
    assert _tree(tmp_path / "root") == before  # M26: no file appears


def test_a_server_that_dies_after_connecting_is_caught_by_the_ping(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_STORE", "mongo")
    monkeypatch.setenv(MONGO_URI_ENV, URI)
    server = FakeMongoServer()
    with seams(client_factory=lambda _uri: server.client()):
        validate_store_env()
        server.down = True
        with pytest.raises(StoreUnavailable, match="projects"):
            validate_store_env()


def test_the_server_refuses_to_start_when_the_store_is_down(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_STORE", "mongo")
    monkeypatch.setenv(MONGO_URI_ENV, URI)
    server = FakeMongoServer()
    server.down = True

    async def start() -> None:
        async with app_module._lifespan(app):
            pass

    with seams(client_factory=lambda _uri: server.client()), pytest.raises(StoreUnavailable):
        asyncio.run(start())


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
