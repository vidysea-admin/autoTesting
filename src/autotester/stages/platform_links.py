"""Follow every declared PlatformLink and account for it (MP12).

One job: for each `Project.platform_links` row, drive the from-platform's role account through
the hop, watch every main-frame navigation it causes, and return a typed `LinkOutcome`: followed,
failed with a reason, or not reached. A navigation to a host outside EVERY declared platform is
aborted in the browser before that host is contacted, and becomes an `OFF_PLATFORM_HOP`
`MultiRoleFinding` (T-209) carrying only a value-free repro (ids and query values are placeholders).

The verdict rules live in the pure `judge_hops`; the browser work lives in `trace_link`, which
`follow_platform_links` takes as a parameter so the accounting is testable without a browser.
It wraps `browser/session.py` (public methods) and `browser/role_probe.HopWatch`, and touches no
page itself (the actuator choke-point).
"""

from __future__ import annotations

import contextlib
import re
from collections.abc import Callable
from typing import Any
from urllib.parse import parse_qsl, urljoin, urlsplit

from autotester.browser.locators import LocatorNotFound, format_role
from autotester.browser.role_probe import HopWatch
from autotester.browser.secrets import bad_scheme, host_of
from autotester.schema.leak_evidence import contains_personal_shape, segment_is_id_like
from autotester.schema.link_outcome import LinkOutcome, LinkStatus
from autotester.schema.multi_role_enums import FindingClass
from autotester.schema.multi_role_finding import MultiRoleFinding
from autotester.schema.platform import Platform
from autotester.schema.platform_link import PlatformLink
from autotester.schema.project import Project
from autotester.schema.role_account import RoleAccount
from autotester.stages.multi_role_session import RoleSessions, host_in_platform

Trace = tuple[list[str], str | None, int | None, str | None]
"""What a trace saw: main-frame navigation URLs in order, landing URL, its HTTP status, error."""
Verdict = tuple[LinkStatus, str | None, str | None]
"""(status, reason, the stray host[:port] when a hop left every declared platform)."""

MAX_REASON = 300


_URL = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://\S+")


def _safe_reason(exc: BaseException) -> str:
    """Exception class plus its first line with every URL (and so every query) removed."""
    first = (str(exc).splitlines() or [""])[0]
    return f"{type(exc).__name__}: {_URL.sub('<url>', first)}"[:MAX_REASON]


def _netloc(url: str) -> str:
    """`host[:port]`, lowercase, no userinfo; empty when the URL has no usable host."""
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    try:
        port = parts.port
    except ValueError:
        port = None
    return f"{host}:{port}" if host and port else host


def judge_hops(project: Project, link: PlatformLink, hops: list[str], landing_url: str | None,
               status: int | None, error: str | None) -> Verdict:
    """Decide one link from what a trace saw. First match wins, in this order:
    a hop outside every declared platform, a browser error, an HTTP error status, no landing,
    a landing on a host other than `expected_landing_host` (port compared only if declared)."""
    platforms = project.effective_platforms()
    for url in hops:
        host = host_of(url)
        if (not host or bad_scheme(url)
                or not any(host_in_platform(p, host) for p in platforms)):
            return (LinkStatus.FAILED,
                    "a hop reached a host outside every declared platform; "
                    "the link was not followed further",
                    _netloc(url) or "unparseable")
    if error:
        return LinkStatus.FAILED, error, None
    if status is not None and status >= 400:
        return LinkStatus.FAILED, f"the landing page answered HTTP {status}", None
    if not landing_url:
        return LinkStatus.FAILED, "the trigger did not navigate anywhere", None
    expected = link.expected_landing_host
    landed = _netloc(landing_url) if ":" in expected else host_of(landing_url)
    if landed != expected:
        return LinkStatus.FAILED, f"landed on {landed or 'no host'}, expected {expected}", None
    return LinkStatus.FOLLOWED, None, None


def _click_control(session: Any, name: str) -> None:
    """Click the link or button called `name` (a declared control is a human-visible name)."""
    for role in ("link", "button"):
        try:
            session.click(format_role(role, name))
            return
        except LocatorNotFound:
            continue
    raise LocatorNotFound(f"no link or button named {name!r}")


def _outside_fn(platforms: list[Platform]) -> Callable[[str], bool]:
    """A URL is outside when it has no host, a non-web scheme, or a host on no declared platform."""
    def outside(url: str) -> bool:
        host = host_of(url)
        return (not host or bool(bad_scheme(url))
                or not any(host_in_platform(p, host) for p in platforms))
    return outside


