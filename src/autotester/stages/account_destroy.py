"""One job: decide whether a control would destroy the account (Umesh 2026-10-15, D-098).

THE one list and THE one matcher. The crawler, the case guard, BrowserSession and the browser-use
actuator all ask this module. Matching is case-insensitive over the accessible name, text and
aria-label, read three ways: spaced (camelCase split, separators folded), joined (`closeaccount`),
and by href path (`/account/delete`). Bare verbs (`Deactivate`, `Terminate`, `Delete user`) count
only on an account/profile/settings page, and Confirm/Yes/OK count only inside a short-lived
"destroy context" opened by an earlier destroy-like request.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from urllib.parse import urlsplit

ACCOUNT_DESTROY_REFUSED = "not exercised: account-destroying (policy)"
"""The one report wording for a control never clicked because it destroys the account."""

_VERB = r"(?:close|delete|deactivate|terminate|cancel|erase|destroy|remove|deregister|wipe)"
_NOT_SUBOBJECT = (r"(?!\s+(?:photo|picture|image|avatar|pic|icon|link|url|name|settings|menu|"
                  r"dialog|panel|tab|switcher|dropdown|form)\b)")
ACCOUNT_DESTROY_PATTERNS = (
    rf"\b{_VERB}\b(?:\s+(?:my|your|the|this|own|entire|whole|all))*\s+"
    rf"(?:account|profile)\b{_NOT_SUBOBJECT}",
    rf"\b{_VERB}\b(?:\s+(?:my|your|the|this|own|entire|whole|all|of))*\s+"
    r"(?:data|information)\b(?:\s+(?:permanently|forever))?$",
    r"\bpermanently\s+delete\b", r"\bdelete\s+me\b", r"\bright to be forgotten\b",
)
# `closeaccount`, `DeleteMyProfile` once every separator is gone (anchored: whole label only).
JOINED_PATTERNS = (
    r"^(?:close|delete|deactivate|terminate|erase|destroy|deregister|wipe)(?:my|your|the)?"
    r"(?:account|profile|data)$",
)
# Bare verbs: destructive only where the page is the user's own account/profile/settings.
BARE_PATTERNS = (r"^(?:deactivate|terminate|delete users?|delete profile)$",)
ACCOUNT_PAGE = re.compile(r"\b(?:account|profile|settings|preferences|security|privacy)\b",
                          re.IGNORECASE)
# Href paths: /account/delete, /profile/close, /deactivate, /delete-account ...
HREF_PATTERNS = (
    r"^/(?:[\w-]+/)*(?:account|profile|user|me|settings)/(?:delete|close|deactivate|terminate"
    r"|destroy|erase)(?:[-_](?:account|profile))?/?$",
    r"^/(?:deactivate|terminate)(?:[-_](?:account|profile))?/?$",
    r"^/(?:[\w-]+/)*(?:delete|close|deactivate|terminate|erase)[-_](?:my[-_])?(?:account|profile)/?$",
)
CONFIRM_PATTERN = r"^(?:confirm|yes|yes delete.*|yes close.*|yes i am sure|ok|okay|proceed)$"
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_SEP = re.compile(r"[-_./+|,]+")
_WS = re.compile(r"\s+")


def _spaced(label: str) -> str:
    return _WS.sub(" ", _SEP.sub(" ", _CAMEL.sub(" ", label))).strip().casefold()


def _joined(label: str) -> str:
    return re.sub(r"[\W_]+", "", label).casefold()


def _any(patterns: tuple[str, ...], text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


class DestroyContext:
    """A short-lived flag: a destroy-like request was just seen, so a Confirm/Yes/OK that
    follows (same step or page) is part of the same destroy and is refused too."""

    def __init__(self, ttl_s: float = 30.0, clock: Callable[[], float] = time.monotonic) -> None:
        self.ttl_s, self.clock, self._until = ttl_s, clock, 0.0

    def note(self) -> None:
        self._until = self.clock() + self.ttl_s

    def active(self) -> bool:
        return self.clock() < self._until


def destroying_href(href: str | None) -> bool:
    """True if the link's path (not its text) is an account-destroying route."""
    if not href:
        return False
    path = urlsplit(href.strip()).path.casefold()
    return _any(HREF_PATTERNS, path)


def destroys_account(*labels: str | None, href: str | None = None, context: str = "",
                     ctx: DestroyContext | None = None) -> bool:
    """True if any label (name, text, aria-label, locator), the href, or the page `context`
    (URL + heading) says this control destroys the account. A match opens `ctx`."""
    hit = destroying_href(href)
    for label in (lb for lb in labels if lb):
        spaced = _spaced(label)
        hit = hit or _any(ACCOUNT_DESTROY_PATTERNS, spaced) or _any(JOINED_PATTERNS,
                                                                    _joined(label))
        hit = hit or (bool(ACCOUNT_PAGE.search(context)) and _any(BARE_PATTERNS, spaced))
        hit = hit or (ctx is not None and ctx.active() and _any((CONFIRM_PATTERN,), spaced))
    if hit and ctx is not None:
        ctx.note()
    return hit
