# PDF teaching extraction unit

This unit adds local PDF extraction, not nonvideo FlowSpec generation or all-source orchestration.
No model or browser is invoked by extraction. Existing source deduplication remains unchanged;
previously registered deferred PDFs require a later explicit re-extraction action.

## Runtime

- Python dependencies are declared in `pyproject.toml` and locked in `uv.lock`.
- Add Poppler's `pdftoppm` and Tesseract with English tessdata to the application process PATH.
- Ubuntu: install `poppler-utils`, `tesseract-ocr` and `tesseract-ocr-eng` through apt.
- Windows acceptance used the portable Tesseract under the main checkout's
  `.work/tools/tesseract-5.5.3`, alongside bundled Poppler. Its verified provenance is in
  main-checkout `.work/tools/ocr-downloads/EVIDENCE.md`; no system installation or persistent
  PATH change was performed. Put the supplied runtime on the application's process PATH.
- English OCR only is configured in this unit. OCR confidence is a heuristic; confidence below
  70 requires review, and does not become a successful teaching reading.
- OCR subprocesses enforce `OMP_THREAD_LIMIT=1`. Every tool invocation has its own deadline.

## Safety and limits

`PdfLimits` declares 50 MB input, 100 pages, 500,000 characters, 120-second parser deadline,
15-second per-tool deadline, and maximum rendered side of 2,000 pixels. Parsing runs in an
isolated subprocess. These bounds do not claim a fixed process-memory quota. On total parser
timeout, an already started OCR subprocess remains bounded by its own tool deadline.

Corrupt/encrypted inputs produce explicit errors. Page read/OCR failures retain numbered page
receipts; character-limit stops name unprocessed pages. An incomplete PDF has no consumable
combined text. Extracted PDF registration scrubs known root `.env` values and contact PII,
rejects recoverable encoded secrets, and stores `sources/<source-id>/document.json` evidence.

## Evidence

`focused-tests.log` records the related source suite, including actual local scanned-page
extraction. `run-00.log` is the asserted final PDF mutation baseline, including mixed-page
acceptance. `mutation-results.json` binds each sabotaged behavior to its named failing test.
`boundaries.log` covers existing schema and redaction foundations. `ruff.log` is repository-wide
lint. `doctor.log` reports the remaining baseline generated-SNAPSHOT freshness issue honestly.

The mutation adapter calls the existing repository harness with no changes to its anchor,
baseline, named-failure, or restoration checks. It sets the isolated source import root, creates
the required temporary parent, saves raw logs, and narrows each red run to its named defenders.
The harness's default inherited PYTHONPATH would otherwise import the original editable tree.
No `__pycache__` directories enter its copy. Full combined release tests remain an integration gate.
