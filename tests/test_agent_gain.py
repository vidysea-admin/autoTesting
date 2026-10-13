"""T-181: agent guardrails (AL11) and the measured gain vs the pipeline (AL12/AL13), offline.

Fakes only: a scripted chat model stands in for the LLM, runners stand in for the live pipeline
and agent, and no browser opens. The budget number and the win rule are Umesh's to set; the
defaults tested here are the configurable placeholders."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import AIMessage
from test_agent_comparison import MAP, _corpus, _fail
from test_agent_layer import Scripted, call, ctx, run  # noqa: F401  (ctx: the fixture)
from test_agent_tools import (
    BASE,
    Spies,
    _case,
    _ctx,
    _grant,
    _nav,
    spies,  # noqa: F401  (the fixture)
)

from autotester.agents import comparison, gain, lead_agent
from autotester.schema.agent_comparison import Comparison
from autotester.schema.agent_guardrails import AgentGuardrails, WinRule
from autotester.schema.enums import Action, ApprovalKind, WritePolicy
from autotester.schema.flowspec import Step
from autotester.schema.lead_loop import AgentRun, TokenBudget
from autotester.schema.verdict import Verdict

JOB = lambda: [call("get_catalog"), call("get_persona"), call("get_catalog")]  # noqa: E731


def _rails(**kw: Any) -> AgentGuardrails:
    return AgentGuardrails(**kw)


def _ran(stopped: str = "finished", tokens: int = 500) -> AgentRun:
    return AgentRun(run_id="r", stopped=stopped, tokens_used=tokens)  # type: ignore[arg-type]


def _measure(pipeline: list[str], agent: list[str], rule: WinRule | None,
             stopped: str = "finished") -> Comparison:
    return comparison.compare(_corpus(), MAP, [_fail(c) for c in pipeline],
                              [_fail(c) for c in agent], _ran(stopped), rule=rule)


# -- the configured defaults: fields, not magic numbers ---------------------------------------
def test_defaults_live_in_a_schema_and_are_overridable() -> None:
    d = AgentGuardrails()
    assert d.budget.max_tokens and d.budget.max_cost_usd and d.max_steps >= 1
    assert (d.win_rule.min_bugs_delta, d.win_rule.max_fp_rate_delta,
            d.win_rule.require_strict_gain) == (0, 0.0, False)
    custom = AgentGuardrails(budget=TokenBudget(max_tokens=7), max_steps=3,
                             win_rule=WinRule(min_bugs_delta=1, require_strict_gain=True))
    assert (custom.budget.max_tokens, custom.max_steps, custom.win_rule.min_bugs_delta) == (7, 3, 1)


# -- AL11: budget and step cap halt with a named reason ---------------------------------------
def test_budget_halt_is_named_and_comes_from_the_guardrails(ctx: Any) -> None:  # noqa: F811
    out, _ = run(ctx, *JOB(), guardrails=_rails(budget=TokenBudget(max_tokens=25)))
    assert out.stopped == "budget_exceeded" and "token budget exceeded" in out.reason


def test_default_budget_lets_a_small_job_finish(ctx: Any) -> None:  # noqa: F811
    out, _ = run(ctx, *JOB(), guardrails=_rails())
    assert out.stopped == "finished" and out.tokens_used > 0


def test_step_cap_halts_with_its_own_reason(ctx: Any) -> None:  # noqa: F811
    out, _ = run(ctx, *JOB(), guardrails=_rails(max_steps=2))
    assert out.stopped == "step_cap" and out.reason == "graph step cap reached"


# -- allowed domains and write policy bind the agent's actions --------------------------------
@pytest.mark.parametrize("policy", [WritePolicy.READ_ONLY, WritePolicy.ALLOW_WRITES])
def test_an_off_domain_action_is_refused_at_every_policy(tmp_path: Path, spies: Spies,  # noqa: F811
                                                         policy: WritePolicy) -> None:
    c = _ctx(tmp_path, spies, policy)
    _grant(c.store, ApprovalKind.LIVE_CASE)
    case = c.store.add_case(_case([_nav(), Step(order=2, action=Action.NAVIGATE,
                                                target="https://evil.test/x")]))
    out, _ = run(c, call("run_case", case_id=case.id), guardrails=_rails())
    assert out.refusals == 1 and spies.sessions == 0 and spies.count("run_case") == 0


def test_a_write_under_read_only_is_refused_and_an_in_domain_read_runs(
        tmp_path: Path, spies: Spies) -> None:  # noqa: F811
    c = _ctx(tmp_path, spies, WritePolicy.READ_ONLY)
    _grant(c.store, ApprovalKind.LIVE_CASE)
    bad = c.store.add_case(_case([_nav(), Step(order=2, action=Action.CLICK, target="Save")]))
    good = c.store.add_case(_case([Step(order=1, action=Action.NAVIGATE, target=f"{BASE}/home")]))
    out, _ = run(c, call("run_case", case_id=bad.id), call("run_case", case_id=good.id),
                 guardrails=_rails())
    assert out.refusals == 1 and spies.count("run_case") == 1


# -- AL12/AL13: the win rule, explicit and configurable ---------------------------------------
def test_default_rule_a_tie_at_equal_fp_rate_is_a_gain() -> None:
    cmp = _measure(["c1"], ["c1"], WinRule())
    assert cmp.verdict == "gain" and cmp.verdict_line.startswith("GAIN")


def test_default_rule_fewer_bugs_or_a_higher_fp_rate_is_no_gain() -> None:
    assert _measure(["c1", "c2"], ["c1"], WinRule()).verdict == "no_gain"
    assert _measure(["c1"], ["c1", "cX"], WinRule()).verdict == "no_gain"  # FP rate 0 -> 0.5
    assert _measure(["c1", "cX"], ["c1", "c2"], WinRule()).verdict == "gain"


def test_the_rule_is_configurable() -> None:
    assert _measure(["c1"], ["c1"], WinRule(require_strict_gain=True)).verdict == "no_gain"
    assert _measure(["c1"], ["c1"], WinRule(min_bugs_delta=1)).verdict == "no_gain"
    assert _measure(["c1"], ["c1", "c2"], WinRule(min_bugs_delta=1)).verdict == "gain"
    lenient = WinRule(max_fp_rate_delta=0.6)
    assert _measure(["c1"], ["c1", "cX"], lenient).verdict == "gain"


def test_a_budget_halt_is_no_gain_whatever_the_rule() -> None:
    cmp = _measure(["c1"], ["c1", "c2"], WinRule(), stopped="budget_exceeded")
    assert cmp.verdict == "no_gain" and "breached its budget" in cmp.verdict_line


# -- the harness: both paths, four numbers each, a verdict line always ------------------------
def _harness(ctx_: Any, tmp_path: Path, agent_found: list[str], budget: int,
             **kw: Any) -> Comparison:
    def agent(rails: AgentGuardrails) -> tuple[AgentRun, list[Verdict]]:
        model = Scripted(script=[*JOB(), AIMessage("fin")], tokens=10)
        done = lead_agent.run_lead_agent(ctx_, model, "test", guardrails=rails)
        return done, [_fail(c) for c in agent_found]
    return gain.measure_gain(
        _corpus(), MAP, lambda: [_fail("c1"), _fail("cX")], agent,
        _rails(budget=TokenBudget(max_tokens=budget), **kw), pipeline_tokens=0,
        out=tmp_path / "gain.json")


def test_harness_reports_both_paths_and_a_gain(ctx: Any, tmp_path: Path) -> None:  # noqa: F811
    cmp = _harness(ctx, tmp_path, ["c1", "c2"], 10_000)
    assert cmp.verdict == "gain" and cmp.agent_stopped == "finished"
    for path in (cmp.pipeline, cmp.agent):
        assert path.wall_s is not None and path.tokens is not None
    assert (cmp.pipeline.bugs_found, cmp.pipeline.false_positives) == (1, 1)
    assert (cmp.agent.bugs_found, cmp.agent.false_positives) == (2, 0) and cmp.agent.tokens > 0
    saved = Comparison.model_validate_json((tmp_path / "gain.json").read_text(encoding="utf-8"))
    assert saved == cmp


def test_harness_states_no_gain_when_the_agent_breaches_its_budget(
        ctx: Any, tmp_path: Path) -> None:  # noqa: F811
    cmp = _harness(ctx, tmp_path, ["c1", "c2"], 25)
    assert cmp.verdict == "no_gain" and cmp.agent_stopped == "budget_exceeded"
    assert cmp.verdict_line.startswith("NO GAIN") and "tokens" in cmp.verdict_line


# -- T-181 r2: step-cap is no gain; a 0-vs-0 tie is "no evidence", never GAIN ------------------
def test_a_step_cap_halt_is_no_gain_whatever_the_rule() -> None:
    cmp = _measure(["c1"], ["c1", "c2"], WinRule(), stopped="step_cap")
    assert cmp.verdict == "no_gain" and cmp.agent_stopped == "step_cap"
    assert cmp.verdict_line.startswith("NO GAIN") and "step cap" in cmp.verdict_line


def test_a_zero_vs_zero_tie_reports_no_evidence_not_gain() -> None:
    for rule in (WinRule(), None, WinRule(require_strict_gain=True)):
        cmp = _measure([], [], rule)
        assert cmp.verdict == "no_evidence" and cmp.verdict_line.startswith("NO EVIDENCE")
        assert "GAIN" not in cmp.verdict_line.split("|")[0].replace("NO EVIDENCE", "")


def test_a_zero_tie_that_also_step_capped_still_reads_no_evidence_and_names_the_halt() -> None:
    cmp = _measure([], [], WinRule(), stopped="step_cap")
    assert cmp.verdict == "no_evidence" and "step_cap" in cmp.verdict_line


def test_a_nonzero_tie_keeps_the_win_rule_and_states_it_is_a_tie() -> None:
    cmp = _measure(["c1"], ["c1"], WinRule())
    assert cmp.verdict == "gain" and "tie" in cmp.verdict_line


# -- AL13 (D-095): the agent layer is OFF by default; the plain pipeline is the main path -------
def test_no_default_path_imports_the_agent_layer() -> None:
    """Only the agents package, the model constructor and opt-in scripts may import it, so a
    fresh project (any CLI, UI or stage run) executes the pipeline unless someone opts in."""
    src = Path(__file__).resolve().parents[1] / "src" / "autotester"
    allowed = {"agents", "providers"}
    offenders = [p.relative_to(src).as_posix() for p in src.rglob("*.py")
                 if p.relative_to(src).parts[0] not in allowed
                 and ("autotester.agents" in p.read_text(encoding="utf-8")
                      or "from autotester import agents" in p.read_text(encoding="utf-8"))]
    assert offenders == []
    from autotester.schema.project import Project
    assert "agent_mode" not in Project.model_fields  # no setting makes the agent the default
