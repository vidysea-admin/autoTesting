# Manifest — qa-current-state-reconcile

Status: checked-PASS
Fix cycle: 1
Branch: codex/qa-current-state-reconcile
Implementation base: 4c7a9efd72776c5d467e73fc3098020bc63055fb
Review base: abc4a0ef49406936dd0047b7986b449bf3771ee2 (D-099/D-100 merged without conflicts)
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

## Cycle 1 optimized review packet

D-099/D-100 merged from master; the four record inputs of the original invariant proof have unchanged bytes (git diff 39bbfddf HEAD over those paths empty). `qa/evidence/qa-current-state-reconcile/maker-receipt.json` records SHA256 hashes of those inputs and the three original status-correction verdict files; it explicitly records missing environment/runtime identity, unknown maker timing/tokens, prior failure and limits. Exact full receipt reuse cannot be claimed; independent records proof is still required. No new test run after policy merge.

Budget dispatch input/result are persisted beside the receipt. assess exited 0, BOOTSTRAP_REVIEW, finite 180 active seconds / 6000 tokens including commands; efficiency ratios unverified. Reviewer must re-assess before material phases and preserve all usage/unknowns. If runtime/setup exceeds allocation, checkpoint HOLD/NEEDS_EXTRA_REVIEW instead of inventing metrics or skipping required checks.

Applicable acceptance: core-invariants C7 independent scoped review/D-100, C6 human-editable files, issue-id uniqueness existing doctor rule. No domain shape, product behavior, contracts or enforcement edited by this unit. Exact records expectations remain the preceding Checker instructions. Select the six collected tests in tests/test_issue_ids.py for append refusal, duplicate detection, grandfather handling, migration preservation and real ledger uniqueness. Before pytest, preflight intended Python/import identity and writable temp parent. Then run once with a fresh --basetemp under verified parent and -p no:cacheprovider, only after a code/test slot is released. Parent coordinates temp preflight; no preflight PASS is claimed here. Full integration/release commands stay owed on the combined release SHA.
