# T-177 — browser-use fallback actuator for unknown screens; revives `run_with_fallback` (AT-253)

Status: ready-for-check
Fix cycle: 0
Policy-Version: proportional-verification/2026-10-07.7
Tier: L (a new dependency, `browser-use`, added; an agent that can click on a product under test)
Dual check: not required (no auth, tenancy or production-write path changed)
Contract: `qa/contracts/agent-fallback.md` AF1-AF6 (DRAFT, goes ACTIVE on first PASS) · `qa/contracts/core-invariants.md` · `qa/gates/at253-agent-fallback-wiring.md` (answered: option A, wire it in)
Source: branch `wave/t177-agent-fallback`, built on `origin/master` 7782df41. Commit 6c74a898 is the dependency line alone (rebase-friendly); commit 18529a7b is the code.

## Criteria (verbatim from the contract)

- **AF1 — The fallback runs only when the deterministic path has no answer.** The browser-use actuator is engaged for a screen with no matching persona/script answer, never for a screen Playwright already handles. AL1 ("never consulted on a clean run") holds and this contract adds no exception to it. Verify: a fixture with one known and one unknown screen and a counting stub for the actuator — known screen: 0 invocations; unknown screen: exactly 1. Sabotage: engage the actuator unconditionally — the known-screen count goes red.
- **AF2 — Its output is typed and refused when malformed.** The actuator returns a Pydantic model (`extra="forbid"`): the action taken, the observed result and the evidence reference. A free-text-only or malformed return is rejected, not passed through. Verify: feed the adapter a malformed actuator result — it raises a typed error and the case outcome is not `PASS`. A well-formed result round-trips through the model.
- **AF3 — It obeys the same guards as every other actuation, and never grades.** An agent-chosen action is subject to: the deny-list (D-016), the same-domain destination check (X7), `write_policy`, and the run's `RunApproval` budget — it consumes a probe like any other. It never produces a verdict (C7); `grade.py` still owns that. Verify: under `write_policy=READ_ONLY`, an agent-chosen write/destructive action is refused and recorded; an agent-chosen off-domain navigation is refused; the run budget is decremented by agent actions. Sabotage: bypass the destination check inside the adapter — the off-domain test goes red on the refusal assertion.
- **AF4 — It is bounded, and exhaustion is never a pass.** A fallback invocation has a maximum number of steps and a wall-clock bound. Exhausting either ends in an explicit unresolved/inconclusive outcome that names the bound — never `PASS`, never silence (O4). `run_with_fallback`'s own bound (AL4, `MAX_ITERATIONS`) is unchanged. Verify: a fixture actuator that never resolves — the invocation stops at the bound, the outcome names it, and it is not `PASS`.
- **AF5 — `run_with_fallback` becomes a production path, driven by a real test.** At least one production call site of `run_with_fallback` exists, and a test drives that path end to end against a fixture page (a corrected step folds back idempotently, AL3). A repair changes a stored script only through the explicit, recorded act `script-replay.md` SR5 requires. Verify: `grep -rn "run_with_fallback" src/` finds a call site outside its own definition and a test that reaches it through that site, not by importing the function directly.
- **AF6 — Model calls go through the Provider seam, and the dependency is this unit's only.** `browser-use` is added to `pyproject.toml` only within this unit (C11), its licence checked (D-041 says MIT) and `check_dependencies_declared` clean. Whatever LLM the actuator uses is reached through `providers.base.Provider` — no direct vendor client outside `providers/`. Verify: the dependency line arrives in this unit's commit; a grep of `src/` for a vendor-client import outside `providers/` returns nothing; the actuator adapter accepts a fake `Provider` and the test uses it.

## What changed (edited in place unless marked new)

- `src/autotester/schema/agent_fallback.py` (new, 75 lines) — `FallbackAction`, `ActuatorResult` (all fields required, `actions` non-empty), `FallbackStatus` (resolved / unresolved / bound_exhausted / refused / malformed / failed; no PASS), `FallbackOutcome`. All `extra="forbid"`.
- `src/autotester/stages/agent_actuator.py` (new) — `ActionGuard` (the `vet` callable): step bound, wall-clock bound, destination check via `browser.session.check_destination` on both a navigate destination and the page an action lands on, `explore_safety.deny_reason` (deny-list and never-click), write kinds and Enter refused under `READ_ONLY`, `RunBudget.check(actions=1)` per action. `FallbackActuator.invoke` never raises; `parse_result` raises `MalformedActuatorResult`; a result reporting an action the guard never saw is refused. `outcome_evidence` renders the end as one DOM-evidence line.
- `src/autotester/stages/browser_use_backend.py` (new) — `ProviderChatModel` (browser-use's chat-model protocol answered by `Provider.act`, with the caller's secret guard applied to every prompt) and `BrowserUseBackend` (vets each planned action in `register_new_step_callback`, before it runs; an unmapped browser-use action is refused; telemetry disabled).
- `src/autotester/prompts/agent_fallback_v1.md` (new) — the task prompt, a file (CLAUDE.md rule).
- `src/autotester/stages/agent_loop.py:75-122` — `run_with_fallback` gains an optional `actuator`; after the fix loop, if still `ERRORED`, it is engaged once and its outcome appended as evidence (the case outcome is never changed by it). A `ProviderError` from `agent.act` now ends the repair loop (recorded in `AgentLoopResult.agent_error`) instead of propagating. `build_fix_prompt` takes a template name.
- `src/autotester/stages/run_case_pipeline.py:56-90` — `fallback_executor` is the production call site; `run_and_grade_case` and `run_and_grade_case_resilient` take optional keyword-only `agent` / `actuator`. With neither (the default) behaviour is unchanged. A replay is never repaired (SR5: it reports `ERRORED`, the stored script is untouched); a repaired live run persists the corrected case through `store.add_case` (content-addressed) and records an `agent repair: ...` evidence line.
- `pyproject.toml` (+1 line, own commit 6c74a898) and `uv.lock` (regenerated; large diff, includes version moves of shared transitive packages). `browser-use` 0.5.9, classifier `License :: OSI Approved :: MIT License`.
- `docs/MAP.md` regenerated by `autotester map`. `tests/test_agent_fallback.py` (273 lines, 31 tests) and `tests/agent_fallback_fake.py` (helper, 51 lines).

