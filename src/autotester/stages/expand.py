"""EXPAND: FlowSpec -> Case[], covering every applicable CaseClass per flow.

Contract: qa/contracts/expand.md X1-X5. Gate: `stages/review.py::require_generatable` (D-097):
an APPROVED spec expands through human-approved proposals; a reconciled DRAFT spec built from
sources expands with no human step, every case carrying "from unreviewed DRAFT flow" provenance.
NEEDS_EDIT and unreconciled flows are still refused.

AT-890 (D-084): a flow's steps come from source material (a video, a crawl), and the prompt
built from them goes to an external model. Emails and phone numbers are masked as the prompt is
built, and the whole prompt passes the project's redaction and `SecretStore.guard_prompt`
immediately before `provider.act` -- see `guard_expand_prompt`.
"""

from __future__ import annotations

from collections.abc import Callable

from autotester.browser.secrets import SecretStore
from autotester.core.paths import RepoDocs
from autotester.core.redact import mask_pii
from autotester.providers.base import Provider, load_skill_prompt
from autotester.schema.case import Case, CaseProposal, ExpandedSteps
from autotester.schema.enums import KIND_BY_CLASS, Action, CaseClass
from autotester.schema.flowspec import Flow, FlowSpec
from autotester.stages.review import (
    case_provenance,
    is_unreviewed_draft,
    require_generatable,
)
from autotester.store.project_store import ProjectStore

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
    # Mask each step on its own: the phone pattern spans whitespace, so masking the joined text
    # lets a value ending in a phone swallow the next line's ordinal.
    steps_text = "\n".join(
        mask_pii(f"{s.order}. {s.action.value} {s.target}" + (f" = {s.value}" if s.value else ""))
        for s in sorted(flow.steps, key=lambda s: s.order)
    )
    return (
        template.replace("{{CASE_CLASS}}", case_class.value)
        .replace("{{CLASS_DESCRIPTION}}", CLASS_DESCRIPTIONS.get(case_class, case_class.value))
        .replace("{{FLOW_NAME}}", mask_pii(flow.name))
        .replace("{{ORIGINAL_STEPS}}", steps_text)
    )


def guard_expand_prompt(prompt: str, secrets: SecretStore | None) -> str:
    """The prompt as the provider may see it: every .env value (declared or not) scrubbed out,
    then refused outright if a folded or encoded spelling of one is still in it. `{{SECRET:KEY}}`
    placeholders pass untouched. With no project there is nothing declared to guard; the PII
    mask already ran in `build_expand_prompt`."""
    if secrets is None:
        return prompt
    return secrets.guard_prompt(secrets.redactor().scrub(prompt))


def _store_secrets(store: ProjectStore | None) -> SecretStore | None:
    """The saved project's declared secrets, read the way every other stage reads them."""
    project = store.load_project() if store else None
    if project is None or store is None:
        return None
    return SecretStore.load(project, store.paths.env_file, strict=False)


def _happy_case(flow: Flow, project: str, provenance: str | None = None) -> Case:
    return Case(provenance=provenance,
        project=project, flow_id=flow.id, kind=KIND_BY_CLASS[CaseClass.HAPPY],
        case_class=CaseClass.HAPPY, title=f"{flow.name} — happy path",
        rationale="the flow's own observed steps", steps=list(flow.steps),
    )


def _expanded_case(
    flow: Flow, project: str, case_class: CaseClass, expanded: ExpandedSteps,
    provenance: str | None = None,
) -> Case | None:
    if not expanded.steps:
        return None
    return Case(provenance=provenance,
        project=project, flow_id=flow.id, kind=KIND_BY_CLASS[case_class],
        case_class=case_class, title=f"{flow.name} — {case_class.value}",
        rationale=expanded.rationale, steps=expanded.steps,
    )


def propose_cases(spec: FlowSpec) -> list[CaseProposal]:
    """Prepare a deterministic step-less taxonomy for human review, with no provider calls."""
    require_generatable(spec)
    return [CaseProposal(
        project=spec.project, flow_id=flow.id,
        spec_fingerprint=CaseProposal.fingerprint_for(spec), case_class=case_class,
        title=f"{flow.name} — {case_class.value}",
        rationale=("the flow's own observed steps" if case_class is CaseClass.HAPPY
                   else CLASS_DESCRIPTIONS[case_class]),
    ) for flow in spec.flows for case_class in applicable_classes(flow)]


