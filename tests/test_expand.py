"""EXPAND stage. Contract: qa/contracts/expand.md X1-X5."""

from __future__ import annotations

import pytest

from autotester.providers.mock import MockProvider
from autotester.schema.case import ExpandedSteps
from autotester.schema.enums import Action, CaseClass, CaseKind
from autotester.schema.flowspec import Flow, FlowSpec, Step
from autotester.stages.expand import applicable_classes, expand, expand_flow, propose_cases
from autotester.stages.review import FlowSpecNotReviewed, approve
from autotester.store.project_store import ProjectStore

LOGIN_FLOW = Flow(
    id="flow_login", name="Login",
    entry_screen="scr_signin",
    steps=[
        Step(order=1, action=Action.NAVIGATE, target="https://app.test/signin"),
        Step(order=2, action=Action.FILL, target="email field", value="{{SECRET:USER_EMAIL}}"),
        Step(order=3, action=Action.FILL, target="password field",
             value="{{SECRET:USER_PASSWORD}}"),
        Step(order=4, action=Action.CLICK, target="Login button"),
    ],
)

NO_FILL_FLOW = Flow(
    id="flow_browse", name="Browse catalog",
    entry_screen="scr_home",
    steps=[
        Step(order=1, action=Action.NAVIGATE, target="https://app.test/catalog"),
        Step(order=2, action=Action.CLICK, target="First item"),
    ],
)


def approved_spec(flows: list[Flow]) -> FlowSpec:
    spec = FlowSpec(project="pathlynks", flows=flows)
    return approve(spec, by="umesh")


def not_applicable() -> ExpandedSteps:
    return ExpandedSteps(steps=[], rationale="does not apply to this flow")


def make_steps(target: str, value: str | None = None) -> ExpandedSteps:
    return ExpandedSteps(
        steps=[Step(order=1, action=Action.FILL, target=target, value=value)],
        rationale="a real edge case",
    )


def reviewed_store(tmp_path, spec: FlowSpec) -> ProjectStore:
    store = ProjectStore(spec.project, tmp_path)
    store.save_flowspec(spec)
    proposals = propose_cases(spec)
    store.stage_case_proposals(proposals)
    for proposal in proposals:
        store.review_case_proposal(proposal.id, "umesh", approved=True)
    return store


# -- applicable_classes: deterministic, D-004 -------------------------------

def test_login_flow_gets_input_and_auth_classes() -> None:
    classes = applicable_classes(LOGIN_FLOW)
    assert CaseClass.INPUT_EMPTY in classes
    assert CaseClass.AUTH_WRONG_CREDS in classes
    assert CaseClass.HAPPY in classes


def test_no_fill_flow_skips_input_and_auth_classes() -> None:
    classes = applicable_classes(NO_FILL_FLOW)
    assert CaseClass.INPUT_EMPTY not in classes
    assert CaseClass.AUTH_WRONG_CREDS not in classes
    assert CaseClass.HAPPY in classes
    assert CaseClass.DOUBLE_SUBMIT in classes  # universal class, always asked


def test_regression_anchor_is_reachable(tmp_path) -> None:
    """AT-541: REGRESSION_ANCHOR sat in KIND_BY_CLASS but was absent from
    applicable_classes, so the ANCHOR kind could never be generated. Every
    flow is now asked about it, and an accepting model produces an ANCHOR
    case."""
    classes = applicable_classes(LOGIN_FLOW)
    assert CaseClass.REGRESSION_ANCHOR in classes

    non_happy = [c for c in classes if c is not CaseClass.HAPPY]
    responses = [make_steps(f"field for {c.value}") for c in non_happy]
    provider = MockProvider(responses={"agent": responses})
    cases = expand_flow(LOGIN_FLOW, "pathlynks", provider,
                        store=reviewed_store(tmp_path, approved_spec([LOGIN_FLOW])))
    anchors = [c for c in cases if c.kind is CaseKind.ANCHOR]
    assert anchors, "the model accepted the anchor ask but no ANCHOR case was built"
    assert all(c.case_class is CaseClass.REGRESSION_ANCHOR for c in anchors)


