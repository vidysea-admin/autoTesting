# Checker A evidence (image-privacy-mask, cycle 0, head e975ff60, base e1d59c35)
Probe script: session scratchpad ipm/probe_a.py (reads the worktree src, writes only under scratch). Python: the worktree .venv.

## P1 synthetic TSV (exact Tesseract TSV shape), 400x120 image
Row 1 text `"hi` conf 30 at (10,10,40x20); row 2 text `hunterTwo` conf 97 at (10,80,90x20).
- head: boxes=[(10,10,50,30),(0,6,400,34)] -> line 2 (y 76..104) NOT masked, image released
- base: ImagePrivacyError uncertain_ocr (image withheld)
- head, row 1 at conf 97: boxes=[(0,6,400,34)] -> line 2 not masked (same at base, pre-existing)
- plain `hi` without the quote: both lines masked.
Cause: src/autotester/core/image_privacy.py:87 `csv.DictReader(..., delimiter="<TAB>")` keeps the default quotechar; a text field that starts with a double quote opens a quoted field that swallows the following TSV rows (Tesseract does not quote).

## P4 real Tesseract (C:/Program Files/Tesseract-OCR), 900x200 PNG: line 1 `say "hi`, line 2 `Password hunterTwo`, black on white
- raw TSV line: `5 1 1 1 1 2 90 26 33 23 95.018959 "hi`
- head: sanitized_images -> 1 path, withheld=0; re-OCR of the released PNG contains "hunter" and "password" (secret NOT masked)
- base (e1d59c35 src, Tesseract on PATH): the same leak (pre-existing for a confident quote token)
- head plus `quoting=csv.QUOTE_NONE` at line 87 (in a copy): re-OCR leaks=[]; tests/test_image_privacy.py 38 passed; tests/test_image_privacy_engine.py 11 passed.

## Other probes
- P2 blank white image, real OCR: withheld, reason no_recognized_text (head and base).
- P3 real OCR, black "Password hunterTwo", light-gray "faint blurry word", "token sk-LIVE-998877": released, black fraction 0.246, re-OCR leaks=[].
- Affected tests at head: tests/test_image_privacy.py + test_image_privacy_engine.py + test_run_failure_artifacts.py -> 53 passed in 9.71 s. ruff on the 4 changed py files: All checks passed.
