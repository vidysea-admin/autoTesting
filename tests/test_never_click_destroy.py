"""Umesh 2026-10-15 "Block destroy buttons": account-destroying controls are never clicked at any
write policy, on every action path; ordinary writes stay allowed under allow_writes."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from autotester.agents import guards
from autotester.browser.session import AccountDestroyRefused, BrowserSession
from autotester.schema.agent_fallback import FallbackAction, FallbackActionKind
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, WritePolicy
from autotester.schema.flowspec import Step
from autotester.schema.project import Project
from autotester.schema.screen_graph import ElementRef
from autotester.stages.agent_actuator import ActionGuard
from autotester.stages.explore_safety import (
    ACCOUNT_DESTROY_REFUSED,
    deny_reason,
    destroys_account,
    policy_for,
)

BASE = "https://app.test"
DESTROY = ["Close account", "Delete account", "Deactivate account", "Delete my profile",
           "Terminate account", "Erase my data", "CLOSE  ACCOUNT", "Delete-Account",
           "Close my account", "Permanently delete"]
ALLOWED = ["Save", "Book session", "Delete draft", "Remove profile photo", "Pay now",
           "Close dialog", "Account settings", "Close account settings", "Delete row"]


def _project(policy: WritePolicy = WritePolicy.ALLOW_WRITES) -> Project:
    return Project(slug="demo", name="Demo", base_url=BASE, allowed_domains=["app.test"],
                   write_policy=policy)


@pytest.mark.parametrize("name", DESTROY)
def test_matcher_blocks_destroy_names(name: str) -> None:
    assert destroys_account(name)
    assert destroys_account(None, name.lower())


@pytest.mark.parametrize("name", ALLOWED)
def test_matcher_allows_ordinary_names(name: str) -> None:
    assert not destroys_account(name)


@pytest.mark.parametrize("policy", list(WritePolicy))
def test_crawl_deny_reason_all_policies(policy: WritePolicy) -> None:
    pol = policy_for(_project(policy))
    for name in ("Close account", "Delete account"):
        el = ElementRef(role="button", name=name, selector="#x")
        assert deny_reason(el, pol) == ACCOUNT_DESTROY_REFUSED
    for name in ("Save", "Book session"):
        assert deny_reason(ElementRef(role="button", name=name, selector="#x"),
                           pol) is None or policy is WritePolicy.READ_ONLY
    ad = ElementRef(role="button", name="Delete draft", selector="#x")
    allowed = WritePolicy.ALLOW_WRITES
    assert deny_reason(ad, policy_for(_project(allowed))) is None


def _case(target: str) -> Case:
    return Case(project="demo", flow_id="f", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                title="c", steps=[Step(order=1, action=Action.CLICK, target=target)])


@pytest.mark.parametrize("target", ["Close account", "Delete account"])
def test_case_guard_refuses_under_allow_writes(target: str) -> None:
    out = guards.write_policy_refusal(_case(target), _project())
    assert out is not None and ACCOUNT_DESTROY_REFUSED in out[1]


@pytest.mark.parametrize("target", ["Save", "Book session", "Delete draft"])
def test_case_guard_allows_ordinary_under_allow_writes(target: str) -> None:
    assert guards.write_policy_refusal(_case(target), _project()) is None


def test_read_only_close_account_now_refused() -> None:
    assert guards.write_policy_refusal(_case("Close account"), _project(WritePolicy.READ_ONLY))


def _actuator() -> ActionGuard:
    return ActionGuard(SimpleNamespace(project=_project()), 5, 60.0, lambda: 0.0)


@pytest.mark.parametrize("name", ["Close account", "Delete account"])
def test_actuator_refuses(name: str) -> None:
    act = FallbackAction(kind=FallbackActionKind.CLICK, target=name, role="button")
    assert _actuator().refusal(act) == ACCOUNT_DESTROY_REFUSED


@pytest.mark.parametrize("name", ["Save", "Book session", "Delete draft"])
def test_actuator_allows(name: str) -> None:
    act = FallbackAction(kind=FallbackActionKind.CLICK, target=name, role="button")
    assert _actuator().refusal(act) is None


class _Target:
    def __init__(self, facts: list[Any]) -> None:
        self.facts, self.clicked = facts, False

    def evaluate(self, *_a: Any, **_k: Any) -> list[Any]:
        return self.facts

    def click(self, **_k: Any) -> None:
        self.clicked = True

    def press(self, *_a: Any, **_k: Any) -> None:
        self.clicked = True


def _session(target: _Target) -> BrowserSession:
    s = BrowserSession.__new__(BrowserSession)
    s.budget = None
    s.locate = lambda _loc: target  # type: ignore[method-assign]
    s._record = lambda *a, **k: None  # type: ignore[method-assign]
    return s


@pytest.mark.parametrize("locator,facts", [
    ("role=button[name='Close account']", []),
    ("#btn", ["Delete account", None, None, None]),
    ("#btn", ["X", "Delete account", None, None]),  # aria-label
])
def test_session_click_and_submit_refuse(locator: str, facts: list[Any]) -> None:
    target = _Target(facts)
    s = _session(target)
    with pytest.raises(AccountDestroyRefused):
        s.click(locator)
    with pytest.raises(AccountDestroyRefused):
        s.press_key("Enter", locator)
    assert not target.clicked


def test_session_click_allows_ordinary(monkeypatch: pytest.MonkeyPatch) -> None:
    target = _Target(["Book session", "Book", None, None])
    s = _session(target)
    monkeypatch.setattr("autotester.browser.session.ready_to_click", lambda *_a: [])
    s._page = SimpleNamespace()
    s.click("#book")
    assert target.clicked
