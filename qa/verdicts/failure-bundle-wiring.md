# Independent checker — failure-bundle-wiring

VERDICT: PASS
Status: PASS
Cycle checked: 1
Reviewed SHA: 902cbc3f41b6541905886e2d22382c48ec78847d
Base SHA: f5da2cd9d81f530e47a209654e448294c79734c8

Scope: this bounded production bundle/report integration unit only, under D-099/D-100.

Independent readiness verified candidate HEAD, ready-for-check manifest cycle 1, frozen source/test/lock hashes and all twelve v4 green/red/restored receipt identities, exit codes, named failures, environment fingerprints and complete output hashes. See independent-readiness.json. Maker evidence is reused solely for twelve per-guard proofs; its eleven-test success is not substituted for independent tests.

Independent executable checks (compatible Python 3.11.16, candidate src PYTHONPATH, bytecode disabled):
- Four exact nodes in tests/test_run_failure_artifacts.py: launcher_bundles_sanitized_copies_and_reports; bundle_exception_preserves_functional_records; containment_and_uncertain_images_are_explicit; report_lookup_rejects_partial_corrupt_and_wrong_lineage (all prefixed test_). Result: 4 passed, one existing deprecation warning. independent-focused.log.
- Isolated representative mutation disables the index.run_id guard: same report-lookup node green, named assertion failure when red, restored green. independent-mutation-green.log, independent-mutation-red-valid.log, independent-mutation-restored.log and independent-runtime.json.
- Scoped Ruff for four changed source files and focused test: exit 0; source caps/function/name/duplicate checks: exit 0. independent-ruff.log and independent-structure.log.

Coverage: FB1/FB2/FB3/FB6, B11, RE1/RE5 and applicable C1-C8/C10/C12. Reviewed schema inheritance/extra forbid; launcher post-durable-save integration; image containment before sanitation, temporary-copy lifetime and explicit withholding; writer run/case isolation and atomic loader reuse; fixed value-free fault recovery; nested index exclusion from ProjectStore flat result discovery; HTML/Excel validated relative links and corrupt/partial/wrong-lineage refusal. Immediate consumer code inspected, including actual ProjectStore result glob and writer lineage checks. No acceptance violation found.

Limits: four focused integration tests use substituted execution and OCR output; actual sanitation, bundle storage/loading and export execute. No browser, provider or live-account activity. FB4/FB5, CLI/UX and full combined integration remain outside this unit. Full combined pytest/Ruff/doctor, generated MAP/SNAPSHOT remain mandatory before release. This verdict does not claim full doctor or release readiness.

Accounting: maker active time/tokens/cost null; ratio success unverified. Initial readiness actual usage unknown, charged 45s/1500 tokens. Runtime measured 148.094s against 135s allocation (13.094s overrun), charged 4500 tokens with actual tokens/cost null. Parent explicitly authorized finite extra 90s/2000 tokens, cumulative 270s/8000 tokens. Corrected close-phase assessment passed with next phase 75s after prior overrun. Failed preflight due inherited temp ACL and isolated mutation collection error (missing scripts/regression_proof.py) retained; repaired through normal escalation and isolated harness copy respectively. Failed close-phase assessor schema attempt retained and corrected before close work. No successful tests repeated after extra allocation. Final timing ledger records actual close duration, with tokens/cost unknown.

ISSUES-WRITTEN: none
