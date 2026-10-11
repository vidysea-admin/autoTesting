# t202-any-model-provider -- sub-checker A (blind) falsification, head 94c569c0

Worktree D:/autoTesting/.worktrees/t202-any-model-provider: HEAD 94c569c0, `git status --porcelain` empty before and after.
Interpreter: worktree .venv python (litellm 1.104.0). Run as `python -m pytest -p no:xdist -c <pyproject> --rootdir=<root> <abs test paths>`.
Start 05:53 IST 2026-10-11. No real provider call. Scratch: .../scratchpad/t202A-copy-<k>/ (tools in t202A-tools/).

## PART 1 (real worktree, once each)
| cmd | result |
|---|---|
| tests/test_provider_factory.py | 31 passed, 1 warning, 1.37s |
| tests/test_litellm_provider.py | 16 passed, 0.46s |
| tests/test_litellm_guard.py | 21 passed, 30.67s |
| test_providers.py + test_langchain_fallback.py + test_ensemble_honesty.py | 29 passed, 1 warning, 2.29s |
| test_ui_runs_queue.py + test_expand_cli.py + test_cli_advice_resolves.py | 49 passed, 1 warning, 18.53s |

Total 146 passed, 0 failed, 0 skipped.
`git grep -n "LangChainFallbackProvider()" 94c569c0 -- src/autotester/ui` is NOT empty: one hit, ui/app.py:64, inside the
`_lifespan` DOCSTRING ("...invisible to LangChainFallbackProvider() even though..."): prose, not a call.
(test_neither_route_constructs_the_langchain_provider_itself, an AST check, passes.)

## PART 2 isolation
Every copy: `git archive 94c569c0 | tar -x`; run with PYTHONPATH=<copy>/src; proof printed per copy, e.g.
`ISOLATION ...\t202A-copy-1\src\autotester\__init__.py` (the worktree editable install does not shadow it). Tracebacks of every red run cite copy paths.
Each row: own copy, one single-hunk edit, never restored.

