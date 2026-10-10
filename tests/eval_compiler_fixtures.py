"""Builders for the T-166 tests (qa/contracts/eval-compiler.md). Offline only:
a small persona + approved FlowSpec, a scenario list, and a MockProvider whose
every taxonomy answer is "not applicable" (so only deterministic cases remain)."""

from __future__ import annotations

from autotester.providers.mock import MockProvider
from autotester.schema.case import ExpandedSteps
from autotester.schema.enums import Action
from autotester.schema.flowspec import ExpectedState, Flow, FlowSpec, Screen, Step
from autotester.schema.portal_persona import (
    FlowRunRef,
    PersonaScreen,
    PersonaTransition,
    PortalPersona,
    TaughtFlow,
)
from autotester.schema.scenario import Branch, ScenarioSpec
from autotester.stages.expand import applicable_classes
from autotester.stages.review import approve

SLUG = "demo"

LOGIN = Flow(
    id="flow_login", name="Login", entry_screen="scr_signin", exit_screen="scr_home",
    steps=[
        Step(order=1, action=Action.NAVIGATE, target="https://demo.test/signin",
             screen_id="scr_signin"),
        Step(order=2, action=Action.FILL, target="email field", value="a@b.test",
             screen_id="scr_signin"),
        Step(order=3, action=Action.FILL, target="password field", value="pw",
             screen_id="scr_signin"),
        Step(order=4, action=Action.CLICK, target="Login button", screen_id="scr_signin",
             expected=ExpectedState(network=["POST /api/login"])),
    ],
)
BROWSE = Flow(
    id="flow_browse", name="Browse", entry_screen="scr_home",
    steps=[Step(order=1, action=Action.NAVIGATE, target="https://demo.test/home",
                screen_id="scr_home"),
           Step(order=2, action=Action.CLICK, target="First item", screen_id="scr_home")],
)
ORPHAN = Flow(  # entry screen the persona has never seen: no graph edge can resolve
    id="flow_orphan", name="Orphan", entry_screen="scr_unknown",
    steps=[Step(order=1, action=Action.CLICK, target="Ghost", screen_id="scr_unknown")],
)


def spec(*flows: Flow) -> FlowSpec:
    screens = [Screen(id="scr_signin", name="Sign in"), Screen(id="scr_home", name="Home")]
    return approve(FlowSpec(project=SLUG, screens=screens, flows=list(flows)), by="umesh")


def persona(*flows: Flow) -> PortalPersona:
    """Screens + a learned transition + one TaughtFlow per flow whose entry the persona knows."""
    return PortalPersona(
        project=SLUG,
        screens=[PersonaScreen(id="scr_signin", name="Sign in",
                               controls=["email field", "Login button"]),
                 PersonaScreen(id="scr_home", name="Home", controls=["First item"])],
        transitions=[PersonaTransition(from_screen="Sign in", to_screen="Home",
                                       control="Login button")],
        taught_flows=[TaughtFlow(id=f.id, name=f.name, entry_screen=f.entry_screen,
                                 run_ref=FlowRunRef(project=SLUG, flow_id=f.id,
                                                    entry_screen=f.entry_screen))
                      for f in flows],
    )


def provider(*flows: Flow) -> MockProvider:
    """Declines every taxonomy class for every flow: the deterministic cases are what is left."""
    declined = ExpandedSteps(steps=[], rationale="not applicable")
    queue = [declined for f in flows for c in applicable_classes(f)[1:]]
    return MockProvider(responses={"agent": queue})


def branch(bid: str, label: str, values: dict[str, str] | None = None,
           expect: list[str] | None = None) -> Branch:
    return Branch(id=bid, label=label, values=values or {}, expect_text=expect or [])


def scenarios() -> list[ScenarioSpec]:
    """3 scenarios, each with a yes and a no branch (EC5). Exactly one branch,
    `s_browse/no`, names a step target the flow does not have, so it cannot compile."""
    return [
        ScenarioSpec(id="s_valid", flow_id="flow_login", name="valid user", branches=[
            branch("yes", "valid credentials", expect=["Welcome"]),
            branch("no", "wrong password", {"password field": "bad"}, ["Invalid"])]),
        ScenarioSpec(id="s_new", flow_id="flow_login", name="new user", branches=[
            branch("yes", "new email", {"email field": "new@b.test"}, ["Verify"]),
            branch("no", "taken email", {"email field": "old@b.test"}, ["Taken"])]),
        ScenarioSpec(id="s_browse", flow_id="flow_browse", name="browse", branches=[
            branch("yes", "open item", expect=["Item"]),
            branch("no", "missing item", {"ghost field": "x"})]),
    ]
