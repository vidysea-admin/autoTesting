# Verdict - at787-failure-step

**Verdict:** PASS
**Status:** PASS
**Cycle checked:** 1
**Reviewed SHA:** 10d0a95036b58e1e7b5b20e61529d0994fc9788b (base 3f081243; branch at787-failure-step; prior FAIL 6f6d22f6 cycle 0)

## Scope
Cycle 1 fix: `_first` keeps the earlier unmet assertion in both except-returns of `execute._run_steps`; new optional `RawResult.failing_step_cause` (blocked_by_guard | budget_stop) mapped into `BundleManifest.failing_step_source`; 5 new tests.

## Independent checks (receipts in .work/ev1/; main .venv py3.11, PYTHONPATH=worktree src)
- Prior probe rerun: unmet@2 then missing-element raise@3 -> errored, failing_step=2, cause None. Blocker fixed.
- Further probes (probe.txt): unmet@2 then guard refusal@3 -> step 2, cause None; unmet@2 then budget@3 -> step 2, cause None; guard refusal at step 1 (AccountDestroyRefused click, and a real off-site navigate) -> step 1, blocked_by_guard; budget stop raised inside assert_expected (mid-poll) -> step 2, budget_stop; all steps pass then raise at 3 -> step 3, cause None; screenshot error at step 1 -> step 1, cause None.
- Back-compat: RawResult JSON without failing_step and failing_step_cause loads (both None); unknown key rejected; invalid cause value rejected; extra=forbid on RawResult and BundleManifest; BundleManifest new defaults None, so old bundles load.
- pytest (no -q): test_failing_step_bundle, test_failure_bundle, test_failure_bundle_escape, test_run_failure_artifacts, test_execute, test_execute_assertions, test_schema: 89 passed, rc 0.
- ruff check src tests scripts: clean, rc 0. doctor: clean, rc 0. execute.py 282 lines, others under 300.

## Non-blocking
- A brake raised at the post-step budget check on a step that completed is labelled budget_stop for that step; acceptable (it is the step the brake stopped at).
- agent_loop._failing_step_order still has its own heuristic (carried from cycle 0, out of scope).

## Limits
Scoped tests only (CPU shared); full suite not run, remains a post-merge gate. No mutation runs. Maker usage about 100k tokens; checker ratio unverified, tokens not measured.