def test_a_declined_anchor_produces_no_case(tmp_path) -> None:
    """X4 applies to the anchor like any other class: the model may decline."""
    classes = [c for c in applicable_classes(LOGIN_FLOW) if c is not CaseClass.HAPPY]
    responses = [
        not_applicable() if c is CaseClass.REGRESSION_ANCHOR else make_steps(f"f {c.value}")
        for c in classes
    ]
    provider = MockProvider(responses={"agent": responses})
    cases = expand_flow(LOGIN_FLOW, "pathlynks", provider,
                        store=reviewed_store(tmp_path, approved_spec([LOGIN_FLOW])))
    assert not [c for c in cases if c.kind is CaseKind.ANCHOR]


# -- expand_flow: at least 12 cases for the login flow (goal task's own bar) --

def test_login_flow_produces_at_least_twelve_cases(tmp_path) -> None:
    non_happy = [c for c in applicable_classes(LOGIN_FLOW) if c is not CaseClass.HAPPY]
    responses = [make_steps(f"field for {c.value}") for c in non_happy]
    provider = MockProvider(responses={"agent": responses})

    cases = expand_flow(LOGIN_FLOW, "pathlynks", provider,
                        store=reviewed_store(tmp_path, approved_spec([LOGIN_FLOW])))

    assert len(cases) >= 12
    assert any(c.case_class is CaseClass.HAPPY and c.kind is CaseKind.BEST for c in cases)


def test_happy_case_uses_the_flows_own_steps_verbatim(tmp_path) -> None:
    provider = MockProvider(responses={"agent": [not_applicable()] * 20})
    cases = expand_flow(LOGIN_FLOW, "pathlynks", provider,
                        store=reviewed_store(tmp_path, approved_spec([LOGIN_FLOW])))

    happy = next(c for c in cases if c.case_class is CaseClass.HAPPY)
    assert [s.target for s in happy.steps] == [s.target for s in LOGIN_FLOW.steps]


def test_model_declining_a_class_produces_no_case_for_it(tmp_path) -> None:
    non_happy = applicable_classes(LOGIN_FLOW)[1:]  # skip HAPPY
    responses = [not_applicable() for _ in non_happy]
    provider = MockProvider(responses={"agent": responses})

    cases = expand_flow(LOGIN_FLOW, "pathlynks", provider,
                        store=reviewed_store(tmp_path, approved_spec([LOGIN_FLOW])))

    assert len(cases) == 1  # only HAPPY survives
    assert cases[0].case_class is CaseClass.HAPPY


# -- expand(): requires an approved FlowSpec ----------------------------------

def test_expand_refuses_an_unreviewed_flowspec() -> None:
    spec = FlowSpec(project="pathlynks", flows=[LOGIN_FLOW])  # still DRAFT
    provider = MockProvider(responses={"agent": [not_applicable()] * 20})

    with pytest.raises(FlowSpecNotReviewed):
        expand(spec, provider)


def test_expand_runs_all_flows_once_approved(tmp_path) -> None:
    spec = approved_spec([LOGIN_FLOW, NO_FILL_FLOW])
    login_calls = len(applicable_classes(LOGIN_FLOW)) - 1
    browse_calls = len(applicable_classes(NO_FILL_FLOW)) - 1
    provider = MockProvider(responses={"agent": [not_applicable()] * (login_calls + browse_calls)})

    cases = expand(spec, provider, store=reviewed_store(tmp_path, spec))

    flow_ids = {c.flow_id for c in cases}
    assert flow_ids == {"flow_login", "flow_browse"}


# -- prompt is a file, per T-070's own contract's I5-equivalent --------------

