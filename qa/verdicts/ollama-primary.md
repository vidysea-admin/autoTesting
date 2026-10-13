# Verdict - ollama-primary

**Verdict:** FAIL
**Cycle checked:** 1
**Head checked:** 00b71264

## Passed
- tests: test_model_chain, provider_factory, litellm_provider, litellm_guard, providers, langchain_fallback: 96 passed.
- ruff: only the pre-existing E501 at tests/test_isolated_provider.py:59. doctor: clean. `autotester providers` prints the order and readiness, no key values.
- Redaction: `guard_text` runs once up front on the first ready tier, raises before any call, no fall-through (test asserts zero calls and no key in the message).
- Schema: agent/judge default `model-chain`; a project naming another provider (e.g. litellm:...) still wins in `for_role`, so existing configs keep working.
- Tier timeout is the LiteLLM `_TIMEOUT_S = 120` per tier, so GLM cold start (67s measured) is not skipped. Worst case all tiers fail is about 360s.
- OLLAMA_BASE_URL overrides the endpoint (ollama_cloud.base_url); key is passed as kwarg only, never logged.

## Defects
1. Call sites not on the chain by default. `for_role` (run_launcher judge, routes_runs, routes_learn agent) is on the chain, but: `cli_orchestrate.py:236` learn/ingest `--provider` defaults to `gemini` (resolved at line 146 via `providers.get`), `cli.py:204` expand defaults to `langchain-fallback`, `cli.py:149` relitigation defaults to `mock`. Ingest and expand therefore still hardcode Gemini or the legacy chain as primary. Vision/video (Gemini Files API) is legitimately Gemini only.
2. Fall-through is not logged. A failed tier's error is appended to a list and dropped when a later tier answers; nothing says GLM failed and DeepSeek served. The serving tier is recorded only via `self.id = tier.label` and `usage`; `id` stays stale from a prior call if the next call fails.
3. No test for the OLLAMA_BASE_URL override.

## Required to PASS
Default ingest/expand/discover callers to the chain (or route through `for_role`), emit one non-secret log line per fall-through plus the serving tier, add a base-url test.
