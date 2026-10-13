"""The per-run token/cost meter of the lead tester (T-179, AL11).

One `Meter` per run counts the tokens every model call used (the provider's own usage figure,
else a length estimate, so a model that reports none still cannot run unbounded) and says when
the declared `TokenBudget` is passed. The framework middleware (`agents/lead_agent.py`) raises
`BudgetExceeded` on a breach: the run HALTS with a named reason; it is never silently truncated.
"""

from __future__ import annotations

from typing import Any

from autotester.schema.lead_loop import TokenBudget


class BudgetExceeded(Exception):
    """The run passed its declared budget; `str(exc)` is the named reason."""


class Meter:
    def __init__(self, budget: TokenBudget | None = None) -> None:
        self.budget, self.tokens = budget or TokenBudget(), 0

    def add_message(self, message: Any) -> None:
        """Add one model reply's tokens: reported usage when present, else ~4 chars a token."""
        usage = getattr(message, "usage_metadata", None) or {}
        used = usage.get("total_tokens")
        if not isinstance(used, int):
            used = max(1, len(str(getattr(message, "content", ""))) // 4)
        self.tokens += used

    @property
    def cost_usd(self) -> float:
        return self.tokens * self.budget.usd_per_million_tokens / 1_000_000

    def check(self) -> None:
        """Raise `BudgetExceeded` with the breach named, else return."""
        b = self.budget
        if b.max_tokens is not None and self.tokens > b.max_tokens:
            raise BudgetExceeded(f"token budget exceeded: {self.tokens} > {b.max_tokens}")
        if b.max_cost_usd is not None and self.cost_usd > b.max_cost_usd:
            raise BudgetExceeded(
                f"cost budget exceeded: ${self.cost_usd:.4f} > ${b.max_cost_usd:.4f}")
