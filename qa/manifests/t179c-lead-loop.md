# Manifest - t179c-lead-loop (T-179 slice c: the lead loop, trace spans, delegation counts)

## Status: ready-for-check
Fix cycle: 0
Policy-Version: proportional-verification/2026-10-10.9
Tier: L (trace-writer edit; the loop sits on the AL3/AL6 boundary)
Branch: wave/t179c-lead-loop from origin/master 64c5ab0d. Untouched by design: agents/guards.py (t179b-hg1), agents/subagents.py (t180), browser/session.py, ledger files, contracts, DECISIONS.md, goal.json, issues.jsonl, tools.py.

## Criteria covered
- **AL5 (built):** `core/trace.py::TraceWriter.record_tool` writes a `ToolSpan` (`schema/trace.py`, additive) to the run's own `trace.jsonl`, `trace_id` = `run_id`, same writer and redaction gate (RT5/RT6, no second mechanism). One span per lead planning step, tool call and delegation; a tool/delegate span points at its planning step by `parent_seq`. `read_spans` skips these lines so the run-view and failure bundle are unchanged; `read_tool_spans` reads them.
- **AL7 (lead side built, against an interface):** `agents/lead.py::Delegator` is a Protocol; t180's subagents fill it later. `JUDGEMENT` roles delegate; the `runner` (a single `run_case`) is refused as mechanical. `LeadRun.delegations` counts delegations made. Tests: deterministic job = 0, mixed job = exactly 1, runner = refused. The real count over the real subagents needs t180 merged.
- **AL4 (loader side built):** the lead prompt is `skills/agent-lead/SKILL.md` read only through `providers.base.load_skill_prompt`; `lead_skills()` returns the folder for a `skills=` argument. A test asserts no prompt-sized string literal and no `.read_text` in `lead.py`/`tools.py`. The `skills=` argument itself is the framework's, so HELD with AL1.
- **AL6 (planning layer, built):** the system prompt, every transcript line, every delegated task/file name/file body and every subagent reply pass `guard_model_bound`; a secret never reaches the model, a subagent or the trace (tests).
- **AL2 remainder:** `report`, `capture_network` not built.

## Held
- **AL1** (`create_deep_agent`, `deepagents>=1.7`): no dependency, and the floor resolves to nothing (PyPI is 0.7.x). Needs an owner decision. The loop is an executor, not a planner: the model plans. It is the seam the framework call replaces/wraps; it is not a hand-rolled StateGraph.
- AL4 `skills=` argument, AL7 over real subagents: need AL1 / t180.

## Design
`run_lead(ctx, model, delegator, max_steps)`: model (`LeadModel` Protocol) returns one `LeadStep` (tool | delegate | finish); tools go through `tools.dispatch` (guards inside, unchanged); a bad step or model failure stops with `model_error` (nothing echoed); a step cap stops a runaway. New: `agents/lead.py` 118 lines, `schema/lead_loop.py`, `skills/agent-lead/SKILL.md`, `tests/test_agent_lead_loop.py` 170 lines. Edited: `core/trace.py` (100), `schema/trace.py`, `docs/MAP.md` (regenerated).

## Evidence
- `uv run pytest tests/test_agent_lead_loop.py tests/test_run_trace.py tests/test_agent_tools.py tests/test_prompt_skills.py -p no:xdist -o addopts=` -> 53 passed
- `uv run ruff check src tests scripts` -> clean; `uv run autotester doctor` -> clean; mypy on the new files clean.
- Falsification not yet run (checker): suggested edits are dropping `parent_seq`, removing the `JUDGEMENT` check, and removing the transcript gate.

## Open
trace-writer edit (`core/trace.py`, `schema/trace.py`) is outside D-042's listed files; the brief flagged it as needing authorization (blocker 3). It is additive and the one writer is kept.
