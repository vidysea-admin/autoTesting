"""One job: refuse a click or submit on an account-destroying control, at every write policy.

The list and matcher live in `schema.crawl` / `explore_safety` (one concept, one place); this
mixin only asks them about the locator and the element's own text, aria-label, title and value.
"""

from __future__ import annotations

from typing import Any


class AccountDestroyRefused(RuntimeError):
    """A click/submit on an account-destroying control, refused at every write policy."""


def refuse_destroy(*labels: str | None) -> None:
    from autotester.stages.explore_safety import ACCOUNT_DESTROY_REFUSED, destroys_account
    if destroys_account(*labels):
        raise AccountDestroyRefused(ACCOUNT_DESTROY_REFUSED)


class DestroyGuardMixin:
    def _guard_destroy(self, target: Any, locator: str) -> None:
        """Refuse by locator, visible text, aria-label, title or value."""
        refuse_destroy(locator)
        try:
            facts = target.evaluate(
                "el => [el.innerText, el.getAttribute('aria-label'), el.getAttribute('title'),"
                " el.value]", **self._timeout(2000))  # type: ignore[attr-defined]
        except Exception:  # unreadable element: the locator check above already ran
            return
        refuse_destroy(*[str(f) for f in facts or [] if f])
