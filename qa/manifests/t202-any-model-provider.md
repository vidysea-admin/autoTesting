# Manifest — t202-any-model-provider (LiteLLM any-model Provider, re-land on master, D-071)

## Status: ready-for-check

**Contract:** qa/contracts/providers-litellm.md LL1-LL14 (LL15 settings page and LL16 real-provider smoke are NOT built and NOT claimed; LL15 waits on T-204, LL16 is HUMAN-GATED)
**Goal task:** T-202
**Date:** 2026-10-11
**Fix cycle:** 0
Branch: wave/t202-any-model-provider · Base: master 3d8f7d5a · Source: wave/t202-litellm code commits 769358e5 + c27133d8 (never PASSed; qa-only commits and its issue rows not carried; the branch and `codex/t202-completion` are untouched)
Product commit under check: fe0f5be98766f6341593451e0205d458f281a115 (b4716509 plus one test assertion; this manifest is the only later change)
Executor: claude-sonnet-subagent (maker build subagent)

Policy-Version: proportional-verification/2026-10-10.9
Tier: L (new dependency `litellm==1.104.0` in `pyproject.toml`/`uv.lock`; new third-party code in the outbound-prompt path)
**Dual check:** required
dual-trigger: security src/autotester/providers/litellm_provider.py:191 (`_guard`, the provider-level secret guard in front of every model call; also `_secret_values` :184, `_failure` :198 and `_endpoint` :112, key and endpoint handling)
Round cap: SECURITY CLASS -- the diff changes credential handling (LL5 prompt guard, LL8 key/endpoint/echo withholding), so the round cap does not apply. For the record: no `qa/verdicts/` file records a PASS naming `providers/litellm_provider.py` (new file); the earlier verdicts `t202-litellm.r0-1.md` (FAIL) and `t202-litellm.md` (CONTINUE-NEEDED) name it and never passed.
Persona walk: skip (backend only: no screen, route or flow is added; the refusal text of three existing surfaces changes).
Note for the coordinator: the brief (section 1) says `Dual check: no`; the dispatch said to set `required` when credential handling is touched, and it is, so `required` is set.

