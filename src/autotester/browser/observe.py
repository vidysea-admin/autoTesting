"""Passive observation: enumerate a page's controls, capture console/network
failures and dialogs. The explorer (Track B3) reads through this — never
`.page` directly — so every browser touch stays inside `browser/` (the
actuator choke-point, `tests/test_actuator_chokepoint.py`).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from autotester.schema.crawl import DialogEvent
from autotester.schema.screen_graph import ElementRef, PageObservation

_ENUMERATE_JS = (Path(__file__).with_name("enumerate.js")).read_text(encoding="utf-8")
_REACH_MARKER = "// AUTOTESTER:REACH_MODULE"
_REACH_PATH = Path(__file__).with_name("visual_order_reach.js")
_VISUAL_ORDER_REACH_JS = _REACH_PATH.read_text(encoding="utf-8")
_VISUAL_ORDER_JS_RAW = (Path(__file__).with_name("visual_order.js")).read_text(encoding="utf-8")
if _REACH_MARKER not in _VISUAL_ORDER_JS_RAW:
    # AT-408/AT-416: reachOf/isReachable moved to their own file to stay under
    # doctor's 300-line cap (C2). They are spliced back in HERE, as TEXT, so
    # `page.evaluate()` still receives the single `(() => {...})();` script
    # shape it always has -- never two top-level scripts sent separately,
    # which risks Playwright parsing the string differently than today. A
    # missing marker means the split silently stopped happening; fail loudly
    # rather than ship a `reachOf`/`isReachable` ReferenceError from the page.
    raise RuntimeError(
        "visual_order.js is missing the AUTOTESTER:REACH_MODULE splice marker "
        "-- visual_order_reach.js would never run")
_VISUAL_ORDER_JS = _VISUAL_ORDER_JS_RAW.replace(_REACH_MARKER, _VISUAL_ORDER_REACH_JS)

DialogAction = Callable[[str], str]  # dialog_type -> "accept" | "dismiss"


def _default_dialog_action(dialog_type: str) -> str:
    """`beforeunload` is accepted (leave the page); every other dialog is
    dismissed — the crawl never blocks on a confirm/alert/prompt (D-016)."""
    return "accept" if dialog_type == "beforeunload" else "dismiss"


class PageObserver:
    """Installed once per session (`BrowserSession(..., observer=...)`).
    Buffers console errors, failed/4xx+ requests, dialogs, and popup counts
    until `drain()` is called."""

    def __init__(self, dialog_action: DialogAction | None = None, *,
                 passive: bool = False) -> None:
        self.dialog_action = dialog_action or _default_dialog_action
        self.passive = passive
        """A passive observer keeps nothing and handles no dialogs: it installs the one response
        listener and fans each response out to `subscribe`d hooks (role sessions, hop traces)."""
        self._hooks: list[Callable[[Any], None]] = []
        self.console: list[str] = []
        self.failed: list[tuple[str, str]] = []
        self.dialogs: list[DialogEvent] = []
        self.popups = 0
        self.responses: list[tuple[str, str, int]] = []
        """T-170/NA1: EVERY response (method, url, status), not only the
        failing ones `.failed` already counts -- the evidence-producing
        second read of `attach`'s one response listener (NA6)."""
        self._attached = False

    def attach(self, page: Any) -> None:
        """Install listeners exactly once. Safe to call more than once — a
        second `attach` on the same observer is a no-op."""
        if self._attached:
            return
        self._attached = True
        if not self.passive:
            page.on("console", self._on_console)
            page.on("requestfailed", self._on_request_failed)
        page.on("response", self._on_response)
        if self.passive:
            return
        page.on("dialog", self._on_dialog)
        if page.context is not None:
            page.context.on("page", self._on_popup)

    def _on_console(self, message: Any) -> None:
        if getattr(message, "type", "") in ("error", "warning"):
            self.console.append(f"{message.type}: {message.text}")

    def _on_request_failed(self, request: Any) -> None:
        failure = getattr(request, "failure", None)
        reason = failure.get("errorText", "failed") if isinstance(failure, dict) else "failed"
        self.failed.append((request.url, reason))

    def subscribe(self, hook: Callable[[Any], None]) -> None:
        """Also call `hook(response)` for every response (NA6: a read of this one listener)."""
        self._hooks.append(hook)

    def unsubscribe(self, hook: Callable[[Any], None]) -> None:
        if hook in self._hooks:
            self._hooks.remove(hook)

    def _on_response(self, response: Any) -> None:
        if not self.passive:
            if response.status >= 400:
                self.failed.append((response.url, str(response.status)))
            # T-170/NA1: every response, independent of status -- the second,
            # evidence-producing read of the same stream (NA6, no second listener).
            method = getattr(getattr(response, "request", None), "method", "GET")
            self.responses.append((method, response.url, response.status))
        for hook in tuple(self._hooks):
            hook(response)

    def _on_dialog(self, dialog: Any) -> None:
        action = self.dialog_action(dialog.type)
        accepted = action == "accept"
        self.dialogs.append(
            DialogEvent(dialog_type=dialog.type, message=dialog.message or "", accepted=accepted)
        )
        if accepted:
            dialog.accept()
        else:
            dialog.dismiss()

    def _on_popup(self, _page: Any) -> None:
        self.popups += 1

    def drain(self) -> tuple[list[str], list[tuple[str, str]], list[DialogEvent], int]:
        """Return and clear everything buffered since the last drain."""
        console, failed, dialogs, popups = self.console, self.failed, self.dialogs, self.popups
        self.console, self.failed, self.dialogs, self.popups = [], [], [], 0
        return console, failed, dialogs, popups

    def drain_responses(self) -> list[tuple[str, str, int]]:
        """Return and clear the (method, url, status) stream since the last
        drain -- kept separate from `drain()` (T-170/NA1) so existing callers
        of `drain()` are unaffected."""
        responses = self.responses
        self.responses = []
        return responses


def response_observer(session: Any) -> PageObserver:
    """The session's observer, so a caller can `subscribe` to responses without a second listener.
    A session started without one gets a passive observer attached to its page (NA6)."""
    if getattr(session, "observer", None) is None:
        session.observer = PageObserver(passive=True)
        session.observer.attach(session.page)
    return session.observer  # type: ignore[no-any-return]


def enumerate_elements(page: Any) -> list[ElementRef]:
    """Run `enumerate.js` and validate its output into `ElementRef`s."""
    raw = page.evaluate(_ENUMERATE_JS)
    return [ElementRef(**item) for item in raw]


def visual_text(page: Any) -> str:
    """The page's text in VISUAL reading order — what a reader sees, not what
    the DOM stores.

    AT-358. Every instrument this module had (`innerText`, element names, the
    enumerated controls) reports DOCUMENT order, and a bidi override makes the
    two disagree: AT-355 stored a credential backwards and rendered it
    forwards, so every DOM-order check called the page clean while a human
    could read the secret off it in plain type. Characters that paint no box
    are dropped, so a zero-width space or a NUL the parser deleted cannot hide
    inside the result either.

    This is an observation capability, not a test helper: reading other
    people's rendered pages is what this product does.
    """
    return str(page.evaluate(_VISUAL_ORDER_JS))


def observe(session: Any) -> PageObservation:
    """One page-visit's observation: url, title, interactive elements."""
    page = session.page
    return PageObservation(
        url=str(page.url), title=str(page.title()), elements=enumerate_elements(page),
    )
