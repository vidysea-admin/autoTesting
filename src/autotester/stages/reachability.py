"""One job: tell a run, before it starts, what it is aimed at that it may not reach.

Two read-only checks, neither of which spends a bound or a credential:

AT-887 clause 2 (`latest_warnings`): warn about cases aimed at screens the latest crawl never
reached. A crawl's summary records which screen templates it visited and which it found but left
in the frontier (stopped by a bound, or aborted). A case whose first target is a URL on such a
screen was written against a surface the account may not be able to reach, and running it blind
reads as an INCONCLUSIVE product bug. This is a WARNING: it never removes, skips or reorders a
case. Only URL targets are judged; a locator or `{{SECRET}}` first step cannot be matched to a
screen, so it is left unwarned rather than guessed at.

E4.2 / AT-1421 (`probe_target`, `skip_run`): one bounded GET of the project's
`base_url` before the first browser exists. If the host does not answer, every case is recorded
INCONCLUSIVE with ONE message instead of N identical 30 s navigation timeouts. Any HTTP answer
(a 401, a 500) is the product's own and counts as reachable. Only http/https is ever spoken: a
redirect to any other scheme is itself the answer, and a probe bug (not a network failure) lets
the run proceed with a warning rather than skip it.
"""

from __future__ import annotations

import dataclasses
import errno
import http.client
import socket
import ssl
import threading
import time
import urllib.error
import urllib.request

from autotester.browser.secrets import bad_scheme, host_of
from autotester.core.path_pii import safe_path
from autotester.core.urls import url_template
from autotester.providers.base import Provider
from autotester.schema.case import Case
from autotester.schema.crawl_summary import CrawlSummary
from autotester.schema.enums import Action, Outcome
from autotester.schema.project import Project
from autotester.schema.run import RawResult
from autotester.schema.run_state import StageCheckpoint, StageName
from autotester.stages.orchestrate import StageContext
from autotester.stages.parallel_run import ParallelPlan
from autotester.stages.run_case_pipeline import grade_errored_result
from autotester.store.project_store import ProjectStore

TARGET_UNREACHABLE = "target_unreachable"
"""`Run.stop_reason` of a run that never started because its target did not answer."""

PROBE_TOTAL_S = 10.0
"""Everything the probe may spend, the one retry included (each attempt gets half of it)."""

_MAX_REDIRECTS = 3

NO_CLOCK = {"judging": 0.0, "housekeeping": 0.0, "total": 0.0, "acted_during_exclusion": 0.0,
            "acting": 0.0}
"""`Run.excluded_s` of a run that stopped before any case: the clock never ran."""

_NO_ANSWER = TimeoutError("no answer")
_NETWORK_ERRORS = (OSError, http.client.HTTPException)
"""What a dead or unreachable target raises. Anything else out of the probe is OUR bug."""


def _first_route(case: Case) -> str | None:
    if not case.steps or case.steps[0].action is not Action.NAVIGATE:
        return None
    target = case.steps[0].target
    if "{{" in target or not target.startswith(("http://", "https://", "/")):
        return None
    return safe_path(url_template(target, keep_host=False, fold_index=True))


def reachability_warnings(cases: list[Case], summary: CrawlSummary | None) -> list[str]:
    """One line per case whose first target the crawl did not reach; [] when no crawl summary."""
    if summary is None or not (summary.reached_paths or summary.unreached_paths):
        return []  # a summary from before AT-887 holds no screen lists: say nothing, claim nothing
    reached, frontier = set(summary.reached_paths), set(summary.unreached_paths)
    out: list[str] = []
    for case in cases:
        route = _first_route(case)
        if route is None or route in reached:
            continue
        why = ("found by crawl %s but never visited (frontier)" if route in frontier
               else "not seen by crawl %s at all") % summary.crawl_id
        out.append(f"case {case.id}: first target {route} {why}; it will still run")
    return out


def latest_warnings(store: ProjectStore, cases: list[Case]) -> list[str]:
    summaries = store.list_crawl_summaries()  # newest first
    return reachability_warnings(cases, summaries[0] if summaries else None)


class _InScopeRedirects(urllib.request.HTTPRedirectHandler):
    """Follow a redirect only while its host stays inside the project's allowed domains and the
    probe's deadline holds; otherwise the 3xx itself is the answer and no connection is made."""

    max_redirections = _MAX_REDIRECTS

    def __init__(self, project: Project, deadline: float) -> None:
        self.project, self.deadline = project, deadline

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        host = host_of(newurl)
        if (bad_scheme(newurl) or not host or not self.project.allows_domain(host)
                or time.monotonic() >= self.deadline):
            return None  # the 3xx itself is the answer; nothing else is connected to
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _attempt(opener: urllib.request.OpenerDirector, url: str,
             timeout: float) -> BaseException | None:
    """One GET in a daemon thread (so a stuck DNS lookup cannot outlive the bound); None when
    the host answered with anything at all, else what went wrong."""
    outcome: list[BaseException | None] = [_NO_ANSWER]  # still this if the worker outlives its join

    def go() -> None:
        try:
            opener.open(urllib.request.Request(url, method="GET"), timeout=timeout).close()
            outcome[0] = None
        except urllib.error.HTTPError as exc:  # a 4xx/5xx is an answer
            exc.close()
            outcome[0] = None
        except Exception as exc:  # classified by the caller: `_NETWORK_ERRORS` or our own bug
            outcome[0] = exc

    worker = threading.Thread(target=go, daemon=True)
    worker.start()
    worker.join(timeout + 0.5)
    return outcome[0]


