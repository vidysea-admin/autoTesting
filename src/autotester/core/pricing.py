"""Per-token cost estimates for LLM-call trace spans (D-041 phase 1, RT4).

A small, honestly-partial table keyed on `Provider.label` ('id:model'):
an unknown label costs 0.0 rather than raising, because emitting a trace span
must never depend on the pricing table being exhaustive. Rates are USD per
1,000 tokens, input and output priced separately.
"""

from __future__ import annotations

_RATES_PER_1K: dict[str, tuple[float, float]] = {
    "anthropic:claude-sonnet-5": (0.003, 0.015),
    "gemini:gemini-3.6-flash": (0.000075, 0.0003),
    "mock:mock": (0.0, 0.0),
}
"""(input_rate, output_rate). `langchain-fallback:*` labels are intentionally
absent -- that provider's `id` becomes the winning tier's name after a call
(`LangChainFallbackProvider.label`), so its labels collide with the tiers
above once a call succeeds and need no separate entry."""


def estimate_cost(label: str, input_tokens: int, output_tokens: int) -> float:
    """`label` is `Provider.label`. Unknown label -> 0.0, never a raise."""
    rates = _RATES_PER_1K.get(label)
    if rates is None:
        return 0.0
    in_rate, out_rate = rates
    return round(input_tokens / 1000 * in_rate + output_tokens / 1000 * out_rate, 6)
