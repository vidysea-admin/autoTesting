"""Track C check vocabulary: which behavioural checks exist for an AI target (D-017).

Closed enums only. Which checks apply to a target kind is decided by a literal table in
`stages/ai_catalog.py`, never by a model; how a check is decided (code or judge) is a
literal fact recorded there as well.
"""

from __future__ import annotations

from enum import StrEnum


class AiCheckKind(StrEnum):
    """One behavioural check an AI target can be put through. Enum order is report order."""

    RESPONSE_SHAPE = "response_shape"
    LATENCY_BUDGET = "latency_budget"
    GROUND_TRUTH_ANSWER = "ground_truth_answer"
    TOOL_USE = "tool_use"
    HANDOFF_ORDER = "handoff_order"


class AiCheckMethod(StrEnum):
    """Who decides a check: code from recorded facts, or the independent judge (C7)."""

    COMPUTED = "computed"
    JUDGED = "judged"
