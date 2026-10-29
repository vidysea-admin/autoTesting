"""Put a reused entry browser back to a genuinely logged-out state between two entry cases.

One job: D-115 (1) runs a run's entry cases in ONE Chromium instead of one wiped-profile launch
each, so what the wipe used to guarantee (every entry case starts logged out, AT-733 / RU5) is
re-established here, in place, before each reuse. Closes stray tabs, clears the context's cookies,
lands on the project's start URL through `session.goto` (so allowed-domains scoping, B6, still
applies) and clears that origin's web storage and the browser's HTTP cache. A failure to empty
the HTTP cache, to run the page's own storage clear or to reach the start URL raises: the caller
then discards the browser and launches a fresh wiped one, so a case never runs on state this
function could not clear (the DevTools per-origin clear alone is best effort). Native dialogs
need no handling: Playwright auto-dismisses them when no handler is set.
"""

from __future__ import annotations

import contextlib
from typing import Any
from urllib.parse import urlsplit

_CLEAR_STORAGE_JS = "() => { localStorage.clear(); sessionStorage.clear(); }"


def _origin(url: str) -> str | None:
    parts = urlsplit(url or "")
    return f"{parts.scheme}://{parts.netloc}" if parts.scheme in ("http", "https") else None


def _known_origins(session: Any, base: str) -> list[str]:
    """Every origin whose state could hold a login: the start URL's, the page's now, and each one
    the context holds local storage or IndexedDB for (an SSO host the previous case signed in on).
    A CacheStorage-only origin cannot be listed by Playwright or DevTools, so it is not reached."""
    try:
        state = session._context.storage_state(indexed_db=True)  # also origins with only IndexedDB
        stored = [o.get("origin") for o in state.get("origins", [])]
    except Exception:  # unreadable state: the two known origins still clear
        stored = []
    found = (_origin(base), _origin(session.page.url), *(_origin(o or "") for o in stored))
    return [o for o in dict.fromkeys(found) if o]


def _clear_devtools_storage(session: Any, origins: list[str]) -> None:
    """DevTools `clearDataForOrigin` (local storage, IndexedDB, caches, service workers). It has no
    session-storage type, so `reset_to_logged_out` always follows it with the page's own clear.
    It does not reach the HTTP cache; `_clear_http_cache` does."""
    cdp = session._context.new_cdp_session(session._page)
    try:
        for origin in origins:
            cdp.send("Storage.clearDataForOrigin", {"origin": origin, "storageTypes": "all"})
    finally:
        with contextlib.suppress(Exception):
            cdp.detach()


def _clear_http_cache(session: Any) -> None:
    """`Network.clearBrowserCache`: a `max-age` document fetched while logged in would otherwise be
    served to the logged-out case. Unlike the storage clears it is never suppressed: if the cache
    cannot be emptied the reset raises and the pool launches a fresh wiped browser (fail closed)."""
    cdp = session._context.new_cdp_session(session._page)
    try:
        cdp.send("Network.clearBrowserCache")
    finally:
        with contextlib.suppress(Exception):
            cdp.detach()


def reset_to_logged_out(session: Any) -> None:
    """Return `session` to a logged-out, single-tab state on the project's start URL."""
    context, keep = session._context, session._page
    for page in list(context.pages):
        if page is not keep:
            with contextlib.suppress(Exception):
                page.close()
    base = session.project.base_url
    origins = _known_origins(session, base)  # read before the clear empties the list
    context.clear_cookies()
    session.goto(base)
    origins = list(dict.fromkeys([*origins, *_known_origins(session, base)]))
    with contextlib.suppress(Exception):  # no DevTools session: the page's own clear still runs
        _clear_devtools_storage(session, origins)
    _clear_http_cache(session)  # raises on failure: a stale cached login must never survive
    session.page.evaluate(_CLEAR_STORAGE_JS)  # sessionStorage lives only here; a failure raises
    session.goto(base)  # the app starts from the cleared state, not from what it held in memory
