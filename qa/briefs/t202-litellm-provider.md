# Brief - t202-litellm-provider (LiteLLM any-model Provider, D-071)

Readiness pass written 2026-10-11 against master `3a16616c`. Self-contained: the builder needs nothing from the dispatching session. Items marked `unknown` are not stated anywhere in the repo.

## 1. Policy and tier

Policy-Version: proportional-verification/2026-10-10.9
Tier: L
Dual check: no
Trigger for L: dependency bump (`pyproject.toml`/`uv.lock`, `litellm` authorized in this unit only, D-071 item 4 / D-072 item 2) and new third-party code in the outbound-prompt path (`qa/contracts/providers-litellm.md` header: tier L). Dual check is `no`: there is no `security|auth|tenancy|prod-write <path:line>` trigger; the secret guard (LL5/LL8) is a single-checker L row, as the prior cycle-0 and cycle-1 verdicts treated it (`qa/verdicts/t202-litellm.md`, single checker).


## 2. Root and base

- Root: `D:/autoTesting`. Base: master `3a16616c`.
- Branch: **continue `wave/t202-litellm`** (tip `46ef6f87`, code `c27133d8`, merge-base with master `a77ed746`, 34 files changed). Reason: its slice is fully built (LL1-LL14), cycle 0 FAIL was fixed in fix cycle 1 (LL8 scrub, AT-790) and the only thing owed is the one full suite by the checker (`qa/verdicts/t202-litellm.md:67-68`, `VERDICT: CONTINUE-NEEDED`, "all slice criteria evidenced except the owed full suite (LL8 now met)").
- Do NOT build a new `wave/t202-*` from scratch and do not take `codex/t202-completion` as the base (D-080: Codex worktrees are inputs only). Create `wave/t202-litellm-reland` from master `3a16616c`, `git cherry-pick`/merge the code commits of `wave/t202-litellm` up to `c27133d8` (not the qa-only commits `7b87b222`, `46ef6f87`), resolve, re-run the section 6 tests, and commit before asking for a check.
- `litellm` stays pinned exactly in `pyproject.toml`; regenerate `uv.lock` with `uv lock` on top of master's lock (do not hand-merge the lock file).

## 3. Acceptance criteria (verbatim from `qa/contracts/providers-litellm.md`)

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

