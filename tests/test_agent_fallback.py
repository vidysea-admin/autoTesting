"""Agent fallback actuator. Contract: qa/contracts/agent-fallback.md AF1-AF6."""

from __future__ import annotations

import asyncio
import re
import tomllib
from pathlib import Path

import pytest
from agent_fallback_fake import DEMO, demo_case, demo_env, fix_agent, judge
from test_agent_loop import LOGIN, make_case, session_with

from autotester.providers.mock import MockProvider
from autotester.schema.agent_fallback import (
    ActuatorResult,
    FallbackAction,
    FallbackActionKind,
    FallbackOutcome,
    FallbackStatus,
)
from autotester.schema.approval import RunApproval
from autotester.schema.case import AgentFix
from autotester.schema.enums import (
    Action,
    ApprovalKind,
    Outcome,
    Result,
    WritePolicy,
)
from autotester.stages.agent_actuator import (
    FallbackActuator,
    MalformedActuatorResult,
    outcome_evidence,
    parse_result,
)
from autotester.stages.agent_loop import MAX_ITERATIONS, run_with_fallback
from autotester.stages.browser_use_backend import ProviderChatModel
from autotester.stages.run_budget import RunBudget
from autotester.stages.run_case_pipeline import fallback_executor, run_and_grade_case

SRC = Path(__file__).resolve().parents[1] / "src" / "autotester"
NEXT = FallbackAction(kind=FallbackActionKind.CLICK, target="Next", url=LOGIN)


def click(name: str, **kw) -> FallbackAction:
    return FallbackAction(kind=FallbackActionKind.CLICK, target=name, **kw)


def result_for(actions: list[FallbackAction], resolved: bool = True) -> ActuatorResult:
    return ActuatorResult(actions=actions, observed="the page shows a plan picker",
                          evidence_ref="evidence/step01.png", resolved=resolved)


class Backend:
    """Counting stub: proposes `actions` through `vet`, then returns `raw`."""

    def __init__(self, actions: list[FallbackAction] | None = None, raw: object = "default",
                 forever: bool = False) -> None:
        self.calls, self.actions, self.forever = 0, actions or [NEXT], forever
        self.raw = result_for(self.actions) if isinstance(raw, str) and raw == "default" else raw

    def run(self, task, vet, *, max_steps, timeout_s):
        self.calls += 1
        for action in self.actions:
            vet(action)
        while self.forever:
            vet(NEXT)
        return self.raw


def broken_session(tmp_path: Path):
    return session_with(tmp_path, {"button.old", "button.still"})


def stuck_agent() -> MockProvider:
    fix = AgentFix(action=Action.CLICK, target="button.still", reasoning="try another")
    return MockProvider(responses={"agent": [fix] * MAX_ITERATIONS})


def approval(max_actions: int = 10) -> RunApproval:
    return RunApproval(project="pathlynks", run_kind=ApprovalKind.LIVE_CASE, target=LOGIN,
                       scope="t", max_actions=max_actions, max_probes=10, wall_clock_s=600,
                       granted_by="t", granted_at="2026-10-07", expires_at="2026-12-31")


def with_policy(session, policy: WritePolicy):
    session.project = session.project.model_copy(update={"write_policy": policy})
    return session


# -- AF1 only when the deterministic path has no answer ---------------------------------

def test_af1_known_screen_never_engages_the_actuator(tmp_path: Path) -> None:
    backend = Backend()
    loop = run_with_fallback(make_case(), session_with(tmp_path, set()), MockProvider(),
                             actuator=FallbackActuator(backend))
    assert loop.result.outcome is Outcome.COMPLETED and backend.calls == 0
    assert loop.fallback is None


def test_af1_unknown_screen_engages_it_exactly_once_after_the_fix_loop(tmp_path: Path) -> None:
    backend = Backend()
    loop = run_with_fallback(make_case(), broken_session(tmp_path), stuck_agent(),
                             actuator=FallbackActuator(backend))
    assert backend.calls == 1 and loop.iterations == MAX_ITERATIONS
    assert loop.fallback is not None and loop.fallback.status is FallbackStatus.RESOLVED
    assert loop.result.outcome is Outcome.ERRORED  # an agent's free run is evidence, not a pass
    assert any("agent fallback" in e.path for e in loop.result.evidence)


# -- AF2 typed output, malformed refused -------------------------------------------------

