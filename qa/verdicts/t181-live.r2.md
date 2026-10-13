# t181-live r2: AL12 live comparison on the model chain (measured 2026-10-13)

**Not a checker PASS.** Measurement record; Umesh makes the keep/drop call.

## Setup
Same harness as `t181-live.md` (`scripts/agent_live_comparison.py`, `agents/gain.py::measure_gain`), local regression_site fixture (temp copy, `login.broken.html` seeded: 1 planted S1 bug, 2 cases), one headed browser, 127.0.0.1 only. Changes vs r1: model chain Ollama `glm-5.3-flash` -> `deepseek-v4.1-flash` -> Gemini (`autotester providers`: all three ready); the fixed oracle (grade_note_guard); step cap 40; budget 1,000,000 tokens / $10 via `AgentGuardrails`. New `providers/agent_model.py::agent_chain_model` gives the agent a tool-calling chat model with the same tier order and a per-call served log; judges are `ModelChainProvider`.

## Serving tier per call (qa/evidence/t181-live-r2/run_meta.json)
All calls were served by `ollama_chat/glm-5.3-flash`: 10 of 10 agent model calls, 2 of 2 pipeline judge calls, 0 agent judge calls (the agent never reached grade_case). DeepSeek and Gemini were never reached (no fall-through).

## Numbers
| | bugs (of 1) | FP | tokens | est. cost | wall |
|---|---|---|---|---|---|
| pipeline | 1 | 0 | 12,642 (judge only) | ~$0.13 | 92.7 s |
| agent | 0 | 0 | 62,476 (model 62,476 + judge 0) | ~$0.62 | 45.1 s |

Cost is **estimated** at the configured $10/M; no per-token price is known for the Ollama cloud models (flat plan). Total about 75k tokens, about $0.75 estimated, 7.5% of budget.
Pipeline: login case FAIL (bug found), homepage INCONCLUSIVE (not scored as an FP, no bug claimed). Agent: stopped `step_cap` after 6 tool calls, 0 delegations, graded nothing.

## Rule outcome
`comparison.compare`: **NO GAIN** (agent halted at step cap before finishing; agent 0 bugs vs pipeline 1). Plain reading agrees: the agent layer found fewer bugs at about 5x the tokens, faster only because it did less.

## Recommendation (not a decision)
The chain and fixed oracle work (pipeline now catches the planted bug on GLM, which r1 on Gemini missed). The agent layer shows no gain on this corpus; lean drop or hold until the agent can finish its run under the cap. Caveats: n=1 bug, 1 run, GLM only, homepage case INCONCLUSIVE worth a look.

## Cleanup
Server shut down in `finally`, browsers closed by context managers. No key value printed or stored.
