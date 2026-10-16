# Verdict - at787-failure-step

**Verdict:** FAIL
**Status:** FAIL
**Cycle checked:** 0
**Reviewed SHA:** 3b36a3e000ec2f0a28c1e0ca76d1dcf15f60aa20 (base 3f081243; branch at787-failure-step, tree clean)

## Scope
AT-787: RawResult.failing_step, execute._run_steps recording, failure_bundle._failing_step order (explicit, recorded, heuristic), BundleManifest.failing_step_source.

## Independent checks (receipts in .work/ev/, gitignored; interpreter main .venv py3.11.16, PYTHONPATH=worktree src, preflight PREFLIGHT_OK)
- pytest test_failing_step_bundle, test_failure_bundle, test_run_failure_artifacts, test_execute, test_execute_serial_evidence_scope, test_agent_loop: 46 passed, rc 0.
- pytest test_execute_assertions, test_schema, test_failure_bundle_escape: 44 passed, rc 0.
- ruff on the 5 changed src/test paths: clean, rc 0. doctor: clean, rc 0. File sizes under 300.
- Own probe (.work/ev/probe.py): old RawResult JSON without failing_step loads (None); extra key still rejected; BundleManifest keeps extra=forbid and new field defaults None, so old bundles load. Both schema changes are backward compatible.
- Purity: failure_bundle._failing_step reads only the RawResult and Case arguments. OK.
- No false failing_step on COMPLETED (tested); NOT_RUN and budget-exceeded-before-steps paths set none.

## Finding that fails the unit (proven)
1. Not the FIRST failure when an assertion fails and a later step raises. Probe: step 2 expectation unmet (visible_text Dashboard, page shows "Invalid credentials"), step 3 click on a missing element. Result: outcome=errored, failing_step=3. Step 2 failed first. Cause: execute.py _run_steps keeps the unmet-assertion order in the local `assertion_failed` but the `except` returns use `failing_step=step.order` and discard it. With two unmet assertions the first is correctly chosen (probe: failing_step=2). Fix direction: in both except returns use `assertion_failed if assertion_failed is not None else step.order`, and add a test for unmet-then-raise. If the intended contract is "terminal error wins", state it in the manifest and docstring and add the test; the checker then re-reviews.

## Non-blocking observations (not failures)
2. Guard refusals (AccountDestroyRefused and NavigationRefused are RuntimeError) and RunBudgetExceeded raised inside a step land in the generic ERRORED branch, so failing_step is that step with failing_step_source "recorded". The bundle labels them only by outcome=errored and the error text, not "blocked". Same as before the unit, but a budget stop before a step is now reported as that step failing. No test covers guard or budget cases.
3. Assertion polling is fine: the unmet check runs once after assert_expected finishes polling, so the step order is the settled one. No test covers it.
4. agent_loop._failing_step_order still uses its own screenshot heuristic and ignores result.failing_step (consumer left as is, one-concept-one-place note).

## Limits
Maker usage unknown; BOOTSTRAP_REVIEW plus standing escalation, ratio unverified. Full suite not run (CPU shared). No mutation runs performed.
