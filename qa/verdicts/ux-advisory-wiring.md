# Verdict - ux-advisory-wiring (AT-794)

**Verdict:** PASS
**Status:** PASS
**Cycle checked:** 0
**Reviewed SHA:** 12e6cb9b3dc0a2b855b68bbd147f9f29ad7bca15
**Base SHA:** 5e76ae2238707161fa33f5ae379a11a281a951d3
**Reviewer:** independent checker (Sonnet 5.5), fresh context

## Diff identity
`git diff base..HEAD` touches 5 files: `stages/ux_wiring.py` (new, 29 lines), `stages/run_launcher.py` (+1 import, +1 call, docstring condensed; still 300 lines), `tests/test_ux_advisory_wiring.py`, `docs/MAP.md`, the manifest. Working tree clean at the reviewed SHA.

## Probe results (independently produced)
1. Non-fatal. `advise_after_run` catches `Exception`. A real-stage probe (`.work/ck/test_probe_ux.py`, real `run_ux_advisory` + `launch_run`, fake `Provider` subclass) with RuntimeError, OSError, TimeoutError, KeyError: run saved and equal to `store.load_run`, no `ux_report.json`, no raise. ValueError maps to a `withheld` outcome inside the stage. `KeyboardInterrupt` (BaseException) propagates, which is correct. `run_ux_advisory` only reads `Run`/results/verdicts and writes `ux_report.json`; byte snapshot of run dir showed no other file changed. The returned `Run` is created before the call and never passed to it.
2. Secrets/boundaries (read in `ux_advisory.py`). `judge_case_ux`: `build_ux_prompt` uses `load_skill_prompt("ux_judge")` (file, FileNotFoundError on missing), then `secrets.guard_prompt` then `mask_pii`, then `provider.judge` (Provider seam, `prompt_file=ux_judge`). ValueError from the guard fires before the call, case recorded `withheld`. Pre-existing T-190 tests for PU6/PU8 pass.
3. Budget/latency. Cap is `ux_policy.max_calls` (schema le=100, default 20, opt-in off by default). The pass is synchronous in the run slot and has NO pass-level wall-clock bound: the hang probe (3 s sleeping provider) blocked `launch_run` for 3.8 s. Production providers do bound each call (litellm 120 s; gemini <=120 s; model_chain attempt_budget 240 s x tiers), so worst case is finite (max_calls x per-call bound, up to hours only if every call hangs) and not unbounded. Non-blocking finding F1.
4. Seam. `launch_run` is called by `run_service.py:104` (CLI/MCP service) and `ui/routes_runs.py:116` (queue entry, which Run button/scheduler/CI feed). No other caller invokes `run_ux_advisory`, so no double invocation. Finding F2: the orchestrate pipeline REPORT stage (`orchestrate_downstream.py::make_report_stage`) saves runs via `save_tracked_run` directly and never runs the advisory; the manifest claim "none found" is inaccurate. Out of AT-794's stated `launch_run` scope; not a regression.
5. Real-stage probe described in 1 and 3; raising providers exercised through the real stage, not a stubbed `run_ux_advisory`.
6. Downstream. `test_the_pass_output_appears_in_the_exports` plus `test_user_persona_report.py` read the produced `ux_report.json` through `load_ux_state`, `ux_findings_html`, `add_ux_sheet` and the `export_html`/`export_excel` paths: pass. Exports are generated on demand from disk, after the run, so ordering is fine.

## Commands (outputs in .work/ck/, all exit 0)
- preflight (review_budget.py): PREFLIGHT_OK, import origin = this worktree, Python 3.11.16.
- `pytest` tests/test_ux_advisory_wiring.py test_user_persona.py test_user_persona_report.py test_run_launcher.py test_run_launcher_approval.py test_run_launcher_priorities_approval.py test_report_export.py test_report_export_secrets.py test_report_export_reason.py: 85 passed, 1 skipped (pytest.txt).
- ruff on ux_wiring.py, run_launcher.py, the new test: All checks passed (ruff.txt).
- doctor (candidate, `autotester.cli:app doctor`): "doctor: clean", exit 0 (doctor_cand.txt). Base doctor not re-run (candidate clean).
- Throwaway probe: 8 passed (probe.txt). Probe used a dummy AUTOTESTER_APPROVAL_KEY.

## Not done / limits
Full suite not run (post-merge gate). No sabotage/mutation of the new call (the failure test and the probe cover the swallow path). Maker usage unknown: BOOTSTRAP_REVIEW plus standing escalation; ratio unverified; checker tokens unknown (null). Active time exceeded the 180 s bootstrap scope plus 300 s escalation allowance is NOT claimed met: wall time was roughly 10-12 min including two ~50 s test runs under CPU contention; recorded as an overrun, not waived.

## Findings (non-blocking)
- F1: no pass-level timeout; a project that opts in holds its run slot for up to max_calls provider calls. Recommend a follow-up wall-clock cap in `ux_wiring.py` or the stage.
- F2: orchestrate pipeline path produces runs without the advisory; correct the manifest note or open a follow-up.
- F3: advisory provider usage accrues on the shared judge after the run is saved; verify cost reporting if it is read from the `Run` after launch.
