# Task-level verdict - T-181 agent guardrails and measured gain (close-out, 2026-10-13)

Contract `qa/contracts/agent-layer.md`, AL11-AL13 (T-181 section). done_check `uv run pytest tests/test_agent_gain.py` passes (53 passed across
test_agent_gain, test_agent_step_cap, test_agent_layer, test_agent_model, test_model_chain; ruff and doctor clean after SNAPSHOT regeneration).

VERDICT: PASS (task closed; the outcome of the measured comparison is NO GAIN and the layer is DROPPED AS DEFAULT, D-095)

- AL11 budget meter and halt: judged in T-179/t181-guardrails (e8118070); step cap re-tested in tests/test_agent_step_cap.py
  (cap 40 allows 8 tool calls; a runaway halts as `step_cap`; the cap counts graph supersteps, about 4 per model turn).
- AL12 live comparison: done three times against a seeded product in a visible browser (qa/verdicts/t181-live.r2.md, .r3.md; r1 in the
  earlier record). Numbers r3: pipeline 1 bug, 0 FP, 12,554 tokens; agent 1 bug, 0 FP, 73,781 tokens, halted at the step cap.
  r1: 0 vs 0 bugs at about 15x tokens; r2: pipeline 1 vs agent 0.
- AL13 keep/drop: declared by Umesh, 2026-10-13 (D-095, per D-042): DROPPED AS DEFAULT. The finding is recorded and not hidden, and the
  layer is NOT declared kept on unfavourable evidence, which is what AL13 requires. The code stays opt-in; `test_no_default_path_imports_the_agent_layer`
  proves no default path imports it.
