# Manifest — qa-current-state-reconcile

Status: ready-for-check
Fix cycle: 0
Branch: codex/qa-current-state-reconcile
Base: 4c7a9efd72776c5d467e73fc3098020bc63055fb
Role: delegated checker-owned records reconciliation; independent fresh verdict still required.

## Purpose and changes

Reconcile narrowly evidenced records before implementing the approved Ollama-first completion goal. No product code, contracts, historical verdicts, feature ledger, goal task statuses or credentials changed.

- Recomputed existing renumber script plan and applied it losslessly to 12 later duplicate rows; new IDs AT-1000 through AT-1011. Mapping stores original line, title, status, date and row SHA256 in qa/evidence/qa-current-state-reconcile/duplicate-id-mapping.json. Historical citations remain unchanged and must be interpreted with that mapping. All paired dates tie, so file order decides. AT-710/AT-745 share titles but divergent statuses/evidence: preserved, not adjudicated as distinct new bugs. Grandfather file only shrinks.
- AT-900/925/956: open to verified from security-trio cycle 1 PASS and merged 084cc7e6. AT-692: open to verified for the tracked exit-preserving wrapper from infra-trio cycle 1 and merge 0cb6c69c. AT-928: open to verified from scrub-escaped cycle 1 PASS, b2e491c4 and object-before-JSON span scrubbing. Verification dates record this reconciliation, not a new product test run. Existing evidence preserved.
- AT-840 image PII, AT-820 weak enforcement tripwire, AT-887 reachability warning, AT-999 summary selection and AT-676 remaining collision-history concerns stay open.
- Nine queue entries marked checked only against task-level verdict commits already ancestral to base. Each adds evidence and explicit scope/deferred production requirements; original implementation briefs remain historical. AT-281 numeric threshold decision wording corrected to recorded owner judgment/completeness design; missing live acceptance stays open.
- Future T-206 manifest/verdict filenames in runbook aligned to goal's t-206-g10-acceptance.md; historical t206-rig names unchanged.

## Verification

Exact-row invariant proof PASS: 1,025 rows/order preserved; 12 ID-only mappings; exactly five status/verification metadata updates; all other fields unchanged. Unique IDs, grandfather only shrank, uncertain rows remain open, seven queue evidence commits are ancestors. `git diff --check` exit 0. Focused `tests/test_issue_ids.py`: exit 1, six setup errors before any test body, PermissionError creating %TEMP%/pytest-of-product; pytest cache also denied. Environmental, not counted as PASS. Fresh checker should use a writable --basetemp and disable cacheprovider when a test slot is free. No full suite run.

## Checker instructions

Independently compare every row to base, allowing only 12 ID fields and the five named rows' status/date/fixed_in/checker_note metadata. Confirm row count/order/evidence unchanged, mapping hashes match base, unique IDs and grandfather shrink. Re-derive cited verdict/merge ancestry and correct partial-scope treatment. Confirm future T-206 path matches goal and no task-level T-206 PASS is claimed.

Full product pytest/ruff/doctor are not run in this records-only unit; final integrated release gates remain owed under the parent goal. No publication authorized by this unit.
