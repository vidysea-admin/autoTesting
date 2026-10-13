# Verdict - ollama-primary (re-check of the three cycle-1 defects)

**Verdict:** PASS
**Cycle checked:** 2

## Defects re-checked
1. Call sites: `cli.py` expand and `cli_orchestrate.py` ingest/learn `--provider` now default to `providers.DEFAULT_SPEC` (the schema default, `model-chain`); the learn path resolves `--provider` via `parse_spec`, so `litellm:<model>` or an explicit vendor still overrides. Test `test_cli_provider_defaults_resolve_through_the_chain` asserts both defaults. Left as is on purpose: `ledger relitigation` default `mock` (no model call by design) and `cli_video*.py` `gemini` (video/vision is Gemini Files API only). No hardcoded vendor defaults found in UI routes, stages or MCP.
2. Observability: one warning per fall-through (tier label + error class only) and one info line for the serving tier. `ModelChainProvider.served`/`id` are thread-local, reset at the start of every call; a failed call reports None / `model-chain`. Tests: `test_fall_through_is_logged_without_prompt_or_key`, `test_failed_call_leaves_no_stale_serving_id`. `grade.py` reads `judge.id` after the call, so verdict `grader_provider` now names the serving tier.
3. `test_ollama_base_url_override` covers `OLLAMA_BASE_URL`.

## Checks
- pytest (model_chain, provider_factory, litellm, litellm_guard, providers, langchain_fallback, expand_cli, cli_orchestrate*, orchestrate_runners, cli_surface): all pass.
- ruff: only the pre-existing E501 in tests/test_isolated_provider.py:59. doctor: clean.
