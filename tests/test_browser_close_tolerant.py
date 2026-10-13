"""Cleanup in BrowserSession never masks the original start() error and close() is tolerant."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from playwright import sync_api
from test_browser import session_with_fake_page


def _boom(msg: str):
    def raiser() -> None:
        raise RuntimeError(msg)
    return raiser


def _failing_launch(**_kw):
    raise ValueError("launch failed")


def test_start_failure_with_failing_cleanup_raises_original(tmp_path, monkeypatch) -> None:
    driver = SimpleNamespace(chromium=SimpleNamespace(launch_persistent_context=_failing_launch))
    driver.stop = _boom("stop failed")
    monkeypatch.setattr(sync_api, "sync_playwright", lambda: SimpleNamespace(start=lambda: driver))
    session = session_with_fake_page(tmp_path)
    with pytest.raises(ValueError, match="launch failed"):
        session.start()
    assert session._playwright is None


def test_close_is_tolerant_when_stop_raises_and_runs_every_step(tmp_path) -> None:
    calls: list[str] = []
    session = session_with_fake_page(tmp_path)
    session._context = SimpleNamespace(close=lambda: (calls.append("ctx"), _boom("ctx")()))
    session._playwright = SimpleNamespace(stop=lambda: (calls.append("stop"), _boom("stop")()))
    session.close()
    assert calls == ["ctx", "stop"]
    assert session._context is session._page is session._playwright is None


def test_close_is_idempotent(tmp_path) -> None:
    calls: list[str] = []
    session = session_with_fake_page(tmp_path)
    session._context = SimpleNamespace(close=lambda: calls.append("ctx"))
    session._playwright = SimpleNamespace(stop=lambda: calls.append("stop"))
    session.close()
    session.close()
    assert calls == ["ctx", "stop"]
