"""First-party network capture as evidence (T-170, NA1/NA2/NA4/NA5/NA6).

Turns `PageObserver`-buffered `(method, url, status)` responses into
`EvidenceKind.NETWORK` evidence -- one item per FIRST-PARTY response,
independent of status (NA1). Third-party/noise hosts are excluded by
reusing `explore_safety.classify_request` (X9, C3) rather than a second
classifier. Every URL passes through the caller's `Redactor` before it
becomes evidence (NA5, core-invariants C5). Pure data transform: no
browser, no provider (NA4), and nothing here assigns a verdict (NA2, C7) --
`stages/execute.py` (a run) and `stages/explore.py` (a crawl) both call
this, so the ONE capture mechanism (NA6) has ONE conversion too (C3).
"""

from __future__ import annotations

from urllib.parse import urlsplit

from autotester.core.redact import Redactor
from autotester.core.urls import url_template
from autotester.schema.crawl import SafetyPolicy
from autotester.schema.enums import EvidenceKind
from autotester.schema.project import Project
from autotester.schema.run import Evidence
from autotester.schema.screen_graph import ApiCall
from autotester.stages.explore_safety import classify_request


def first_party_evidence(
    responses: list[tuple[str, str, int]],
    project: Project,
    policy: SafetyPolicy,
    redactor: Redactor,
    *,
    step_order: int | None = None,
) -> list[Evidence]:
    """One `EvidenceKind.NETWORK` item per first-party `(method, url,
    status)` response in `responses`; third-party/noise hosts produce none."""
    items: list[Evidence] = []
    for method, url, status in responses:
        if classify_request(url, project, policy) != "first_party":
            continue
        items.append(Evidence(
            kind=EvidenceKind.NETWORK,
            path=redactor.scrub(f"{method} {url} -> {status}"),
            step_order=step_order,
            label="network",
        ))
    return items


MAX_API_CALLS_PER_NODE = 100
"""Bound on the distinct (method, path, status) rows kept per screen (X4: nothing unbounded)."""

_ASSET_SUFFIXES = (".js", ".mjs", ".css", ".map", ".png", ".jpg", ".jpeg", ".gif", ".svg",
                   ".webp", ".ico", ".woff", ".woff2", ".ttf", ".otf")


ApiKey = tuple[str, str, int]
"""(METHOD, path pattern, status): one row of a screen's tally."""


def count_api_calls(
    responses: list[tuple[str, str, int]], project: Project, policy: SafetyPolicy,
    redactor: Redactor, counts: dict[ApiKey, int],
) -> None:
    """Add XHR/fetch `(method, url, status)` responses to `counts`, in place: first-party only,
    status < 400, static assets and the framework's own `/_next/` routes dropped, path
    `url_template`'d and redacted (no query, no host). The tally is constant-size in the number
    of calls (a poll adds 1 to a counter, not a row) and holds at most `MAX_API_CALLS_PER_NODE`
    distinct keys: a new key past the cap is dropped, an existing one still counts."""
    for method, url, status in responses:
        path = urlsplit(url).path.lower()
        if (status >= 400 or classify_request(url, project, policy) != "first_party"
                or path.endswith(_ASSET_SUFFIXES) or path.startswith("/_next/")):
            continue
        key = (method.upper(), redactor.scrub(url_template(url, keep_host=False)), status)
        if key in counts or len(counts) < MAX_API_CALLS_PER_NODE:
            counts[key] = counts.get(key, 0) + 1


def api_rows(counts: dict[ApiKey, int]) -> list[ApiCall]:
    """The tally as sorted `ApiCall` rows."""
    return [ApiCall(method=m, path=p, status=s, count=n) for (m, p, s), n in sorted(counts.items())]


def api_inventory(
    responses: list[tuple[str, str, int]], project: Project, policy: SafetyPolicy,
    redactor: Redactor,
) -> list[ApiCall]:
    """One `ApiCall` row per (method, path pattern, status) in `responses`."""
    counts: dict[ApiKey, int] = {}
    count_api_calls(responses, project, policy, redactor, counts)
    return api_rows(counts)
