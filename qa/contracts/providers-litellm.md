# Contract — providers-litellm: any-model provider behind `providers.base.Provider` (T-202)

**Covers:** goal task T-202. **Owner:** /checker. **Status:** ACTIVE (2026-10-07). **Criticality:** HIGH — tier L (new third-party code
in the outbound-prompt path; dependency bump).
**Serves:** D-071 (4) "any AI API, chosen by config"; D-072 item 2 (new modules authorized); spec R10 (independent judge) and R16
(credential boundary) must not regress; intent O7.
**Depends on:** `core-invariants.md` C5, `browser-and-secrets.md`, `grade.md`, `langchain-fallback.md` (unchanged), `auth.md` AU21
(settings page display rule).

## Purpose

A project, or the whole server, switches its agent and judge model to Gemini, Claude, an OpenAI model, a local Ollama model or any
OpenAI-compatible endpoint **by configuration alone**, with no code change. One new provider, `litellm`, implements the existing
`Provider` seam; one factory resolves a role to a provider, and the website uses it instead of constructing `LangChainFallbackProvider()`
itself.

## Resolution rule (one factory, stated so it can be tested)

`providers.for_role(project, role)` (in the existing registry module; no second registry) returns a `Provider` by this order:

1. The project's spec for that role (`ProviderConfig.for_role`) when it differs from the schema default.
2. Otherwise, the server-wide default model `AUTOTESTER_MODEL` (an environment or `.env` value such as `gemini/gemini-3.6-flash`,
   `ollama/llama3.2`, `anthropic/claude-sonnet-5`, `openai/gpt-4o`), as `litellm:<model>`.
3. Otherwise the schema default (`langchain-fallback`), unchanged.

A spec is `<provider_id>[:<model>]` (for example `litellm:ollama/llama3.2`); bare ids (`gemini`, `langchain-fallback`, `mock`) parse as
before. So **the UI default becomes LiteLLM as soon as a model is configured** (project or server), and an unconfigured install keeps its
current behaviour. Whether an unconfigured install should instead guess a LiteLLM model from whichever API key is present is *not*
decided here; it is out of scope (see below).

## Criteria

- **LL1 — The spec grammar.** `parse_spec("litellm:openai/gpt-4o") == ("litellm", {"model": "openai/gpt-4o"})`; bare ids and the comma-list
  `vision` value parse exactly as before; `providers.get("litellm", model="ollama/llama3.2").label == "litellm:ollama/llama3.2"`; an empty
  model after the colon, a spec containing `@`, `://`, or whitespace-embedded credentials, or an unknown provider id raises
  `ProviderError` whose message does not echo the rejected value. `serves:` D-071#4. *Re-derive:* unit test; mutation: drop the model in
  the parser -> fails.
- **LL2 — One factory; the hardcoded construction is gone.** `ui/routes_runs.py::trigger_run` (the `judge = LangChainFallbackProvider()`
  line) and `ui/routes_learn.py` (the `provider = LangChainFallbackProvider()` line) obtain their provider from `providers.for_role`;
  `grep -rn "LangChainFallbackProvider()" src/autotester/ui` returns nothing; the `judge: LangChainFallbackProvider` annotations in
  `ui/routes_runs.py` and `ui/run_execution.py` become `Provider`. With a project `judge` of `litellm:<m>` the route builds the `litellm`
  provider with model `<m>` (recording-registry test through `TestClient`); with `AUTOTESTER_MODEL` set and the project at the schema
  default, it builds `litellm` with that model; with neither, it builds `langchain-fallback` as today. `serves:` D-071#4.
  *Re-derive:* the three-way test; the grep.
- **LL3 — Structured output returns a validated model, or a typed error.** `judge()` and `act()` return the validated Pydantic instance
  for each strategy: provider-native JSON-schema (`response_format`) when the model supports it, a single forced tool call when it supports
  function calling, else JSON-mode with exactly one repair retry. Each is exercised against a fake `litellm` module. An unparsable or
  schema-violating answer raises `ProviderError` naming the model and role and never returns a partial or coerced object; the message does
  not contain the prompt or the model's raw text beyond a short bounded excerpt run through `Redactor.scrub`. `serves:` D-071#4.
  *Re-derive:* three strategy tests, a garbage-JSON test, and a mutation that skips `model_validate` -> fails.