## What changed
- New (from `wave/t202-litellm`, content as built there plus the AT-790 fix): `providers/litellm_provider.py` (267 lines), `providers/litellm_schema.py` (88), `providers/images.py` (26); `tests/litellm_fake.py`, `tests/test_litellm_provider.py`, `tests/test_litellm_guard.py`, `tests/test_provider_factory.py`. D-072 item 2 authorizes the modules.
- `providers/__init__.py` (edited in place): `litellm` registered; `parse_spec`, `for_role(project, role)` (the one factory), `why_unavailable` (changed here: None when ready, else the provider's reason or a plain fallback, so callers need one `if`).
- `ui/routes_runs.py`: `_judge_or_400` + `_prepare_run` calls it, so the ONE construction site serves both the press and the queue's start-time re-check (`_run_queued` already turns the 400 into `refused`, hosting HO16/HO19); annotations `Provider`. `ui/run_execution.py`: annotations only. `ui/routes_learn.py`: `for_role(project, "agent")`; a malformed spec is now a refusal page (the old branch gave a 500); file stays at 300 lines.
- `cli.py::expand_cases` (LL11, not on the old branch): `--provider` takes `litellm:<model>` (`parse_spec`), a bad spec or an unavailable provider exits 1 with the one-line reason before any model call.
- LL10: `_load_litellm` sets `litellm.telemetry = False`. Verified in the installed 1.104.0 source: the package has NO `telemetry` attribute or switch (no phone-home code found; `LITELLM_MODE=PRODUCTION` + local cost map stop the `.env` load and the cost-map fetch). The assignment makes the contract's literal check true and is a no-op on this pin. Contract wording may want an amendment.
- Dependency: `litellm==1.104.0` exact pin in `pyproject.toml`; `uv.lock` taken from the source branch (additions only, +1548 lines: litellm's transitive closure, no existing package changed or removed); `uv lock --check` clean on master's base. No other dependency changed. Chosen by the earlier unit; no `uv add` was needed.
- `.env.example`: keys only. The placeholder `AUTOTESTER_MODEL=` that hosting added under "Group 10 placeholders" moved into "Model providers" (one key, one place). `docs/MAP.md` regenerated.
- Existing tests edited (retarget only, no assertion changed): the 12 files of the old branch (patch `for_role` instead of `LangChainFallbackProvider` on the routes module), plus `test_ui_runs_queue.py` (2 lines) and `test_ui_runs_serial_entry_order.py` (1 more line) from master. `tests/litellm_fake.py::no_network` now lets loopback through (asyncio's self-pipe on Windows needs it for a `TestClient`), so the factory file can carry the guard too (LL12 "every new test").
- New tests this unit: real-SDK quietness in a subprocess (LL10), exact-pin test (LL13), single-secret-set test (the earlier checker's non-blocking proposal), learn route malformed spec, queued run refused, CLI refusal x2 (LL11). The forget-the-fake test uses a TEST-NET IP literal so the guard fires before any DNS lookup.

## Criteria (verbatim from the brief, section 3; full text in qa/contracts/providers-litellm.md)
- **LL1 — The spec grammar.** `parse_spec("litellm:openai/gpt-4o") == ("litellm", {"model": "openai/gpt-4o"})`; bare ids and the comma-list `vision` value parse exactly as before; `providers.get("litellm", model="ollama/llama3.2").label == "litellm:ollama/llama3.2"`; an empty model after the colon, a spec containing `@`, `://`, or whitespace-embedded credentials, or an unknown provider id raises `ProviderError` whose message does not echo the rejected value.
- **LL2 — One factory; the hardcoded construction is gone.** `ui/routes_runs.py::trigger_run` and `ui/routes_learn.py` obtain their provider from `providers.for_role`; `grep -rn "LangChainFallbackProvider()" src/autotester/ui` returns nothing; the `judge: LangChainFallbackProvider` annotations in `ui/routes_runs.py` and `ui/run_execution.py` become `Provider`. With a project `judge` of `litellm:<m>` the route builds the `litellm` provider with model `<m>`; with `AUTOTESTER_MODEL` set and the project at the schema default, it builds `litellm` with that model; with neither, it builds `langchain-fallback` as today.
- **LL3 — Structured output returns a validated model, or a typed error.** `judge()` and `act()` return the validated Pydantic instance for each strategy (response_format, one forced tool call, else JSON-mode with exactly one repair retry), each against a fake `litellm`. An unparsable or schema-violating answer raises `ProviderError` naming the model and role and never returns a partial or coerced object; the message does not contain the prompt or the model's raw text beyond a short bounded excerpt run through `Redactor.scrub`.
- **LL4 — Roles.** `see_video` raises `Unsupported`; the vision role stays with `gemini`.
- **LL5 — The secret guard runs before every call, inside the provider.** Immediately before each physical `litellm.completion` call the provider passes every text part through `core.redact.assert_no_raw_secrets` against the repo-root `.env` values plus provider-key values from the process environment; a hit raises before the network call and names no value; in addition to the stage-level `SecretStore.guard_prompt` in `stages/grade.py`, which stays where it is.
- **LL6 — No hidden retries, and the call count is true.** One successful `judge()` = exactly one physical call; the single repair retry is a second counted call; `num_retries` is 0 and no `fallbacks`/Router is configured.
- **LL7 — Usage and trace.** `record()` once per physical call with the response's prompt and completion tokens; the usage row and trace span carry `provider == label`.
- **LL8 — Endpoint and key handling.** `api_base`/`api_key` only from explicit kwargs built from `LITELLM_API_BASE`/`LITELLM_API_KEY` (or `OLLAMA_BASE_URL` for `ollama/`); the provider never writes `os.environ`; `project.json` cannot carry a key; neither a key nor an `api_base` value appears in any `ProviderError`, log line or trace span.
- **LL9 — Gemini schema dialect.** For `gemini/` models the schema passes through the existing `gemini_schema()` (imported, not re-implemented).
- **LL10 — Lazy, quiet, vendor-neutral import.** Importing `autotester.providers` does not import `litellm`; once constructed `litellm.telemetry` is False and no success/failure callback list is non-empty; the pinned version's telemetry behaviour verified (see What changed).
- **LL11 — Availability and the no-credentials error are graceful.** `available()` False with no model or a missing key/`api_base`, True with model + key or model + `api_base`; `autotester providers` agrees with `available_ids()`; an unavailable resolved LiteLLM provider gives: the themed refusal page (400 for an API client) on `trigger_run` and the learn route naming the model and the one variable, a queued run ends `refused` with the same reason and launches no browser, the CLI exits non-zero with the same one-line message; no message contains a key, a prompt or an `api_base` userinfo.
- **LL12 — The mock provider remains, and tests never go online.** `providers.get("mock")`/`MockProvider` unchanged; `tests/test_providers.py`, `tests/test_langchain_fallback.py`, `tests/test_ensemble_honesty.py` pass without edits to their assertions; every new test uses the fake (or mock) and a fixture that makes a real socket connect raise.
- **LL13 — Dependency.** `pyproject.toml` pins `litellm` exactly and `uv.lock` agrees (`uv lock --check`); no other dependency changes.
- **LL14 — Design rules and one concept.** New modules obey the doctor rules; a class or function is defined once; `autotester doctor` and `ruff check` pass.

## Verification
Pre-check: fe0f5be9 uv run pytest -p no:xdist <brief section 6 set> tests/test_ui_runs_queue.py tests/test_expand_cli.py tests/test_execute_serial_evidence_scope.py tests/test_pinned_regression.py -> 239 passed, 1 warning in 69.73s t=76 (no full suite, no directory run; ruff clean, doctor clean, uv lock --check clean on fe0f5be9)
Pre-check[LL1]: fe0f5be9 uv run pytest -p no:xdist tests/test_provider_factory.py -k "parse_spec or round_trippable" -> 14 passed, 17 deselected t=5
Pre-check[LL2]: fe0f5be9 uv run pytest -p no:xdist tests/test_provider_factory.py -k "ll2 or neither_route or asks_the_factory or malformed" -> 10 passed, 21 deselected t=5 (the three-way TestClient test, the AST no-construction test, the factory-called tests)
Pre-check[LL3]: fe0f5be9 uv run pytest -p no:xdist tests/test_litellm_provider.py -> 16 passed in 0.54s t=6 (schema, tool, json+one repair, garbage JSON, mismatch)
Pre-check[LL4]: fe0f5be9 uv run pytest -p no:xdist tests/test_litellm_provider.py -> 16 passed (same run as LL3; `test_see_video_is_unsupported`); vision stays with gemini by registry, not touched
Pre-check[LL5]: fe0f5be9 uv run pytest -p no:xdist tests/test_litellm_guard.py -> 21 passed in 31.21s t=37 (stage guard through `grade()`, provider guard direct, repair call, undeclared `.env` value, exported key)
Pre-check[LL6]: fe0f5be9 uv run pytest -p no:xdist tests/test_litellm_provider.py -> 16 passed (same run; `test_one_physical_call_zero_retries_and_usage_recorded`, repair-counts test)
Pre-check[LL7]: fe0f5be9 uv run pytest -p no:xdist tests/test_litellm_provider.py -> 16 passed (same run; usage and trace span with `provider == label`)
Pre-check[LL8]: fe0f5be9 uv run pytest -p no:xdist tests/test_litellm_guard.py -> 21 passed (same run as LL5; kwargs from env, `os.environ` unchanged, canary key and endpoint through every error path, AT-790 echo tests)
Pre-check[LL9]: fe0f5be9 uv run pytest -p no:xdist tests/test_litellm_provider.py -> 16 passed (same run; gemini dialect and plain schema tests)
Pre-check[LL10]: fe0f5be9 uv run pytest -p no:xdist tests/test_litellm_guard.py -> 21 passed (same run; subprocess `sys.modules` check, fake callbacks, and the REAL pinned SDK loaded in a subprocess with socket connect disabled: telemetry False, callback lists empty)
Pre-check[LL11]: fe0f5be9 uv run pytest -p no:xdist tests/test_provider_factory.py -k "ll11 or learn_route" -> 4 passed, 27 deselected t=4 (queued run `refused` with model + variable and no browser, CLI one line exit 1, CLI malformed spec, learn route malformed spec); `available()` cases and the run-route 400 are in `test_litellm_guard.py` and the LL2 tests above
Pre-check[LL12]: fe0f5be9 uv run pytest -p no:xdist tests/test_providers.py tests/test_langchain_fallback.py tests/test_ensemble_honesty.py -> 29 passed, 1 warning t=6 (no assertion edited; `no_network` is applied to all three new test files)
Pre-check[LL13]: fe0f5be9 uv lock --check -> Resolved 118 packages in 2ms (no change); `test_litellm_is_pinned_to_one_exact_version_in_pyproject` is in the LL3 run
Pre-check[LL14]: fe0f5be9 uv run ruff check src tests scripts -> All checks passed!; uv run autotester doctor -> doctor: clean

## Falsification (each in a throwaway copy of the committed tree under the session scratchpad, since deleted; the bound tree was never touched; runner `fals.py`, output below)
- LL1 parse_spec drops the model: 14 passed -> 3 failed.
- LL2 server-model step disabled (`if False and ...`): 3 passed -> 1 failed.
- LL3 `model_validate` replaced by `model_construct`: 5 passed -> 3 failed.
- LL4 `see_video` added returning None: 1 passed -> 1 failed.
- LL5 provider guard call deleted from `_complete`: 21 passed -> 4 failed.
- LL6 `num_retries` 0 -> 2: 1 passed -> 1 failed.
- LL7 `record()` neutralised: 1 passed -> 1 failed.
- LL8 provider writes the key into `os.environ`: 1 passed -> 1 failed.
- LL9 Gemini dialect branch disabled: 1 passed -> 1 failed.
- LL10 eager `import litellm` at module top: 1 passed -> 1 failed.
- LL11 route gate `if False` (run route): 6 passed -> 4 failed; CLI gate `if False` (first attempt stayed green, because the provider's own `_require_ready` produced a similar line; the test now also asserts `model call failed` is absent, i.e. refusal before any model call): 3 passed -> 1 failed.
- LL12 socket guard no longer records the attempt in the forget-the-fake test: 1 passed -> 1 failed.
- LL13 pin loosened to `>=`: 1 passed -> 1 failed.
- LL14 40 blank lines pushed into `litellm_provider.py` (>300): doctor clean -> 1 violation.

## Not claimed / held
- LL15 (settings page keys, Models card, "Test this model"): waits on T-204 `settings.manage`. LL16 (`autotester providers --probe`): HUMAN-GATED, not run, no network call was made.
- Owner answers: none missing for LL1-LL14.
- The full suite is the checker's (dependency change trigger).

## PROPOSED-ISSUE (no ids)
- PROPOSED-ISSUE: low, contract: Vertex model names that carry `@` are rejected by LL1's `@` rule; the contract should say whether that is intended.
- PROPOSED-ISSUE: low, contract: LL10 says "`litellm.telemetry` is False", but 1.104.0 has no such attribute; the provider assigns it. Wording may want an amendment.
- PROPOSED-ISSUE: low, `providers/litellm_provider.py::_env_secret_values`: a very short `.env` value is matched floorless and could falsely refuse a prompt on `act()`.
- PROPOSED-ISSUE: low, `providers/__init__.py::get`: the unknown-provider error echoes the id it was given (`parse_spec` does not); `get` is also reached with raw ids from CLI options.
- PROPOSED-ISSUE: low, `ui/routes_runs.py`: `LangChainFallbackProvider` is still the schema default, so with no model configured the UI is unchanged; the "guess a model from whichever key is present" question stays open (contract: out of scope).
- Issue rows AT-790..AT-796 of the old branch were NOT carried; the checker decides what to re-file.

mutant-cap-raise: the contract has 14 criteria and the brief asks for one falsification per criterion; the 15th is the CLI gate of LL11, whose first mutant stayed green

Metrics: start=2026-10-11 end=2026-10-11 wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=15 cycle=0 resumes=1 tokens=unavailable policy=proportional-verification/2026-10-10.9
