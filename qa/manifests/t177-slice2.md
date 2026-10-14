# Manifest - t177-slice2 (browser-use SDK backend)

Unit: T-177 slice 2 on top of t177-slice1 (6addd492), master merged.
Policy-Version: proportional-verification/2026-10-10.9
Tier: L
Dual check: required
dual-trigger: dependency addition (browser-use==0.5.9, D-075) and security src/autotester/stages/browser_use_backend.py (per-action guard)
Fix cycle: 0
Status: superseded
Superseded-by: qa/verdicts/t177-actuator.r2.md (merge a1bab8e8; T-177 done; branch merged)

## Criteria covered (qa/contracts/agent-fallback.md)
- AF6 completed: `browser-use==0.5.9` pinned in pyproject.toml, uv.lock regenerated with `uv lock` (resolves on 3.11; no existing pin changed except transitive markdown-it-py/pytest lock churn); vendor-import grep and import-isolation tests (`browser_use` imported only inside the backend, lazily; importing the product loads no SDK module); telemetry, cloud sync and dotenv forced off.
- AF3 at the SDK seam: `_guarded_controller` subclasses browser-use `Controller`; every `act` is vetted by `ActionGuard` BEFORE dispatch (destination, write policy, READ_ONLY rules, deny-list, budget) and the landing URL is re-checked right AFTER (also after a failed action). Sticky refusal: later acts refuse, and the first refusal is re-raised after the run even if the SDK swallows it. Unmapped actions, unknown element indexes and an absent/closed page fail closed; the guard reads cached page state only (no recovery). guards.py / agent_actuator.py not touched.
- AF4: SDK `max_steps` exhaustion raises named `BoundExhausted`; wall clock via `asyncio.wait_for`.

## Files
New: `stages/browser_use_backend.py` (254), `tests/test_browser_use_guard.py` (14 tests), `tests/test_browser_use_pin_telemetry.py` (12 tests; ported from wave/t177-followup, step-callback landing test replaced by the guard tests).
Edited: `pyproject.toml` (one line), `uv.lock`, `docs/MAP.md`. session.py not touched.

## Pre-check (per file, `-p no:xdist -p no:cacheprovider -o addopts=`)
test_browser_use_guard 14 passed; test_browser_use_pin_telemetry 12 passed; test_agent_fallback and test_agent_fallback_hardening re-run green. ruff clean; autotester doctor clean. No full suite. No falsification runs.

## Notes
- Machine caveat: this host lacks the system VC++ runtime, so `pymupdf` (browser-use -> markdown-pdf) failed to import (`DLL load failed ... _extra`). Local-only workaround: copied msvcp140.dll and vcruntime140_1.dll from System32/Microsoft-Edge-WebView into the untracked .venv pymupdf dir. Checkers on this host need the same, or the VC++ redistributable installed.
- Tests drive the real installed `Controller` subclass with `Controller.act` and the page faked; no real `Agent.multi_act` run and no live browser.
- deepagents untouched (not in the lock).

## Remaining: Slice 3
Owed second-tab video mask, `expose_cdp=True` and agent/actuator wiring in ui (held until T-203/T-204), headed Chrome bind check. Open: T177-HARD-PROVIDER-DEADLINE.