## Falsification records

Each ran in a throwaway copy of the worktree (scratch dir, `PYTHONPATH` pointed at the copy), never the bound tree. "Before" is the unedited copy; "after" is the named edit. The copy was discarded, which is the restore. Script: scratchpad `falsify.py` (not committed).

| Criterion | Falsifying edit | Tests before | Tests after |
|---|---|---|---|
| AF1 | engage the actuator unconditionally (and drop the no-failing-step early return) in `agent_loop.py` | 2 passed | 1 failed, 1 passed (known-screen count) |
| AF2 | `parse_result` passes non-dict through and builds with `model_construct` | 9 passed | 9 failed |
| AF3 destination | bypass `check_destination` in `ActionGuard.refusal` (the contract's sabotage) | 11 passed | 2 failed (off-domain navigate, off-domain landing) |
| AF3 deny-list | `deny_reason` result discarded | 11 passed | 2 failed (Delete, Log out) |
| AF3 budget | `RunBudget.check(actions=1)` removed | 11 passed | 1 failed (budget decrement) |
| AF4 | map `BoundExhausted` to `RESOLVED` | 3 passed | 2 failed (step bound, wall clock) |
| AF5 | replace the `run_with_fallback` call in `fallback_executor` with a plain `run_case` | 4 passed | 2 failed (pipeline repair, call-site grep) |
| AF6 guard | drop the secret guard in `ProviderChatModel.ainvoke` | 2 passed | 1 failed |
| AF6 dependency | remove the `browser-use` line from the copy's `pyproject.toml` | 2 passed | 1 failed |

## Commands run, with output

- `git -C D:/autoTesting worktree add D:/autoTesting/.worktrees/t177 -b wave/t177-agent-fallback origin/master` — HEAD at 7782df41.
- `uv lock` then `uv sync` in the worktree: resolved 291 packages; `browser_use` imports, version 0.5.9.
- Red first: `uv run pytest tests/test_agent_fallback.py` before the modules existed: `ModuleNotFoundError: No module named 'autotester.stages.agent_actuator'`.
- `uv run pytest tests/test_agent_fallback.py tests/test_agent_loop.py tests/test_run_case_pipeline.py tests/test_script_replay.py tests/test_prompt_skills.py`: `77 passed in 202.88s` (31 of them new).
- `uv run pytest tests/test_doctor.py tests/test_ledger_checks.py`: `69 passed in 21.01s`.
- `uv run ruff check src tests scripts`: `All checks passed!`
- `uv run autotester doctor`: `doctor: clean` (after `uv run autotester map` regenerated `docs/MAP.md`; before that: file-too-long on the first draft of the test file and a stale MAP, both fixed).
- The full suite was not run (instructed not to).

## Known limits, for the checker to weigh

1. **The live browser-use path is unproven.** The backend imports and its model shim is tested against a `MockProvider`, and `to_actions` is mapped from browser-use 0.5.9's action names, but no real browser-use run was made (no network model, no live product). browser-use drives async Playwright and cannot take the sync `BrowserSession.page`; it attaches over `cdp_url`. `browser/session.py` does not expose a CDP endpoint and is owned by another session, so nothing in the repo constructs `BrowserUseBackend` yet. Production callers pass an `ActuatorBackend` to `run_and_grade_case(..., agent=, actuator=)`; `ui/routes_*.py` (also owned elsewhere) do not pass either, so the UI path is unchanged until that session wires them. This needs an issue: expose a CDP URL from `BrowserSession`, then construct the backend where the run is launched.
2. After a repaired live run completes, `script_replay._record` records a script against the original case id from the locators of the repaired steps. The corrected case is also persisted. Both are idempotent; neither is a replay-time change.
3. The step cap counts actions the guard vetted, while browser-use's own `max_steps` counts agent steps; both bounds are enforced, the smaller wins.
4. `ProviderError` from `agent.act` no longer propagates out of `run_with_fallback` (it ends the repair loop and is recorded). `tests/test_agent_loop.py` still passes unchanged.

## Not touched (owned elsewhere)

`providers/`, `ui/app.py`, `ui/routes_*.py`, `ui/helpers.py`, `core/consent.py`, `stages/explore_consent.py`, `browser/session.py`, `schema/case.py`, `schema/project.py`, `docker/`, `tests/conftest.py`, `core/paths.py`, `core/env.py`, `store/`.

Metrics: start=2026-10-07T09:10Z end=2026-10-07T10:25Z wall_min=75 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=9 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-07.7
