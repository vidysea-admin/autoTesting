"""T-177 follow-up F3: `BrowserSession.cdp_url` is a read-only, loopback-only, opt-in endpoint."""

from __future__ import annotations

import socket
from pathlib import Path
from typing import Any, ClassVar

import pytest
from test_browser import make_project, make_store

from autotester.browser.launch import cdp_endpoint, launch_options, loopback_port
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths


class FakeContext:
    pages: ClassVar[list] = []

    def new_page(self) -> object:
        return object()

    def close(self) -> None:
        pass


class FakePlaywright:
    def __init__(self) -> None:
        self.launches: list[dict[str, Any]] = []
        self.chromium = self

    def launch_persistent_context(self, **kwargs: Any) -> FakeContext:
        self.launches.append(kwargs)
        return FakeContext()

    def start(self) -> FakePlaywright:
        return self

    def stop(self) -> None:
        pass


@pytest.fixture
def pw(monkeypatch: pytest.MonkeyPatch) -> FakePlaywright:
    fake = FakePlaywright()
    monkeypatch.setattr("playwright.sync_api.sync_playwright", lambda: fake)
    return fake


def session(tmp_path: Path, **kw: Any) -> BrowserSession:
    return BrowserSession(make_project(), make_store(tmp_path), tmp_path / "run",
                          ProjectPaths("pathlynks", tmp_path), **kw)


def port_args(opts: dict) -> list[str]:
    return [a for a in opts["args"] if "remote-debugging" in a]


def test_f3_launch_options_carry_no_debug_port_unless_asked(tmp_path: Path) -> None:
    opts = launch_options(make_project(), ProjectPaths("pathlynks", tmp_path))
    assert port_args(opts) == []


def test_f3_launch_options_bind_the_debug_port_to_127_0_0_1(tmp_path: Path) -> None:
    opts = launch_options(make_project(), ProjectPaths("pathlynks", tmp_path), cdp_port=9333)
    assert sorted(port_args(opts)) == ["--remote-debugging-address=127.0.0.1",
                                       "--remote-debugging-port=9333"]
    assert not any("0.0.0.0" in a for a in opts["args"])


def test_f3_loopback_port_is_a_free_loopback_port() -> None:
    port = loopback_port()
    assert 1024 <= port <= 65535
    with socket.socket() as s:  # nothing holds it, so it can be bound right now
        s.bind(("127.0.0.1", port))
    assert cdp_endpoint(port) == f"http://127.0.0.1:{port}"


def test_f3_not_started_or_not_exposed_is_none(tmp_path: Path, pw: FakePlaywright) -> None:
    quiet = session(tmp_path)
    assert quiet.cdp_url is None  # not started
    quiet.start()
    assert quiet.cdp_url is None  # started, but CDP was never asked for
    assert port_args(pw.launches[0]) == []


def test_f3_exposed_session_reports_the_endpoint_it_launched_with(
        tmp_path: Path, pw: FakePlaywright) -> None:
    s = session(tmp_path, expose_cdp=True).start()
    args = port_args(pw.launches[0])
    port = int(next(a for a in args if a.startswith("--remote-debugging-port=")).split("=")[1])
    assert s.cdp_url == f"http://127.0.0.1:{port}"
    assert "--remote-debugging-address=127.0.0.1" in args
    s.close()
    assert s.cdp_url is None  # the browser is gone, so is the endpoint


def test_f3_reading_cdp_url_never_launches_a_second_browser(
        tmp_path: Path, pw: FakePlaywright) -> None:
    s = session(tmp_path, expose_cdp=True)
    assert s.cdp_url is None and pw.launches == []  # reading before start launches nothing
    s.start()
    seen = {s.cdp_url for _ in range(5)}
    assert len(seen) == 1 and len(pw.launches) == 1


def test_f3_cdp_url_is_read_only(tmp_path: Path, pw: FakePlaywright) -> None:
    s = session(tmp_path, expose_cdp=True).start()
    before = s.cdp_url
    with pytest.raises(AttributeError):
        s.cdp_url = "http://0.0.0.0:1"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        del s.cdp_url
    assert BrowserSession.cdp_url.fset is None and BrowserSession.cdp_url.fdel is None
    assert s.cdp_url == before
