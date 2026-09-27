"""EXPAND: FlowSpec -> Case[], covering every applicable CaseClass per flow.

Contract: qa/contracts/expand.md X1-X5. Requires an APPROVED FlowSpec
(`stages/review.py::require_reviewed`) — expanding an unreviewed guess would
multiply one guess into a dozen, exactly what the review gate exists to stop.
"""

from __future__ import annotations

from autotester.core.paths import RepoDocs
from autotester.providers.base import Provider, load_skill_prompt
from autotester.schema.case import Case, ExpandedSteps
from autotester.schema.enums import KIND_BY_CLASS, Action, CaseClass
from autotester.schema.flowspec import Flow, FlowSpec
from autotester.stages.review import require_reviewed

SKILL_NAME = "expand-case"  # src/autotester/skills/expand-case/SKILL.md (T-175, was expand_case_v1)

CLASS_DESCRIPTIONS: dict[CaseClass, str] = {
    CaseClass.INPUT_EMPTY: "submit with a required field left empty",
    CaseClass.INPUT_BOUNDARY: "a filled field at its size/length/value boundary",
    CaseClass.INPUT_UNICODE_OVERSIZE: "a filled field with unicode/emoji or an oversized value",
    CaseClass.AUTH_WRONG_CREDS: "submit with a deliberately wrong credential",
    CaseClass.AUTH_EXPIRED_SESSION: "attempt the flow with an expired/invalid session",
    CaseClass.DOUBLE_SUBMIT: "submit the same action twice in a row",
    CaseClass.BACK_REFRESH_MIDFLOW: "navigate back or refresh partway through the flow",
    CaseClass.NETWORK_OFFLINE_SLOW: "the network is offline or very slow during the flow",
    CaseClass.SERVER_ERROR: "the backend returns an error partway through",
    CaseClass.VIEWPORT_MOBILE: "the same flow on a mobile-sized viewport",
    CaseClass.LOCALE_I18N: "the same flow with a non-default locale/language",
    CaseClass.CONCURRENT_TAB: "the same flow open in two browser tabs at once",
    CaseClass.DEEPLINK_UNAUTH: "a deep link into the flow without being authenticated first",
    CaseClass.REGRESSION_ANCHOR: (
        "the flow's happy path as a REGRESSION ANCHOR: a stable, minimal replay of exactly "
        "the observed steps, whose only job is to fail loudly when a future change breaks "
        "this flow — prefer the flow's own steps unchanged, adding nothing clever"
    ),
}

# Classes every flow is asked about, regardless of what steps it has (D-004:
# deterministic only where confident -- "this flow has a fillable input" is
# confident; "does locale matter here" is not, so it still goes to the model,
# which may say "not applicable" via an empty ExpandedSteps.steps).
UNIVERSAL_CLASSES = [
    CaseClass.DOUBLE_SUBMIT, CaseClass.BACK_REFRESH_MIDFLOW, CaseClass.NETWORK_OFFLINE_SLOW,
    CaseClass.SERVER_ERROR, CaseClass.VIEWPORT_MOBILE, CaseClass.LOCALE_I18N,
    CaseClass.CONCURRENT_TAB, CaseClass.DEEPLINK_UNAUTH,
]


def _has_fill(flow: Flow) -> bool:
    return any(s.action is Action.FILL for s in flow.steps)


def _has_auth_field(flow: Flow) -> bool:
    return any(s.action is Action.FILL and s.value and "SECRET" in s.value for s in flow.steps)


def applicable_classes(flow: Flow) -> list[CaseClass]:
    """The classes this flow is asked about — HAPPY always, input classes only
    when the flow actually fills something, auth classes only when a fill step
    references a secret, universal classes always, and the REGRESSION_ANCHOR
    last (AT-541: it was declared in `KIND_BY_CLASS` with `CaseKind.ANCHOR`
    but unreachable from here — the one kind the pipeline could never
    produce. It is asked like a universal class, and the model may still
    decline; a declined anchor is fine because the regression-proof scripts
    build their anchors directly, and T-167's release trigger will consume
    whatever anchors exist)."""
    classes = [CaseClass.HAPPY]
    if _has_fill(flow):
        classes += [CaseClass.INPUT_EMPTY, CaseClass.INPUT_BOUNDARY,
                    CaseClass.INPUT_UNICODE_OVERSIZE]
    if _has_auth_field(flow):
        classes += [CaseClass.AUTH_WRONG_CREDS, CaseClass.AUTH_EXPIRED_SESSION]
    classes += UNIVERSAL_CLASSES
    classes.append(CaseClass.REGRESSION_ANCHOR)
    return classes


def build_expand_prompt(flow: Flow, case_class: CaseClass, docs: RepoDocs) -> str:
    template = load_skill_prompt(SKILL_NAME, skills_dir=docs.skills_dir)
    steps_text = "\n".join(
        f"{s.order}. {s.action.value} {s.target}" + (f" = {s.value}" if s.value else "")
        for s in sorted(flow.steps, key=lambda s: s.order)
    )
    return (
        template.replace("{{CASE_CLASS}}", case_class.value)
        .replace("{{CLASS_DESCRIPTION}}", CLASS_DESCRIPTIONS.get(case_class, case_class.value))
        .replace("{{FLOW_NAME}}", flow.name)
        .replace("{{ORIGINAL_STEPS}}", steps_text)
    )


def _happy_case(flow: Flow, project: str) -> Case:
    return Case(
        project=project, flow_id=flow.id, kind=KIND_BY_CLASS[CaseClass.HAPPY],
        case_class=CaseClass.HAPPY, title=f"{flow.name} — happy path",
        rationale="the flow's own observed steps", steps=list(flow.steps),
    )


def _expanded_case(
    flow: Flow, project: str, case_class: CaseClass, expanded: ExpandedSteps
) -> Case | None:
    if not expanded.steps:
        return None
    return Case(
        project=project, flow_id=flow.id, kind=KIND_BY_CLASS[case_class],
        case_class=case_class, title=f"{flow.name} — {case_class.value}",
        rationale=expanded.rationale, steps=expanded.steps,
    )


def expand_flow(
    flow: Flow, project: str, provider: Provider, docs: RepoDocs | None = None
) -> list[Case]:
    """One flow -> one Case per applicable CaseClass (HAPPY, plus every other
    class the model didn't decline)."""
    docs = docs or RepoDocs()
    cases = [_happy_case(flow, project)]
    for case_class in applicable_classes(flow):
        if case_class is CaseClass.HAPPY:
            continue
        prompt = build_expand_prompt(flow, case_class, docs)
        expanded = provider.act(prompt, ExpandedSteps,
                                prompt_file=SKILL_NAME, fed_id=flow.id)
        case = _expanded_case(flow, project, case_class, expanded)
        if case is not None:
            cases.append(case)
    return cases


def expand(spec: FlowSpec, provider: Provider, docs: RepoDocs | None = None) -> list[Case]:
    """FlowSpec -> every flow's cases. Requires `spec.review.status == APPROVED`
    (`require_reviewed` raises otherwise) — the review gate this stage exists to
    respect, not bypass."""
    require_reviewed(spec)
    cases: list[Case] = []
    for flow in spec.flows:
        cases.extend(expand_flow(flow, spec.project, provider, docs))
    return cases
