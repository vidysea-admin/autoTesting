"""Checker cycle-0 W1 (both checkers): a failed `Network.clearBrowserCache` must not be swallowed.

If the HTTP cache cannot be emptied, a `max-age` document fetched while logged in could still be
served to the next logged-out entry case. The reset therefore raises, and the pool discards the
browser and launches a fresh wiped one (fail closed). Fakes only (the real-Chromium proof of the
clear itself is in `test_entry_reset_live.py`).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from autotester.browser.entry_reset import reset_to_logged_out


class _Cdp:
    def __init__(self, sent: list[str], failing: str | None) -> None:
        self.sent, self.failing = sent, failing

    def send(self, method: str, _params: dict | None = None) -> None:
        self.sent.append(method)
        if method == self.failing:
            raise RuntimeError(f"{method} failed")

    def detach(self) -> None:
        self.sent.append("detach")


def _session(sent: list[str], failing: str | None):
    page = SimpleNamespace(url="http://app.test/", evaluate=lambda _js: sent.append("page-clear"))
    context = SimpleNamespace(
        pages=[], clear_cookies=lambda: sent.append("cookies"),
        storage_state=lambda **_k: {"origins": []},
        new_cdp_session=lambda _page: _Cdp(sent, failing))
    return SimpleNamespace(
        project=SimpleNamespace(base_url="http://app.test/"), _context=context, _page=page,
        page=page, goto=lambda _url: sent.append("goto"))


def test_a_failed_cache_clear_raises_after_the_origin_clears_so_the_pool_discards_it():
    sent: list[str] = []
    with pytest.raises(RuntimeError, match="clearBrowserCache failed"):
        reset_to_logged_out(_session(sent, "Network.clearBrowserCache"))
    assert "Storage.clearDataForOrigin" in sent  # the origin clears ran first
    assert sent.index("Storage.clearDataForOrigin") < sent.index("Network.clearBrowserCache")


def test_a_failed_origin_clear_is_still_best_effort_and_the_cache_is_still_cleared():
    sent: list[str] = []
    reset_to_logged_out(_session(sent, "Storage.clearDataForOrigin"))
    assert "Network.clearBrowserCache" in sent and "page-clear" in sent


def test_a_clean_reset_clears_cookies_origins_cache_and_page_storage():
    sent: list[str] = []
    reset_to_logged_out(_session(sent, None))
    wanted = ("cookies", "Storage.clearDataForOrigin", "Network.clearBrowserCache", "page-clear")
    assert all(step in sent for step in wanted)
