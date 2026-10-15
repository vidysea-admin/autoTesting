"""`stages/explore_safety.py` — the D-016 write_policy matrix, the never-click
list, the link/request classifiers, and the dialog circuit breaker. Pure
logic, no browser. Contract: qa/contracts/explore.md X5-X9 (T-143).
"""

from __future__ import annotations

import pytest

from autotester.schema.crawl import DialogEvent
from autotester.schema.enums import WritePolicy
from autotester.schema.project import Project
from autotester.schema.screen_graph import ElementRef
from autotester.stages.explore_safety import (
    DialogBreaker,
    classify_request,
    deny_reason,
    link_is_safe,
    policy_for,
)


def make_project(write_policy: WritePolicy = WritePolicy.READ_ONLY) -> Project:
    return Project(
        slug="erp", name="ERP", base_url="https://www.vidysea.com/erp",
        allowed_domains=["vidysea.com", "www.vidysea.com"], write_policy=write_policy,
    )


def el(name: str, *, role: str = "button", is_form_submit: bool = False) -> ElementRef:
    return ElementRef(role=role, name=name, selector=f"#{name}", is_form_submit=is_form_submit)


CONTROLS = {
    "delete": el("Delete account"),
    "save_submit": el("Save", is_form_submit=True),
    "log_out": el("Log out"),
    "unnamed_button": el(""),
    "unnamed_link": el("", role="link"),
    "deliverables": el("Deliverables"),
    "send": el("Send"),
}


# -- the write_policy matrix (D-016), table-driven ---------------------------

@pytest.mark.parametrize("policy_kind,control,expect_denied", [
    (WritePolicy.READ_ONLY, "delete", True),
    (WritePolicy.READ_ONLY, "save_submit", True),
    (WritePolicy.READ_ONLY, "log_out", True),
    (WritePolicy.READ_ONLY, "deliverables", False),
    (WritePolicy.READ_ONLY, "send", True),
    (WritePolicy.TEST_ACCOUNT, "delete", True),
    (WritePolicy.TEST_ACCOUNT, "save_submit", False),
    (WritePolicy.TEST_ACCOUNT, "log_out", True),
    (WritePolicy.ALLOW_WRITES, "delete", True),  # account-destroying: never-click (2026-10-15)
    (WritePolicy.ALLOW_WRITES, "save_submit", False),
    (WritePolicy.ALLOW_WRITES, "log_out", True),  # never-click applies at EVERY policy
])
def test_deny_matrix(policy_kind: WritePolicy, control: str, expect_denied: bool) -> None:
    policy = policy_for(make_project(policy_kind))
    reason = deny_reason(CONTROLS[control], policy)
    assert (reason is not None) is expect_denied


def test_deliverables_does_not_match_the_deliver_style_pattern() -> None:
    """Word-boundary matching: "Deliverables" must not match a "deliver"-ish
    fragment of any deny pattern."""
    policy = policy_for(make_project(WritePolicy.READ_ONLY))
    assert deny_reason(CONTROLS["deliverables"], policy) is None


def test_unnamed_non_link_control_is_denied_by_default() -> None:
    policy = policy_for(make_project(WritePolicy.ALLOW_WRITES))
    assert deny_reason(CONTROLS["unnamed_button"], policy) == "unnamed control"


def test_unnamed_link_is_not_denied_for_being_unnamed() -> None:
    """A link with no accessible name is still a link — safety for it is
    `link_is_safe`'s job (domain check), not the unnamed-control rule."""
    policy = policy_for(make_project(WritePolicy.READ_ONLY))
    assert deny_reason(CONTROLS["unnamed_link"], policy) is None


def test_click_unnamed_override_allows_an_unnamed_control() -> None:
    policy = policy_for(make_project(WritePolicy.ALLOW_WRITES), click_unnamed=True)
    assert deny_reason(CONTROLS["unnamed_button"], policy) is None