def trace_link(session: Any, project: Project, link: PlatformLink) -> Trace:
    """Drive `link` once in `session` and report what the main frame did.

    Hops come from `request` events, which include every redirect the browser follows. Containment
    has two layers. A route guard fetches the first request of a navigation without following
    redirects and aborts it when the page it asks for, or the redirect it answers with, is outside
    every declared platform: that stray host is never contacted. A redirect further down a chain
    is followed inside the browser (Playwright does not route it), so it is detected from the
    events, judged, and the page is parked on `about:blank`. Errors are returned, not raised, so
    the hops are still judged."""
    platforms = project.effective_platforms()
    start = next(p for p in platforms if p.id == link.from_platform)
    outside = _outside_fn(platforms)
    watch = HopWatch(session, outside)
    watch.attach()
    error: str | None = None
    try:
        _drive(session, start.base_url, link)
        session.settle()
    except Exception as exc:  # -- judged with the hops, never lost
        error = _safe_reason(exc)
    finally:
        watch.detach()
    with contextlib.suppress(Exception):
        now = session.current_url()
        if outside(now) and now != "about:blank":
            watch.park()
            now = ""
        landing = None if error or not now else now
    return watch.hops, landing, watch.status, error


def _drive(session: Any, base_url: str, link: PlatformLink) -> None:
    """Fire the link's trigger: open its url_template, or find and click its control."""
    if link.url_template:
        if "{" in link.url_template:
            raise ValueError("the link's url_template still has unfilled placeholders")
        session.goto(urljoin(base_url, link.url_template))
        return
    session.goto(base_url)  # a known page to find the control on
    _click_control(session, link.control_name or "")


def _param(name: str) -> str:
    return re.sub(r"[^a-z]+", "_", name.lower()).strip("_") or "value"


def _template_of(url: str) -> str:
    """The URL as a value-free template: id-like path segments and query values become
    placeholders, the host, userinfo and fragment are dropped (MPI1)."""
    parts = urlsplit(url)
    path = "/".join("{id}" if segment_is_id_like(s) else s for s in parts.path.split("/")) or "/"
    pairs = [f"{_param(k)}={{{_param(k)}}}" for k, _ in parse_qsl(parts.query, True)]
    return (path + ("?" + "&".join(pairs) if pairs else ""))[:400]


def _off_platform_finding(index: int, link: PlatformLink, account: RoleAccount,
                          start_url: str) -> MultiRoleFinding:
    template = _template_of(link.url_template or start_url)
    name = link.control_name or ""
    if link.url_template:
        step = f"goto {template}"
    else:
        step = f"click {'control' if contains_personal_shape(name) else name}"
    return MultiRoleFinding(
        finding_id=f"off-platform-{index}-{link.from_platform}-{link.to_platform}"[:64].rstrip("-_"),
        finding_class=FindingClass.OFF_PLATFORM_HOP,
        title=f"A hop from {link.from_platform} to {link.to_platform} left every declared platform",
        role=account.role, platform_id=link.from_platform, url_template=template,
        steps=[f"login {account.id}", step[:200]], count=1)


def _hosts_seen(hops: list[str]) -> list[str]:
    seen: list[str] = []
    for url in hops:
        host = _netloc(url)
        if host and (not seen or seen[-1] != host):
            seen.append(host)
    return seen


def _follow_one(project: Project, roles: RoleSessions, index: int, link: PlatformLink,
                account: RoleAccount, trace: Callable[..., Trace]) -> LinkOutcome:
    base = {"link_index": index, "from_platform": link.from_platform,
            "to_platform": link.to_platform, "kind": link.kind, "account_id": account.id}
    scrub = roles.secrets.scrub_optional
    try:
        hops, landing, status, error = roles.run_as(
            account.id, lambda session: trace(session, project, link))
    except Exception as exc:
        reason = scrub(_safe_reason(exc)) or "trace failed"
        return LinkOutcome(**base, status=LinkStatus.FAILED, reason=reason[:MAX_REASON])
    verdict, reason, stray = judge_hops(project, link, hops, landing, status, error)
    reason = (scrub(reason) or None) if reason else None
    start = next(p for p in project.effective_platforms() if p.id == link.from_platform)
    finding = None
    if stray:
        try:
            finding = _off_platform_finding(index, link, account,
                                            urlsplit(start.base_url).path or "/")
        except ValueError:  # an unrepresentable trigger must not drop this or later links
            reason = (reason or "")[:MAX_REASON - 40] + " (finding could not be built)"
    landed = stray or (_netloc(landing) if landing else None) or None
    return LinkOutcome(**base, status=verdict, reason=reason[:MAX_REASON] if reason else None,
                       landed_host=landed, hops=_hosts_seen(hops), finding=finding)


def follow_platform_links(project: Project, roles: RoleSessions, *,
                          trace: Callable[..., Trace] = trace_link) -> list[LinkOutcome]:
    """One `LinkOutcome` per declared link, in declaration order. A link whose from-platform has
    no role account is `NOT_REACHED` (nothing could drive it); the others use the platform's
    first account."""
    outcomes: list[LinkOutcome] = []
    for index, link in enumerate(project.platform_links or []):
        accounts = roles.accounts_on(link.from_platform)
        if not accounts:
            outcomes.append(LinkOutcome(
                link_index=index, from_platform=link.from_platform, to_platform=link.to_platform,
                kind=link.kind, status=LinkStatus.NOT_REACHED,
                reason=f"no role account on platform {link.from_platform!r} to follow it"))
            continue
        outcomes.append(_follow_one(project, roles, index, link, accounts[0], trace))
    return outcomes
