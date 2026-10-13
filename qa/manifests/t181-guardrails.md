# Manifest - t181-guardrails (T-181: agent guardrails + measured gain vs pipeline, AL11-AL13)

## Status: ready-for-check
Fix cycle: 1
Policy-Version: proportional-verification/2026-10-10.9
Tier: M (builds on the checked T-179 layer; no new dependency, no guard change)
Branch: wave/t181-guardrails from wave/t179d-agent-layer (3b8c9225). Untouched: qa/contracts/, guards.py, DECISIONS.md, goal.json, ledger.

## AWAITING UMESH (not decided; placeholders, configurable)
- **Budget number:** `schema/agent_guardrails.py::AgentGuardrails.budget` defaults to 200,000 tokens / $2.00 at $15 per M tokens. Conservative placeholder, not a ruling.
- **Win rule:** `WinRule` default = agent bugs >= pipeline bugs AND agent false-positive rate <= pipeline's, within budget; a tie is a gain. `require_strict_gain`, `min_bugs_delta`, `max_fp_rate_delta` change it. Note: `comparison.compare(rule=None)` keeps T-179's stricter rule (tie = no gain) so T-179's checked tests stand.
- **AL13 keep/drop is NOT declared.** No live comparison has run (see Held); the layer is not claimed "kept".

## Built
- **AL11 (guardrails):** one meter (`agents/budget.py::Meter`) and one middleware (`lead_agent.Rails`), reused. `run_lead_agent(guardrails=...)` takes the budget and step cap from `AgentGuardrails`: budget breach -> `stopped="budget_exceeded"` with named reason; step cap -> `stopped="step_cap"`, reason "graph step cap reached".
- **Allowed domains / write policy:** no new code; the agent's `run_case` already goes through `guards.write_policy_refusal`. Tests drive it through the framework: an off-domain navigate is refused at READ_ONLY and ALLOW_WRITES (zero sessions); a commit-named click is refused under READ_ONLY while an in-domain read runs.
- **AL12/AL13 harness:** `agents/gain.py::measure_gain(corpus, case_bug_map, pipeline_runner, agent_runner, guardrails)` times both paths, calls the one `comparison.compare` (scored by `stages/bench.py`), writes the report. `PathMeasure` gained `false_positive_rate` (from the scorer) for the rule.

## Held / not built
- The LIVE run: real `run_and_grade_case` vs the real model agent on a seeded product in a visible browser. The repo has no seeded fixture site wired to a case map; runners are caller-supplied, tests use fakes. Needs Umesh's budget/rule and a model key.

## Evidence
- `uv run pytest tests/test_agent_gain.py` -> passes (13 tests); `tests/test_agent_comparison.py`, `test_agent_layer.py`, `test_bench.py` -> 51 passed together with it.
- ruff clean; doctor clean after `autotester map`.
