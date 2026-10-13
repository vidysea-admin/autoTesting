# Manifest - t179d-agent-layer (T-179 slice d: the Deep Agents lead tester, remaining AL1-AL7, AL11-AL13)

## Status: checked-PASS
Fix cycle: 1
Policy-Version: proportional-verification/2026-10-10.9
Tier: L (dependency add; the rails middleware sits on the AL3/AL6 boundary)
Branch: wave/t179d-agent-layer from master 71cf5827, with wave/t179c-lead-loop (d30c3b00) merged. Untouched by design: qa/contracts/, guards.py, subagents.py, ledger files, DECISIONS.md, goal.json. MAP.md regenerated (the merge conflict was in a generated file).
Authority: D-089 item 1 (deepagents `>=0.7.24,<0.8`, Approved-by Umesh). `langchain` is declared directly because the doctor's undeclared-dependency check requires it (`langchain.agents.middleware`); it was already a transitive dependency.

## Criteria covered
- **AL1 (built):** `agents/lead_agent.py::build_lead_agent` is the one `create_deep_agent` call, with the framework `TodoListMiddleware` for planning (0.7.24 has none by default; feedback-inbox 2). Test drives `write_todos` and reads `todos` from state. Skills are read-only to the model (deny-write permission), tested.
- **AL2 (built):** `report` (wraps `stages/unified_report.py::build_report`) and `capture_network` (wraps `stages/network_capture.py::first_party_evidence`) added in `agents/report_tools.py`, registered into the one dispatcher. All 7 contract tools exist plus the 3 read tools of t180. Test resolves every `wraps` path and spies the stage call.
- **AL3 (built through the framework):** the three clauses (secret in args, crawl with no approval, write under READ_ONLY) driven as scripted tool calls; each asserted from the span's `refusal` (`secret`, `approval`, `write_policy`), zero sessions, zero stage calls.
- **AL4 (built):** `skills=["/"]` over the packaged SK1 folders; the system prompt comes from `load_skill_prompt`; no `.read_text` and no prompt-sized literal in `lead_agent.py` (test).
- **AL5 (built, framework path):** `Rails` middleware writes a `ToolSpan` per planning step, tool call and `task` delegation on the run's `trace.jsonl`, `trace_id` = `run_id`.
- **AL6 (built, framework path):** every message and the model's own earlier tool-call arguments are scrubbed then gated before each model call; a secret in the user task halts before any model call; a secret in a `task` call is refused. Tests assert the raw value is in no message the model saw nor the trace.
- **AL7 (built):** only judgement subagents registered; `runner` and `general-purpose` are refused. Tests: deterministic job = 0 delegations, one judgement step = exactly 1.
- **AL11 (built):** `agents/budget.py::Meter` (reported usage, else length estimate) + `TokenBudget`; a breach raises in the middleware and `run_lead_agent` returns `AgentRun(stopped="budget_exceeded", reason="token budget exceeded: ...")` plus a `budget` span. Reasons distinguishable (finished / approval-refusal-continues / budget_exceeded). Cost ceiling tested.
- **AL12 (built on injected verdicts):** `agents/comparison.py::compare` scores both paths through `stages/bench.py` and writes the four numbers for each path. See feedback-inbox 6: the live pipeline-vs-agent run on a seeded product with a browser is NOT built.
- **AL13 (built):** the verdict line (GAIN / NO GAIN with the reason and both paths' numbers) is always produced; a tie, a loss and a budget breach are all NO GAIN. The unit does not declare D-042's layer "kept".

## Held / not built
- Live AL12 run (real pipeline and real model), no browser here.
- `run_lead` (t179c loop) has no budget; AL11 is on the framework path only.
- AL8-AL10 belong to T-180 (passed).

## Evidence
- `uv run pytest tests/test_agent_layer.py tests/test_agent_comparison.py` -> 23 passed. Plus agent tests (lead_loop, tools, subagents, read_only, credential_gate, click_names, destination_seam), test_run_trace, test_prompt_skills -> 519 passed overall in the run.
- `uv run ruff check src tests scripts` -> clean; `uv run autotester doctor` -> clean (after `autotester map`).
- No live model, no browser. Falsification edits not yet run (checker): drop `_clean` (AL6), drop the `JUDGEMENT` check (AL7), drop `meter.check()` (AL11), drop `TodoListMiddleware` (AL1).

## Open
Questions in `qa/feedback-inbox.md` (from maker t179d), items 1-7.
