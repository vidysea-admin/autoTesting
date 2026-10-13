# t181-live r3: AL12 rerun, step cap investigated (measured 2026-10-13)

**Not a checker PASS.** Measurement record; Umesh makes the keep/drop call.

## Why r2 stopped "after 6 tool calls" with a cap of 40
The cap WAS honoured. `AgentGuardrails.max_steps` flows `scripts/agent_live_comparison.py --max-steps` -> `AgentGuardrails` -> `run_lead_agent` -> LangGraph `recursion_limit` (no hardcoded 6 anywhere). But `recursion_limit` counts graph supersteps, and the deep-agent graph spends about 4 supersteps per model turn (middleware hooks plus the model and tool nodes). Cap 40 is therefore about 10 model turns, and `tool_calls` (only the stored-case tools Rails dispatches) is much smaller than turns. Evidence: both live runs made exactly 10 model calls before `GraphRecursionError`; r2 counted 6 tool calls, r3 counted 3. Cap semantics unchanged. New tests (`tests/test_agent_step_cap.py`): cap 40 allows 8 tool calls and finishes; a runaway loop at cap 40 still halts as `step_cap` with 6 < tool_calls < 40; `agent_chain_model` tries tiers in chain order (GLM, then DeepSeek on GLM failure) and logs the serving tier. To get 40 model turns the cap would need to be about 160 (Umesh's call; not changed).

## Setup
Same as r2: regression_site temp copy with `login.broken.html` seeded (1 planted S1 bug, 2 cases), one headed browser, 127.0.0.1 only, fixed oracle, chain GLM -> DeepSeek -> Gemini, cap 40, budget 1M tokens / $10 via `AgentGuardrails`.

## Models served (qa/evidence/t181-live-r3/run_meta.json)
`ollama_chat/glm-5.3-flash` served all calls: 10/10 agent model calls, 2/2 pipeline judge calls, 1/1 agent judge call. DeepSeek and Gemini never reached.

## Numbers
| | bugs (of 1) | FP | tokens | est. cost | wall |
|---|---|---|---|---|---|
| pipeline | 1 | 0 | 12,554 (judge) | ~$0.13 | 88.2 s |
| agent | 1 | 0 | 73,781 (model 64,891 + judge 8,890) | ~$0.74 | 95.8 s |

Agent tool calls actually made: 3 (run_case path, 0 delegations, 0 refusals); stopped `step_cap` after 10 model calls. Cost is **estimated** at $10/M (no known Ollama per-token price); total about 86k tokens, about $0.87, 8.6% of budget. Pipeline homepage case INCONCLUSIVE, not an FP.

## Rule outcome
**NO GAIN** (`agent run halted at its step cap before finishing`). By detection alone it is a tie (1 vs 1 bug, 0 FP each) with the agent at about 5.9x the tokens and slightly slower. The step-cap halt forces no-gain by the rule, so this run cannot show a gain at cap 40; the cap, not the agent's ability, is the binding limit.

## Recommendation (not a decision)
Agent matched the pipeline on detection but cost about 6x tokens and never finished. Drop unless a rerun at a cap near 160 (about 40 turns) finishes and beats the pipeline on bugs or FP; n=1 bug, 1 run.
