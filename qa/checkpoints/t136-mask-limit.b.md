# Checkpoint - t136-mask-limit coordinator B (cycle 0)
Head checked: 8fc7c215 (src/tests/scripts identical to code commit 7ac56034; `git diff 7ac56034 HEAD -- src tests scripts` is empty). Base 8956c9bc.
Env: worktree .venv (imports worktree src, verified), Tesseract C:/Program Files/Tesseract-OCR, win32. Policy proportional-verification/2026-10-19.17.

| check | command / scope | code+test identity | result |
|---|---|---|---|
| C1/C2/C12 affected set | uv run pytest tests/test_image_privacy_engine.py tests/test_image_privacy.py tests/test_grade_visual.py (66 collected) | image_privacy.py MAX_MASK_FRACTION 0.75; test blobs per manifest | 66 passed, 1 warning, 2.84 s |
| ruff | uv run ruff check src tests scripts | same | All checks passed |
| doctor | uv run autotester doctor | same | doctor: clean |
| mutant M1 (floor C1) | isolated copy, MAX_MASK_FRACTION 0.75 -> 0.6, same 3 files | copy of HEAD src/tests/scripts | 1 failed (test_dashboard_shaped_screenshot_is_kept_with_every_text_band_masked), 65 passed |
| mutant M2 (floor C2) | isolated copy, stages/grade_images.py:88 `if unseen` -> `if False` | same | 3 failed (g2_..withheld, ..absent, ..dashboard_withheld_for_mask_size), 63 passed |
| mutant M3 (security) | isolated copy, band box (0..size[0]) -> word extent only (image_privacy.py:112) | same | 5 failed |
| mutant M4 (limit) | isolated copy, 0.75 -> 0.95 | same | 1 failed (test_mostly_sensitive_screenshot_is_still_withheld), 65 passed |
| real-image probe | sanitized_images on 22 run-5 pngs + 30 random other Pathlynks pngs (seed 1); original OCR word boxes vs sanitized pixels; then re-OCR of the sanitized output | worktree src, local Tesseract, no network | 52/52 kept; max fraction 0.636, both run-5 dashboards 0.621; 0 original recognized word boxes left unmasked; re-OCR of sanitized output finds >=1 word in 46 of 52 kept images |

Re-OCR detail on the two newly kept run-5 dashboards (cases efaed2c0eb91, cfa40e6b95c2, 04-step04-click.png): 5 words conf>=92 in unmasked pixels, character-class shapes only: y=171 'Aa','Aaaaa'; y=452 'Aaaaaaaa','Aaaaaaa'; y=581 'Aaaaaa'. Old-limit kept image case_093f5070df7 (fraction 0.34): 11 such words.

Mutants were isolated copies under the scratchpad (PYTHONPATH override, module path verified per copy); the bound tree was never edited. The probe printed counts, geometry and character-class shapes only, never OCR text; no screenshot was opened in a viewer; nothing from real screenshots was committed. Probe summary file (filenames and numbers only, untracked): qa/evidence/t136-mask-limit-b/probe-52-real-screenshots.txt.
