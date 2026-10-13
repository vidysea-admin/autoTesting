# Verdict - t181-guardrails
Cycle checked: 1
Verdict: PASS (unit scope: guardrails + harness). T-181 TASK NOT CLOSED.
Head checked: 3d9b4564 (master merged into branch, clean, no conflicts)

Verified: guardrails reuse T-179 `agents/budget.py::Meter` and `lead_agent.Rails` (no duplicate); named halts `budget_exceeded` / `step_cap` tested; off-domain and commit-click refused through the agent's `run_case` (guards.write_policy_refusal) at READ_ONLY/ALLOW_WRITES; `measure_gain` scores only via `comparison.compare` -> `stages/bench.py`; defaults are fields of `AgentGuardrails`/`WinRule`, not magic numbers.
Ran: test_agent_gain, test_agent_layer, test_agent_comparison, test_bench -> 68 passed; ruff clean; doctor clean.

## Provisional defaults (NOT confirmed by Umesh)
- Budget 200,000 tokens / $2.00 (at $15 per M tokens); max_steps 60.
- Win rule: agent bugs >= pipeline AND agent FP rate <= pipeline; tie = gain; within budget.
- None FP rate treated as 0.0.

## Remaining before T-181 can close (D-042: layer stays only on measured gain)
1. Umesh confirms (or changes) budget number and win rule.
2. Live AL12 run: real run_and_grade_case vs real model agent, seeded product with case-to-bug map, visible headed browser, model key; report with four numbers per path.
3. AL13 keep/drop declaration in manifest/report/ledger from that run (not "kept" on unfavourable evidence).
