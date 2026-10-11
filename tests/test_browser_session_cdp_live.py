"""T-177 slice 0, real browser: the DevTools endpoint a session exposes is Chromium's own,
loopback-only, answers as this browser, and is gone after teardown.

Launches a real (headless) Chromium on `about:blank`, never a product page. Headed Chrome is NOT
exercised here: whether it honours `--remote-debugging-address` is unverified (headless Chromium
151 ignores that flag and binds loopback by default, which `verified_cdp_url` then enforces).
"""

from __future__ import annotations

import json
import socket
import time
import urllib.request
from pathlib import Path

import pytest
from test_browser import make_project, make_store

from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths


def _skip_if_no_chromium() -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    try:
        with sync_api.sync_playwright() as pw:
            pw.chromium.launch(headless=True).close()
    except Exception as exc:  # pragma: no cover - browser binary missing
        pytest.skip(f"chromium unavailable: {type(exc).__name__}")


def _accepts(host: str, port: int) -> bool:
    try:
        socket.create_connection((host, port), timeout=3).close()
    except OSError:
        return False
    return True


def test_a_real_browser_serves_devtools_on_loopback_only_and_closes_at_teardown(
        tmp_path: Path) -> None:
    _skip_if_no_chromium()
    project = make_project(headed=False)
    s = BrowserSession(project, make_store(tmp_path), tmp_path / "run",
                       ProjectPaths("pathlynks", tmp_path), expose_cdp=True)
    s.start()
    try:
        url = s.cdp_url
        assert url is not None and url.startswith("http://127.0.0.1:")
        port = int(url.rsplit(":", 1)[1])
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f"{url}/json/version", timeout=5) as reply:
            assert "webSocketDebuggerUrl" in json.load(reply)
        assert _accepts("127.0.0.1", port)
        assert not _accepts("127.0.0.2", port)  # not a wildcard bind
        assert not _accepts(socket.gethostbyname(socket.gethostname()), port)
    finally:
        s.close()
    assert s.cdp_url is None
    deadline = time.monotonic() + 10
    while _accepts("127.0.0.1", port) and time.monotonic() < deadline:
        time.sleep(0.2)
    assert not _accepts("127.0.0.1", port)  # teardown closed the port
    assert not (s.paths.profile_dir / "DevToolsActivePort").exists()


def test_a_real_session_that_did_not_ask_has_no_devtools_port(tmp_path: Path) -> None:
    _skip_if_no_chromium()
    s = BrowserSession(make_project(headed=False), make_store(tmp_path), tmp_path / "run",
                       ProjectPaths("pathlynks", tmp_path))
    s.start()
    try:
        assert s.cdp_url is None
        assert not (s.paths.profile_dir / "DevToolsActivePort").exists()
    finally:
        s.close()
