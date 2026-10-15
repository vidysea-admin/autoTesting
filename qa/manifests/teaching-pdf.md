# Manifest — bounded local PDF teaching extraction

- Status: ready-for-check
- Fix cycle: 1
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
