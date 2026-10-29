"""D-115 (1) fix cycle 1: `reset_to_logged_out` on a REAL headless Chromium (loopback only).

The fakes in `test_entry_browser_reuse_run.py` cannot see what Chromium actually keeps: the
CDP `Storage.clearDataForOrigin` call does not cover sessionStorage (checker A, F1), and login
state on a second origin (an SSO host) is outside the base and landing origins (checker B, W1).
Two `serve_dir` servers are two loopback origins. Skipped when no Chromium binary is installed.
"""

from __future__ import annotations

import http.server
import threading
from collections.abc import Callable, Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest

from autotester.browser.entry_reset import reset_to_logged_out

_PAGE = "<!doctype html><title>t</title><p>start page: sets nothing</p>"
_STORED = "() => [localStorage.getItem('L'), sessionStorage.getItem('S')]"


@pytest.fixture
def chromium() -> Iterator[object]:
    playwright = pytest.importorskip("playwright.sync_api")
    runner = None
    try:
        runner = playwright.sync_playwright().start()
        browser = runner.chromium.launch(headless=True)
    except Exception as exc:  # no browser binary on this machine
        if runner is not None:
            runner.stop()
        pytest.skip(f"chromium unavailable: {type(exc).__name__}")
    yield browser
    browser.close()
    runner.stop()


def _site(tmp_path: Path, name: str, serve_dir: Callable[[Path], str]) -> str:
    root = tmp_path / name
    root.mkdir()
    (root / "index.html").write_text(_PAGE, encoding="utf-8")
    return serve_dir(root)


def test_reset_clears_cookie_local_session_storage_and_a_second_origin_on_real_chromium(
    chromium, tmp_path: Path, serve_dir: Callable[[Path], str],
) -> None:
    base, sso = _site(tmp_path, "app", serve_dir), _site(tmp_path, "sso", serve_dir)
    context = chromium.new_context()
    page = context.new_page()
    context.add_cookies([{"name": "sid", "value": "secret", "url": base, "httpOnly": True}])
    page.goto(f"{base}/index.html")
    page.evaluate("() => { localStorage.setItem('L', '1'); sessionStorage.setItem('S', '1'); }")
    other = context.new_page()  # a stray tab on the second origin, with its own login state
    other.goto(f"{sso}/index.html")
    other.evaluate("() => localStorage.setItem('L', 'sso-token')")
    assert [c["httpOnly"] for c in context.cookies()] == [True]  # the fixture is real
    assert page.evaluate(_STORED) == ["1", "1"]

    session = SimpleNamespace(
        project=SimpleNamespace(base_url=f"{base}/"), _context=context, _page=page, page=page,
        goto=lambda url: page.goto(url))
    reset_to_logged_out(session)

    assert context.cookies() == []  # the HttpOnly cookie too
    assert len(context.pages) == 1 and context.pages[0] is page
    assert page.evaluate(_STORED) == [None, None]  # localStorage AND sessionStorage, same tab
    probe = context.new_page()
    probe.goto(f"{sso}/index.html")
    assert probe.evaluate(_STORED) == [None, None]  # the second origin's storage is gone too
    context.close()


_IDB_PUT = """() => new Promise((resolve, reject) => {
  const open = indexedDB.open('auth', 1);
  open.onupgradeneeded = () => open.result.createObjectStore('kv');
  open.onsuccess = () => {
    const tx = open.result.transaction('kv', 'readwrite');
    tx.objectStore('kv').put('token', 'jwt');
    tx.oncomplete = () => { open.result.close(); resolve(true); };
  };
  open.onerror = () => reject(open.error);
})"""
_IDB_NAMES = "async () => (await indexedDB.databases()).map(d => d.name)"


def test_reset_clears_indexeddb_on_a_second_origin_that_holds_no_local_storage(
    chromium, tmp_path: Path, serve_dir: Callable[[Path], str],
) -> None:
    """Checker B cycle-1 W2: `storage_state()` lists only origins with localStorage, so an SSO
    origin whose login lives in IndexedDB alone was never cleared."""
    base, sso = _site(tmp_path, "app", serve_dir), _site(tmp_path, "sso", serve_dir)
    context = chromium.new_context()
    page = context.new_page()
    page.goto(f"{base}/index.html")
    other = context.new_page()
    other.goto(f"{sso}/index.html")
    other.evaluate(_IDB_PUT)  # IndexedDB only: no localStorage on this origin
    assert other.evaluate(_IDB_NAMES) == ["auth"]  # the fixture is real
    session = SimpleNamespace(
        project=SimpleNamespace(base_url=f"{base}/"), _context=context, _page=page, page=page,
        goto=lambda url: page.goto(url))
    reset_to_logged_out(session)
    probe = context.new_page()
    probe.goto(f"{sso}/index.html")
    assert probe.evaluate(_IDB_NAMES) == []  # the IndexedDB-only origin is cleared too
    context.close()


class _CachedPage(http.server.BaseHTTPRequestHandler):
    """`/cached`: LOGGED-IN-ONLY with a `sid` cookie, PLEASE-LOGIN without; freshness 10 minutes."""

    def log_message(self, *_args: object) -> None:
        pass

    def do_GET(self) -> None:
        mine = "sid=" in (self.headers.get("Cookie") or "")
        body = b"LOGGED-IN-ONLY" if mine else b"PLEASE-LOGIN"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Cache-Control", "private, max-age=600")
        self.end_headers()
        self.wfile.write(b"<!doctype html><title>t</title><h1 id=h>" + body + b"</h1>")


def test_reset_drops_the_http_cache_so_a_logged_out_case_never_sees_a_cached_login(
    chromium,
) -> None:
    """Checker B cycle-2 W1: a document served `max-age` while logged in stayed in the HTTP cache
    after the reset, so the next logged-out entry case was handed the authenticated body without a
    request. The wiped-profile launch this unit replaces removed the cache with the directory."""
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _CachedPage)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        context = chromium.new_context()
        page = context.new_page()
        context.add_cookies([{"name": "sid", "value": "s", "url": base}])
        page.goto(f"{base}/cached")
        assert page.inner_text("#h") == "LOGGED-IN-ONLY"  # the fixture is real, and now cached
        session = SimpleNamespace(
            project=SimpleNamespace(base_url=f"{base}/"), _context=context, _page=page,
            page=page, goto=lambda url: page.goto(url))
        reset_to_logged_out(session)
        assert context.cookies() == []
        page.goto(f"{base}/cached")
        assert page.inner_text("#h") == "PLEASE-LOGIN"  # fetched fresh, not the cached login
        context.close()
    finally:
        server.shutdown()
        server.server_close()
