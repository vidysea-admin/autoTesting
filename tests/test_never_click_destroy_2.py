"""Never-click destroy, follow-up: bare verbs on account pages, joined/camelCase names, href-only
links, confirm dialogs after a destroy request, and page-level Enter."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from autotester.agents import guards
from autotester.browser.destroy_guard import AccountDestroyRefused
from autotester.browser.session import BrowserSession
from autotester.schema.agent_fallback import FallbackAction, FallbackActionKind
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, WritePolicy
from autotester.schema.flowspec import Step
from autotester.schema.project import Project
from autotester.schema.screen_graph import ElementRef
from autotester.stages.account_destroy import (
    ACCOUNT_DESTROY_REFUSED,
    DestroyContext,
    destroying_href,
    destroys_account,
)
from autotester.stages.agent_actuator import ActionGuard
from autotester.stages.explore_safety import deny_reason, policy_for

PROJECT = Project(slug="demo", name="Demo", base_url="https://app.test",
                  allowed_domains=["app.test"], write_policy=WritePolicy.ALLOW_WRITES)
POLICY = policy_for(PROJECT)


@pytest.mark.parametrize("name", ["Deactivate", "Terminate", "Delete user"])
def test_bare_verbs_blocked_on_account_pages(name: str) -> None:
    for page in ("/account/settings", "/profile", "/settings/security Account settings"):
        assert destroys_account(name, context=page)
        el = ElementRef(role="button", name=name, selector="#x")
        assert deny_reason(el, POLICY, page=page) == ACCOUNT_DESTROY_REFUSED


@pytest.mark.parametrize("name", ["Deactivate", "Terminate", "Delete user"])
def test_bare_verbs_allowed_elsewhere(name: str) -> None:
    assert not destroys_account(name, context="/admin/jobs Job list")
    assert not destroys_account(name)


@pytest.mark.parametrize("name", ["DeleteAccount", "closeaccount", "CloseAccount",
                                  "delete_account", "deactivateMyAccount", "close-account"])
def test_joined_and_camel_case(name: str) -> None:
    assert destroys_account(name)


@pytest.mark.parametrize("href", ["/account/delete", "/account/close", "/profile/delete",
                                  "/deactivate", "https://app.test/account/delete?x=1",
                                  "/delete-account"])
def test_href_only_links(href: str) -> None:
    assert destroying_href(href)
    el = ElementRef(role="link", name="Continue", selector="a", href=href)
    assert deny_reason(el, POLICY) == ACCOUNT_DESTROY_REFUSED


@pytest.mark.parametrize("href", ["/drafts/delete", "/cart/remove", "/account/settings", "/"])
def test_ordinary_hrefs_allowed(href: str) -> None:
    assert not destroying_href(href)


def test_confirm_blocked_only_inside_destroy_context() -> None:
    clock = [0.0]
    ctx = DestroyContext(ttl_s=10, clock=lambda: clock[0])
    for name in ("Confirm", "Yes", "Yes, delete", "OK"):
        assert not destroys_account(name, ctx=ctx)  # no context yet
    assert destroys_account("Delete account", ctx=ctx)
    for name in ("Confirm", "Yes", "Yes, delete", "OK"):
        assert destroys_account(name, ctx=ctx)
    clock[0] = 11.0  # short-lived
    assert not destroys_account("Confirm", ctx=ctx)


def test_still_allowed() -> None:
    ctx = DestroyContext()
    for name in ("Delete draft", "Remove from cart", "Close dialog", "Cancel subscription"):
        assert not destroys_account(name, context="/account/settings", ctx=ctx)


def _case(*steps: tuple[Action, str]) -> Case:
    return Case(project="demo", flow_id="f", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                title="c", steps=[Step(order=i, action=a, target=t)
                                  for i, (a, t) in enumerate(steps, 1)])


def test_case_guard_href_navigate_and_confirm() -> None:
    out = guards.write_policy_refusal(_case((Action.NAVIGATE, "/account/delete")), PROJECT)
    assert out is not None and ACCOUNT_DESTROY_REFUSED in out[1]
    out = guards.write_policy_refusal(_case((Action.CLICK, "DeleteAccount")), PROJECT)
    assert out is not None
    assert guards.write_policy_refusal(_case((Action.CLICK, "Confirm")), PROJECT) is None


def test_actuator_confirm_after_destroy() -> None:
    g = ActionGuard(SimpleNamespace(project=PROJECT), 5, 60.0, lambda: 0.0)

    def click(name: str) -> str | None:
        return g.refusal(FallbackAction(kind=FallbackActionKind.CLICK, target=name))

    assert click("Confirm") is None
    assert click("closeAccount") == ACCOUNT_DESTROY_REFUSED
    assert click("Yes, delete") == ACCOUNT_DESTROY_REFUSED
    assert click("Deactivate") is None  # no account page known


class _El:
    def __init__(self, facts: list[Any]) -> None:
        self.facts, self.clicked = facts, False

    def evaluate(self, *_a: Any, **_k: Any) -> Any:
        return self.facts

    def click(self, **_k: Any) -> None:
        self.clicked = True


class _Page:
    def __init__(self, focused: list[Any] | None, ctx: str = "/dashboard") -> None:
        self.focused, self.ctx, self.pressed = focused, ctx, False
        self.keyboard = SimpleNamespace(press=lambda _k: setattr(self, "pressed", True))

    def evaluate(self, js: str) -> Any:
        return self.focused if "activeElement" in js else self.ctx


def _session(page: _Page, el: _El | None = None) -> BrowserSession:
    s = BrowserSession.__new__(BrowserSession)
    s.budget = None
    s._page = page
    s.locate = lambda _l: el  # type: ignore[method-assign]
    s._record = lambda *a, **k: None  # type: ignore[method-assign]
    return s


def test_session_href_bare_verb_and_confirm() -> None:
    s = _session(_Page(None, "/account/settings Account"),
                 _El(["Deactivate", None, None, None, None]))
    with pytest.raises(AccountDestroyRefused):
        s.click("#b")
    s2 = _session(_Page(None), _El(["Go", None, None, None, "/account/close"]))
    with pytest.raises(AccountDestroyRefused):
        s2.click("#b")
    s2.locate = lambda _l: _El(["Yes", None, None, None, None])  # type: ignore[method-assign]
    with pytest.raises(AccountDestroyRefused):  # confirm right after a destroy request
        s2.click("#confirm")


@pytest.mark.parametrize("key", ["Enter", " "])
def test_page_level_enter_refused_when_focus_is_destroy(key: str) -> None:
    page = _Page(["Delete account", None, None, None, None])
    with pytest.raises(AccountDestroyRefused):
        _session(page).press_key(key)
    assert not page.pressed


def test_page_level_enter_allowed_on_ordinary_focus() -> None:
    page = _Page(["Save", None, None, None, None])
    _session(page).press_key("Enter")
    assert page.pressed
    page2 = _Page(None)
    _session(page2).press_key("Enter")
    assert page2.pressed
