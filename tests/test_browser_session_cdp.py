"""T-177 slice 0 (F3, D-075, D-082 item 1): `BrowserSession.cdp_url` is a read-only, loopback-only,
opt-in DevTools endpoint that Chromium itself chose and that is proven to be THIS browser's.

The fake browser below does what the real one does: it picks its own port (here, a real local
server) and writes it to `<profile>/DevToolsActivePort`. No browser is launched in this file;
`test_browser_session_cdp_live.py` does the real launch.
"""

from __future__ import annotations

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest
from test_browser import make_project, make_store

from autotester.browser import launch
from autotester.browser.launch import CdpEndpointError, launch_options
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths

GUID = "/devtools/browser/11111111-2222-3333-4444-555555555555"


class FakeDevTools:
    """A local `/json/version` server standing in for Chromium's DevTools HTTP endpoint."""

    def __init__(self, guid: str = GUID, host: str = "127.0.0.1") -> None:
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                outer.hits += 1
                body = json.dumps({"webSocketDebuggerUrl":
                                   f"ws://127.0.0.1:{outer.port}{guid}"}).encode()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_a: object) -> None:
                pass

        self.hits = 0
        self.server = HTTPServer((host, 0), Handler)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()


class FakeContext:
    pages: list = []  # noqa: RUF012

    def __init__(self, devtools: FakeDevTools | None) -> None:
        self.devtools = devtools

    def new_page(self) -> object:
        return object()

    def close(self) -> None:  # the browser process exits: its port goes away
        if self.devtools:
            self.devtools.stop()


class FakePlaywright:
    """`write_port_file=False` models a browser that never published its port."""

    def __init__(self, devtools: FakeDevTools | None = None, guid: str = GUID,
                 write_port_file: bool = True) -> None:
        self.launches: list[dict[str, Any]] = []
        self.devtools, self.guid, self.write_port_file = devtools, guid, write_port_file
        self.chromium = self

    def launch_persistent_context(self, **kwargs: Any) -> FakeContext:
        self.launches.append(kwargs)
        wants_port = any(a.startswith("--remote-debugging-port=") for a in kwargs["args"])
        if wants_port and self.devtools and self.write_port_file:
            (Path(kwargs["user_data_dir"]) / "DevToolsActivePort").write_text(
                f"{self.devtools.port}\n{self.guid}", encoding="utf-8")
        return FakeContext(self.devtools if wants_port else None)

    def start(self) -> FakePlaywright:
        return self

    def stop(self) -> None:
        pass


def install(monkeypatch: pytest.MonkeyPatch, **kw: Any) -> FakePlaywright:
    fake = FakePlaywright(**kw)
    monkeypatch.setattr("playwright.sync_api.sync_playwright", lambda: fake)
    monkeypatch.setattr(launch, "ATTACH_TIMEOUT_S", 0.5)
    return fake


def session(tmp_path: Path, **kw: Any) -> BrowserSession:
    return BrowserSession(make_project(), make_store(tmp_path), tmp_path / "run",
                          ProjectPaths("pathlynks", tmp_path), **kw)


def debug_args(opts: dict) -> list[str]:
    return [a for a in opts["args"] if "remote-debugging" in a]


def refuses_connections(port: int) -> bool:
    try:
        socket.create_connection(("127.0.0.1", port), timeout=3).close()
    except OSError:
        return True
    return False


def test_launch_options_carry_no_debug_port_unless_asked(tmp_path: Path) -> None:
    assert debug_args(launch_options(make_project(), ProjectPaths("pathlynks", tmp_path))) == []


@pytest.mark.parametrize("headed", [True, False])
@pytest.mark.parametrize("video", [True, False])
def test_launch_args_never_hold_a_non_loopback_debugging_address(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, headed: bool, video: bool) -> None:
    monkeypatch.setenv("AUTOTESTER_SLOW_MO_MS", "5")
    opts = launch_options(make_project(headed), ProjectPaths("pathlynks", tmp_path),
                          record_video_dir=tmp_path / "v" if video else None, expose_cdp=True)
    assert sorted(debug_args(opts)) == ["--remote-debugging-address=127.0.0.1",
                                        "--remote-debugging-port=0"]  # Chromium picks the port
    assert not any("0.0.0.0" in a or "::" in a for a in opts["args"])