- **LL4 — Roles.** `see_video` raises `Unsupported`; the vision role stays with `gemini` (`autotester providers` still lists it as the
  vision provider); "any model" in this contract means any agent or judge model. `serves:` D-071#4.
- **LL5 — The secret guard runs before every call, inside the provider.** Immediately before each physical `litellm.completion` call,
  the provider passes every text part of the request through `core.redact.assert_no_raw_secrets` against the values of the repo-root
  `.env` (the set C5 masks, declared or not, plus provider-key values from the process environment). A hit raises before the network
  call (the fake is never invoked) and the error names no value. This is **in addition to** the stage-level `SecretStore.guard_prompt`
  call in `stages/grade.py`, which stays exactly where it is: neither replaces the other. `serves:` O7, spec R16, C5.
  *Re-derive:* two tests: through `stages.grade.grade` (stage guard fires first) and calling `provider.judge` directly with a prompt
  holding a declared secret and an undeclared `.env` value (provider guard fires); mutation: delete the provider-level call -> the second
  fails; delete the stage call -> the first fails.
- **LL6 — No hidden retries, and the call count is true.** Each successful `judge()` makes exactly one physical `litellm.completion`
  call; the single repair retry (LL3) is a second counted call; `num_retries` is 0 on every call and no litellm `fallbacks`/Router is
  configured (fallback is `langchain-fallback`'s job, one concept one place). `serves:` D-071#4, `RunBudget` accounting.
  *Re-derive:* the fake records `call_count` and kwargs.
- **LL7 — Usage and trace.** `record()` is called once per physical call with the response's prompt and completion tokens; the usage row
  and the trace span carry `provider == label`. `serves:` R19 (`run-trace.md`).
- **LL8 — Endpoint and key handling.** `api_base` and `api_key` come only from explicit kwargs built from `LITELLM_API_BASE` /
  `LITELLM_API_KEY` (or `OLLAMA_BASE_URL` for `ollama/` models); the provider never writes `os.environ`; vendor-native keys
  (`GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) are used by litellm as usual. `project.json` cannot carry a key (schema
  `extra="forbid"` plus LL1's rejection). Neither a key nor an `api_base` value appears in any `ProviderError`, log line or trace span.
  `serves:` O7. *Re-derive:* the test sets env, asserts kwargs and an unchanged `os.environ`; canary key through an error path.
- **LL9 — Gemini schema dialect.** For `gemini/` models the schema handed to the fake passes through the existing `gemini_schema()`
  (it contains no `additionalProperties` or `$defs`); the function is imported, not re-implemented. `serves:` AT-230.
- **LL10 — Lazy, quiet, vendor-neutral import.** Importing `autotester.providers` does not import `litellm` (subprocess `sys.modules`
  check); after the provider is constructed, `litellm.telemetry` is False and no success/failure callback list is non-empty. The
  behaviour of the pinned version's telemetry setting is verified against its current documentation before the pin (user rule "verify
  before applying"), noted in the manifest. `serves:` O7.
- **LL11 — Availability and the no-credentials error are graceful.** `available()` is False with no model, or with a model whose
  required key or `api_base` is missing, and True with model + key or model + `api_base`; `autotester providers` agrees with
  `available_ids()`. When the factory resolves a LiteLLM provider that is not available:
  - `trigger_run` and the learn route return the themed refusal page (HTTP 400 for an API client) naming the model and the one variable to
    set, with a link to the settings page, not a 500 and not a traceback;
  - a queued run (`hosting.md` HO16) ends `refused` with the same reason and launches no browser;
  - the CLI exits non-zero with the same one-line message;
  - no message contains a key, a prompt, or an `api_base` userinfo part.
  `serves:` D-071#4. *Re-derive:* each surface with no credentials; mutation: let the exception escape -> the 400/refusal test fails.
- **LL12 — The mock provider remains, and tests never go online.** `providers.get("mock")` and the existing `MockProvider` behave as
  before; `tests/test_providers.py`, `tests/test_langchain_fallback.py` and `tests/test_ensemble_honesty.py` pass **without edits to their
  assertions**. Every new test uses an injected fake `litellm` module (or the mock) and a fixture that makes a real socket connect or a
  real `litellm.completion` raise, so a test that forgets the fake fails loudly instead of calling out. The default suite makes no network
  call. `serves:` D-070. *Re-derive:* run the new test file with sockets blocked; delete the fake from one test -> it fails
  with the guard's error.
- **LL13 — Dependency.** `pyproject.toml` pins `litellm` exactly and `uv.lock` agrees (`uv lock --check`); no other dependency changes in
  this unit. D-071 authorizes `litellm` in T-202 only. `serves:` D-071#4. *Re-derive:* `git diff` on both files.
- **LL14 — Design rules and one concept.** New modules (`providers/litellm_provider.py`, a split `litellm_schema.py` if over 300 lines, and a
  shared image-part helper if added) are authorized by D-072#2 and obey the doctor rules; a class or function is defined once
  (`providers/langchain_fallback.py`, `anthropic.py`, `gemini*.py` are not edited except to import a shared helper); `uv run autotester
  doctor` and `uv run ruff check src tests scripts` pass. `serves:` D-072#2. *Re-derive:* doctor, ruff, `git diff --stat`.
- **LL15 — Settings and project pages.** The settings page's closed key set gains `LITELLM_API_BASE`, `LITELLM_API_KEY` and
  `AUTOTESTER_MODEL`, and follows `auth.md` AU21 (values visible only with `credentials.view`; set/not set otherwise; writing needs
  `settings.manage`). The project edit page gets a "Models" card with the judge / agent / vision strings: an invalid spec is refused with a
  message that does not echo the submitted value (the AT-088 pattern), and a "Test this model" button makes **one** tiny structured call
  with a fixed synthetic prompt (never project data), showing success or the typed error. Needs `project.edit` on that project. Mode D
  browser check plus a **tester** persona walk; the help text names the destination vendor and that screenshots go to it. `serves:`
  D-071#4, D-072#5, spec user type tester.
- **LL16 — Real-provider smoke (HUMAN-GATED; the only criterion allowed to touch the network).** `uv run autotester providers --probe
  litellm:<model>` returns a valid typed answer for **at least two vendor families** (one hosted, for example Gemini or Claude, and one
  local Ollama or OpenAI-compatible), output pasted into `qa/evidence/t202-smoke.md`. It runs only on an approved call, with a synthetic
  prompt: no Pathlynks, student or production data goes to any model through this probe (Vidysea data-boundary rule). Until it runs, T-202
  is PASS-able for LL1-LL15 and its `done_check` stays open. `serves:` D-071#4.

## Out of scope / ignore

- Replacing or retiring `anthropic`, `gemini`, `langchain-fallback` (a later decision entry may supersede one after LL16 shows parity).
- A LiteLLM proxy server, fallback chains or routing inside litellm, vision/video through LiteLLM, cost-budget features of litellm.
- Auto-guessing a LiteLLM model from whichever key happens to be present when nothing is configured (the unconfigured default stays
  `langchain-fallback`; Umesh can ask for a different default as a routine amendment).
- Judge-quality claims for small local models: a PASS from a weak judge is still a PASS, and that honesty question belongs to
  `grade.md`/`bench.md`, not here. The Settings help text says so, but that wording is not a blocker.
- Per-vendor prompt tuning, streaming, function-calling beyond the one forced tool, embeddings.

## No-fire list (must NOT happen)

- No raw secret reaches a model call, an error, a log or a trace (LL5, LL8).
- No hidden litellm retry, callback, telemetry, or process-global export of a vendor key.
- No live network or paid call in the default test suite.
- No change to `grade.py`/`agent_loop.py` signatures, the stage-level `guard_prompt` call, or the existing providers' behaviour.
- No fallback behaviour inside the new provider; no silent swap to another model when the configured one fails.
- No `LangChainFallbackProvider()` constructed in `ui/` after this unit.

## Amendment log (append-only; git history is the version)

- 2026-10-07 · init · contract created for T-202 from D-071 (4) and D-072 (2, 5), folding in the maker's LP1-LP16 proposal
  (`.work/plan-golive/T-202-contract-proposal.md`): LP1 -> LL1, LP2 -> LL2 (with the added server-wide `AUTOTESTER_MODEL` step, so the
  UI default is LiteLLM once a model is configured), LP3 -> LL3, LP4 -> LL4, LP5 -> LL6, LP6 -> LL7, LP7 -> LL5 (strengthened: the guard
  also runs inside the provider, as the request asked for "before every call"), LP8 -> LL8, LP9 -> LL9, LP10 -> LL10, LP11 -> LL11 (adds the
  graceful no-credentials error on every surface), LP12 -> LL13, LP13 -> LL14, LP14 -> LL12, LP15 -> LL16, LP16 -> LL15 (gated by
  `auth.md` AU21).