| LL | copy | tests | green-before | mutation (one hunk) | red-after (assertion that fired) |
|---|---|---|---|---|---|
| LL1 | copy-1 | test_provider_factory.py | 31 passed | providers/__init__.py parse_spec: `if _CREDENTIAL_IN_SPEC.search(model):` -> `if False and ...` | 6 failed: test_parse_spec_rejects_empty_models_and_embedded_credentials_without_echoing x3 `Failed: DID NOT RAISE ProviderError`; test_a_malformed_project_spec_is_a_400_not_a_500 (`assert 403 == 400`); learn-route refusal page test; test_ll11_the_cli_refuses_a_malformed_spec_without_echoing_it (`'pw-canary' is contained here: ps://user:pw-canary@host/v1 agent call failed`) |
| LL2 | copy-2 | test_provider_factory.py | 31 passed | ui/routes_learn.py:238 `for_role(project,"agent")` -> inline `...LangChainFallbackProvider()` | 2 failed: test_neither_route_constructs_the_langchain_provider_itself[routes_learn.py] (`assert 'for_role' in {...names...}`); test_generate_cases_asks_the_factory_for_the_agent_of_this_project (`assert [] == [('demo','agent')]`) |
| LL3 | copy-3 | test_litellm_provider.py | 16 passed | _structured `if strategy != "json":` -> `if False:` | 1 failed: test_unparsable_answer_raises_naming_model_and_role_never_a_partial_object `assert 2 == 1` (repair retry taken for non-json) |
| LL4 | copy-4 | test_litellm_provider.py | 16 passed | added `see_video(...) -> None` to LiteLLMProvider | 1 failed: test_see_video_is_unsupported `Failed: DID NOT RAISE Unsupported` |
| LL5a | copy-5 | test_litellm_guard.py | 21 passed | `_complete`: `self._guard(messages)` -> `pass` | 4 failed: test_assert_no_raw_secrets_runs_before_every_call_including_the_repair (`assert 0 == 2`), test_a_prompt_carrying_a_secret_never_reaches_litellm, test_dotenv_values_are_guarded_without_any_option, test_an_exported_vendor_key_is_guarded_though_it_is_not_in_dotenv (`DID NOT RAISE ProviderError`) |
| LL5b | copy-55 | test_litellm_guard.py | 21 passed | `_env_secret_values` returns `[]` first line | 2 failed: test_dotenv_values_are_guarded_without_any_option (`DID NOT RAISE ProviderError`); test_a_dotenv_value_echoed_by_a_vendor_error_is_withheld (`'sk-ant-DOTENV-CANARY-777' ... is contained`). The exported-key test stays green, correctly: that path is `_PROVIDER_KEY_ENV`, not `.env` |
| LL6 | copy-6 | test_litellm_provider.py | 16 passed | `"num_retries": 0` -> `1` | 1 failed: test_one_physical_call_zero_retries_and_usage_recorded `assert (1 == 1 and 1 == 0)` |
| LL7 | copy-7 | test_litellm_provider.py | 16 passed | output_tokens reads `prompt_tokens` | 1 failed: same test, `assert ('judge',1,21,21) == ('judge',1,21,5)` |
| LL8 | copy-8 | test_litellm_guard.py | 21 passed (187s, host memory pressure) | `_failure`: `hidden = []` | 4 failed: test_neither_the_key_nor_the_endpoint_appears_in_an_error (`'canary' ... pw-canary@models.internal:8000/v1 with key k-canary-key`), plus the exported-key, dotenv-value and extra-secret echo tests |
| LL9 | copy-9 | test_litellm_provider.py | 16 passed | litellm_schema.json_schema_for: gemini branch -> `if False:` | 1 failed: test_gemini_models_get_the_gemini_dialect_schema `assert 'additionalProperties' not in '{...}'` |
| LL10a | copy-10 | guard::test_no_callbacks_are_registered_and_telemetry_is_off, ::test_the_real_pinned_sdk_is_quiet_after_the_provider_loads_it, ::test_importing_providers_does_not_import_litellm | 3 passed (54s) | deleted `litellm.telemetry = False` | 1 failed: test_the_real_pinned_sdk_is_quiet... (subprocess stderr `AttributeError: module 'litellm' has no attribute 'telemetry'`). The FAKE test test_no_callbacks_are_registered_and_telemetry_is_off STAYS GREEN (finding 1) |
| LL10b | copy-105 | same 3 | 3 passed | `import litellm` at top of providers/__init__.py | 2 failed: ..real_pinned_sdk_is_quiet.. (`AssertionError: network touched`, litellm's import-time cost-map fetch hit the refused socket) and test_importing_providers_does_not_import_litellm (`assert 1 == 0`) |
| LL11a | copy-11 | test_provider_factory.py | 31 passed | routes_runs._judge_or_400: refusal made unreachable (`... and False`) | 5 failed incl. test_ll11_a_queued_run_whose_litellm_judge_lost_its_key_ends_refused_with_no_browser `assert ran == [] and "refused" in page` (a run was launched); 4 others (test_ll2_*, test_trigger_run_asks_the_factory...) `assert 403 == 400` |
| LL11b | copy-115 | test_provider_factory.py | 31 passed | cli_orchestrate.usable_provider gate unreachable | 1 failed: test_ll11_the_cli_exits_non_zero_with_the_same_one_line_reason `assert "model call failed" not in result.output` |
| LL12 | copy-12 | guard::test_a_test_that_forgets_the_fake_fails_loudly_instead_of_going_online | 1 passed (8.9s) | tests/litellm_fake.py no_network: both setattr lines -> `pass` | 1 failed `AssertionError: the real SDK never reached the socket guard / assert []` (31s) |
| LL13 | copy-13 | litellm_provider::test_litellm_is_pinned_to_one_exact_version_in_pyproject | 1 passed | pyproject `litellm==1.104.0` -> `>=1.104.0` | 1 failed `assert (1 == 1 and '==' in 'litellm>=1.104.0')` |
| LL14 | copy-14 | `autotester doctor` (PYTHONPATH=copy/src, repo_root derives from file path) | `doctor: clean`, exit 0 | +40 blank lines in providers/litellm_provider.py (267 -> 307) | `file-too-long: src\autotester\providers\litellm_provider.py - 307 lines > 300; split by responsibility`, `1 violation(s)`, exit 1 |

## PART 3 probes (real worktree, socket.socket.connect patched to raise)
(i) `import autotester.providers` -> file = worktree src; `'litellm' in sys.modules: False`.
(ii) LiteLLMProvider(model="openai/gpt-4o"), OPENAI/ANTHROPIC/GEMINI/GOOGLE keys, AUTOTESTER_MODEL and LITELLM_API_* cleared:
- reason: 'litellm:openai/gpt-4o is missing credentials: set OPENAI_API_KEY in .env (or LITELLM_API_KEY / LITELLM_API_BASE for an OpenAI-compatible endpoint)'
- key-like regex (sk-, AIza, 32+ char token): False. available(): False.
- litellm.telemetry = False; success_callback = []; failure_callback = []; _async_success_callback = []; input_callback = [].
- litellm.__file__ = worktree .venv; LITELLM_MODE=PRODUCTION and LITELLM_LOCAL_MODEL_COST_MAP=True were set by the provider.
- An `Exception ignored in BaseEventLoop.__del__ ... _ssock` trace prints at exit: an artefact of my patching socket.connect, not product code.

## Findings
1. LL10 telemetry assignment is pinned only by the REAL-SDK test, and incidentally: litellm 1.104.0 has no `telemetry` attribute, so deleting the line makes `litellm.telemetry` raise AttributeError. The fake-module test (`assert not getattr(fake,"telemetry",False)`) stays green when the line is deleted (it can only catch a True). The mutant is killed, but the cheap test does not pin the assignment; the kill depends on the pinned SDK lacking the attribute.
2. LL12 mutant run: with the guard disabled the test genuinely tried a connect to 203.0.113.7:9 (RFC 5737 TEST-NET, non-routable) for ~30s before failing; no real provider/host contacted.
3. Every other mutant was killed on the intended assertion; none stayed green. LL1 and LL11a kill several tests at once (collateral reds consistent with the gate sitting upstream of other tests).
4. `git grep LangChainFallbackProvider()` in ui/ is non-empty only because of a docstring in ui/app.py:64.
