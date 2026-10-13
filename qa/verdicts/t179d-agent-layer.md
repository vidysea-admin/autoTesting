# Verdict - t179d-agent-layer

Cycle checked: 1
Verdict: PASS
Head checked: 0166425a (branch wave/t179d-agent-layer, includes t179c-lead-loop)

## Evidence (fresh)
- pytest: test_agent_layer, test_agent_comparison, test_agent_lead_loop, test_agent_subagents, test_agent_tools, test_prompt_skills, test_run_trace, test_agent_credential_gate: 184 passed. T-179 done_check `uv run pytest tests/test_agent_layer.py`: 19 passed, exit 0.
- `ruff check src tests scripts`: all checks passed. `autotester doctor`: clean (advisory citation warnings only, pre-existing).
- Design rules: agents/*.py max 299 lines (tools.py), lead_agent.py 191; functions short; agents module imports schema models (extra=forbid in schema/).

## Per criterion
- AL1 PASS: one `create_deep_agent` call (lead_agent.py:158); pin `deepagents>=0.7.24,<0.8` (D-089); `langchain>=1.4.5` declared because `langchain.agents.middleware` is imported directly (already transitive; doctor requires declaration) - justified. TodoListMiddleware planner tested via write_todos.
- AL2 PASS: 7 contract tools wrap real stage functions (test resolves each `wraps`, spies stage call).
- AL3 PASS: a/b/c each driven through the framework, refusal read from the span, zero sessions.
- AL4 PASS: `skills=["/"]` read-only, prompt via `load_skill_prompt`, no inline prompt/read_text. All-skills exposure ruled acceptable (contract amended).
- AL5 PASS: Rails writes ToolSpan per plan/tool/delegate on the run's trace.jsonl, trace_id = run_id.
- AL6 PASS: every message and prior tool-call args scrubbed and gated before each model call; secret in task halts before any model call.
- AL7 PASS: judgement subagents only; runner/general-purpose refused; 0 and 1 delegation tests.
- AL11 PASS: Meter halts with `budget_exceeded` and named reason; above-budget completes.
- AL12/AL13: mechanism PASS on injected verdicts (four numbers per path, verdict line, no-gain recorded, budget-breach not a gain). Live comparison NOT judged here; it is T-181 (test_agent_gain.py).
- AL8-AL10: T-180, not judged here.
- Guardrail middleware: the same Rails instance is on the lead and every judgement subagent (`cfg["middleware"] = [rails]`).
- Model-call seam: no direct provider SDK in agents/; the chat model is injected (`BaseChatModel`), there is no production caller yet. When one is wired it must be built in providers/ (note for T-181/T-177 wiring, not a defect now).

## Defects
None blocking.
