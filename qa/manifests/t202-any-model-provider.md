# Manifest — t202-any-model-provider (LiteLLM any-model Provider, re-land on master, D-071)

## Status: checked-PASS

**Contract:** qa/contracts/providers-litellm.md LL1-LL14 (LL15 settings page and LL16 real-provider smoke are NOT built and NOT claimed; LL15 waits on T-204, LL16 is HUMAN-GATED)
**Goal task:** T-202
**Date:** 2026-10-11
**Fix cycle:** 0
Branch: wave/t202-any-model-provider · Base: master 3d8f7d5a (integrated, see below) · Source: wave/t202-litellm code commits 769358e5 + c27133d8 (never PASSed; qa-only commits and its issue rows not carried; the branch and `codex/t202-completion` are untouched)
Product commit under check: 8e66190b (fe0f5be9, then the integration merges 8a9bafaa and 41aff5a5, then a one-line test registry swap; this manifest is the only later change)
Integrated master: db77d7bf (merge commit 41aff5a5; an earlier merge of 7201a820 is 8a9bafaa). Master brought T-153, T-167 (the `release` command) and T-154. Conflict: `uv.lock` only (took master's lock, ran `uv lock`: litellm==1.104.0 and its closure re-added, 123 packages, additions only, `uv lock --check` clean). `cli.py` auto-merged to 304 lines, so expand's provider resolution moved into the existing `cli_orchestrate.py::usable_provider` (cli.py is 295, cli_orchestrate.py 276); `tests/test_cli_advice_resolves.py::EXPECTED_SITES` swaps `("cli.py", "providers")` for `("cli_orchestrate.py", "providers")` because the advice text moved (no assertion weakened). `qa/issues.jsonl` is identical to master's. `pyproject.toml` merged automatically (litellm pin kept).
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
- `cli.py::expand_cases` calls `cli_orchestrate.usable_provider` (LL11, not on the old branch): `--provider` takes `litellm:<model>` (`parse_spec`), a bad spec or an unavailable provider exits 1 with the one-line reason before any model call.
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
Pre-check: 8e66190b uv run pytest -p no:xdist <brief section 6 set> tests/test_ui_runs_queue.py tests/test_expand_cli.py tests/test_execute_serial_evidence_scope.py tests/test_pinned_regression.py -> 319 passed, 1 warning in 83.01s t=89 (adds tests/test_cli_advice_resolves.py, test_cli_surface.py, test_cli_harness_safety.py; no full suite, no directory run; ruff clean, doctor clean, uv lock --check clean on fe0f5be9)
Pre-check[LL1]: 8e66190b uv run pytest -p no:xdist tests/test_provider_factory.py -k "parse_spec or round_trippable" -> 14 passed, 17 deselected t=5
Pre-check[LL2]: 8e66190b uv run pytest -p no:xdist tests/test_provider_factory.py -k "ll2 or neither_route or asks_the_factory or malformed" -> 10 passed, 21 deselected t=5 (the three-way TestClient test, the AST no-construction test, the factory-called tests)
Pre-check[LL3]: 8e66190b uv run pytest -p no:xdist tests/test_litellm_provider.py -> 16 passed in 0.36s t=4 (schema, tool, json+one repair, garbage JSON, mismatch)
Pre-check[LL4]: 8e66190b uv run pytest -p no:xdist tests/test_litellm_provider.py -> 16 passed (same run as LL3; `test_see_video_is_unsupported`); vision stays with gemini by registry, not touched
Pre-check[LL5]: 8e66190b uv run pytest -p no:xdist tests/test_litellm_guard.py -> 21 passed in 25.58s t=31 (stage guard through `grade()`, provider guard direct, repair call, undeclared `.env` value, exported key)
Pre-check[LL6]: 8e66190b uv run pytest -p no:xdist tests/test_litellm_provider.py -> 16 passed (same run; `test_one_physical_call_zero_retries_and_usage_recorded`, repair-counts test)
Pre-check[LL7]: 8e66190b uv run pytest -p no:xdist tests/test_litellm_provider.py -> 16 passed (same run; usage and trace span with `provider == label`)
Pre-check[LL8]: 8e66190b uv run pytest -p no:xdist tests/test_litellm_guard.py -> 21 passed (same run as LL5; kwargs from env, `os.environ` unchanged, canary key and endpoint through every error path, AT-790 echo tests)
Pre-check[LL9]: 8e66190b uv run pytest -p no:xdist tests/test_litellm_provider.py -> 16 passed (same run; gemini dialect and plain schema tests)
Pre-check[LL10]: 8e66190b uv run pytest -p no:xdist tests/test_litellm_guard.py -> 21 passed (same run; subprocess `sys.modules` check, fake callbacks, and the REAL pinned SDK loaded in a subprocess with socket connect disabled: telemetry False, callback lists empty)
Pre-check[LL11]: 8e66190b uv run pytest -p no:xdist tests/test_provider_factory.py -k "ll11 or learn_route" -> 4 passed, 27 deselected t=4 (queued run `refused` with model + variable and no browser, CLI one line exit 1, CLI malformed spec, learn route malformed spec); `available()` cases and the run-route 400 are in `test_litellm_guard.py` and the LL2 tests above
Pre-check[LL12]: 8e66190b uv run pytest -p no:xdist tests/test_providers.py tests/test_langchain_fallback.py tests/test_ensemble_honesty.py -> 29 passed, 1 warning t=7 (no assertion edited; `no_network` is applied to all three new test files)
Pre-check[LL13]: 8e66190b uv lock --check -> Resolved 123 packages in 2ms (no change; diff against master's lock is additions only, 1555 lines, 0 removed); `test_litellm_is_pinned_to_one_exact_version_in_pyproject` is in the LL3 run
Pre-check[LL14]: 8e66190b uv run ruff check src tests scripts -> All checks passed!; uv run autotester doctor -> doctor: clean

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

## Merge reconcile 2026-10-11
Repair base: 94c569c0
Master merged: a0adcb31 (at792-stale-rc2-test checked-PASS; it contains the t178 merge 1ddbb377 and t155, t197, t198a, t168-r2 qa files). Product commit under check: ae0220cd (merge commit; this section is the only later change). Fix cycle unchanged (0): no criterion failed, nothing was fixed; this only reconciles two PASSed units. The second `git merge master` that was owed once t168 landed is DONE; see "Second master merge" below.

Conflicts and how each was resolved (both sides kept):
- `src/autotester/cli.py::expand_cases`: master took the order flowspec check, then `expand_stage.stage_and_review` (t178 moved the `expand` call's review into it, `--proposals/--approve/--prune`), then `store_.preflight_case_proposals`, then provider, then `expand_stage.expand(spec, model, store=store_)`. Taken from master as is, except the provider step stays t202's `model = cli_orchestrate.usable_provider(provider)` (LL11: bad spec or no credentials = one red line, exit 1, before any model call) in place of master's `providers.get(provider)` + `available()` block; `fg="red"` strings from master. t178's order means `--proposals` no longer needs a credential (its intent); t202's refusal still precedes any model call. cli.py 296 lines (cap 300); cli_orchestrate.py unchanged (276).
- `src/autotester/ui/routes_learn.py::generate_cases`: master's proposal staging (`stage_case_proposals(propose_cases(spec))`, `preflight_case_proposals`, "Case proposals need human review" refusal) first, then t202's `for_role(project, "agent")` + `why_unavailable` refusal, then master's `expand(spec, provider, RepoDocs(), store=store)`. `LangChainFallbackProvider` stays removed (LL2). 300 lines (cap 300).
- `tests/test_cli_advice_resolves.py`: `EXPECTED_SITES` keeps `("cli.py", "expand")` (t178's advice site, still in cli.py) and `("cli_orchestrate.py", "providers")` (t202: the providers advice moved with the refusal); `("cli.py", "providers")` is gone because that site no longer exists in cli.py. `EXPECTED_SITE_COUNT` stays 23 (verified: 32 passed).
- Auto-merged but needing follow-up so the union is green and inside the doctor caps (no assertion weakened or dropped):
  - t178's new `test_generate_stages_pending_without_implicit_happy_approval` and master's `tests/test_ui_runs.py::test_trigger_runs_exact_selected_priority_plus_pinned_once` patched the removed `LangChainFallbackProvider`; retargeted to `for_role`.
  - the t202 route echo test (AT-790/LL8) now meets t178's proposal gate, so it calls `_approve_proposals(store)` first; it moved unchanged otherwise to the new `tests/test_ui_learn_vendor_echo.py` because `tests/test_ui_learn.py` reached 323 lines (cap 300; master 299).
  - `tests/test_ui_runs_serial_resilience.py` was 301 lines after the merge; the one `for_role` patch is back on one line.
- `docs/MAP.md`: auto-merged, regenerated with `autotester map`. `docs/SNAPSHOT.md` regenerated with `autotester snapshot` (doctor flagged it stale after the merge). `pyproject.toml` / `uv.lock` did not conflict; `uv lock --check` clean.

Pre-check[LL1]: 0dd59183 uv --directory <worktree> run pytest -p no:xdist -o addopts= tests/test_provider_factory.py tests/test_litellm_provider.py tests/test_litellm_guard.py tests/test_providers.py tests/test_langchain_fallback.py tests/test_ensemble_honesty.py tests/test_ui_runs.py tests/test_ui_runs_queue.py tests/test_expand_cli.py tests/test_expand.py tests/test_failure_bundle.py tests/test_execute_serial_evidence_scope.py tests/test_pinned_regression.py tests/test_cli_advice_resolves.py tests/test_cli_surface.py tests/test_cli_harness_safety.py tests/test_ui_learn_vendor_echo.py tests/test_ui_learn.py -> 272 passed, 1 warning in 803.37s (one run, cited for every criterion below; `test_provider_factory.py` parse_spec cases)
Pre-check[LL2]: 0dd59183 same 272-passed run -> `test_provider_factory.py` (three-way route test, AST no-construction test, factory-called tests) and `test_ui_runs.py` retargeted trigger test
Pre-check[LL3]: 0dd59183 same 272-passed run -> `test_litellm_provider.py`
Pre-check[LL4]: 0dd59183 same 272-passed run -> `test_litellm_provider.py::test_see_video_is_unsupported`
Pre-check[LL5]: 0dd59183 same 272-passed run -> `test_litellm_guard.py`
Pre-check[LL6]: 0dd59183 same 272-passed run -> `test_litellm_provider.py` one-call and repair-count tests
Pre-check[LL7]: 0dd59183 same 272-passed run -> `test_litellm_provider.py` usage and span test
Pre-check[LL8]: 0dd59183 same 272-passed run -> `test_litellm_guard.py` plus `test_ui_learn_vendor_echo.py` (route echo, AT-790)
Pre-check[LL9]: 0dd59183 same 272-passed run -> `test_litellm_provider.py` gemini dialect tests
Pre-check[LL10]: 0dd59183 same 272-passed run -> `test_litellm_guard.py` subprocess and real-SDK quietness tests
Pre-check[LL11]: 0dd59183 same 272-passed run -> `test_provider_factory.py` ll11 tests, `test_expand_cli.py::test_expand_refuses_when_the_named_provider_has_no_credentials`, `test_ui_learn.py` unavailable-provider test, `test_cli_advice_resolves.py` (EXPECTED_SITE_COUNT 24, real count verified by the test)
Pre-check[LL12]: 0dd59183 same 272-passed run -> `test_providers.py`, `test_langchain_fallback.py`, `test_ensemble_honesty.py` (no assertion edited)
Pre-check[LL13]: 0dd59183 uv --directory <worktree> lock --check -> Resolved 123 packages in 1ms (no change; the exact-pin test is in the 272-passed run)
Pre-check[LL14]: 0dd59183 uv --directory <worktree> run ruff check src tests scripts -> All checks passed!; uv --directory <worktree> run autotester doctor -> doctor: clean (cli.py 295, routes_learn.py 300)

Falsification of the reconciled seam (throwaway copy of ae0220cd outside the worktree under the session scratchpad, run with PYTHONPATH on the copy; copy deleted; the worktree was not touched). Baseline on `test_provider_factory.py test_ui_learn.py test_ui_learn_vendor_echo.py test_expand_cli.py`: 55 passed.
- Mutant A: `cli.py::expand_cases` ignores `--provider` (`model = providers.get("mock")` instead of `cli_orchestrate.usable_provider(provider)`): 2 failed (`test_ll11_the_cli_exits_non_zero_with_the_same_one_line_reason`, `test_expand_refuses_when_the_named_provider_has_no_credentials`), 53 passed.
- Mutant B: `routes_learn.py::generate_cases` ignores the selected provider (`for_role(project, "agent")` replaced by a MockProvider): 4 failed (`test_neither_route_constructs_the_langchain_provider_itself[routes_learn.py]`, `test_generate_cases_asks_the_factory_for_the_agent_of_this_project`, `test_a_malformed_spec_on_the_learn_route_is_a_refusal_page_not_a_500`, `test_generate_creates_real_cases_in_the_projects_cases_file`), 51 passed.
- Restored copy: 55 passed.

## Second master merge 2026-10-11
Master merged: 29d02c4b (t168-damage-control-report merged at fbf82ff5, then SNAPSHOT regeneration 8ad646d3, plus t198a, t200b and at773 qa files). Product commit under check: 0dd59183 (merge commit; this section and the refreshed Pre-check lines are the only later change). Fix cycle unchanged (0): nothing failed, nothing was fixed; this reconciles two PASSed units. Status stays ready-for-check.

Conflicts and how each was resolved:
- `docs/SNAPSHOT.md`: the only textual conflict (generated file). Resolved by regenerating with `autotester snapshot`, never by hand; `docs/MAP.md` auto-merged and `autotester map` produced no further change.
- `src/autotester/cli.py`: auto-merged, no conflict. Master's `release-report` registration and the one-line signature join from t168 sit alongside t202's `cli_orchestrate.usable_provider(provider)` in `expand_cases`. 295 lines, no formatting edit needed; `git diff master -- src/autotester/cli.py` is only the t202 provider-refusal hunk.
- `tests/test_cli_advice_resolves.py`: auto-merged, no conflict. `EXPECTED_SITES` has all master entries (including t168's `cli_release.py` release and release-log and `stages/unified_report.py` release sites) plus t202's `("cli_orchestrate.py", "providers")` swap. `EXPECTED_SITE_COUNT` stays 24, the real count (the test asserts it and passed). No test deleted, skipped, moved or weakened.
- No other file under `src/` conflicted. `ui/routes_learn.py` is 300 lines (unchanged by this merge).

All runs in the Pre-check lines were done with `uv --directory <t202 worktree> run ...` so they act on the worktree, not on master.

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
