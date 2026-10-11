"""AT-890 (D-084): the case-expansion prompt is masked before it reaches a provider.

`build_expand_prompt` renders every step's target and typed value from SOURCE material (a
video, a crawl). That text goes to an external model, so the project's own redaction and the
PII mask both stand between it and `provider.act` -- and the model is spied on, because the
claim is about what the provider RECEIVES, not about what a helper returns.
"""

from __future__ import annotations

import base64

import pytest

from autotester.core.paths import RepoDocs
from autotester.providers.mock import MockProvider
from autotester.schema.case import ExpandedSteps
from autotester.schema.enums import Action, CaseClass
from autotester.schema.flowspec import ExpectedState, Flow, FlowSpec, Step
from autotester.schema.project import Project, SecretRef
from autotester.stages.expand import build_expand_prompt, expand, expand_flow, propose_cases
from autotester.stages.review import approve
from autotester.store.project_store import ProjectStore

SECRET = "Hunter2-Zebra-4411"
UNDECLARED = "Other-Projects-Key-9082"
EMAIL = "ada.lovelace@example.org"
PHONE = "+91 98765 43210"


def flow_with(*, name: str = "Sign in", target: str = "email field", value: str | None = None,
              **extra) -> Flow:
    return Flow(id="flow_x", name=name, entry_screen="scr", steps=[
        Step(order=1, action=Action.NAVIGATE, target="https://app.test/signin"),
        Step(order=2, action=Action.FILL, target=target, value=value, **extra),
        Step(order=3, action=Action.CLICK, target="Continue"),
    ])


def make_store(tmp_path, flow: Flow) -> ProjectStore:
    store = ProjectStore("demo", tmp_path)
    store.save_project(Project(
        slug="demo", name="Demo", base_url="https://app.test", allowed_domains=["app.test"],
        secrets=[SecretRef(key="ST_PASS", domains=["app.test"])]))
    (tmp_path / ".env").write_text(f"ST_PASS={SECRET}\nOTHER_KEY={UNDECLARED}\n", encoding="utf-8")
    spec = approve(FlowSpec(project="demo", flows=[flow]), by="umesh")
    store.save_flowspec(spec)
    rows = propose_cases(spec)
    store.stage_case_proposals(rows)
    for row in rows:
        store.review_case_proposal(row.id, "umesh", approved=True)
    return store


def sent_to_provider(tmp_path, flow: Flow, *, whole_spec: bool = False) -> list[str]:
    store = make_store(tmp_path, flow)
    provider = MockProvider(responses={"agent": [ExpandedSteps(steps=[], rationale="n/a")] * 30})
    if whole_spec:
        expand(store.load_flowspec(), provider, store=store)
    else:
        expand_flow(flow, "demo", provider, store=store)
    assert provider.prompts, "the provider was never called, so nothing was proven"
    return [prompt for _, prompt in provider.prompts]


MUST_NOT_REACH = [
    pytest.param(dict(value=SECRET), SECRET, "[REDACTED]", id="declared-in-value"),
    pytest.param(dict(target=f"field {SECRET}"), SECRET, "[REDACTED]", id="declared-in-target"),
    pytest.param(dict(name=f"Sign in {SECRET}"), SECRET, "[REDACTED]", id="declared-in-name"),
    pytest.param(dict(value=UNDECLARED), UNDECLARED, "[REDACTED]", id="undeclared-env-value"),
    pytest.param(dict(value=EMAIL), EMAIL, "<email>", id="email-in-value"),
    pytest.param(dict(target=f"link {EMAIL}"), EMAIL, "<email>", id="email-in-target"),
    pytest.param(dict(name=f"Sign in as {EMAIL}"), EMAIL, "<email>", id="email-in-flow-name"),
    pytest.param(dict(value=PHONE), PHONE, "<phone>", id="phone-in-value"),
    pytest.param(dict(value="9876543210"), "9876543210", "<phone>", id="bare-ten-digit-phone"),
    pytest.param(dict(value=f"{EMAIL} {PHONE} {SECRET}"), SECRET, "[REDACTED]", id="all-in-one"),
]


