# Coordinator A, cycle 1: probes and commands (all run by the checker, in copies under the session scratchpad)

Copy: `src tests scripts pyproject.toml` of head cfa7732b; `autotester.__file__` printed from the copy.

## Acceptance (bound tree, no cache, TMP in scratchpad)
`.venv/Scripts/python.exe -m pytest tests/test_image_privacy.py tests/test_image_privacy_engine.py tests/test_run_failure_artifacts.py -p no:xdist -o addopts= -p no:cacheprovider` -> 54 passed in 16.07s, exit 0.
`ruff check --no-cache` on the 4 changed py files -> All checks passed. Line counts: image_privacy.py 191, tests 295 and 141 (limit 300); `_text_boxes` 30 lines.

## Falsification C1 (repair)
Copy, new test `-k quote`: 1 passed (green before). Removed `, quoting=csv.QUOTE_NONE` at image_privacy.py:87 in the copy ->
1 failed at tests/test_image_privacy.py:295 `assert (255, 255, 255) == (0, 0, 0)` (the secret row after the quote token). Copy discarded, bound tree untouched.

## Probes (synthetic TSV through `sanitized_images`, probe_a.py; and real Tesseract, probe_real.py)
- high-conf secret line + low-conf word line: released, both bands black, far corner white.
- blank low-conf row, valid geometry: masked, released.
- header-only TSV, empty TSV, blank-only TSV, text-free real image: withheld `no_recognized_text`.
- quote tokens (`"`, `"a ""b`, `c'd"`) followed by a secret row: every row processed, released, bands black.
- 20 line bands covering > 60% of the page: withheld `mask_exceeds_limit` (checked before any pixel is drawn, image_privacy.py:139-141).
- conf nan / inf: `uncertain_ocr`; conf -1 non-blank: masked and released; short row, conf `abc`, CR inside a token: `sanitation_failed` (withheld, no OCR text in the reason).
- real Tesseract found at the Windows path (not on PATH): real screenshot with a password line, tiny text and a grey SSN line -> released, re-OCR of the output finds none of hunter/password/qwerty/123-45/login.
- P1 evidence: blank low-conf row at x=280..340 on a 300 px image -> released with its region unmasked (a non-blank word with the same geometry is withheld `invalid_ocr_geometry`).
- P2 evidence: a near-white (235 grey) line `token: ZXCVBNM98765` that Tesseract returned no row for at all stays readable in the released image; a larger word beside tiny text pokes out below its band. Same at base e1d59c35 (unreported text was never masked); documented in the module docstring as heuristic OCR.
- P3 evidence: `AUTOTESTER_TESSERACT=tesseract.exe` (relative) is accepted when that file exists in the cwd and is executed by name; a directory is rejected. `${OTHER}` in `.env` expands into the candidate path; no value is logged or returned in any message.