def test_not_started_or_not_exposed_is_none_and_never_probes_a_port(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = FakeDevTools()
    pw = install(monkeypatch, devtools=dev)
    quiet = session(tmp_path)
    assert quiet.cdp_url is None  # not started
    quiet.start()
    assert quiet.cdp_url is None  # started, but CDP was never asked for
    assert debug_args(pw.launches[0]) == [] and dev.hits == 0
    dev.stop()


def test_exposed_session_reports_the_port_the_browser_chose(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = FakeDevTools()
    install(monkeypatch, devtools=dev)
    s = session(tmp_path, expose_cdp=True)
    assert s.cdp_url is None  # reading before start launches nothing
    s.start()
    assert s.cdp_url == f"http://127.0.0.1:{dev.port}"
    assert {s.cdp_url for _ in range(3)} == {s.cdp_url}
    s.close()


def test_teardown_closes_the_endpoint_and_forgets_the_port_file(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = FakeDevTools()
    install(monkeypatch, devtools=dev)
    s = session(tmp_path, expose_cdp=True).start()
    port_file = s.paths.profile_dir / "DevToolsActivePort"
    assert port_file.exists() and not refuses_connections(dev.port)
    s.close()
    assert s.cdp_url is None
    assert refuses_connections(dev.port) and not port_file.exists()


def test_an_endpoint_that_is_not_this_browser_is_refused_and_torn_down(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = FakeDevTools(guid="/devtools/browser/someone-else")  # answers, but is another browser
    install(monkeypatch, devtools=dev)
    s = session(tmp_path, expose_cdp=True)
    with pytest.raises(CdpEndpointError, match="not this browser"):
        s.start()
    assert s.cdp_url is None and refuses_connections(dev.port)  # context closed on refusal


def test_a_stale_port_file_never_becomes_the_url(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The TOCTOU window: a port written by an earlier run, now owned by another process."""
    other_process = FakeDevTools()  # live, answers with the right-looking guid
    profile = ProjectPaths("pathlynks", tmp_path).profile_dir
    profile.mkdir(parents=True)
    (profile / "DevToolsActivePort").write_text(f"{other_process.port}\n{GUID}", encoding="utf-8")
    install(monkeypatch, devtools=FakeDevTools(), write_port_file=False)  # new browser: no file
    s = session(tmp_path, expose_cdp=True)
    with pytest.raises(CdpEndpointError, match="did not publish"):
        s.start()
    assert s.cdp_url is None and other_process.hits == 0  # never even asked the other process
    other_process.stop()


def test_a_wildcard_bound_endpoint_is_refused(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dev = FakeDevTools(host="0.0.0.0")  # reachable on every interface, e.g. 127.0.0.2
    install(monkeypatch, devtools=dev)
    s = session(tmp_path, expose_cdp=True)
    with pytest.raises(CdpEndpointError, match="beyond loopback"):
        s.start()
    assert s.cdp_url is None


def test_cdp_url_is_read_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, devtools=FakeDevTools())
    s = session(tmp_path, expose_cdp=True).start()
    before = s.cdp_url
    with pytest.raises(AttributeError):
        s.cdp_url = "http://0.0.0.0:1"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        del s.cdp_url
    assert BrowserSession.cdp_url.fset is None and BrowserSession.cdp_url.fdel is None
    assert s.cdp_url == before
    s.close()


class MaskSpyPage:
    def __init__(self) -> None:
        self.init_scripts: list[str] = []

    def add_init_script(self, script: str) -> None:
        self.init_scripts.append(script)

    def close(self) -> None:
        pass


class MaskSpyContext:
    def __init__(self) -> None:
        self.pages: list[MaskSpyPage] = []

    def new_page(self) -> MaskSpyPage:
        self.pages.append(MaskSpyPage())
        return self.pages[-1]


def test_owed_gap_a_second_tab_opened_during_a_recorded_case_has_no_mask(tmp_path: Path) -> None:
    """RECORDS A KNOWN GAP, owed by the next slice (the one that adds the agent): video.py puts the
    secret-mask init script on the ONE page `begin_case_video` creates, not on the context, so a
    tab the agent opens mid-case is recorded unmasked. This passes today because that is the
    behaviour; the slice that masks at context level must flip it (D-082 item 1, slice 0 review)."""
    s = session(tmp_path, record_video=True)
    s._context = MaskSpyContext()
    s.begin_case_video("case-1")
    case_page, second_tab = s._page, s._context.new_page()
    assert len(case_page.init_scripts) == 1  # the case page is masked
    assert second_tab.init_scripts == []  # GAP: a second tab is not