@pytest.mark.parametrize(("fields", "raw", "mask"), MUST_NOT_REACH)
def test_the_provider_never_receives_the_raw_value(tmp_path, fields, raw, mask) -> None:
    prompts = sent_to_provider(tmp_path, flow_with(**fields))
    assert all(raw not in p for p in prompts)
    assert any(mask in p for p in prompts)


@pytest.mark.parametrize("whole_spec", [False, True], ids=["expand_flow", "expand"])
def test_both_entry_points_guard_the_prompt(tmp_path, whole_spec) -> None:
    prompts = sent_to_provider(tmp_path, flow_with(value=SECRET), whole_spec=whole_spec)
    assert all(SECRET not in p for p in prompts)


def test_a_secret_placeholder_survives_untouched(tmp_path) -> None:
    prompts = sent_to_provider(tmp_path, flow_with(value="{{SECRET:ST_PASS}}"))
    assert all("{{SECRET:ST_PASS}}" in p for p in prompts)
    assert all("[REDACTED]" not in p for p in prompts)


@pytest.mark.parametrize("field", [
    dict(note=SECRET), dict(narration=EMAIL), dict(on_screen_text=PHONE),
    dict(expected=ExpectedState(visible_text=[SECRET, EMAIL, PHONE])),
], ids=["note", "narration", "on_screen_text", "expected"])
def test_nested_step_fields_are_not_in_the_prompt_at_all(tmp_path, field) -> None:
    prompts = sent_to_provider(tmp_path, flow_with(value="x", **field))
    assert all(raw not in p for p in prompts for raw in (SECRET, EMAIL, PHONE))


def test_an_encoded_secret_is_refused_before_any_model_call(tmp_path) -> None:
    """Masking catches the exact value; the guard catches a spelling of it the mask misses."""
    encoded = base64.b64encode(SECRET.encode()).decode()
    flow = flow_with(value=encoded)
    store = make_store(tmp_path, flow)
    provider = MockProvider(responses={"agent": [ExpandedSteps(steps=[], rationale="n/a")] * 30})
    with pytest.raises(ValueError, match="raw secret"):
        expand_flow(flow, "demo", provider, store=store)
    assert provider.prompts == []


def test_without_a_saved_project_the_pii_mask_still_applies(tmp_path) -> None:
    flow = flow_with(value=EMAIL)
    spec = approve(FlowSpec(project="demo", flows=[flow]), by="umesh")
    store = ProjectStore("demo", tmp_path)
    store.save_flowspec(spec)
    rows = propose_cases(spec)
    store.stage_case_proposals(rows)
    for row in rows:
        store.review_case_proposal(row.id, "umesh", approved=True)
    provider = MockProvider(responses={"agent": [ExpandedSteps(steps=[], rationale="n/a")] * 30})
    expand_flow(flow, "demo", provider, store=store)
    assert all(EMAIL not in p and "<email>" in p for _, p in provider.prompts)


def test_build_expand_prompt_masks_pii_on_its_own() -> None:
    prompt = build_expand_prompt(flow_with(value=f"{EMAIL} {PHONE}"), CaseClass.INPUT_EMPTY,
                                 RepoDocs())
    assert EMAIL not in prompt and PHONE not in prompt
    assert "<email>" in prompt and "<phone>" in prompt


def test_the_happy_case_keeps_the_real_steps_only_the_prompt_is_masked(tmp_path) -> None:
    """The model sees masked text; the persisted HAPPY case is the flow's own steps."""
    flow = flow_with(value=EMAIL)
    store = make_store(tmp_path, flow)
    provider = MockProvider(responses={"agent": [ExpandedSteps(steps=[], rationale="n/a")] * 30})
    cases = expand_flow(flow, "demo", provider, store=store)
    assert cases[0].steps == flow.steps
