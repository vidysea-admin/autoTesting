"""The explorer's inner safety guard (Track B4, D-016).

Umesh's OUTER boundary is the test account's own permissions — whatever the
account can reach, the crawl may reach. This module is the INNER guard he
can loosen (`WritePolicy.ALLOW_WRITES`): by default the explorer never
clicks a destructive-looking control, never submits a form under
`READ_ONLY`, never clicks a logout/sign-out control at any policy, and
never treats third-party noise (analytics, trackers) as a product issue.

Pure logic — no browser, no provider. Contract: qa/contracts/explore.md
X5-X9 (lands at T-143, when the contract itself is written).
"""

from __future__ import annotations

import re
from urllib.parse import urljoin

from autotester.browser.secrets import host_of
from autotester.schema.crawl import DEFAULT_NEVER_CLICK_PATTERNS, DialogEvent, SafetyPolicy
from autotester.schema.enums import WritePolicy
from autotester.schema.project import Project
from autotester.schema.screen_graph import ElementRef
from autotester.stages.account_destroy import (
    ACCOUNT_DESTROY_REFUSED,
    DestroyContext,
    destroys_account,
)

_UNSAFE_SCHEMES = ("javascript:", "mailto:", "tel:")
FORM_SUBMIT_REFUSED = "form submit under read_only"
"""The refusal a login wall is recognised by (X18) — one string, read by both."""
OFF_DOMAIN_LINK_REFUSED = "href outside allowed domains"
"""A link refused BEFORE it is tried (V7's per-node count must not include it)."""
TYPING_DISABLED = "typing disabled under this policy (X10-b)"
"""Why a form field was not typed: the run has not met D-029's four conditions."""

_UNTYPEABLE_INPUT_TYPES = frozenset({"password", "file"})
_TYPING_POLICIES = frozenset({WritePolicy.TEST_ACCOUNT, WritePolicy.ALLOW_WRITES})


def typing_allowed(policy: SafetyPolicy) -> bool:
    """X10-b's one gate (D-029). True only when the write policy is one a human
    deliberately widened AND the run's policy carries `synthetic_typing` — the
    default is OFF, so every existing crawl and every existing test keeps X10
    exactly as it was."""
    return policy.synthetic_typing and policy.write_policy in _TYPING_POLICIES


def typing_target_allowed(el: ElementRef) -> bool:
    """Which elements may receive a synthetic value: textbox/textarea/combobox
    roles the observer already reports, never an upload (`type="file"`), never
    a real password input (`type="password"`), never a field whose own name
    marks it a password/credential field (a "change password" form is a
    credential change — D-029's non-destructive clause)."""
    if el.role not in ("textbox", "combobox", "search"):
        return False
    if el.type.lower() in _UNTYPEABLE_INPUT_TYPES:  # AT-650: the real type, not a name guess
        return False
    label = f"{el.name} {el.selector}".lower()
    return not ("password" in label or "passwd" in label)


def policy_for(project: Project, **overrides: object) -> SafetyPolicy:
    """Build a `SafetyPolicy` from a project's `write_policy`, with any field
    overridden explicitly (e.g. a per-project `deny_patterns` extension for
    control names in another language — a documented limit, not a bug)."""
    return SafetyPolicy(write_policy=project.write_policy, **overrides)  # type: ignore[arg-type]


_SEPARATORS = re.compile(r"[-_./+|]+")
_WHITESPACE = re.compile(r"\s+")


def normalise_label(name: str) -> str:
    """Fold a control's accessible name to a plain space-separated form before
    pattern matching.

    AT-093: `Log-Out`, `LOG_OUT`, `Sign-Out` and `Log.Out` are all ordinary
    real-world button labels, and every one of them slipped past patterns
    written for `log out`/`logout` — the guard meant to stop this crawler
    logging itself out of a production app did not recognise the hyphenated
    spelling. Normalising once here fixes every pattern at the same time and
    keeps the patterns themselves readable, instead of growing a separator
    alternation into each one.
    """
    return _WHITESPACE.sub(" ", _SEPARATORS.sub(" ", name)).strip()


def _matches_any(name: str, patterns: list[str]) -> bool:
    folded = normalise_label(name)
    return any(re.search(pattern, folded, re.IGNORECASE) for pattern in patterns)


