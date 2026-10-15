# teaching-pdf independent verdict

Status: PASS
Cycle checked: 2
Reviewed candidate: 0f48beaea6abc9c3a0ce9c238c6cf09abe03d118
Base: abc4a0ef
Checker: fresh review_pdf_ocr, provenance-only continuation

Scoped unit PASS: bounded local PDF extraction/registration. This does not close all-source teaching, T-169/T-206, or integration/release acceptance.

Cycle1 HOLD remains in commit1e6d9276 and checker/cycle1-verdict.md. Its two gaps are now closed:21 missing mutation proofs have contemporaneous source/environment/log bindings; parent explicitly authorized cumulative225active-seconds/8000allocated-tokens continuation with45s/2000 additional allocation.

## Independently verified cycle2

The deterministic checker probe exits0:21 proof rows,55 sealed artifact hashes and983 source/test/script/dependency manifest entries match actual bytes. Each mutation has one anchor, actual distinct mutated hash, attributable named test failure, correct per-command mutated-tree binding, and restored source/tree hashes. Baseline and final restored controls each report12passed. Python executable hash, installed dependency versions and OCR binary hashes match context. Raw log hashes match receipts. A deliberately corrupted seal digest is rejected. Probe measured0.344s. Raw checker driver/result: qa/evidence/teaching-pdf/checker/checker-pdf-cycle2.py and .json.

`git diff c1f67d93b9ae1c9cab0c0cdbffdb5adadf68fcee 0f48beaea6abc9c3a0ce9c238c6cf09abe03d118 -- src tests scripts pyproject.toml uv.lock` is empty. Therefore prior independent runtime evidence remains applicable without repeat:62tests passed54.42s, scoped Ruff passed, representative secret-sanitation mutation killed by its named test after green baseline with verified restoration. Actual scanned/mixed pages, errors/unreadable/low confidence, bounds/deadlines, provenance/dedupe and raw/encoded-secret/PII registration boundaries were independently exercised. Exact old commands and limitations are preserved in cycle1 verdict/evidence. No historical unbound maker logs are retroactively authenticated; new contemporaneous proofs supply the missing evidence.

Applicable scope: SA1/2/4/5/6 and SA7 PDF subset; core C1/2/3/5/6/7/8/10/12. Independent code/consumer review and boundary tests remain from cycle1 unchanged bytes.

## Remaining integration obligations

Full pytest/Ruff/doctor on exact combined candidate remains mandatory. Cycle1 doctor exit1 only stale-generated docs/SNAPSHOT.md; dirty generated docs/MAP.md excluded from unit. Neither is certified current here. No fixed child memory quota; English OCR; timed-out supervisor can leave an OCR child bounded by its own deadline, as disclosed by maker. No merge/push/manifest closeout performed.

## Accounting

Parent dispatch metrics .work/checker-dispatch/pdf-provenance.json and -assess.json authorize this finite scope; helper assess passed before material review. Prior actual active_s/tokens/cost remain null plus180s/6000token debit. This continuation adds committed45s/2000tokens: cumulative225s/8000tokens, never represented as actual usage. Probe alone measured0.344s; initial cycle1 monotonic launch/complete active time unavailable. Maker usage null, cost null, efficiency ratios unverified. No children; no tests/mutations/doctor repeated in cycle2.