_UNREACHABLE_ERRNOS = frozenset(
    getattr(errno, name) for name in ("ENETUNREACH", "EHOSTUNREACH", "WSAENETUNREACH",
                                      "WSAEHOSTUNREACH") if hasattr(errno, name))
"""A network or host that cannot be routed to: a TCP-stage failure with no `ConnectionError`."""


def _failure_message(host: str, exc: BaseException) -> str:
    """Host + failure class + one `[stage=...]` token (AT-1420), never the path, the resolved
    address or the exception text. `dns` / `tcp` / `tls` / `http` / `timeout` / `unknown`."""
    cause = exc.reason if isinstance(exc, urllib.error.URLError) else exc
    if isinstance(cause, TimeoutError):
        text, stage = f"did not answer within {PROBE_TOTAL_S:g} s", "timeout"
    elif isinstance(cause, socket.gaierror):
        text, stage = "could not be resolved (DNS)", "dns"
    elif isinstance(cause, ssl.SSLError):
        text, stage = "failed the TLS handshake", "tls"
    elif isinstance(cause, http.client.HTTPException):  # (also a ConnectionError)
        text, stage = "closed the connection without an HTTP answer", "http"
    elif isinstance(cause, ConnectionRefusedError):
        text, stage = "refused the connection", "tcp"
    elif isinstance(cause, ConnectionError):
        text, stage = "closed the connection without an HTTP answer", "tcp"
    elif isinstance(cause, OSError) and cause.errno in _UNREACHABLE_ERRNOS:
        text, stage = "could not be reached", "tcp"
    else:
        text, stage = "could not be reached", "unknown"
    return f"target {host} {text} from this server [stage={stage}]"


def _build_opener(project: Project, deadline: float) -> urllib.request.OpenerDirector:
    """http and https only: no FTP, file or data handler exists to be redirected into, no cookie
    processor, no proxy."""
    opener = urllib.request.OpenerDirector()
    for handler in (urllib.request.ProxyHandler({}), urllib.request.HTTPHandler(),
                    urllib.request.HTTPSHandler(), urllib.request.UnknownHandler(),
                    urllib.request.HTTPDefaultErrorHandler(), _InScopeRedirects(project, deadline),
                    urllib.request.HTTPErrorProcessor()):
        opener.add_handler(handler)
    return opener


def probe_target(project: Project, notes: list[str] | None = None) -> str | None:
    """None to proceed, or one sentence (host + failure class, never the path) to stop.

    One GET of `base_url`: no cookies, credentials or body, no proxy, redirects only inside
    `allowed_domains` over http(s), at most two attempts inside `PROBE_TOTAL_S`. A host outside the
    allowed domains (or a URL that is not plain http/https without userinfo) is not probed at all.
    A failure that is not a network failure is a bug in the probe: it fails open (None) and appends
    one warning naming the exception class to `notes`, so a probe bug never skips a real run."""
    url, host = project.base_url, host_of(project.base_url)
    if "://" not in url or bad_scheme(url) or not host or not project.allows_domain(host):
        return None
    deadline = time.monotonic() + PROBE_TOTAL_S
    opener = _build_opener(project, deadline)
    failure: BaseException | None = None
    for _ in range(2):
        left = deadline - time.monotonic()
        if left <= 0:
            break
        failure = _attempt(opener, url, min(PROBE_TOTAL_S / 2, left))
        if failure is None:
            return None
        if failure is not _NO_ANSWER and not isinstance(failure, _NETWORK_ERRORS):
            if notes is not None:
                notes.append(f"the reachability check of {host} could not run "
                             f"({type(failure).__name__}); the run went ahead without it")
            return None
    return _failure_message(host, failure or _NO_ANSWER)


def check_target(project: Project, notes: list[str] | None = None) -> str | None:
    """`RunSeams.target_probe`'s default. `probe_target` is looked up at call time, so a test
    suite can switch the network off in one place (tests/conftest.py)."""
    return probe_target(project, notes)


def skip_run(ctx: StageContext, plan: ParallelPlan, cases: list[Case], judge: Provider,
             message: str) -> ParallelPlan:
    """End a run whose target did not answer, before any case executes: every case gets one
    saved result and an INCONCLUSIVE verdict (`grade` settles an ERRORED outcome by rule, no
    model call) naming the one cause, and the EXECUTE span is failed with it. No screenshot or
    video exists because no browser did, and no second was spent acting (`NO_CLOCK`). Returns the
    plan carrying the stop and the message."""
    started = ctx.clock()
    for case in cases:
        result = RawResult(case_id=case.id, outcome=Outcome.ERRORED, error=f"not run: {message}")
        ctx.store.save_result(ctx.run_id, result)
        ctx.store.save_verdict(
            ctx.run_id, grade_errored_result(case, result, judge, ctx.run_id, ctx.store))
    ctx.trace.record_stage(StageCheckpoint(
        stage=StageName.EXECUTE, status="failed", error=message,
        started=started, finished=ctx.clock()))
    return dataclasses.replace(plan, excluded_s=dict(NO_CLOCK), stop_reason=TARGET_UNREACHABLE,
                               warnings=(message,))
