# Verdict B (blind dual check, correctness and wiring) — T-177 agent fallback

Unit: `wave/t177-agent-fallback` @ 4e06f18c · Contract `qa/contracts/agent-fallback.md` AF1-AF6 · Policy proportional-verification/2026-10-07.7, tier L
Checker: B (did not read any `*.a.md` or A's evidence; did not run the full suite)

## Check plan (written first)

1. Read every changed product line (agent_actuator, agent_loop, run_case_pipeline, schema, backend, prompt) and the tests; map each AF to code lines.
2. Wiring: is `run_with_fallback` called on the production path (`run_case_pipeline.fallback_executor`) and reachable from a real case run?
3. Provider outage: can the newly caught `ProviderError` turn a failing case into a pass? Probe it through the real pipeline and the resilient pipeline.
4. Design rules: file ≤300 / function ≤50 (doctor), `extra="forbid"`, prompt is a file, product code does not import `tests/agent_fallback_fake.py`.
5. Is a live browser-use backend demanded by any AF criterion?
6. Run affected tests, ruff, doctor. Dependency delta of `uv.lock`.
7. Falsification in a throwaway copy (scratch dir, never the bound tree): 22 mutants, at least one per AF, plus my own probes.

## Verdict: PASS

## Evidence

**AF1** `agent_loop.py` (`run_with_fallback`, after the fix loop): the actuator is reached only when `result.outcome is ERRORED and actuator is not None`; a clean run never reaches a model or the actuator. `test_af1_known_screen...` (0 calls) and `test_af1_unknown_screen...` (exactly 1, after MAX_ITERATIONS fixes, outcome stays ERRORED). My mutant "engage whenever an actuator is given" SURVIVED, see PROPOSED-ISSUE 1: it is masked by the incidental `ValueError` in `_failing_step_order`, not by a test. The maker's own sabotage (which also drops the early return) is killed. Behaviour is correct; the test is thinner than the sabotage clause implies.

**AF2** `schema/agent_fallback.py` `ActuatorResult`: `extra="forbid"`, `actions` min_length=1, `observed`/`evidence_ref` min_length=1, all required. `parse_result` (`agent_actuator.py`) raises `MalformedActuatorResult` for non-dict, None, int, {}, missing field and extra field; 8 parametrized cases assert the typed raise AND `outcome is not COMPLETED`. Round trip tested. Mutants (extra=ignore, min_length dropped) KILLED.

**AF3** `ActionGuard.refusal` (`agent_actuator.py`): destination via `check_destination`, READ_ONLY write kinds and Enter, `deny_reason` (D-016 deny-list and never-click), `budget.check(actions=1)` per action, step and clock bounds, and the `unseen` check in `_finish` refuses reported-but-never-vetted actions. No verdict anywhere (`FallbackStatus` has no PASS; the actuator never sets `result.outcome`). Mutants (write dropped, Enter dropped, navigate-without-url dropped, unseen dropped) KILLED. Probe: a CLICK with an empty target is refused ("unnamed control"). Backend order verified against browser-use 0.5.9 source: `register_new_step_callback` runs in `_handle_post_llm_processing` inside `_get_next_action`, before `_execute_actions`/`multi_act`, so vet-before-act holds; a raise in the callback lands in the step error handler and `agent.stop()` is called first.

**AF4** Step bound (`>=`), wall-clock `deadline`, and a `_finish` post-check; the reason names the bound (`max_steps=3`, `wall_clock_s=25`); `FallbackStatus` has no PASS and the case outcome stays ERRORED, which `grade.py:133` settles as INCONCLUSIVE by rule. Off-by-one mutant KILLED; unresolved-as-resolved KILLED; actuator-promotes-outcome KILLED.

**AF5** `run_case_pipeline.py` `fallback_executor` calls `run_with_fallback`; `run_and_grade_case` and `run_and_grade_case_resilient` both route through it when `agent` is given. `test_af5_pipeline_repairs_through_the_call_site_and_persists_once` goes `run_and_grade_case` -> `run_scripted` -> executor -> `run_with_fallback` against a fixture page and checks idempotent persistence (AL3: 1 stored case after 2 runs). Replay is never repaired (SR5), tested. The grep test is weak alone but the pipeline test reaches the site. Mutants (replay guard dropped, persistence dropped) KILLED.

**AF6** `pyproject.toml` +1 line `browser-use>=0.5.9` (MIT classifier confirmed in installed METADATA); no vendor-client import under `src/` outside `providers/` (grep, empty); `ProviderChatModel` takes a `Provider`, tested with `MockProvider` and the secret guard. `tests/agent_fallback_fake.py` is imported only from tests; no `src/` file imports it (grep). Doctor includes `check_dependencies_declared`: clean.

**Provider outage (focus).** `ProviderError` from `agent.act` breaks the repair loop; the result keeps its ERRORED outcome. Probe through the real pipeline with an agent that always raises `ProviderError`: `run_and_grade_case` -> outcome `errored`, verdict `INCONCLUSIVE`, nothing persisted; `run_and_grade_case_resilient` the same. A provider outage cannot make a failing case pass. No existing test covers this path, see PROPOSED-ISSUE 2 (the mutant "swallow ProviderError and set COMPLETED" SURVIVED, so a regression would go unseen).

**Known gap (no live backend).** `BrowserSession` exposes no CDP URL, so `BrowserUseBackend` is never constructed in `src/`, and no `ui/routes_*` passes `agent=`/`actuator=`. No AF criterion demands a live backend: AF1 requires a counting stub, AF5 a fixture page, AF6 a fake `Provider`. Not a FAIL; recorded as PROPOSED-ISSUE 3. To be explicit: today a real UI or CLI run never reaches `run_with_fallback`; the call site is reachable only from code that passes `agent=`.

**Design rules.** `autotester doctor`: clean (covers file and function length, schema rules); ruff: All checks passed; `extra="forbid"` on all four models; prompt `prompts/agent_fallback_v1.md` is a file; `browser_use_backend.py` 176 lines, `agent_actuator.py` 200.

**Commands run**
- `uv run pytest tests/test_agent_fallback.py tests/test_agent_loop.py tests/test_run_case_pipeline.py tests/test_script_replay.py tests/test_prompt_skills.py` -> `77 passed in 326.07s`
- `uv run ruff check src tests scripts` -> `All checks passed!`
- `uv run autotester doctor` -> `doctor: clean`
- Lock delta (tomllib compare of origin/master vs branch): 209 packages added, none removed; one existing package moved: `markdown-it-py 4.2.0 -> 3.0.0` (held back by `markdown-pdf` via browser-use; the `rich`/`typer` consumers' tests still green).

**Mutation table** (throwaway copy; 22 mutants; unmodified copy 35 passed first)

| # | Mutant | Result |
|---|---|---|
| 0 | actuator engaged when `actuator is not None` (ERRORED check dropped) | SURVIVED |
| 1 | READ_ONLY write refusal dropped | killed |
| 2 | Enter-under-read-only dropped | killed |
| 3 | navigate-without-destination refusal dropped | killed |
| 4 | unseen-action check dropped | killed |
| 5 | pre-invoke `budget.check()` dropped | SURVIVED (redundant with the per-action check) |
| 6 | step bound off by one | killed |
| 7 | final `over_time` check dropped | SURVIVED (redundant with the per-vet check for the stub) |
| 8 | unresolved reported as resolved | killed |
| 9 | `extra="forbid"` -> ignore | killed |
| 10 | `actions` min_length dropped | killed |
| 11 | replay guard dropped | killed |
| 12 | repair not persisted | killed |
| 13 | `_record_repair` early return on not-fixed dropped | SURVIVED |
| 14 | resilient pipeline ignores `agent` | SURVIVED |
| 15 | actuator `resolved` promotes outcome to COMPLETED | killed |
| 16 | ProviderError swallowed and outcome set COMPLETED | SURVIVED |
| 17 | backend: unmapped browser-use action skipped instead of refused | SURVIVED |
| 18 | backend: action recorded without `vet` | SURVIVED |
| 19 | outcome evidence not scrubbed | SURVIVED |
| 20 | `agent_error` not scrubbed | SURVIVED |
| 21 | telemetry-off env dropped | SURVIVED |

Survivors 0, 13, 14, 16-21 are test gaps in code that is correct as read; none shows a PASS-critical behaviour wrong. 5 and 7 are redundant-defence equivalents.

## PROPOSED-ISSUE lines

PROPOSED-ISSUE: [medium] AF1 guard untested in isolation: with the `result.outcome is ERRORED` condition removed in `run_with_fallback`, the known-screen test stays green because `_failing_step_order` raises `ValueError` on a fully-screenshotted clean run. Add a non-ERRORED result with a screenshot-less step and assert 0 actuator calls (contract AF1 sabotage clause).
PROPOSED-ISSUE: [medium] No test for `ProviderError` from `agent.act` in `run_with_fallback` (new behaviour, manifest limit 4). A mutant that sets COMPLETED on ProviderError survives. Add a loop-level test (ERRORED, `agent_error` recorded and scrubbed, `fixed` False) and a pipeline-level one (verdict not PASS). B's probe shows the current code is correct (INCONCLUSIVE).
PROPOSED-ISSUE: [high] Live path unconstructed and UI unwired: `BrowserSession` exposes no CDP URL so `BrowserUseBackend` is never built, and no `ui/routes_*` caller passes `agent=`/`actuator=`, so no real run reaches `run_with_fallback` today (gate `at253-agent-fallback-wiring.md` option A, "every broken case", is not yet true at runtime). Expose a CDP endpoint, wire the run launcher, then one real-browser smoke of `BrowserUseBackend`. Does not fail AF1-AF6 as written.
PROPOSED-ISSUE: [medium] `BrowserUseBackend`/`to_actions`/`_element` have no tests (mutants 17, 18 survive): unmapped action must refuse, vet must precede recording, empty selector_map node, href-based destination. Also X7 "re-checked after every action" is not enforced for a JS-driven click with no `href` (the guard only sees a destination the mapper can derive); consider a post-step page URL check through the callback.
PROPOSED-ISSUE: [low] `_record_repair` early return on `not loop.fixed` and the `run_and_grade_case_resilient` agent wiring have no test (mutants 13, 14 survive).
PROPOSED-ISSUE: [low] Scrub of outcome evidence and `agent_error` has no test (mutants 19, 20); telemetry-off env has no test (21).
PROPOSED-ISSUE: [low] Dependency weight: browser-use adds 209 packages (openai, google-genai, anthropic clients etc. enter the install, though `src/` imports none outside `providers/`) and downgrades the shared `markdown-it-py` 4.2.0 -> 3.0.0. Record it in the decisions log with a rollback note; consider an optional extra.
PROPOSED-ISSUE: [low] AF1's "unknown screen" is approximated as "fix loop exhausted and still ERRORED"; a known screen with a broken locator that 5 agent repairs fail to fix also engages the actuator. Acceptable per AL1 but state it in the contract when it goes ACTIVE.

Cycle checked: 0

Metrics: start=2026-10-07T14:05Z end=2026-10-07T14:40Z wall_min=35 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=22 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-07.7
