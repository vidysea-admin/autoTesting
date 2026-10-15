"""One job: refuse a click or submit on an account-destroying control, at every write policy.

The list and matcher live in `stages.account_destroy` (one concept, one place); this mixin only
asks them about the locator, the element's own text, aria-label, title, value and href, the page
it sits on, and (for a page-level Enter) the focused element. Refusals open a short-lived destroy
context so a following Confirm / Yes / OK is refused too.
"""

from __future__ import annotations

from typing import Any

from autotester.stages.account_destroy import (
    ACCOUNT_DESTROY_REFUSED,
    DestroyContext,
    destroys_account,
)

_FACTS_JS = ("el => [el.innerText, el.getAttribute('aria-label'), el.getAttribute('title'),"
             " el.value, el.getAttribute('href')]")
_FOCUS_JS = ("() => { const el = document.activeElement; if (!el || el === document.body)"
             " return null; return [el.innerText, el.getAttribute('aria-label'),"
             " el.getAttribute('title'), el.value, el.getAttribute('href')]; }")
_PAGE_JS = "() => location.pathname + ' ' + (document.querySelector('h1,h2')?.innerText || '')"
_SUBMIT_KEYS = frozenset({"Enter", " ", "Space"})


class AccountDestroyRefused(RuntimeError):
    """A click/submit on an account-destroying control, refused at every write policy."""


class DestroyGuardMixin:
    @property
    def destroy_ctx(self) -> DestroyContext:
        if "_destroy_ctx" not in self.__dict__:
            self.__dict__["_destroy_ctx"] = DestroyContext()
        return self.__dict__["_destroy_ctx"]  # type: ignore[no-any-return]

    def _page_context(self) -> str:
        try:
            return str(self.page.evaluate(_PAGE_JS))  # type: ignore[attr-defined]
        except Exception:
            return ""

    def _refuse_if_destroying(self, locator: str, facts: list[Any] | None) -> None:
        facts = [str(f) if f else None for f in facts or []]
        href = facts[4] if len(facts) > 4 else None
        if destroys_account(locator, *facts[:4], href=href, context=self._page_context(),
                            ctx=self.destroy_ctx):
            raise AccountDestroyRefused(ACCOUNT_DESTROY_REFUSED)

    def _guard_destroy(self, target: Any, locator: str) -> None:
        """Refuse by locator, visible text, aria-label, title, value or href."""
        try:
            facts = target.evaluate(_FACTS_JS, **self._timeout(2000))  # type: ignore[attr-defined]
        except Exception:  # unreadable element: the locator check still runs
            facts = None
        self._refuse_if_destroying(locator, facts)

    def _guard_focused(self, key: str) -> None:
        """A page-level Enter/Space submits whatever has focus: judge the focused element."""
        if key not in _SUBMIT_KEYS:
            return
        try:
            facts = self.page.evaluate(_FOCUS_JS)  # type: ignore[attr-defined]
        except Exception:
            return
        self._refuse_if_destroying("", facts)
