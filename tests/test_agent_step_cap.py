"""T-181: the configured step cap is honoured end to end, and the chain model keeps its order.

`AgentGuardrails.max_steps` is LangGraph's recursion limit, so it counts graph supersteps (a
model turn and a tool turn are separate steps), not tool calls. Offline: scripted fake models."""

from __future__ import annotations

from typing import Any

import pytest
from test_agent_layer import Scripted, call, ctx  # noqa: F401  (ctx: the fixture)
from test_agent_tools import spies  # noqa: F401  (the fixture)

from autotester.agents import lead_agent
from autotester.providers import agent_model, ollama_cloud
from autotester.schema.agent_guardrails import AgentGuardrails
from autotester.schema.lead_loop import TokenBudget


def _go(ctx: Any, calls: int, cap: int) -> Any:  # noqa: F811
    model = Scripted(script=[call("get_catalog") for _ in range(calls)] + [])
    rails = AgentGuardrails(max_steps=cap, budget=TokenBudget(max_tokens=10**6))
    return lead_agent.run_lead_agent(ctx, model, "test the product", guardrails=rails)


def test_a_cap_of_40_allows_more_than_six_tool_calls(ctx: Any) -> None:  # noqa: F811  # noqa: F811
    out = _go(ctx, calls=8, cap=40)
    assert out.stopped == "finished" and out.tool_calls == 8


def test_a_cap_of_40_still_halts_a_runaway_loop_as_step_cap(ctx: Any) -> None:  # noqa: F811  # noqa: F811
    model = Scripted(script=[call("get_catalog") for _ in range(500)])
    out = lead_agent.run_lead_agent(ctx, model, "test", guardrails=AgentGuardrails(
        max_steps=40, budget=TokenBudget(max_tokens=10**7, max_cost_usd=1000)))
    assert out.stopped == "step_cap" and 6 < out.tool_calls < 40


def test_chain_model_uses_the_chain_order(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ollama_cloud.KEY_ENV, "k")
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.delenv("AUTOTESTER_MODEL_ORDER", raising=False)
    built: list[str] = []

    def fake_chat(name: str, fail: bool) -> Any:
        class M:
            def bind_tools(self, tools: Any, **kw: Any) -> Any:
                class B:
                    def invoke(self, messages: Any) -> str:
                        built.append(name)
                        if fail:
                            raise RuntimeError("down")
                        return "ok"
                return B()
        return M()

    monkeypatch.setattr(agent_model, "_build_tiers", lambda order: [
        (n, fake_chat(n, fail=i == 0)) for i, n in enumerate(order)])
    _, model, served = agent_model.agent_chain_model()
    assert model.bind_tools([]).invoke("hi") == "ok"
    assert built == [ollama_cloud.GLM, ollama_cloud.DEEPSEEK] and served == [ollama_cloud.DEEPSEEK]
