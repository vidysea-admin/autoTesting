"""Put a reused entry browser back to a genuinely logged-out state between two entry cases.

One job: D-115 (1) runs a run's entry cases in ONE Chromium instead of one wiped-profile launch
each, so what the wipe used to guarantee (every entry case starts logged out, AT-733 / RU5) is
re-established here, in place, before each reuse. Closes stray tabs, clears the context's cookies,
lands on the project's start URL through `session.goto` (so allowed-domains scoping, B6, still
applies) and clears that origin's web storage. Any failure raises: the caller then discards the
browser and launches a fresh wiped one, so a case never runs on state this function could not
clear. Native dialogs need no handling: Playwright auto-dismisses them when no handler is set.
"""

from __future__ import annotations

import contextlib
from typing import Any
from urllib.parse import urlsplit

_CLEAR_STORAGE_JS = "() => { localStorage.clear(); sessionStorage.clear(); }"


def _origin(url: str) -> str | None:
    parts = urlsplit(url or "")
    return f"{parts.scheme}://{parts.netloc}" if parts.scheme in ("http", "https") else None


def _clear_origin_storage(session: Any, origins: list[str]) -> None:
    """Storage of the page's origins: DevTools `clearDataForOrigin` (all types, service workers
    and IndexedDB included), else the page's own localStorage and sessionStorage."""
    try:
        cdp = session._context.new_cdp_session(session._page)
        try:
            for origin in origins:
                cdp.send("Storage.clearDataForOrigin", {"origin": origin, "storageTypes": "all"})
        finally:
            with contextlib.suppress(Exception):
                cdp.detach()
    except Exception:  # no DevTools session: the page's own storage still goes
        session.page.evaluate(_CLEAR_STORAGE_JS)


def reset_to_logged_out(session: Any) -> None:
    """Return `session` to a logged-out, single-tab state on the project's start URL."""
    context, keep = session._context, session._page
    for page in list(context.pages):
        if page is not keep:
            with contextlib.suppress(Exception):
                page.close()
    context.clear_cookies()
    base = session.project.base_url
    session.goto(base)
    origins = [o for o in dict.fromkeys((_origin(base), _origin(session.page.url))) if o]
    _clear_origin_storage(session, origins)
