"""URL templating: the identity input a crawled screen shares with the
ingest pipeline (`core.urls.url_template` is the ONLY place a URL is
normalised into a screen-identity path — `stages/ingest.py` A2 and
`stages/screen_identity.py` B2 both call this instead of reimplementing it).

A numeric/uuid/ULID/hex/date-shaped path segment is templated to `{id}` or
`{date}` so `/students/1` and `/students/2` collapse to the same identity,
while `/students/me` (not id-shaped) is left alone.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

_NUMERIC = re.compile(r"^\d+$")
_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)
_ULID = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")  # Crockford base32, no I/L/O/U
_HEX = re.compile(r"^[0-9a-f]{16,}$", re.IGNORECASE)
_DATE = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")
_INDEX_SEGMENTS = {"index.html", "index.htm"}


def _template_segment(segment: str) -> str:
    if not segment:
        return segment
    if _DATE.match(segment):
        return "{date}"
    if _NUMERIC.match(segment) or _UUID.match(segment) or _ULID.match(segment) or _HEX.match(
        segment
    ):
        return "{id}"
    return segment


def absolute_url(url: str) -> str:
    """Restore the scheme a browser hid, so the host is never read as a path.

    An address bar shows an ABSOLUTE url, and every mainstream browser now hides
    `https://` — so a vision model transcribing one returns `vidysea.com/erp/trainers`,
    not `https://vidysea.com/erp/trainers`. `urlsplit` has no `//` to anchor on
    there, puts the host in `.path`, and `url_template` templates it as a path
    segment: `/vidysea.com/erp/trainers`. That is AT-294, and it is why the same
    screen learned from a video and found by a crawl still did not collapse to
    one row after both producers were switched to `keep_host=False` — the flags
    agreed, the inputs did not.

    Callers holding a genuine relative path must not use this. In practice they
    sometimes do anyway -- an ingest observation is a model's transcription, not
    a validated address bar -- and AT-299b is what that costs: prepending
    `https://` unconditionally makes `urlsplit` read the FIRST segment as the
    host no matter what it is, so `keep_host=False` silently deletes it even
    when it was real path (`erp/trainers` -> `https://erp/trainers` -> `/trainers`,
    losing "erp"; `students/1` -> `/{id}`, losing "students").

    The guard: only treat the first segment as a host when it carries a signal
    an address bar's host actually has -- a domain dot (`vidysea.com`) or a port
    colon (`localhost:3000`). Narrower than the whole-string host-shape guessing
    AT-287's first fix tried and failed at (`settings.json` vs `example.com` --
    genuinely indistinguishable): this only asks whether the first segment of an
    already-multi-part string looks host-like, so a relative path built from
    real segments (`erp/trainers`, `students/1`) carries neither signal and is
    left alone. `localhost/students` is likewise left as a path -- `localhost`
    alone has no dot or colon. Residual, accepted gap: a first segment that
    itself contains a dot (`v1.2/foo`, `settings.json/edit`) still reads as a
    host. A related, separate ambiguity -- a bare dotted/ported token with NO
    path at all (`file.html`, `example.com`) still promotes here and then
    templates to `/`, indistinguishable by shape from a real host's root -- is
    resolved by `screen_url_pattern` below, not here (AT-299b cycle 2).
    """
    if not url or "//" in url.split("?", 1)[0][:8]:
        return url
    if url.startswith("/"):
        return url
    first_segment = url.split("/", 1)[0].split("?", 1)[0]
    if "." not in first_segment and ":" not in first_segment:
        return url
    return f"https://{url}"


def url_template(url: str, *, keep_host: bool = True, fold_index: bool = False) -> str:
    """Normalise `url` to a screen-identity path: strip query/fragment,
    collapse repeated slashes, template id/date-shaped segments, and drop a
    trailing slash (the root `/` is kept as-is).

    **Idempotent for path-shaped input only** — `url_template(p) == p` for any
    `p` this function produced with `keep_host=False`. It is NOT idempotent over
    its own `keep_host=True` output: `urlsplit("demo.test/x")` has no `//`, so
    the host lands in `.path` and re-templating yields `/demo.test/x`.

    That asymmetry is why `Screen.url_pattern` is stored host-LESS by every
    producer (`stages/ingest.py`, `stages/explore_merge.py`,
    `stages/product_map.py`, `stages/screen_identity.py`) — a path pattern, not
    a browsing identity. AT-287: two producers stored it host-ful, coverage
    re-templated it to compare, and the screen became invisible. Inferring
    host-ness back out of a schemeless string is impossible in principle —
    `settings.json` and `example.com` are the same shape — so the fix is one
    canonical stored shape, not a smarter parser.

    AT-334: pass `fold_index=True` to fold a trailing `index.html`/`index.htm`
    PATH SEGMENT away before templating, so a directory index reached by its
    bare directory URL and by its served filename collapse to one identity:
    `/index.html` -> `/`, `/docs/index.html` -> `/docs` — matching whatever
    the directory form ALREADY normalises to under the trailing-slash rule
    above, never a new third shape (`/docs/` -> `/docs` already; folding to
    `/docs/` instead would break that idempotence). Exact, case-SENSITIVE
    match only — `myindex.html`, `index.html.bak`, `index.php` and
    `/Index.html` are untouched; guessing case-insensitively is the kind of
    shape-based inference AT-287/AT-299b already paid for getting wrong.

    **Default OFF.** `scripts/migrate_url_patterns.py::repair` calls this
    directly and its own tests pin `/index.html` as an unchanged remainder
    once a real declared host is stripped — that script sits behind its own
    unanswered gate (`qa/gates/t135-url-pattern-data-migration.md`) and
    AT-334 does not authorize touching it. Opt-in keeps `repair` unchanged;
    only `stages/screen_identity.py::node_from` and `screen_url_pattern`
    below pass `fold_index=True`."""
    parts = urlsplit(url)
    segments = [seg for seg in parts.path.split("/") if seg != ""]
    if fold_index and segments and segments[-1] in _INDEX_SEGMENTS:
        segments = segments[:-1]
    templated = "/".join(_template_segment(seg) for seg in segments)
    path = f"/{templated}" if segments else "/"
    if keep_host and parts.netloc:
        return f"{parts.netloc}{path}"
    return path


def screen_url_pattern(raw: str | None) -> str | None:
    """The ONE boundary where an observed url becomes a stored `url_pattern` —
    `Screen.url_pattern` (`stages/ingest.py`), `MappedScreen.url_pattern`
    (`stages/product_map.py`, both call sites), and the login case's own
    target (`stages/explore_status.py::login_template`) all call this instead
    of each composing `url_template(absolute_url(x), keep_host=False)` and
    re-deciding the None-vs-"/" question for themselves.

    AT-299b cycle 2: that composition alone still turns a schemeless,
    slash-free, dotted/ported token — `file.html`, `example.com`, `report.pdf`,
    `sitemap.xml` — into `/`, a false claim that the site ROOT is covered.
    `absolute_url` promotes such a token to a host (needed so a REAL bare host
    like `example.com` still normalises correctly), and once promoted, a token
    with no path at all is indistinguishable BY SHAPE from a real host's root —
    the same "settings.json vs example.com" ambiguity `url_template`'s own
    docstring already names for AT-287. `absolute_url` must keep promoting
    (turning off promotion would misfile a genuine bare host as a path segment:
    `example.com` -> `/example.com`); the fix is not to stop the guess, but to
    not report `/` when nothing in the raw string actually asked for a root. I7
    already makes `None` the honest, normal outcome for "no pattern is
    knowable" — so this reports None instead, exactly for that one ambiguous
    shape.

    A root is still reported whenever the raw string is not ambiguous:
    `raw == "/"`, a real scheme or scheme-relative input (`absolute_url` left
    it untouched precisely because it already had one), or an explicit
    trailing slash after a promoted host (`example.com/`). Only a bare,
    slash-free promoted token collapses to None instead of `/`.

    AT-334: `fold_index=True` here, so a stored `Screen.url_pattern` folds a
    trailing `index.html`/`index.htm` exactly like `ScreenNode.url_template`
    does (`stages/screen_identity.py::node_from`) — the two boundaries X15
    already requires to reduce to the same identity for coverage to compare
    them at all. This is the one direct caller of `url_template` that opts in
    alongside `node_from`; `scripts/migrate_url_patterns.py::repair` calls
    `url_template` on its own and deliberately does not.
    """
    if not raw:
        return None
    templated = url_template(absolute_url(raw), keep_host=False, fold_index=True)
    if templated != "/":
        return templated
    before_query = raw.split("?", 1)[0]
    if raw.startswith("/") or "//" in before_query[:8]:
        return "/"  # already-absolute path, or a genuine scheme/scheme-relative input
    if "/" in before_query:
        return "/"  # e.g. "example.com/" -- an explicit trailing slash after the host
    return None  # a bare token ("file.html", "example.com") -- ambiguous, AT-287/AT-299b
