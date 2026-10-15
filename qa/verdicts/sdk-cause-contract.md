# SDK cause contract — independent docs verdict

VERDICT: PASS
Status: PASS
Cycle checked: 1
Reviewed SHA: b665f128f4024ded282832127af5f37b28e05096
Base SHA: 921a4ac5e8c8b8f77b1752bb285c82034ae2db26

Scope: docs-only I9/C5 compatibility clarification, exactly qa/contracts/ingest.md and qa/manifests/sdk-cause-contract.md. No runtime certification.

Independently inspected the complete candidate diff, original I9, C5, D-100/D-101/D-102 and effective docs tier. The complete historical ingest bytes remain the candidate prefix, including original I9. The addendum requires typed ProviderError, explicit MAX_TOKENS/truncation and exclusion from malformed-JSON repair. Safe category attribution or sanitized surrogate is permitted while original secret-bearing vendor cause/context rendering and payload copying are forbidden. ACTIVE polling, bounded timeout, upload-cache miss behavior and fallback privacy/budget boundaries remain explicitly unchanged. Existing D-101/D-102 limits are consistent; no additional fallback eligibility is authorized. No source, test, credential, dependency, enforcement or decision-log path changed. Separate maker feedback is left untouched.

Independent structural probe: baseline addendum accepted; in-memory deletion of the raw-cause prohibition changes bytes and is rejected. This distinguishes the required privacy clause; it is a documentation probe, not proof of Python traceback safety. Candidate git diff --check exits 0. Evidence: qa/evidence/sdk-cause-contract/structural-check.json. No maker runtime receipts reused.

Remaining gates: Gemini SDK runtime boundary probes and all applicable implementation tests belong to gemini-media-guard; combined integration/release still requires pytest, ruff and doctor on its exact candidate. No browser, SDK, build or runtime command ran in this review.

Accounting: bounded bootstrap allocation 60 active seconds/2500 tokens, readiness debit 20/800 plus structural/verdict allocation 40/1700. Helper phase gate BOOTSTRAP_REVIEW; maker and historical reviewer actual active/token/cost unknown; ratios UNVERIFIED. Debits are allocations, not measured usage. Evidence: qa/evidence/sdk-cause-contract/phase2-budget.json and phase2-assess.json. Tool receipts expose command durations; host usage and complete monotonic launch accounting unavailable, so no efficiency-success claim.