def deny_reason(el: ElementRef, policy: SafetyPolicy, *, page: str = "",
                destroy_ctx: DestroyContext | None = None) -> str | None:
    """Why `el` must NOT be clicked right now, or `None` if it's safe to try.

    Order matters: never-click applies at every policy (checked first);
    then an unnamed non-link control (nothing to match against, and
    clicking blind is how the prior attempt found "Delete" the hard way);
    then the deny-list, disabled entirely under `ALLOW_WRITES`; then a
    form-submit control, refused only under `READ_ONLY`.

    AT-092: never-click is checked against `DEFAULT_NEVER_CLICK_PATTERNS`
    directly, NOT `policy.never_click_patterns` — that field is an ordinary
    overridable `SafetyPolicy` attribute with no floor, so
    `policy_for(project, never_click_patterns=[])` would otherwise silently
    disarm the one guard D-016 says configuration must never be able to
    loosen. `policy.never_click_patterns` still widens the set (a project
    may add more patterns); it can never narrow it.
    """
    if destroys_account(el.name, href=el.href, context=page, ctx=destroy_ctx):
        return ACCOUNT_DESTROY_REFUSED
    if _matches_any(el.name, list(DEFAULT_NEVER_CLICK_PATTERNS)) or _matches_any(
        el.name, list(policy.never_click_patterns)
    ):
        return "never-click pattern (logout/sign-out)"
    if not el.name and el.role != "link":
        if policy.click_unnamed:
            return None
        return "unnamed control"
    if policy.write_policy != WritePolicy.ALLOW_WRITES and _matches_any(
        el.name, list(policy.deny_patterns)
    ):
        return "destructive-name deny-list"
    if policy.write_policy == WritePolicy.READ_ONLY and el.is_form_submit:
        return FORM_SUBMIT_REFUSED
    return None


def is_destructive(el: ElementRef, policy: SafetyPolicy) -> bool:
    """Whether this control's own NAME marks it destructive (D-016's deny-list
    vocabulary), independently of whether the tier lets the crawl press it.

    `deny_reason` asks a different question — *may I click this now* — and answers
    "yes" under `ALLOW_WRITES`, which is exactly the tier where the ordering below
    matters most. So the classification is read off `policy.deny_patterns` directly;
    a project that widens its deny-list widens what counts as destructive too.
    """
    return _matches_any(el.name, list(policy.deny_patterns))


def destructive_last(elements: list[ElementRef],
                     policy: SafetyPolicy) -> list[ElementRef]:
    """D-040 verbatim ("destructive actions are ordered last"), per screen.

    A stable partition, not a sort: the order inside each half is byte-identical to
    the order the observer reported, so the only behaviour this changes is that a
    `Delete`/`Send`/`Pay` control is attempted after every ordinary control on the
    same screen. Under a bound that stops the crawl mid-screen, that is the
    difference between losing the read-only controls and losing the irreversible one.
    """
    ordinary = [el for el in elements if not is_destructive(el, policy)]
    destructive = [el for el in elements if is_destructive(el, policy)]
    return ordinary + destructive


def link_is_safe(el: ElementRef, project: Project, base_url: str) -> bool:
    """A link the explorer may `goto` directly: same-domain, not a scheme the
    browser would treat specially (`javascript:`, `mailto:`, `tel:`).

    AT-333: the href is resolved against `base_url` — the page the link is ON —
    with the SAME `urljoin` the navigation itself uses, so the guard judges the
    URL the browser will actually visit. Judging the raw href instead made two
    separate mistakes at once. It refused every document-relative link, because
    `host_of` force-prefixes `//` and so read `reports.html` as a *hostname*;
    and it allowed anything `host_of` fails closed on (a backslash, AT-007),
    because an empty host was read as "relative, therefore safe". A resolved
    absolute URL always has a host, so no host now means refuse.
    """
    if not el.href or el.href.startswith(_UNSAFE_SCHEMES):
        return False
    target = urljoin(base_url, el.href)
    if target.startswith(_UNSAFE_SCHEMES):
        return False
    host = host_of(target)
    return bool(host) and project.allows_domain(host)


def classify_request(url: str, project: Project, policy: SafetyPolicy) -> str:
    """`"first_party"` (a real issue candidate), `"ignored"` (a known
    analytics/tracker host, dropped entirely), or `"noise"` (some other
    third party, counted but never reported as a product issue) — X9."""
    host = host_of(url)
    if host and project.allows_domain(host):
        return "first_party"
    if host and any(host == d or host.endswith(f".{d}") for d in policy.third_party_ignore):
        return "ignored"
    return "noise"


class DialogBreaker:
    """Trips when one screen shows too many dialogs in a row — the prior
    attempt got permanently trapped by a repeated `beforeunload` loop."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self._counts: dict[str, int] = {}

    def record(self, node_id: str, _event: DialogEvent) -> bool:
        """Returns True once `node_id` has exceeded `limit` dialogs."""
        self._counts[node_id] = self._counts.get(node_id, 0) + 1
        return self._counts[node_id] > self.limit

    def reset(self, node_id: str) -> None:
        self._counts.pop(node_id, None)
