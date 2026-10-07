"""AI CATALOG: which Track C checks apply to a classified AI target, and which can run now.

Contract: qa/contracts/ai-target.md AI2-AI5 (D-017). A model may NAME the target's kind
(`discover.classify_target`); it never CHOOSES the checks. The kind -> checks mapping is the
literal `CHECKS_BY_KIND` below, so a reader can re-derive it by eye. A kind that is not exactly a
member of `AiTargetKind` is refused outright, never mapped. The result extends the project's one
`Catalog` (CT7) with `ai_checks`; it is pure: no model call, no network call, no write.
"""

from __future__ import annotations

from autotester.schema.ai_check import AiCheckKind, AiCheckMethod
from autotester.schema.ai_target import AiTarget, AiTargetKind
from autotester.schema.catalog import AiCheckEntry, BlockedReason, Catalog, Tier

_SHAPE, _LATENCY = AiCheckKind.RESPONSE_SHAPE, AiCheckKind.LATENCY_BUDGET
_TRUTH, _TOOLS, _HANDOFF = (
    AiCheckKind.GROUND_TRUTH_ANSWER, AiCheckKind.TOOL_USE, AiCheckKind.HANDOFF_ORDER)

CHECKS_BY_KIND: dict[AiTargetKind, tuple[AiCheckKind, ...]] = {
    AiTargetKind.CONVERSATIONAL: (_SHAPE, _LATENCY, _TRUTH),
    AiTargetKind.AGENTIC: (_SHAPE, _LATENCY, _TRUTH, _TOOLS),
    AiTargetKind.ORCHESTRATION: (_SHAPE, _LATENCY, _TRUTH, _HANDOFF),
    AiTargetKind.HYBRID: (_SHAPE, _LATENCY, _TRUTH, _TOOLS, _HANDOFF),
}
"""The whole selection rule (AI2). Adding a kind or a check is an edit to this literal."""

CHECK_METHOD: dict[AiCheckKind, AiCheckMethod] = {
    _SHAPE: AiCheckMethod.COMPUTED,
    _LATENCY: AiCheckMethod.COMPUTED,
    _TRUTH: AiCheckMethod.JUDGED,
    _TOOLS: AiCheckMethod.JUDGED,
    _HANDOFF: AiCheckMethod.JUDGED,
}
"""Latency and shape are computed in code from recorded facts; the rest go to the judge (C7)."""

CHECK_TIER: dict[AiCheckKind, Tier] = {
    _SHAPE: Tier.STATIC,
    _LATENCY: Tier.STATIC,
    _TRUTH: Tier.BEHAVIOURAL,
    _TOOLS: Tier.BEHAVIOURAL,
    _HANDOFF: Tier.BEHAVIOURAL,
}
"""Cheap -> expensive, the same `Tier` ordering the web catalog uses (CT6)."""

NEEDS_GROUND_TRUTH = frozenset({_TRUTH})
"""Every check needs a live endpoint to capture from; these also need a ground-truth file."""

_KIND_BY_VALUE = {member.value: member for member in AiTargetKind}


class UnclassifiedTarget(ValueError):
    """The target has no valid kind, so no check set is chosen (AI3). Names no input text."""


def resolve_kind(raw: object) -> AiTargetKind:
    """The `AiTargetKind` that `raw` exactly is, or `UnclassifiedTarget`.

    Exact match only: the member itself, or a plain `str` equal to a member's value. No case
    folding, no trimming, no substring match and no `str` subclass (its `__eq__` can lie), so
    text that merely contains a kind or a check name cannot select anything (AI3)."""
    if isinstance(raw, AiTargetKind):
        return raw
    if type(raw) is str and raw in _KIND_BY_VALUE:
        return _KIND_BY_VALUE[raw]
    raise UnclassifiedTarget("target kind is not one of the closed AiTargetKind members")


def _blocker(target: AiTarget, kind: AiCheckKind) -> tuple[BlockedReason, str] | None:
    """The one reason (endpoint first) and the one action that clears it, or None if runnable."""
    if not (target.endpoint or "").strip():
        return (BlockedReason.NO_LIVE_ENDPOINT,
                f"no live endpoint is configured: set the endpoint of the AI target at "
                f"'{target.root_path}' so a run can be captured")
    if kind in NEEDS_GROUND_TRUTH and not target.has_ground_truth:
        return (BlockedReason.NO_GROUND_TRUTH,
                f"no ground-truth file was found: add reference question/answer pairs under "
                f"'{target.root_path}'")
    return None


def _entry(target: AiTarget, kind: AiCheckKind, applicable: bool) -> AiCheckEntry:
    blocker = _blocker(target, kind) if applicable else None
    return AiCheckEntry(
        kind=kind, tier=CHECK_TIER[kind], method=CHECK_METHOD[kind], applicable=applicable,
        runnable=applicable and blocker is None,
        blocked_reason=blocker[0] if blocker else None,
        unblock_action=blocker[1] if blocker else None)


def match(target: AiTarget, base: Catalog) -> Catalog:
    """`base` (the project's `Catalog`) with every `AiCheckKind` listed once in `ai_checks`.

    A non-AI target lists every check as not applicable. A target with no valid kind raises
    `UnclassifiedTarget` rather than guess. `base` is not mutated."""
    if target.not_ai_target:
        chosen: tuple[AiCheckKind, ...] = ()
    else:
        chosen = CHECKS_BY_KIND[resolve_kind(target.system_kind)]
    entries = [_entry(target, kind, kind in chosen) for kind in AiCheckKind]
    return Catalog(
        project=base.project, created_at=base.created_at, provenance=base.provenance,
        entries=base.entries, packs=base.packs, ai_checks=entries)
