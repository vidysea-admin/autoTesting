# Manifest — ollama-primary

**Status:** ready-for-check
**Fix cycle:** 1
**Unit:** Primary models are Ollama-served GLM 5.3 Flash then DeepSeek 4.1 Flash (OLLAMA_API_KEY, repo-root .env); Gemini is fallback only. Decision: Umesh, 2026-10-13.
**Branch:** wave/ollama-primary

## What changed
- `providers/ollama_cloud.py` (new): endpoint `https://ollama.com` (or `OLLAMA_BASE_URL`), key `OLLAMA_API_KEY`, model ids.
- `providers/model_chain.py` (new): `model-chain` provider, ordered LiteLLM tiers, fall through on any ProviderError (error, timeout, unparsable). Order: spec `model-chain:<m1>,<m2>` > `AUTOTESTER_MODEL_ORDER` > default `ollama_chat/glm-5.3-flash`, `ollama_chat/deepseek-v4.1-flash`, `gemini/gemini-3.6-flash`. Tiers without credentials are skipped.
- `litellm_provider.py`: Ollama endpoint/key via ollama_cloud; public `guard_text` (redaction gate); OLLAMA_API_KEY in the secret set.
- `schema/project.py`: agent and judge default `model-chain`; `cli.py providers` prints the order and readiness.
- `pyproject.toml`/`uv.lock`: `langchain-ollama` declared (doctor undeclared-dependency).
- `tests/test_model_chain.py`: order, fallback, timeout, skip, config, redaction (fake litellm, no network).

## Verify
`uv run pytest tests/test_model_chain.py tests/test_provider_factory.py tests/test_litellm_provider.py tests/test_litellm_guard.py tests/test_providers.py tests/test_langchain_fallback.py`; `uv run ruff check src tests scripts` (one pre-existing E501 in tests/test_isolated_provider.py:59 from master); `uv run autotester doctor`.

## Notes
- providers/agent_model.py does not exist on master; agent and judge both resolve through `providers.for_role`, which now defaults to the chain.
- Live smoke 2026-10-13 (trivial prompt, no project data): glm-5.3-flash ok 67.1s (cold), deepseek-v4.1-flash ok 0.9s.
- langchain-fallback is unchanged (legacy, still selectable).
