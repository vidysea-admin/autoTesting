# t181-live: AL12 live comparison and AL13 keep/drop (measured 2026-10-13)

**Not a checker PASS.** This is a measurement record. Umesh makes the final keep/drop call (D-042).

## Setup

- Product: `tests/fixtures/regression_site` copied to a temp dir with `login.broken.html` seeded as `login.html` (one planted bug, `bug_login_password`, S1). Local server on 127.0.0.1 only, headed browser, one at a time, no external site. Corpus is tiny: 2 cases (login = the bug, home = clean).
- Model provider: `gemini` (first entry of the langchain fallback chain; the only configured vendor with a working key besides OpenRouter/Ollama, which the chain does not use). The same provider class judged both paths (`LangChainFallbackProvider`, separate instances). New constructor `providers/agent_model.py::agent_chat_model` (test `tests/test_agent_model.py`, 2 pass) because T-179 had no production model constructor.
- Pipeline: `stages/run_case_pipeline.py::run_and_grade_case` per case. Agent: `agents/lead_agent.py::run_lead_agent` under `AgentGuardrails`. Same persisted default rubric per case for both. Scored by `agents/gain.py::measure_gain` and re-scored by `comparison.compare` with the pipeline token count, both through `stages/bench.py`.
- Budget per Umesh 2026-10-13: 1,000,000 tokens / $10.00, set via `AgentGuardrails(budget=TokenBudget(...))` in the script arguments. `usd_per_million_tokens` is a configured estimate ($10/M, deliberately high); the real Gemini price was not looked up.
- Win rule: default `WinRule()` (agent bugs >= pipeline bugs, agent FP rate <= pipeline FP rate, tie = gain, within budget).
- `write_policy=ALLOW_WRITES` on the fixture project (the login case clicks; per project policy the account is the scope).

## Numbers (qa/evidence/t181-live/comparison.json, run_meta.json)

| | bugs found (of 1 seeded) | false positives | FP rate | tokens | est. cost @ $10/M | wall |
|---|---|---|---|---|---|---|
| pipeline | 0 | 0 | 0.0 | 8,725 (judge only) | $0.09 | 175.6 s |
| agent | 0 | 0 | 0.0 | 135,679 (126,954 model + 8,725 judge) | $1.36 | 124.4 s |

Total spent in this run: about 144,400 tokens, about $1.44 at the configured estimate (budget remaining: 86%).
Agent stop reason: `step_cap` ("graph step cap reached"), 6 tool calls, 0 delegations, 0 refusals. It did not breach the token budget.

## AL13 outcome by the win rule

**Mechanical result of the default rule: GAIN (a 0-0 tie on bugs and a 0.0-0.0 tie on FP rate, tie = gain).** That is what `comparison.compare` printed.

**Plain reading, which the rule's tie clause hides:**
- Neither path found the planted bug. Both graded the broken login case PASS. Detection is 0 of 1 for both, so the layer shows NO gain on bugs found and NO gain on false-positive rate. AL13's own text asks for "a gain on bugs-found or false-positive rate"; this run shows none.
- The agent used about 15.5x the tokens of the pipeline (135,679 vs 8,725) and halted at the step cap, not at a normal finish. It was faster on wall time (124 s vs 176 s), but the pipeline timing includes a one-off browser start.
- The planted bug was seen and then passed: the agent's judge note reads "reproduced the expected bug resulting in an invalid credentials error" and the pipeline's note cites the seeded issue, yet both returned PASS. The cause is the shared default rubric ("evidence consistent with the case's stated claim"), not the agent layer. The comparison therefore could not discriminate the layer from the pipeline on this corpus.

**Recommendation for Umesh (not a decision): do not declare D-042's layer "kept" on this evidence.** The tie-as-gain clause makes the default rule say GAIN, but no axis improved, cost rose about 15x, and the run step-capped. Treat AL13 as inconclusive-to-drop until a corpus and rubric that can discriminate exist.

## Findings to carry (not fixed here; no test weakened)

1. `comparison.compare` treats only `budget_exceeded` as a no-gain halt; `agent_stopped == "step_cap"` still returned GAIN. `agents/gain.py`'s docstring says a "budget or step-cap halt is carried into the verdict as no gain". Code and docstring disagree.
2. When the rule yields GAIN on a pure tie, the verdict line's reason still reads "more bugs found or fewer false positives", which is false for a tie.
3. The seeded corpus is 1 bug / 2 cases. A discriminating AL12 needs an assertion-bearing rubric (for example `make_rubric` in `scripts/bench_trial.py`, which names the expected text) and more planted bugs, with the same rubric on both paths.
4. Pipeline token count covers judge calls only (no acting model in the pipeline); the agent's covers its model plus its judge calls.

## Cleanup

The script's local server is shut down in a `finally`; both browser sessions are closed by their context managers. No external site was touched, no key value was printed or stored (evidence holds verdict reasons and token counts only).
