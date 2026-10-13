# Manifest - t177-actuator (T-177 final slice: isolated provider, context-level video mask)

Unit: T-177 remaining slices, on top of wave/t177-slice2 (395e91c9; slice0 browser seam, slice1 actuator core, slice2 SDK backend are all ancestors).
Policy-Version: proportional-verification/2026-10-10.9
Tier: L
Dual check: required
dual-trigger: security src/autotester/providers/isolated.py (killable child process around the model call) and src/autotester/browser/video.py (secret mask on every tab)
Fix cycle: 2
Status: checked-PASS

## Criteria (qa/contracts/agent-fallback.md)
- AF4 hard return: `providers/isolated.py::IsolatedProvider` runs `Provider.act` in a spawned child, kills it at the deadline, raises named `ProviderDeadline` (a `ProviderError`). Authorized by D-089 item 2 (new module). `BrowserUseBackend._drive` binds the provider deadline to the invocation wall clock (`bind_deadline`), and `ProviderChatModel` validates the raw JSON text an isolated provider returns for a dynamic (browser-use) schema.
- AF3 / run-video V3-V4: the slice 0 owed gap is closed: `video.py::_mask_context` installs the mask on the context once per context, so a second tab is masked. The owed-gap test is flipped (`test_a_second_tab_opened_during_a_recorded_case_is_masked`).
- AF1, AF2, AF5, AF6 unchanged from slice 1 and 2 (re-run green).
- Not built (held): `expose_cdp=True` and agent/actuator wiring in `ui/routes_runs.py` (D-075 hold until T-203/T-204); headed Chrome bind check.

## Files
New: `providers/isolated.py` (about 165), `tests/isolated_fake.py`, `tests/test_isolated_provider.py` (7), `tests/test_isolated_backend.py` (2).
Edited: `browser/video.py`, `stages/browser_use_backend.py`, `tests/test_browser_session_cdp.py` (flip), `tests/test_browser_cdp_restart.py` and `tests/test_session_survives_failure.py` (fake context gains `add_init_script`), `docs/DECISIONS.md` (taken verbatim from master so D-089 resolves; merge-clean), `docs/MAP.md`, `docs/SNAPSHOT.md` (regenerated).

## Pre-check (per file, `-p no:cacheprovider -o addopts=`, no full suite)
test_isolated_provider 7, test_isolated_backend 2, test_browser_session_cdp, test_browser_cdp_restart, test_session_survives_failure, test_video_parallel_sweep, test_browser_use_guard 14, test_browser_use_pin_telemetry 12, test_agent_fallback, test_agent_fallback_hardening: all green. One local browser smoke: `tests/test_video_masking_live.py` (2 passed, 1 skipped). ruff clean; `autotester doctor` clean. No falsification runs by the builder.

## Notes
- Merging master into this branch conflicts in `browser/secrets.py`, `browser/session.py`, `uv.lock`, `docs/MAP.md`, `tests/test_browser_navigation_secrets.py` (master reworked teardown and exact-host secrets; the slice 0 seam is not on master yet). Not resolved here; the merge owner must reconcile, taking master's `close()` teardown plus the CDP forget/publish lines.
- Spawn start-up adds roughly 1-3 s per isolated call on this host; the deadline includes it.
- Host caveat from slice 2: pymupdf needs msvcp140/vcruntime140_1 beside it (copied from the Edge folder into the untracked .venv).

## Fix cycle 2 - merge of master (AT-651, T-174, T-179)
- Conflicts: browser/secrets.py (kept master's exact-host `_host_matches`/`_norm_host`, no suffix matching; kept T-177 `bad_scheme`), browser/session.py (T-177 CDP start/close merged with master's guarded teardown and `_sweep_orphan_videos`), tests/test_browser_navigation_secrets.py (both sides' tests kept), uv.lock (master's, then `uv lock`), docs/MAP.md (regenerated).
- D-089 item 2: IsolatedProvider already exists and is bound by BrowserUseBackend._drive; no production code constructs AgentActuator/BrowserUseBackend yet, so there is no production path to wire. Left as is.
- Verified: 454 passed, 1 skipped across 29 related test files; ruff clean; doctor has no violation of ours.