def test_never_click_cannot_be_disarmed_by_clearing_the_policy_field() -> None:
    """AT-092 (checker-found): `never_click_patterns` is an ordinary
    overridable field with no floor. Configuration can WIDEN the never-click
    set, but clearing it must never narrow it below the hardcoded baseline —
    logout/sign-out stays refused regardless."""
    policy = policy_for(
        make_project(WritePolicy.ALLOW_WRITES), never_click_patterns=[],
    )
    assert deny_reason(CONTROLS["log_out"], policy) is not None


@pytest.mark.parametrize("name,expect_denied", [
    ("Log me out", True), ("Sign yourself out", True), ("Log out", True),
    ("Log in to your account", False), ("Sign in with Google", False),
    ("Login", False), ("Signing up", False), ("Outstanding balance", False),
    ("Log this event", False),
])
def test_never_click_tolerates_a_short_gap_without_over_matching(
    name: str, expect_denied: bool,
) -> None:
    """AT-092 follow-up (found while re-probing the checker's crashed adversarial
    run): the literal "log ?out" pattern missed "Log me out". Widened to
    tolerate a bounded gap; re-probed against plausible false-positive
    sentences ("Log in to your account") to confirm it doesn't over-match."""
    policy = policy_for(make_project(WritePolicy.ALLOW_WRITES))
    reason = deny_reason(el(name), policy)
    assert (reason is not None) is expect_denied


@pytest.mark.parametrize("name", [
    "Log-Out", "LOG_OUT", "Sign-Out", "Log.Out", "log-out", "Sign_Out",
    "Sign|Out", "Log/Out", "LOGOUT", "Logout", "Log me out",
])
def test_separator_joined_logout_labels_are_denied(name: str) -> None:
    """AT-093 (checker-found, escalated to high because it gates the live ERP
    crawl): `Log-Out`/`LOG_OUT`/`Sign-Out` are ordinary real button labels and
    every one slipped past patterns written for `log out`. Fixed by folding
    separators before matching, not by growing each pattern."""
    policy = policy_for(make_project(WritePolicy.ALLOW_WRITES))
    assert deny_reason(el(name), policy) is not None


@pytest.mark.parametrize("name", [
    "Log in to your account", "Sign-in", "Backlog-Outline", "Re-send code",
    "Outstanding balance", "Sign up", "Log this event", "Deliverables", "About-us",
])
def test_separator_folding_does_not_create_false_positives(name: str) -> None:
    """The other direction: folding `-`/`_`/`.` to spaces must not make
    innocent labels look like logout or destructive controls."""
    policy = policy_for(make_project(WritePolicy.ALLOW_WRITES))
    assert deny_reason(el(name), policy) is None


def test_normalise_label_folds_every_separator() -> None:
    from autotester.stages.explore_safety import normalise_label

    assert normalise_label("Log-Out") == "Log Out"
    assert normalise_label("LOG_OUT") == "LOG OUT"
    assert normalise_label("a.b/c+d|e") == "a b c d e"
    assert normalise_label("  spaced   out  ") == "spaced out"


def test_never_click_still_widens_with_extra_patterns() -> None:
    policy = policy_for(
        make_project(WritePolicy.ALLOW_WRITES), never_click_patterns=[r"\bexit\b"],
    )
    assert deny_reason(el("Exit"), policy) is not None
    assert deny_reason(CONTROLS["log_out"], policy) is not None  # baseline still applies


# -- link safety --------------------------------------------------------------

PAGE = "https://www.vidysea.com/erp/dashboard/"
"""The page the links under test are ON — `link_is_safe` resolves against it,
exactly as the navigation does (AT-333)."""

BACKSLASH_HREFS = ["\\evil.test/x", "/a\\b", "\\\\evil.test"]
"""Hrefs `host_of` deliberately fails closed on (AT-007). Held as a name so the
literals are written once, in Python, and never retyped into a decorator."""


def _link(href: str) -> ElementRef:
    link = el("x", role="link")
    link.href = href
    return link


def test_same_domain_root_relative_link_is_safe() -> None:
    assert link_is_safe(_link("/erp/students"), make_project(), PAGE) is True


