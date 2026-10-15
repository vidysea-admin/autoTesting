# teaching-pdf independent verdict

Status: HOLD
Cycle checked: 1
Reviewed candidate: c1f67d93b9ae1c9cab0c0cdbffdb5adadf68fcee
Base: abc4a0ef
Checker: fresh review_pdf_ocr

## Evidence independently produced

- Exact SHA/diff, schema, subprocess supervisor/worker, local OCR, source registration and immediate extract consumer reviewed for SA1/2/4/5/6 and SA7 PDF subset; core C1/2/3/5/6/7/8/10/12 considered.
- Verified Python3.11.16 existing root venv and worktree src import containment; writable temp probe passed under standard escalation after one sandbox ACL failure.
- `python -m pytest tests/test_pdf_teaching.py tests/test_source_adapters.py tests/test_schema.py tests/test_core.py --basetemp .work/checker-pdf-01 -p no:cacheprovider`: exit0,62passed,54.42s. PDF13 cover actual scanned/mixed bytes, provenance, unreadable/error/low confidence, resource bounds and sanitation; source11 cover immediate registration/dedupe consumer; foundation38 included C1/C5 Verify commands. This last group was broader than minimum D100 scope; no duplicate run.
- Scoped Ruff on all seven changed Python files: exit0.
- Independent isolated repository mutation harness: sanitation removal baseline green; mutation exit1 with named `test_pdf_registration_scrubs_root_secrets_and_contact_details` failure; unique anchor, changed bytes and restoration asserted by inspected harness. Evidence: checker-pdf-mutation*.log/json and driver.
- Doctor exit1: only stale-generated docs/SNAPSHOT.md; no code-rule violations, citation advisories nonblocking. docs/MAP.md is preexisting uncommitted generated output excluded from unit. SNAPSHOT/MAP refresh and full pytest/Ruff/doctor remain combined integration obligations.

## HOLD reasons

1. Supplied maker22 mutation rows all have expected named failures, but lack an immutable source/environment binding receipt. Committing historical output does not authenticate which source bytes produced it. Twenty-one proofs remain unauthenticated; either supply their original immutable fingerprints/environment receipts or rerun bounded affected proofs. No evidence reuse certified. No demonstrated runtime defect.
2. NEEDS_EXTRA_REVIEW: cumulative committed allocation180s/6000tokens exhausted; helper rejects next30s/1000. Requested finite cumulative300s/9000 escalation not yet received at checkpoint. Required work is not dropped for efficiency.

## Accounting and limits

Actual checker active_s/tokens/currency cost null; initial monotonic launch was not recorded. Conservative budget debit180s/6000tokens represents committed allocation, never measured usage. No efficiency-success claim; maker denominators null, ratios unverified. No checker children. Actual pytest execution54.42s; other command overall active durations unavailable. Initial preflight ACL failure included; selected commands were completed, not repeated. Wait intervals after escalation request are not represented as measured active time. Phase2 input and terminal helper checkpoint preserved. Parent predispatch pdf.json/-assess.json remains external raw evidence.

Unit manifest remains ready-for-check. No merge, push, closeout or integration/release certification.