@pytest.mark.parametrize("raw", [
    "I clicked the button and it worked", None, 42, {},
    {"actions": [], "observed": "x", "evidence_ref": "e", "resolved": True},
    {"actions": [NEXT.model_dump()], "observed": "", "evidence_ref": "e", "resolved": True},
    {"actions": [NEXT.model_dump()], "observed": "x", "resolved": True},
    {"actions": [NEXT.model_dump()], "observed": "x", "evidence_ref": "e", "resolved": True,
     "verdict": "pass"},
])
def test_af2_a_malformed_result_raises_typed_and_is_never_a_pass(tmp_path, raw) -> None:
    with pytest.raises(MalformedActuatorResult):
        parse_result(raw)
    loop = run_with_fallback(make_case(), broken_session(tmp_path), stuck_agent(),
                             actuator=FallbackActuator(Backend(raw=raw)))
    assert loop.fallback.status is FallbackStatus.MALFORMED
    assert loop.result.outcome is not Outcome.COMPLETED


def test_af2_a_well_formed_result_round_trips() -> None:
    made = result_for([NEXT, click("Save")])
    again = parse_result(made.model_dump(mode="json"))
    assert again == made and parse_result(made) == made


# -- AF3 same guards as every other actuation, and never grades ---------------------------

def run_one(tmp_path: Path, actions, policy=WritePolicy.READ_ONLY, budget=None) -> FallbackOutcome:
    session = with_policy(session_with(tmp_path, set()), policy)
    session.budget = budget
    return FallbackActuator(Backend(actions)).invoke(session, "explore")


@pytest.mark.parametrize("action, needle", [
    (FallbackAction(kind=FallbackActionKind.FILL, target="Email", value="a@b.co"), "read_only"),
    (FallbackAction(kind=FallbackActionKind.PRESS_KEY, value="Enter"), "read_only"),
    (click("Delete account"), "deny-list"),
    (click("Log out"), "never-click"),
    (FallbackAction(kind=FallbackActionKind.NAVIGATE, url="https://evil.example/x"),
     "allowed domains"),
    (click("Next", url="https://evil.example/landed"), "allowed domains"),
    (FallbackAction(kind=FallbackActionKind.NAVIGATE), "destination"),
])
def test_af3_refused_actions_are_recorded_and_never_run(tmp_path, action, needle) -> None:
    outcome = run_one(tmp_path, [action])
    assert outcome.status is FallbackStatus.REFUSED and outcome.vetted == []
    assert needle in " ".join(outcome.refusals) and outcome.reason


def test_af3_the_same_write_is_allowed_when_the_policy_allows_it(tmp_path: Path) -> None:
    fill = FallbackAction(kind=FallbackActionKind.FILL, target="Email", value="a@b.co")
    outcome = run_one(tmp_path, [fill], policy=WritePolicy.TEST_ACCOUNT)
    assert outcome.status is FallbackStatus.RESOLVED and outcome.vetted == [fill]


def test_af3_agent_actions_spend_the_run_budget(tmp_path: Path) -> None:
    budget = RunBudget(approval())
    outcome = run_one(tmp_path, [NEXT, click("Save")], budget=budget)
    assert outcome.status is FallbackStatus.RESOLVED and budget.actions_used == 2
    tight = RunBudget(approval(max_actions=1))
    spent = run_one(tmp_path, [NEXT, click("Save")], budget=tight)
    assert spent.status is FallbackStatus.REFUSED and "budget" in spent.reason


def test_af3_an_action_reported_but_never_vetted_is_refused(tmp_path: Path) -> None:
    sneaky = Backend([NEXT], raw=result_for([NEXT, click("Delete everything")]))
    outcome = FallbackActuator(sneaky).invoke(session_with(tmp_path, set()), "explore")
    assert outcome.status is FallbackStatus.REFUSED and "never vetted" in outcome.reason


def test_af3_the_actuator_never_writes_a_verdict() -> None:
    assert "pass" not in {s.value for s in FallbackStatus}
    assert "verdict" not in FallbackOutcome.model_fields
    assert Result.PASS.value not in {s.value for s in FallbackStatus}


# -- AF4 bounded; exhaustion is never a pass ----------------------------------------------

def test_af4_step_bound_stops_a_backend_that_never_resolves(tmp_path: Path) -> None:
    outcome = FallbackActuator(Backend(forever=True), max_steps=3).invoke(
        session_with(tmp_path, set()), "explore")
    assert outcome.status is FallbackStatus.BOUND_EXHAUSTED
    assert "max_steps=3" in outcome.reason and outcome.steps_used == 3