def test_prompt_is_read_from_a_file() -> None:
    from autotester.core.paths import RepoDocs
    from autotester.stages.expand import build_expand_prompt

    prompt = build_expand_prompt(LOGIN_FLOW, CaseClass.INPUT_EMPTY, RepoDocs())
    assert "input_empty" in prompt
    assert "{{CASE_CLASS}}" not in prompt
    assert "Login" in prompt


@pytest.mark.parametrize("approved_count", [2, 0])
def test_five_nonhappy_proposals_prune_before_spend(tmp_path, approved_count) -> None:
    spec = approved_spec([LOGIN_FLOW])
    store = ProjectStore(spec.project, tmp_path)
    store.save_flowspec(spec)
    proposals = propose_cases(spec)
    happy = next(p for p in proposals if p.case_class is CaseClass.HAPPY)
    nonhappy = [p for p in proposals if p.case_class is not CaseClass.HAPPY][:5]
    store.stage_case_proposals([happy, *nonhappy])
    store.review_case_proposal(happy.id, "tester", True)
    for index, proposal in enumerate(nonhappy):
        store.review_case_proposal(proposal.id, "tester", index < approved_count)
    provider = MockProvider(responses={"agent": [make_steps("edge") for _ in range(5)]})
    cases = expand(spec, provider, store=store)
    assert len(provider.prompts) == approved_count
    assert len(cases) == approved_count + 1
    assert cases[0].steps == LOGIN_FLOW.steps
    assert all("steps" not in p.model_dump() for p in store.list_case_proposals())


def test_no_recorded_approval_or_missing_happy_spends_nothing(tmp_path) -> None:
    spec = approved_spec([LOGIN_FLOW])
    store = ProjectStore(spec.project, tmp_path)
    store.save_flowspec(spec)
    proposals = propose_cases(spec)
    store.stage_case_proposals(proposals)
    provider = MockProvider(responses={"agent": [make_steps("edge")] * 20})
    with pytest.raises(ValueError, match="HAPPY"):
        expand(spec, provider, store=store)
    for proposal in proposals:
        if proposal.case_class is not CaseClass.HAPPY:
            store.review_case_proposal(proposal.id, "tester", True)
    with pytest.raises(ValueError, match="HAPPY"):
        expand(spec, provider, store=store)
    assert provider.prompts == []
    assert store.list_cases() == []


def test_all_flows_preflight_before_any_prompt_and_happy_prune_invalidates(tmp_path) -> None:
    spec = approved_spec([LOGIN_FLOW, NO_FILL_FLOW])
    store = reviewed_store(tmp_path, spec)
    happy = next(p for p in store.list_case_proposals()
                 if p.flow_id == NO_FILL_FLOW.id and p.case_class is CaseClass.HAPPY)
    assert store.review_case_proposal(happy.id, "tester", False).status == "proposed"
    provider = MockProvider(responses={"agent": [make_steps("edge")] * 30})
    with pytest.raises(ValueError, match="HAPPY"):
        expand(spec, provider, store=store)
    assert provider.prompts == []


def test_forged_or_stale_proposal_input_cannot_reach_provider(tmp_path) -> None:
    spec = approved_spec([LOGIN_FLOW])
    store = reviewed_store(tmp_path, spec)
    provider = MockProvider(responses={"agent": [make_steps("edge")] * 20})
    forged = propose_cases(spec)[0].reviewed("invented caller", True)
    with pytest.raises(ValueError, match="staging"):
        store.stage_case_proposals([forged])
    with pytest.raises(ValueError, match="saved human"):
        expand(spec, provider)
    changed = spec.model_copy(update={"version": spec.version + 1})
    with pytest.raises(ValueError, match="exact current"):
        expand(changed, provider, store=store)
    store.save_flowspec(changed)
    with pytest.raises(ValueError, match="HAPPY"):
        expand(changed, provider, store=store)
    with pytest.raises(ValueError, match="absent or stale"):
        expand(changed, provider, store=store, proposal_ids=[forged.id])
    assert provider.prompts == []
