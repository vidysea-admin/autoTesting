"""T-177 fix cycle 1: checker A's AF3 / X7 findings and the ProviderError mutant.

F1 landing-URL re-check, F3 key allow-list, F6 scheme, F10 ProviderError. Contract:
qa/contracts/agent-fallback.md AF3, explore.md X7. No real browser runs here.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_agent_fallback import Backend, click, result_for, with_policy
from test_agent_loop import LOGIN, make_case, make_project, session_with

from autotester.browser.session import NavigationRefused, check_destination
from autotester.providers.mock import MockProvider
from autotester.schema.agent_fallback import FallbackAction, FallbackActionKind, FallbackStatus
from autotester.schema.enums import Outcome, WritePolicy
from autotester.stages.agent_actuator import ActionGuard, ActionRefused, FallbackActuator
from autotester.stages.agent_loop import run_with_fallback

K = FallbackActionKind
OFF = "https://evil.example/landed"


class LandingBackend(Backend):
    """Acts, then leaves the shared page wherever the agent 'ended up'."""

    def __init__(self, session, lands_on: str, actions=None) -> None:
        super().__init__(actions)
        self.session, self.lands_on = session, lands_on

    def run(self, task, vet, *, max_steps, timeout_s):
        out = super().run(task, vet, max_steps=max_steps, timeout_s=timeout_s)
        self.session.page.url = self.lands_on
        return out


# -- F1 the landing URL is re-checked after the agent has acted ------------------------------

@pytest.mark.parametrize("landing", [
    OFF,                                        # a redirect that left the domain
    "https://evil.example/?next=app.pathlynks.test",  # an open redirect's final page
    "https://pathlynks.test.evil.example/",     # a lookalike suffix
    "javascript://app.pathlynks.test/%0aalert(1)",    # a script URL dressed in our host
])
def test_f1_an_off_scope_landing_page_is_a_blocked_step(tmp_path: Path, landing: str) -> None:
    session = session_with(tmp_path, set())
    outcome = FallbackActuator(LandingBackend(session, landing)).invoke(session, "explore")
    assert outcome.status is FallbackStatus.REFUSED
    assert "landed" in outcome.reason and "outside allowed domains" in outcome.reason
    assert any("landed" in r for r in outcome.refusals)
    assert outcome.result is None  # the agent's own "resolved" is not believed


def test_f1_an_in_scope_landing_is_unchanged(tmp_path: Path) -> None:
    session = session_with(tmp_path, set())
    inside = "https://app.pathlynks.test/plans"
    outcome = FallbackActuator(LandingBackend(session, inside)).invoke(session, "explore")
    assert outcome.status is FallbackStatus.RESOLVED


def test_f1_a_click_with_no_href_that_leaves_the_domain_is_still_caught(tmp_path: Path) -> None:
    session = session_with(tmp_path, set())
    no_href = click("Next")  # url=None: nothing for the per-action check to read
    outcome = FallbackActuator(LandingBackend(session, OFF, [no_href])).invoke(session, "t")
    assert outcome.status is FallbackStatus.REFUSED and outcome.vetted == [no_href]


def test_f1_the_guard_exposes_landed_for_a_backend_that_can_see_each_step(tmp_path) -> None:
    guard = ActionGuard(session_with(tmp_path, set()), 5, 60.0, lambda: 0.0)
    guard.landed("https://app.pathlynks.test/ok")
    with pytest.raises(ActionRefused, match="landed"):
        guard.landed(OFF)
    assert guard.refusals and "landed" in guard.refusals[0]


# -- F3 under read_only only a navigation key may be pressed ---------------------------------

def press(value: str) -> FallbackAction:
    return FallbackAction(kind=K.PRESS_KEY, value=value)


@pytest.mark.parametrize("key", [
    "Enter", "Return", "enter ", "NumpadEnter", "Control+Enter", "ctrl+enter", "Shift+Enter",
    "Meta+Enter", "Alt+Enter", "x\n", "hello", "Space", "Backspace", "Delete", "Control+a",
    "Enter Enter", "", "Control",
])
def test_f3_read_only_refuses_every_key_that_is_not_a_navigation_key(tmp_path, key) -> None:
    session = with_policy(session_with(tmp_path, set()), WritePolicy.READ_ONLY)
    outcome = FallbackActuator(Backend([press(key)])).invoke(session, "t")
    assert outcome.status is FallbackStatus.REFUSED and outcome.vetted == []
    assert "read_only" in " ".join(outcome.refusals)


@pytest.mark.parametrize("key", ["Tab", "Shift+Tab", "Escape", "ArrowDown", "PageDown", "Home",
                                 "End", "Control+Home", "Tab Tab"])
def test_f3_read_only_still_allows_navigation_keys(tmp_path: Path, key: str) -> None:
    session = with_policy(session_with(tmp_path, set()), WritePolicy.READ_ONLY)
    outcome = FallbackActuator(Backend([press(key)])).invoke(session, "t")
    assert outcome.status is FallbackStatus.RESOLVED


def test_f3_enter_is_allowed_when_the_policy_allows_writes(tmp_path: Path) -> None:
    session = with_policy(session_with(tmp_path, set()), WritePolicy.TEST_ACCOUNT)
    outcome = FallbackActuator(Backend([press("Enter")])).invoke(session, "t")
    assert outcome.status is FallbackStatus.RESOLVED


# -- F6 only http and https are destinations -------------------------------------------------

@pytest.mark.parametrize("url", [
    "javascript://app.pathlynks.test/%0aalert(1)", "data://app.pathlynks.test/x",
    "file://app.pathlynks.test/etc/passwd", "ftp://app.pathlynks.test/", "blob://app.pathlynks.test/",
    "JavaScript://app.pathlynks.test/x", "javascript:alert(1)", "about:blank",
    "chrome://settings", "ws://app.pathlynks.test/",
])
def test_f6_a_non_http_scheme_is_refused_even_when_the_host_matches(url: str) -> None:
    with pytest.raises(NavigationRefused):
        check_destination(make_project(), url)


@pytest.mark.parametrize("url", ["https://app.pathlynks.test/x", "HTTP://app.pathlynks.test/",
                                 "app.pathlynks.test/plain", "app.pathlynks.test:8443/x"])
def test_f6_http_https_and_scheme_less_hosts_still_pass(url: str) -> None:
    assert check_destination(make_project(), url) == "app.pathlynks.test"


# -- F10 a provider that cannot act ends the repair loop, never the run -----------------------

def test_f10_run_with_fallback_survives_a_provider_error(tmp_path: Path) -> None:
    session = session_with(tmp_path, {"button.old"})
    loop = run_with_fallback(make_case("button.old"), session, MockProvider())  # no responses
    assert loop.result.outcome is Outcome.ERRORED  # never silently a pass
    assert loop.iterations == 0 and loop.fixed is False
    assert loop.agent_error and "ProviderError" in loop.agent_error
    notes = [e.path for e in loop.result.evidence if "agent provider error" in e.path]
    assert len(notes) == 1 and "ProviderError" in notes[0]  # one diagnostic, still ERRORED


def test_f10_the_actuator_still_gets_its_one_attempt_after_a_provider_error(tmp_path) -> None:
    session = session_with(tmp_path, {"button.old"})
    backend = Backend([click("Next", url=LOGIN)], raw=result_for([click("Next", url=LOGIN)]))
    loop = run_with_fallback(make_case("button.old"), session, MockProvider(),
                             actuator=FallbackActuator(backend))
    assert backend.calls == 1 and loop.fallback is not None
    assert loop.result.outcome is Outcome.ERRORED  # evidence only, never a changed outcome
