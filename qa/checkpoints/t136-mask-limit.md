# Checkpoint - t136-mask-limit (coordinator A) - cycle 0
Code hashes: src/autotester/core/image_privacy.py @ d530dbe1 blob 8883fd240fc80ec088385a54977d295beaed44e2; config, conftest, lock: unchanged vs 8956c9bc (diff stat lists none). Env: Windows 11, worktree .venv python, real Tesseract at C:/Program Files/Tesseract-OCR. Checker: claude-sonnet-subagent A; this file only.
1. `uv run pytest tests/test_image_privacy_engine.py tests/test_image_privacy.py tests/test_grade_visual.py` (66 collected) -> 66 passed.
2. `uv run pytest` on every tests/ file naming image_privacy or sanitized_images (210 collected) -> 210 passed.
3. ruff src tests scripts -> clean; autotester doctor -> clean.
4. Falsification C1 (copy, MAX_MASK_FRACTION 0.6): 1 failed, 12 passed. Falsification C2 (copy, grade_images.py:88 `if False`): 3 failed, 11 passed.
5. Real-OCR probe (synthetic page): 22 lines 0.734 kept, 0 residual words, 0 un-blacked ink px; 26 lines 0.842 withheld; 30 lines 0.929 withheld.
Result: PASS. Remaining: none.