@pytest.mark.parametrize("href", ["students", "students/1/", "./students", "../up"])
def test_document_relative_links_are_safe(href: str) -> None:
    """AT-333: every one of these was REFUSED as off-domain, because the raw
    href was fed to `host_of`, which reads `students/1/` as the host
    `students`. They point at the same origin as the page they are on."""
    assert link_is_safe(_link(href), make_project(), PAGE) is True


def test_external_link_is_not_safe() -> None:
    assert link_is_safe(_link("https://example.com/"), make_project(), PAGE) is False


def test_javascript_and_mailto_links_are_never_safe() -> None:
    for href in ("javascript:void(0)", "mailto:x@y.com", "tel:+1234567890"):
        assert link_is_safe(_link(href), make_project(), PAGE) is False


def test_link_with_no_href_is_not_safe() -> None:
    assert link_is_safe(el("x", role="link"), make_project(), PAGE) is False


def test_protocol_relative_link_is_not_safe() -> None:
    assert link_is_safe(_link("//evil.test/phish"), make_project(), PAGE) is False


@pytest.mark.parametrize("href", BACKSLASH_HREFS)
def test_a_backslash_href_is_refused_not_waved_through(href: str) -> None:
    """AT-333's second half. `host_of` deliberately fails CLOSED on a backslash
    (AT-007: Chromium treats it as a path separator, so urlparse and the
    browser disagree about which host the navigation will reach). The old
    `if not host: return not href.startswith("//")` then read that empty host
    as "relative, therefore safe" — turning a deliberate fail-closed into a
    fail-open. A resolved URL with no host is now refused."""
    assert link_is_safe(_link(href), make_project(), PAGE) is False


def test_an_off_domain_link_resolved_from_an_off_domain_page_is_refused() -> None:
    """The base URL is an input, so it gets its own test: a relative link is
    safe because of the page it sits on, not on its own."""
    assert link_is_safe(_link("students"), make_project(), "https://evil.test/x/") is False


# -- request classification (X9) ----------------------------------------------

def test_first_party_request_is_classified_first_party() -> None:
    project = make_project()
    policy = policy_for(project)
    assert classify_request("https://www.vidysea.com/erp/api/x", project, policy) == "first_party"


def test_known_analytics_host_is_ignored() -> None:
    project = make_project()
    policy = policy_for(project)
    assert classify_request(
        "https://www.google-analytics.com/collect", project, policy
    ) == "ignored"


def test_unknown_third_party_host_is_noise() -> None:
    project = make_project()
    policy = policy_for(project)
    assert classify_request("https://cdn.unknown-third.test/x", project, policy) == "noise"


def test_userinfo_spoofed_host_is_never_first_party() -> None:
    """AT-007-style host confusion: a backslash-userinfo trick must not be
    classified as first-party."""
    project = make_project()
    policy = policy_for(project)
    spoofed = "https://evil.test" + chr(92) + "@www.vidysea.com/x"
    assert classify_request(spoofed, project, policy) != "first_party"


# -- dialog circuit breaker ----------------------------------------------------

def test_breaker_trips_after_the_limit() -> None:
    breaker = DialogBreaker(limit=3)
    event = DialogEvent(dialog_type="confirm", message="are you sure?")
    tripped = [breaker.record("node_a", event) for _ in range(5)]
    assert tripped == [False, False, False, True, True]


def test_breaker_counts_per_node() -> None:
    breaker = DialogBreaker(limit=1)
    event = DialogEvent(dialog_type="alert")
    assert breaker.record("node_a", event) is False
    assert breaker.record("node_b", event) is False  # different node, own count
    assert breaker.record("node_a", event) is True


def test_breaker_reset_clears_the_count() -> None:
    breaker = DialogBreaker(limit=1)
    event = DialogEvent(dialog_type="alert")
    breaker.record("node_a", event)
    breaker.record("node_a", event)  # tripped
    breaker.reset("node_a")
    assert breaker.record("node_a", event) is False
