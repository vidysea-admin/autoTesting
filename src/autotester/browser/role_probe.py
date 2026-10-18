"""Page-level reads and viewport sweeps for the multi-role port (MP11, MP25, MP26).

One job: everything `stages/role_session_port.py` needs from a live page, kept inside `browser/`
(the actuator choke-point, `tests/test_actuator_chokepoint.py`). Every function takes a started
`BrowserSession` and must run on that session's own thread (`RoleSessions.run_as`). It looks and
measures; it types nothing and never persists a page: visible text, layouts and screenshots go
back to the caller as in-memory values, and a secret input is masked before any capture.

`ResponseLog` is the one listener that records first-party-candidate responses (document, xhr,
fetch only, so favicons and assets never read as API errors) with a timestamp; it can be paused so
a re-visit made only to measure a layout is not counted as the product's own traffic.
"""

from __future__ import annotations

import collections
import contextlib
import re
import time
from collections.abc import Iterator, Sequence
from typing import Any, NamedTuple
from urllib.parse import urlsplit

from autotester.browser.evidence import MASK_CSS
from autotester.browser.locators import LocatorNotFound, format_label, resolve
from autotester.browser.observe import visual_text

RECORDED_TYPES = frozenset({"document", "xhr", "fetch"})
HISTORY = 2000
MAX_TEXT = 200_000
MAX_CONTROLS = 500
LOOK_TIMEOUT_MS = 1500
Row = tuple[str, str, int, float]

_LAYOUT_JS = """() => {
  const sel = 'a[href],button,input:not([type=hidden]),select,textarea,[role=button],summary';
  const controls = [];
  for (const el of document.querySelectorAll(sel)) {
    const r = el.getBoundingClientRect();
    const st = getComputedStyle(el);
    const hidden = st.visibility === 'hidden' || st.display === 'none';
    if (r.width <= 0 || r.height <= 0 || hidden) continue;
    let name = el.tagName.toLowerCase();
    if (el.id) name += '#' + el.id;
    else if (el.getAttribute('name')) name += '[name=' + el.getAttribute('name') + ']';
    controls.push({name: name.slice(0, 80), left: r.left, right: r.right});
    if (controls.length >= MAX_CONTROLS) break;
  }
  const body = document.body ? document.body.scrollWidth : 0;
  return {width: Math.max(document.documentElement.scrollWidth, body), controls};
}""".replace("MAX_CONTROLS", str(MAX_CONTROLS))


class PageSnapshot(NamedTuple):
    """What one role's page showed right after a step."""

    url: str
    success: str | None
    text: str
    responses: list[Row]


class ResponseLog:
    """Timestamped document/xhr/fetch responses of one page; `take` drains the new ones."""

    def __init__(self) -> None:
        self.pending: list[Row] = []
        self.history: collections.deque[Row] = collections.deque(maxlen=HISTORY)
        self.paused = False
        self._t0 = time.monotonic()
        self._since = 0.0

    def attach(self, session: Any) -> None:
        session.page.on("response", self._on_response)

    def _on_response(self, response: Any) -> None:
        request = response.request
        if self.paused or request.resource_type not in RECORDED_TYPES:
            return
        row = (request.method, response.url, response.status, round(time.monotonic() - self._t0, 3))
        self.pending.append(row)
        self.history.append(row)

    def mark(self) -> None:
        """Responses before now (sign-in traffic) no longer count for `seen`."""
        self._since = round(time.monotonic() - self._t0, 3)

    def take(self) -> list[Row]:
        rows, self.pending = self.pending, []
        return rows

    def seen(self, pattern: str) -> tuple[bool, str]:
        """A response on this route pattern since `mark`? Never a body, never a number."""
        pieces = re.split(r"(\{[^}]*\}|\*)", pattern)
        rx = "".join(".*" if p == "*" else "[^/]+" if p.startswith("{") else re.escape(p)
                     for p in pieces)
        hit = next((r for r in reversed(self.history)
                    if r[3] >= self._since and re.fullmatch(rx, urlsplit(r[1]).path)), None)
        if hit is None:
            return False, ""
        return True, "api response seen: " + ("error" if hit[2] >= 400 else "ok")

    @contextlib.contextmanager
    def quiet(self) -> Iterator[None]:
        """Responses made inside the block are not the product's traffic and are not recorded."""
        before, self.paused = self.paused, True
        try:
            yield
        finally:
            self.paused = before


def look(session: Any, target: str) -> tuple[bool, str]:
    """One look: (is the target visible, its text -- or a count when it matches several)."""
    loc = resolve(session.page, target)
    count = loc.count()
    if count == 0 or not loc.first.is_visible():
        return False, ""
    if count > 1:
        return True, f"{count} items"
    return True, " ".join(loc.first.inner_text(timeout=LOOK_TIMEOUT_MS).split())


def appears(session: Any, target: str, timeout_ms: int = 3000) -> bool:
    """Wait up to `timeout_ms` for `target` to become visible."""
    try:
        resolve(session.page, target).first.wait_for(state="visible", timeout=timeout_ms)
    except Exception:
        return False
    return True


def page_snapshot(session: Any, success_selectors: Sequence[str], log: ResponseLog) -> PageSnapshot:
    """URL, the first visible success element, the page's text and the responses since last step."""
    page = session.page
    success = next((s for s in success_selectors if resolve(page, s).first.is_visible()), None)
    return PageSnapshot(str(page.url), success, visual_text(page)[:MAX_TEXT], log.take())


def field_locator(session: Any, field: str) -> str:
    """The one locator for a form field named `field`: by name, then id, then label."""
    escaped = field.replace("\\", "\\\\").replace('"', '\\"')
    for candidate in (f'[name="{escaped}"]', f'[id="{escaped}"]', format_label(field)):
        if resolve(session.page, candidate).count() == 1:
            return candidate
    raise LocatorNotFound("no single field matched the declared field name")


@contextlib.contextmanager
def _at_viewport(session: Any, log: ResponseLog, width: int, height: int) -> Iterator[Any]:
    """Resize the page, keep the log quiet, then put the size and the page back."""
    page = session.page
    prior_size, prior_url = page.viewport_size, str(page.url)
    try:
        with log.quiet():
            page.set_viewport_size({"width": width, "height": height})
            yield page
    finally:
        with log.quiet():
            if prior_size:
                page.set_viewport_size(prior_size)
            if str(page.url) != prior_url and prior_url.startswith(("http://", "https://")):
                session.goto(prior_url)


def _show(session: Any, url: str) -> None:
    session.goto(url)
    session.settle(timeout_ms=2000)


def measure_screens(session: Any, log: ResponseLog, urls: Sequence[str], width: int,
                    height: int) -> list[dict[str, Any]]:
    """Scroll width and control boxes of each URL at the given viewport, then restore the page."""
    out: list[dict[str, Any]] = []
    with _at_viewport(session, log, width, height) as page:
        for url in urls:
            _show(session, url)
            out.append(page.evaluate(_LAYOUT_JS))
    return out


def screenshot_png(session: Any, log: ResponseLog, url: str, width: int, height: int) -> bytes:
    """A PNG of `url` at the viewport, secret inputs masked; bytes only, nothing is written."""
    with _at_viewport(session, log, width, height) as page:
        _show(session, url)
        page.add_style_tag(content=MASK_CSS)
        return bytes(page.screenshot(full_page=False))