Deferred, not in this unit (header only):
- **LL15 — Settings and project pages.** The settings page's closed key set gains `LITELLM_API_BASE`, `LITELLM_API_KEY` and
- **LL16 — Real-provider smoke (HUMAN-GATED; the only criterion allowed to touch the network).** `uv run autotester providers --probe

LL15 needs the T-204 permission model (`settings.manage`) and stays out of this brief; LL16 is HUMAN-GATED and the only criterion allowed to touch the network. Neither may be claimed.

## 4. What exists and what is missing

- Exists on `wave/t202-litellm` (cycle 0 FAIL, then fix cycle 1): `providers/litellm_provider.py` (266 lines), `providers/litellm_schema.py` (88), `providers/images.py` (26), registry change in `providers/__init__.py` (+73 lines of diff on a 48-line master file), the factory wiring in `ui/routes_runs.py` (24), `ui/routes_learn.py` (13), `ui/run_execution.py` (12), `.env.example` (14), 9 test updates for the new factory, and new `tests/test_litellm_provider.py` (196), `tests/test_litellm_guard.py` (277), `tests/test_provider_factory.py` (213), `tests/litellm_fake.py` (92).
- Verdicts: `qa/verdicts/t202-litellm.r0-1.md` (cycle 0, FAIL: LL8 key/endpoint leak in a failure message) and `qa/verdicts/t202-litellm.md` (cycle 1, CONTINUE-NEEDED; LL8 met, full suite owed). Checkpoint `qa/checkpoints/t202-litellm.md`.
- Missing for a PASS: (a) a rebase onto current master with the `ui/routes_runs.py` conflict resolved; (b) the full suite by the checker; (c) renumbering of ALL seven of the branch's issue rows AT-790..AT-796 (the t203 branch also uses AT-790..AT-793, and master already uses AT-790..AT-823); the next free id is AT-824 at master `3a16616c`; use AT-836..AT-842 (reserved for this unit; land-t203-hosting reserves AT-824..AT-835) and re-check `qa/issues.jsonl` before commit.
- Exact conflict (from `git merge-tree` master vs the branch): `src/autotester/ui/routes_runs.py` only. Master added a `cat = catalog(...)` call and passes `cat` into the run; the branch replaced the hardcoded provider construction in `trigger_run` with `providers.for_role(...)`. Resolution: keep master's `cat` plumbing and apply the factory call in the same place. If `land-t203-hosting` has landed first, the construction has moved into the queued execution call (`ui/run_queue.py` / `run_execution.py`): then put the factory call there and leave `trigger_run` queue-only (LL2 still needs the one construction site). Do not wait for it: build against master, rebase at the end.
- Line-cap risk: `ui/routes_learn.py` is exactly 300 lines on master and the branch adds 13; move the added code into `providers/` or an existing helper so the file stays <= 300 (doctor fails otherwise).

## 5. Files the builder will touch (current line counts on master `3a16616c`)

Existing: `pyproject.toml` (74), `uv.lock` (2435), `.env.example` (38), `docs/MAP.md` (349, regenerated), `src/autotester/providers/__init__.py` (48), `src/autotester/ui/routes_runs.py` (204), `src/autotester/ui/routes_learn.py` (300, AT CAP), `src/autotester/ui/run_execution.py` (195), `tests/test_coverage_wiring.py`, `tests/test_credential_run_approval.py` (287), `tests/test_ui_credential_safety.py`, `tests/test_ui_learn.py` (275), `tests/test_ui_runs.py` (250), `tests/test_ui_runs_live_case_approval.py`, `tests/test_ui_runs_parallel_crash_recovery.py`, `tests/test_ui_runs_parallel_trace.py`, `tests/test_ui_runs_serial_entry_mix_live.py`, `tests/test_ui_runs_serial_entry_order.py`, `tests/test_ui_runs_serial_entry_screenshot_namespace.py`, `tests/test_ui_runs_serial_resilience.py`.
New: `src/autotester/providers/litellm_provider.py`, `src/autotester/providers/litellm_schema.py`, `src/autotester/providers/images.py`, `tests/litellm_fake.py`, `tests/test_litellm_provider.py`, `tests/test_litellm_guard.py`, `tests/test_provider_factory.py`.
Total 27 files. New modules are authorized by D-072 item 2 and `litellm` by D-071 item 4 (`docs/DECISIONS.md` D-071 line 2136, D-072 line 2170).

## 6. Test scope

`uv run pytest tests/test_litellm_provider.py tests/test_litellm_guard.py tests/test_provider_factory.py tests/test_providers.py tests/test_langchain_fallback.py tests/test_provider_record_concurrency.py tests/test_coverage_wiring.py tests/test_credential_run_approval.py tests/test_ui_credential_safety.py tests/test_ui_learn.py tests/test_ui_runs.py tests/test_ui_runs_live_case_approval.py tests/test_ui_runs_parallel_crash_recovery.py tests/test_ui_runs_parallel_trace.py tests/test_ui_runs_serial_entry_mix_live.py tests/test_ui_runs_serial_entry_order.py tests/test_ui_runs_serial_entry_screenshot_namespace.py tests/test_ui_runs_serial_resilience.py`
Plus `uv run ruff check src tests scripts`, `uv run autotester doctor`, `uv lock --check`. If a name is removed or renamed, expand with `git grep` and add the importers' test files (no whole directory). No network: every test uses `tests/litellm_fake.py`.

## 7. Reachable test cases per criterion (happy path first)

| Criterion | Happy path | Then |
|---|---|---|
| LL1 | `parse_spec("litellm:openai/gpt-4o")` returns the pair | malformed specs, empty model, case, whitespace refused |
| LL2 | `for_role("judge", "litellm:...")` returns the LiteLLM provider; the hardcoded construction is gone from `routes_runs.py`/`run_execution.py` | grep test over those files; mock still resolves |
| LL3 | fake returns valid JSON, `judge()` returns the validated model | invalid JSON/missing field gives the typed error, not a raw dict |
| LL4 | `judge()`/`vision` roles work; `see_video` raises `Unsupported` | gemini keeps the video role |
| LL5 | clean prompt passes the guard and reaches the fake | prompt containing a secret value raises before the fake is called (call count 0) |
| LL6 | one `judge()` = one physical call = `call_count` 1 | failure is not retried; count stays true |
| LL7 | `record()` once per call with the fake's usage | no record on failure, trace line shape |
| LL8 | explicit `api_base`/`api_key` flow only from config | a failure message never contains the key or endpoint (cycle-0 regression) |
| LL9 | non-gemini schema passes unchanged | `gemini/` model gets the dialect-clean schema |
| LL10 | `import autotester.providers` does not import litellm | first call imports it quietly |
| LL11 | `available()` true with a key, false without | no-credentials error is the graceful typed one |
| LL12 | `providers.get("mock")` unchanged | tests never go online (socket guard) |
| LL13 | `pyproject.toml` pins `litellm==X` and `uv lock --check` agrees | |
| LL14 | `autotester doctor` clean; files <= 300 | one concept one place |

## 8. Gate answers

- Dependency `litellm`: authorized, `docs/DECISIONS.md` D-071 line 2136 item (4): "`litellm` is authorized in that unit"; new modules: D-072 line 2170 item 2.
- LL16 real-provider smoke: HUMAN-GATED, no `Answered:` line exists (`qa/contracts/providers-litellm.md` LL16). Not in this unit; do not run `autotester providers --probe`.
- No other gate applies. `qa/gates/t136-model-credentials.md:48` is about a different unit.

## 9. UI surface and persona walk

Persona walk: skip (backend only: no screen, route or flow changes; the settings-page display rule LL15 is excluded and waits for T-204).

## 10. Dependencies and conflicts

- Must land first: none (`after: none`, dispatchable now).
- Shared files and the proposed single owner (details in the dispatcher's table):
  - `src/autotester/ui/routes_runs.py`: owner `land-t203-hosting` first; this unit rebases on it and re-applies one factory call.
  - `pyproject.toml` / `uv.lock`: this unit first (it has no `after`); `t204-team-login` (argon2-cffi), `t167`, `t174`, `t179` then run `uv lock` on top, never hand-merge. One lock-file writer at a time.
  - `.env.example`: serialized `land-t203-hosting`, then `t204-team-login`, then this unit (keys only, no values).
  - `ui/routes_learn.py`, `ui/run_execution.py`: this unit owns the factory edit; T-205 (G1 launcher) and T-198 touch them later and rebase on it.
  - `docs/MAP.md`: regenerated by every unit, no owner, never hand-merged.
- Others in the list (T-197, T-198, T-199, T-201, T-205, T-206, T-200, T-204): no file shared with this unit beyond the above.

## 11. Budget and process rules

- Check budget for this tier: L = 45 min. The builder runs NO full suite (the checker owes it); it runs only the test files in section 6, `uv run ruff check src tests scripts` and `uv run autotester doctor` (no CLI `-q` on pytest, AT-503).
- Falsification (mutation) only in a throwaway copy of the tree under `.work/`, never in the bound tree; restore nothing by hand because nothing was changed.
- Kill only PIDs the builder itself started (record them). Never `taskkill`/`Stop-Process` by image name; a host-wide python/uv kill is AT-820.
- No `cd X && cmd`: use `git -C <dir>`, absolute paths or the tool's working directory.
- Design rules (CLAUDE.md, enforced by `autotester doctor`): file <= 300 lines, function <= 50 lines, one-job module docstring, every shape a Pydantic model in `schema/` with `extra="forbid"`, one concept one place, no `*_v2`/`*_new`, scratch and evidence under `.work/`, model calls only through `providers.base.Provider`, prompts are files.
- Credentials: values only in the one repo-root `.env` (gitignored); print key names, never values; never put a value in a test, fixture, log, screenshot or commit.
- The maker never edits `qa/contracts/`. Contract wording problems go verbatim into `qa/feedback-inbox.md`. Only `/checker` passes a unit.
- Commit before the verdict is requested (`qa/gates/commit-before-verdict.md`, C10): the manifest names the exact commit sha; `Status: ready-for-check` with `Fix cycle: N`; the checker answers in `qa/verdicts/<slug>.md` with `Cycle checked: N`.
- Issue ids: renumber any issue row to start after the max AT id on the branch you land on, re-read `qa/issues.jsonl` immediately before the commit (master max was AT-823 at 3a16616c); `qa/issues.jsonl` is `merge=union`, so a duplicate id is not caught by git. The checker owns issue status.
- `docs/MAP.md` is generated: never hand-merge it. After the final rebase run `uv run autotester map`, then `uv run autotester doctor`.
- Push: none by the builder. The checker pushes `origin master` after its PASS (D-007).
- The builder reports with: files changed, the exact commands run with their output lines, any criterion it could not evidence and why. A claim without a re-run is not done.
