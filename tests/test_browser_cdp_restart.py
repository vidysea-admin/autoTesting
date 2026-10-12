"""T-177 slice 0 x AT-888: a session restart re-publishes the DevTools endpoint.

`video.py::_restart_session` goes through `BrowserSession.start()`, the only launch path, so the
stale port file is forgotten and the new browser's endpoint is verified again. No browser: a
fake Playwright that gives every launch its own loopback `/json/version` listener.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from test_browser_session_cdp import FakeDevTools, FakePlaywright, refuses_connections, session


class Page:
    video = None

    def add_init_script(self, _script: str) -> None:
        pass

    def close(self) -> None:
        pass

    def is_closed(self) -> bool:
        return False


class Context:
    def __init__(self, dev: FakeDevTools) -> None:
        self.dev, self.dead, self.pages = dev, False, [Page()]

    def new_page(self) -> Page:
        if self.dead:
            raise RuntimeError("BrowserContext.new_page: Failed to open a new tab")
        return Page()

    def close(self) -> None:
        self.dev.stop()


class PortPerLaunch(FakePlaywright):
    """Each launch is a new browser with a new DevTools port, as in real life."""

    def __init__(self) -> None:
        super().__init__()
        self.devs: list[FakeDevTools] = []
        self.contexts: list[Context] = []

    def launch_persistent_context(self, **kwargs: Any) -> Context:
        dev = FakeDevTools()
        self.devs.append(dev)
        (Path(kwargs["user_data_dir"]) / "DevToolsActivePort").write_text(
            f"{dev.port}\n/devtools/browser/11111111-2222-3333-4444-555555555555",
            encoding="utf-8")
        self.contexts.append(Context(dev))
        return self.contexts[-1]


def test_a_restart_after_the_browser_died_republishes_the_new_endpoint(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = PortPerLaunch()
    monkeypatch.setattr("playwright.sync_api.sync_playwright", lambda: fake)
    monkeypatch.setattr("autotester.browser.launch.ATTACH_TIMEOUT_S", 0.5)
    s = session(tmp_path, expose_cdp=True, record_video=True).start()
    first = s.cdp_url
    assert first == f"http://127.0.0.1:{fake.devs[0].port}"
    fake.contexts[0].dead = True  # the browser is gone; the next case's page cannot open
    s.begin_case_video("case-2")  # AT-888 restart: start() again, a new browser, a new port
    assert len(fake.devs) == 2 and s.cdp_url == f"http://127.0.0.1:{fake.devs[1].port}"
    assert s.cdp_url != first and refuses_connections(fake.devs[0].port)
    s.close()
    assert s.cdp_url is None and refuses_connections(fake.devs[1].port)
