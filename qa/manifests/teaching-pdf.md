# Manifest — bounded local PDF teaching extraction

- Status: ready-for-check
- Fix cycle: 2
- Base: abc4a0ef
- Candidate: exact SHA supplied by the parent checker packet after scoped commit
- Authorization: user-approved Ollama-first completion plan; D-099; SA7.
- Contracts: source-adapters SA1–SA7 (PDF subset); core-invariants C1–C8, C10, C12;
  D-100 risk-tier unit policy. This unit does not close all of SA7 or T-169/T-206.
- Tier: high_risk (local untrusted input, schema and secret sanitation).

## What changed

- `schema/document.py`: typed page receipts and bounded extraction configuration.
- `sources/pdf_extract.py`: isolated-parser supervisor. New module isolates process ownership.
- `sources/pdf_worker.py`: page extraction and explicit partial/error evidence. New module is
  the subprocess entrypoint, keeping untrusted parsing out of the web worker.
- `sources/pdf_ocr.py`: bounded local rendering/OCR and confidence receipts. New module owns
  tool execution, separate from parser and source registration.
- `sources/extract.py`: PDF dispatch, retaining legacy two-item Extraction construction.
- `sources/adapters.py`: scrubbed page receipts at normal document registration, existing dedupe.
- `tests/test_pdf_teaching.py`: text/scanned/mixed PDF evidence, refusal paths and bounds.
- `pyproject.toml`, `uv.lock`: declare pypdf, add Pillow shared with image privacy work.
- `qa/evidence/teaching-pdf/`: complete unit evidence and reproducible mutation wrapper/spec.

## Checks and limits

- Focused PDF and source adapters: 24 passed; final mutation baseline covers all 13 new tests.
- Real portable Tesseract/Poppler scanned-page acceptance passed; mixed native/scanned pages
  covered by the mutation baseline. No remote API/model/browser calls.
- Existing schema/core boundaries: 38 passed in 7.55 seconds.
- Repository-wide Ruff: clean.
- Doctor: source rules clean after own function-size and pytest-scratch fixes; remaining
  stale `docs/SNAPSHOT.md` comes from unchanged master foundation. `docs/MAP.md` was generated
  with the CLI for this check but is deliberately excluded from the scoped commit; generated
  MAP/SNAPSHOT regeneration is reserved for combined integration. Do not call this doctor PASS.
- Full pytest is deferred under D-100 to the exact combined integration/release candidate.
- Previous attempts: 19 setup errors due Temp ACL; another 19 due missing basetemp parent.
  No test bodies ran in those attempts. Created the parent, used existing compatible Python,
  passed import/temp preflight, then exercised real tests. Their overhead is not hidden.

## Environment and evidence

Root: `C:/Users/product/Desktop/autoTesting/.work/teaching-pdf`.
Python: main checkout `.venv/Scripts/python.exe`, Python 3.11.16.
Import root: this worktree `src`; checker's preflight must verify it independently.
Lock SHA256: C75DED3E0497D6D81932E2915470D337EFD5C0BE27A04879C5620DBC5BA935EF.
Runtime: pypdf 6.20.1, Pillow 12.3.0; portable Tesseract 5.5.3.20260724, bundled Poppler.
Environment names only: PYTHONPATH, PATH, OMP_THREAD_LIMIT=1; no real credentials needed.

Each mutation and defending node ID is in `qa/evidence/teaching-pdf/mutations.json`; raw
outputs, baseline and attributable result rows are adjacent. Command durations are pytest's
reported execution times. Maker active time, total tokens and dollar usage were not exposed
by the host and remain unknown. Do not infer compliance with checker/maker efficiency ratios.

## Remaining work

Explicit re-extraction of existing deferred PDFs, nonvideo learning, all-source dispatch,
source-set checkpoints and FlowSpec merge/review acceptance are separate subsequent units.
English-only OCR and lack of a fixed child memory quota are disclosed runtime limits.

## Cycle 2 — authenticate previously unbound proof receipts

Cycle-1 checker HOLD (`qa/verdicts/teaching-pdf.md`, commit `1e6d9276`) found no runtime defect:
its own 62 focused checks, scoped lint and independent sanitation-removal mutation passed.
The gap was missing immutable source/environment binding on the other 21 maker mutation rows.
The original ephemeral copies were already removed by the repository harness, so their old
outputs remain historical evidence and are not retroactively certified.

Feature source, tests, scripts, pyproject and lock remain byte-identical to `c1f67d93`.
Cycle 2 changes only this manifest and supplementary `qa/evidence/teaching-pdf-cycle2/`.
One complete sandbox is fingerprinted and compared to the source before its first command;
no caches enter the copy. Its context binds source/test/fixture hashes, exact candidate,
Python executable/version/hash, lock, dependency versions, tool executable hashes/versions,
and relevant environment. Every command receipt binds before/after source-tree hashes,
exact node IDs, real UTC/monotonic timing, exit, named failures and raw-output SHA256.

Only missing defenders run: one green union baseline, 21 individually scoped red mutations,
and the same restored-green union. Each mutation asserts its unique anchor, changed bytes,
expected failure, restoration bytes and restored complete source manifest. The already
independently proven sanitation mutation is excluded. No 62-test suite or feature rework.
Final completion receipt and readiness validation must exist before checker dispatch.

Cycle-2 completion: all 21 missing mutations killed with authenticated named failures; green
union 12 passed and restored-green union 12 passed. Measured subprocess command time totals
289.799 seconds; this is command elapsed time, not invented maker active time or token usage.
`readiness.json` is READY_FOR_INDEPENDENT_CHECK with code tree SHA256
`1ffa3f237a630892dfca97ed3b146d4a226fd498a505286fe419d4b4f9d9860b`.
