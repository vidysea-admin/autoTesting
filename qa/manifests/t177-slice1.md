# Manifest - t177-slice1 (actuator core, no SDK)

Unit: T-177 slice 1 on top of t177-slice0-browser-seam (f11cc477), master merged. Ported from `wave/t177-followup` @ 205302b4 (files below), minus everything that needs the `browser-use` SDK.
Policy-Version: proportional-verification/2026-10-10.9
Tier: L
Dual check: required
dual-trigger: security src/autotester/stages/agent_actuator.py (ActionGuard, the AF3 refusal logic)
Fix cycle: 0
Status: ready-for-check

## Criteria covered (qa/contracts/agent-fallback.md)
- AF1 fallback only when the deterministic path has no answer (run_with_fallback engages the actuator only on ERRORED after the fix loop).
- AF2 typed `ActuatorResult` (extra=forbid), malformed result raises `MalformedActuatorResult`, never PASS.
- AF3 guard layer: deny-list, same-domain destination + landing check, write_policy READ_ONLY (PRESS_KEY allow-list, http/https only from slice 0), RunBudget spend; no verdict (C7). guards.py not touched.
- AF4 step and wall-clock bounds, named non-PASS outcome.
- AF5 production call site `run_case_pipeline.py::fallback_executor` (called by `run_and_grade_case[_resilient](agent=, actuator=)`), repair persisted only via `_record_repair` (SR5), replay never repaired.
- AF6 partial: Provider seam only, vendor-client grep test. The `browser-use` dependency line is NOT here.
- Plan item 1: `run_with_fallback` ProviderError adds one scrubbed DOM evidence line, stays ERRORED, fixed False.

## Files
New: `schema/agent_fallback.py`, `prompts/agent_fallback_v1.md`, `stages/agent_actuator.py` (238), `tests/agent_fallback_fake.py`, `tests/test_agent_fallback.py` (30 tests), `tests/test_agent_fallback_hardening.py` (51).
Edited: `stages/agent_loop.py` (124), `stages/run_case_pipeline.py` (283), `docs/MAP.md`. session.py not touched. No `ui/` wiring (D-075 hold).

## Pre-check (per file, `-p no:xdist -p no:cacheprovider -o addopts=`)
test_agent_fallback 30 passed; test_agent_fallback_hardening 51 passed; test_agent_loop 4; test_run_case_pipeline 11; test_script_replay 15. ruff check src tests scripts clean; autotester doctor clean. No full suite. No falsification runs by the builder.

## Remaining slices
- Slice 2: `browser-use==0.5.9` in pyproject/uv.lock (lock writer slot), `stages/browser_use_backend.py` (`_drive`, `ProviderChatModel`, telemetry/dotenv off), per-action SDK guard via Controller subclass with landing check after each action, SDK max_steps exhaustion -> BoundExhausted, AF6 dependency + ProviderChatModel tests, `tests/test_browser_use_pin_telemetry.py`.
- Slice 3: owed second-tab video mask (flip owed-gap test), `expose_cdp=True` and agent/actuator wiring in ui (held until T-203/T-204), headed Chrome bind check.
- Open: T177-HARD-PROVIDER-DEADLINE (sync Provider.act cannot be killed by wall clock). ARCHITECTURE.md lines on "agent fallback unwired" lag; maker owns.