def test_af4_wall_clock_bound_names_itself(tmp_path: Path) -> None:
    ticks = iter(range(0, 10_000, 10))
    outcome = FallbackActuator(Backend(forever=True), max_steps=99, wall_clock_s=25,
                               clock=lambda: float(next(ticks))).invoke(
        session_with(tmp_path, set()), "explore")
    assert outcome.status is FallbackStatus.BOUND_EXHAUSTED
    assert "wall_clock_s=25" in outcome.reason


def test_af4_an_unresolved_result_is_not_a_pass(tmp_path: Path) -> None:
    backend = Backend(raw=result_for([NEXT], resolved=False))
    loop = run_with_fallback(make_case(), broken_session(tmp_path), stuck_agent(),
                             actuator=FallbackActuator(backend))
    assert loop.fallback.status is FallbackStatus.UNRESOLVED
    assert loop.result.outcome is Outcome.ERRORED and loop.iterations == MAX_ITERATIONS
    assert "unresolved" in outcome_evidence(loop.fallback, scrub=str).path


# -- AF5 a production call site, driven end to end ----------------------------------------

def test_af5_pipeline_repairs_through_the_call_site_and_persists_once(tmp_path: Path) -> None:
    store, session = demo_env(tmp_path)
    agent = fix_agent()
    result, _ = run_and_grade_case(demo_case(), session, judge(), "run_1", store, agent=agent)
    assert result.outcome is Outcome.COMPLETED and len(agent.prompts) == 1
    assert any(e.path.startswith("agent repair") for e in result.evidence)
    assert len(store.list_cases()) == 1
    repaired = store.list_cases()[0]
    assert repaired.id != demo_case().id and repaired.steps[0].target == DEMO + "home"
    again, _ = run_and_grade_case(demo_case(), session, judge(), "run_2", store,
                                  agent=fix_agent())
    assert again.outcome is Outcome.COMPLETED and len(store.list_cases()) == 1  # AL3 idempotent


def test_af5_without_an_agent_the_pipeline_is_unchanged(tmp_path: Path) -> None:
    store, session = demo_env(tmp_path)
    result, _ = run_and_grade_case(demo_case(), session, judge(), "run_1", store)
    assert result.outcome is Outcome.ERRORED and store.list_cases() == []


def test_af5_a_replay_is_never_repaired_by_running_it(tmp_path: Path) -> None:
    store, session = demo_env(tmp_path)
    agent, session.replaying = fix_agent(), True
    result = fallback_executor(agent, None, store)(demo_case(), session)
    assert result.outcome is Outcome.ERRORED and agent.prompts == [] and not store.list_cases()


def test_af5_a_production_call_site_exists_outside_the_definition() -> None:
    callers = [p.relative_to(SRC).as_posix() for p in SRC.rglob("*.py")
               if "run_with_fallback(" in p.read_text(encoding="utf-8")
               and p.name != "agent_loop.py"]
    assert "stages/run_case_pipeline.py" in callers


# -- AF6 the Provider seam, and the one dependency ----------------------------------------

def test_af6_browser_use_is_declared_and_no_vendor_client_sits_outside_providers() -> None:
    deps = tomllib.loads((SRC.parents[1] / "pyproject.toml").read_text("utf-8"))
    assert any(d.startswith("browser-use") for d in deps["project"]["dependencies"])
    vendor = re.compile(r"^\s*(?:import|from)\s+(?:anthropic|openai|google\.genai|"
                        r"google\.generativeai|langchain_anthropic|langchain_openai|"
                        r"langchain_google_genai)\b", re.M)
    stray = [p.relative_to(SRC).as_posix() for p in SRC.rglob("*.py")
             if "providers" not in p.relative_to(SRC).parts
             and vendor.search(p.read_text(encoding="utf-8"))]
    assert stray == []


def test_af6_the_backend_reaches_its_model_only_through_a_provider() -> None:
    from browser_use.llm.messages import UserMessage

    fix = AgentFix(action=Action.CLICK, target="Next", reasoning="why")
    provider = MockProvider(responses={"agent": [fix]})
    model = ProviderChatModel(provider, guard=lambda text: text.replace("tok123", "[MASKED]"))
    done = asyncio.run(model.ainvoke([UserMessage(content="click tok123")], AgentFix))
    assert done.completion == fix and provider.usage[0].calls == 1
    assert "tok123" not in provider.prompts[0][1] and "[MASKED]" in provider.prompts[0][1]
