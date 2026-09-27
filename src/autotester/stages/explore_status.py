"""How a finished crawl is judged, and how a stored one is shown (X16, X18).

A crawl that never gets past the login wall must never read as COMPLETED. Umesh,
2026-09-16: "abhi tho hmara testing flow login k baad hi ruk jata hi" — every crawl on
disk had stopped at or before the login page, and three said `completed`. AT-242's
BLOCKED_NO_ACTIONS caught only the crawl that did NOTHING; a sign-in page with one
link that leads back still came out COMPLETED while the product behind it was never
seen. Nobody re-runs a crawl that says it finished, so this is the lie that costs most.

Split out of `stages/explore.py`, which sat at the 300-line cap (AT-460): the terminal
status is a judgement about a finished graph, not part of walking it.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from autotester.browser.observe import observe
from autotester.core.redact import PLACEHOLDER_RE
from autotester.core.urls import screen_url_pattern
from autotester.schema.case import Case
from autotester.schema.crawl import Crawl
from autotester.schema.enums import Action, CrawlStatus, EdgeOutcome
from autotester.schema.screen_graph import ScreenEdge, ScreenNode
from autotester.stages.explore_safety import FORM_SUBMIT_REFUSED
from autotester.stages.screen_identity import structural_signature

NEVER_LEFT_LOGIN = (
    "the login case ran, but every screen reached was still the login page ({template}) -- "
    "check the login case's steps and the credentials it uses"
)
LOGIN_WALL_REASON = (
    "stopped at a login wall: every screen reached only offers a form submit denied by "
    "read_only, and no link led anywhere else -- declare a login case to crawl past it"
)
LOGIN_WALL_REASON_BOUND = (  # AT-480: a fired bound left controls untried -- never claim otherwise
    "stopped at a login wall: every screen reached only offers a form submit denied by "
    "read_only -- declare a login case to crawl past it"
)


def login_template(case: Case) -> str | None:
    """The url template of the login case's own start screen, templated exactly as a
    crawled node is (so the two can be compared), or None when it cannot be known here:
    no NAVIGATE step, or a `{{SECRET:KEY}}` target that only resolves at fill time
    (templating the raw placeholder gives "/", which matches the wrong screens — AT-462)."""
    step = next((s for s in sorted(case.steps, key=lambda s: s.order)
                 if s.action is Action.NAVIGATE), None)
    if step is None or PLACEHOLDER_RE.search(step.target):
        return None
    return screen_url_pattern(step.target)


def observed_signature(session: object) -> tuple[str | None, str | None]:
    """The structural signature of the page the session shows now, computed exactly as a
    crawled node's is — or `(None, "<Type>: <msg>")` if it cannot be observed, in which case
    X18(a) falls back to the fill-target rule (`never_left_login`) or, when that too cannot
    decide, is recorded as not judged rather than guessed (AT-474 — never a crash, never a
    silent skip)."""
    try:
        return structural_signature(observe(session).elements), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def login_fill_targets(case: Case | None) -> frozenset[str]:
    """The selectors the login case types into — X18(a)'s fallback identity check when the
    login page's signature moved (a sticky wrong-password banner, AT-467) or could not be
    observed at all (AT-474)."""
    if case is None:
        return frozenset()
    return frozenset(s.target for s in case.steps if s.action is Action.FILL)


def login_submit_selector(case: Case | None) -> str | None:
    """AT-489: the login case's own submit control -- the selector of its last CLICK step --
    required by the fill-target fallback so a screen cannot be misclassified LOGIN_FAILED merely
    for reusing every FILL selector; a case with no CLICK step never fires the fallback."""
    if case is None:
        return None
    clicks = [s for s in sorted(case.steps, key=lambda s: s.order) if s.action is Action.CLICK]
    return clicks[-1].target if clicks else None


def never_left_login(nodes: Iterable[ScreenNode], case: Case | None,
                     login_signature: str | None) -> str | None:
    """X18(a): with a declared login case, the reason every node IS the login screen.

    A screen is (url_template, signature) — X3 — and the login screen's signature is the one
    OBSERVED on the login page before the case typed anything (`login_signature`). Comparing
    the template alone called a working single-page-app login failed (AT-462, cycle 1); so did
    merely counting signatures, when the dashboard behind the login is a single state at the
    same url (AT-462, cycle 2).

    A node still counts as the login screen when its `url_template` matches AND EITHER its
    signature equals the one observed, OR — when that comparison cannot decide, because the
    signature moved (AT-467: a wrong-password page that grew a sticky error banner) or was
    never observed (AT-474) — every FILL step target AND the login case's own submit control
    (its last CLICK step's selector, AT-489) are still present as an element's `selector` on
    that node. A case with no CLICK step never fires this fallback (signature rule only). A
    FILL target or the submit control missing from the node's elements leaves the
    signature-only rule in force, so a screen that merely reuses the login's FILL selectors
    without also reusing its submit control is never caught by this fallback."""
    reached = list(nodes)
    template = login_template(case) if case is not None else None
    if template is None or not reached:
        return None
    fill_targets = login_fill_targets(case)
    submit_selector = login_submit_selector(case)

    def _still_login(node: ScreenNode) -> bool:
        if node.url_template != template:
            return False
        if node.signature == login_signature:
            return True
        selectors = {el.selector for el in node.elements}
        return (submit_selector is not None and submit_selector in selectors
               and bool(fill_targets) and fill_targets <= selectors)

    if any(not _still_login(node) for node in reached):
        return None
    return NEVER_LEFT_LOGIN.format(template=template)


def is_login_wall(nodes: list[ScreenNode], edges: list[ScreenEdge]) -> bool:
    """X18(b): every reached screen carries a refused form submit, and no NAVIGATED
    edge reaches a screen whose structure differs from the seed's — regardless of
    how many actions were spent going round in front of the wall."""
    if not nodes:
        return False
    seed = min(nodes, key=lambda n: n.depth)
    walled = {e.from_node for e in edges
              if e.outcome is EdgeOutcome.DENIED_POLICY and e.reason == FORM_SUBMIT_REFUSED}
    if any(n.id not in walled for n in nodes):
        return False
    signature = {n.id: n.signature for n in nodes}
    return not any(
        e.outcome is EdgeOutcome.NAVIGATED and e.to_node is not None
        and signature.get(e.to_node, seed.signature) != seed.signature
        for e in edges
    )


def terminal_status(*, completed: bool, actions_used: int, denied: int,
                    nodes: list[ScreenNode], edges: list[ScreenEdge],
                    login_case: Case | None, login_signature: str | None = None,
                    login_observe_error: str | None = None,
                    current_stop_reason: str | None = None) -> tuple[CrawlStatus, str | None]:
    """The status a finished crawl ends in, and a replacement stop reason when the
    status needs one. The wall checks come first: a crawl stuck at the login page is
    stuck whether its frontier emptied or a bound stopped it -- AT-480: when a bound
    fired, the reason still names it (X4), and the wall sentence drops its "no link
    led anywhere else" claim, since a bound can leave controls untried.

    AT-474: when the login page's signature could not be observed AND X18(a) still could
    not be judged (`never_left_login` found nothing conclusive, even via the fill-target
    fallback), the status is never silently displayed as an unqualified success — its
    reason carries a named qualifier saying the check itself could not run."""
    bound_suffix = (f" -- the {current_stop_reason} bound fired before every control was tried"
                    if not completed and current_stop_reason else "")
    reason = never_left_login(nodes, login_case, login_signature)
    if reason is not None:
        return CrawlStatus.LOGIN_FAILED, reason + bound_suffix
    if login_case is None and is_login_wall(nodes, edges):
        wall_reason = LOGIN_WALL_REASON if completed else LOGIN_WALL_REASON_BOUND
        return CrawlStatus.LOGIN_WALL, wall_reason + bound_suffix
    if not completed:
        status = CrawlStatus.STOPPED_BOUND
    elif actions_used == 0 and denied > 0:  # AT-242
        status = CrawlStatus.BLOCKED_NO_ACTIONS
    else:
        status = CrawlStatus.COMPLETED
    reason = (f"{current_stop_reason} -- every reachable action was denied by policy"
             if status is CrawlStatus.BLOCKED_NO_ACTIONS else None)
    if login_case is not None and login_observe_error is not None:  # AT-474
        base = reason or current_stop_reason
        reason = (f"{base} -- login not judged: could not observe the login page "
                 f"({login_observe_error})")
    return status, reason


def _heartbeat_stale(crawl: Crawl, now: datetime) -> bool:
    """AT-483: a RUNNING crawl whose serving process died leaves `heartbeat_at` frozen
    while `now` keeps moving. A crawl with no `heartbeat_at` yet -- a legacy crawl.json
    (X18(d)) or one not a `heartbeat_every_actions`'th action in -- is never flagged;
    there is nothing to compare, so the honest answer is "not yet judged", not "stale"."""
    if crawl.heartbeat_at is None:
        return False
    age = (now - datetime.fromisoformat(crawl.heartbeat_at)).total_seconds()
    return age >= crawl.bounds.heartbeat_stale_after_s


def displayed_status(crawl: Crawl, *, now: datetime | None = None) -> CrawlStatus:
    """X18(d): what a human is SHOWN. A crawl.json written before AT-242 says `completed`
    with 0 actions and refusals — the file is history and stays as written, but it is
    not displayed as success.

    AT-483: a RUNNING crawl whose heartbeat has gone stale (its serving process died
    mid-BFS, so `explore_node`'s incremental writes stopped) displays as ABORTED — the
    same display-only reuse this function already makes for BLOCKED_NO_ACTIONS, not a
    new `CrawlStatus` member (`schema/enums.py` sits at its own 300-line C2 cap with no
    safe trim). `crawl.json` itself is never rewritten by this check, so a crawl that is
    genuinely still running reverts the instant its next heartbeat lands."""
    if crawl.status is CrawlStatus.COMPLETED and crawl.actions == 0 and crawl.denied > 0:
        return CrawlStatus.BLOCKED_NO_ACTIONS
    if crawl.status is CrawlStatus.RUNNING and _heartbeat_stale(crawl, now or datetime.now(UTC)):
        return CrawlStatus.ABORTED
    return crawl.status


def is_success(crawl: Crawl) -> bool:
    """The one test every surface uses to decide whether to colour a crawl as success."""
    return displayed_status(crawl) is CrawlStatus.COMPLETED