def _scrub_proposals(rows: list[CaseProposal], by: str,
                     secrets: SecretStore | None) -> list[CaseProposal]:
    """AT-929 (C5): case_proposals.jsonl is a stored artifact, so operator and target text
    passes the project redactor before it is staged. `by` and `flow_id` cannot be masked
    (attribution, and the link back to the FlowSpec), so a secret in either is refused."""
    if secrets is None:
        return rows
    scrub = secrets.redactor().scrub
    if scrub(by) != by:
        raise ValueError("the reviewer name matches a stored secret; use your own name")
    if any(scrub(p.flow_id) != p.flow_id for p in rows):
        raise ValueError("a flow id matches a stored secret; rename the flow before staging")
    return [CaseProposal.model_validate({**p.model_dump(), "id": "", "title": scrub(p.title),
                                         "rationale": scrub(p.rationale)}) for p in rows]


def stage_scrubbed_proposals(store: ProjectStore, spec: FlowSpec,
                             by: str = "") -> list[CaseProposal]:
    """The one way proposals reach case_proposals.jsonl: scrubbed first (AT-929), then staged."""
    rows = _scrub_proposals(propose_cases(spec), by, _store_secrets(store))
    store.stage_case_proposals(rows)
    return rows


def stage_and_review(store: ProjectStore, spec: FlowSpec, approve: list[str],
                     prune: list[str], by: str) -> list[CaseProposal]:
    """Stage this spec's proposals, apply the human's approve/prune decisions, return the rows."""
    rows = stage_scrubbed_proposals(store, spec, by)
    if set(approve) & set(prune):
        raise ValueError("a proposal cannot be approved and pruned together")
    for proposal_id in approve + prune:
        store.review_case_proposal(proposal_id, by=by, approved=proposal_id in approve)
    ids = {p.id for p in rows}
    return [p for p in store.list_case_proposals() if p.id in ids]


def _reviewed_batch(spec: FlowSpec, store: ProjectStore | None,
                    proposal_ids: list[str] | None = None,
                    flow_id: str | None = None) -> list[CaseProposal]:
    if is_unreviewed_draft(spec):  # D-097: no human step; the whole taxonomy, unapproved
        return [p for p in propose_cases(spec) if (flow_id is None or p.flow_id == flow_id)
                and (proposal_ids is None or p.id in proposal_ids)]
    if store is None:
        raise ValueError("saved human-reviewed case proposals are required")
    batch = store.preflight_case_proposals(spec, proposal_ids, flow_id)
    canonical = {p.slot_id for p in propose_cases(spec)}
    if any(p.slot_id not in canonical for p in batch):
        raise ValueError("proposal differs from the staged current taxonomy")
    return batch


def _expand_reviewed_flow(flow: Flow, project: str, provider: Provider, docs: RepoDocs,
                          proposals: list[CaseProposal], secrets: SecretStore | None,
                          draft: bool = False,
                          before_call: Callable[[], None] | None = None) -> list[Case]:
    prov = case_provenance(flow.source_id) if draft else None
    cases = [_happy_case(flow, project, prov)]
    for proposal in proposals:
        if proposal.flow_id != flow.id or proposal.case_class is CaseClass.HAPPY:
            continue
        prompt = mask_pii(  # AT-840
            guard_expand_prompt(build_expand_prompt(flow, proposal.case_class, docs), secrets))
        if before_call is not None:
            before_call()
        expanded = provider.act(prompt, ExpandedSteps, prompt_file=SKILL_NAME, fed_id=flow.id)
        case = _expanded_case(flow, project, proposal.case_class, expanded, prov)
        if case is not None:
            cases.append(case)
    return cases


def expand_flow(
    flow: Flow, project: str, provider: Provider, docs: RepoDocs | None = None,
    *, store: ProjectStore | None = None, proposal_ids: list[str] | None = None,
    secrets: SecretStore | None = None,
) -> list[Case]:
    """Expand one exact saved flow after its persisted proposal approvals are checked."""
    spec = store.load_flowspec() if store else None
    if spec is None or spec.project != project or spec.flow(flow.id) != flow:
        raise ValueError("flow differs from the current saved FlowSpec")
    require_generatable(spec)
    batch = _reviewed_batch(spec, store, proposal_ids, flow.id)
    return _expand_reviewed_flow(flow, project, provider, docs or RepoDocs(), batch,
                                 secrets or _store_secrets(store), is_unreviewed_draft(spec))


def expand(spec: FlowSpec, provider: Provider, docs: RepoDocs | None = None,
           *, store: ProjectStore | None = None, proposal_ids: list[str] | None = None,
           secrets: SecretStore | None = None,
           before_call: Callable[[], None] | None = None) -> list[Case]:
    """Generate only saved approved proposals; check every flow before the first model call."""
    require_generatable(spec)
    batch = _reviewed_batch(spec, store, proposal_ids)
    guard = secrets or _store_secrets(store)
    cases: list[Case] = []
    for flow in spec.flows:
        cases.extend(_expand_reviewed_flow(
            flow, spec.project, provider, docs or RepoDocs(), batch, guard,
            is_unreviewed_draft(spec), before_call))
    return cases
