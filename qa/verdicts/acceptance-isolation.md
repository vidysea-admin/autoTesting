# Independent verdict — acceptance-isolation

**Verdict:** HOLD
**Cycle checked:** 1
**Reviewed SHA:** 7cda16f66dc96514edb3776efd32af64ca5e1791
**Base SHA:** abc4a0ef49406936dd0047b7986b449bf3771ee2
**Scope:** bounded acceptance-driver repair; no real T-169/T-206 acceptance or release certification.

Changed logic and immediate consumers were independently inspected: ordinary login and HTTPS Origin/cookies, centralized project view/edit/run/report authorization before yielding, root binding, vision-role selection, and source/prior-truth contamination refusal. No source guard was weakened. Final clean-tree identity and manifest ready-for-check cycle 1 were rechecked before this verdict. All four runtime/test hashes match qa/evidence/acceptance-isolation/identity.json.

Independent evidence under C:/Users/product/Desktop/autoTesting/.work/checker-acceptance/:
- preflight-elevated.json: Python 3.11.16, intended venv, import contained in reviewed worktree src, existing writable temp parent.
- baseline-elevated.log: exact candidate command `python -m pytest tests/test_acceptance_isolation.py tests/test_generic_acceptance.py::test_both_modes_end_to_end_without_cli tests/test_real_acceptance.py::test_ui_run_trigger_refuses_production_without_approval tests/test_real_acceptance.py::test_script_verifies_with_the_key_only_in_dotenv -p no:cacheprovider --basetemp <scratch>/elevated-temp`; exit 0, 12 passed, 1 deprecation warning, 12.76s pytest duration. Covers authentication, both cookie modes, credential rejection, permission rejection, baseline refusal, root/config selection, generic caller and production approval refusal.
- probe.py, mutation.json, mutation-baseline.log, mutation-result.log: scratch source copy excludes __pycache__; asserted green named permission test baseline (exit0, command10.5s); exact-once removal of PROJECT_RUN from required permissions verified changed bytes; named defender fails (exit1, command8.672s); original scratch bytes restored and asserted. Bound source never mutated.
- Initial sandbox pytest attempt failed with temp PermissionError and is not evidence of behavior; elevated retry succeeded. First scratch mutation baseline failed collection due omitted tests_mutation_fixtures; no kill claimed. Fixture dependencies copied and baseline rerun green. Parent authorized normal filesystem permission retries.

## Remaining evidence requirement

C7 / adapter verify.unit_policy.evidence_reuse requires immutable source and environment identity for reused proof. Seven historical maker mutation results in result.txt lack matching runtime/test source and environment fingerprints for that run. The final identity.json binds current files, but does not retroactively bind the earlier result.txt. The packet explicitly discloses this gap. Historical mutation specs and named failures were inspected, but are not accepted as exact-bound proof. Independent run-permission mutation above replaces one representative claim only. Remaining historical guard proofs require provenance reconciliation or bounded reruns before PASS. This is missing evidence, not a demonstrated runtime defect.

Configured vision selection is verified at the caller seam only: this candidate's provider factory still rejects vision, as the manifest discloses. Real teaching acceptance depends on the separate provider lane and combined checks. No live model, browser, network, credentials or production run occurred.

## Accounting and limits

No child reviewers. Actual total active time, tokens and money are unavailable (null); no measured efficiency success claimed. Initial allocation180s/6000 tokens; bounded parent escalation adds90s/1500, cumulative270s/7500, preserving prior allocation debit and null actuals. Gate/evidence: root .work/checker-dispatch/acceptance-extension.json and -assess.json (BOOTSTRAP_REVIEW, escalated=true, ratios unverified). Root .work/checker-acceptance/phase-final-assess.json records earlier NEEDS_EXTRA_REVIEW checkpoint. Initial helper invocation used a missing relative input; corrected absolute dispatch input succeeded. Helper changed during this review; extension uses the current parent-validated helper. Command durations above are measured independently; complete launch/active/wait telemetry remains unavailable, never invented.

Full pytest, Ruff and doctor on the combined immutable integration/release candidate remain mandatory and parent-owned. HOLD does not close the manifest, authorize push/merge, or certify real acceptance.
