# Checkpoint: image-privacy-mask (cycle 0, coordinator A, FAIL)
Original checker attribution: coordinator A, qa/verdicts/image-privacy-mask.md
Code hash: src/autotester/core/image_privacy.py at head e975ff60
Config/fixtures/conftest: tests/conftest.py not in the diff; uv.lock unchanged; env: Windows 11, worktree .venv python, pytest -p no:xdist -o addopts=, Tesseract at C:/Program Files/Tesseract-OCR (not on PATH)
- affected tests: tests/test_image_privacy.py + test_image_privacy_engine.py + test_run_failure_artifacts.py -> 53 passed (9.71s); ruff on the 4 changed py files clean
- falsifications C1/C2/C3: green before, red after, in copies under the session scratchpad (details in the verdict)
- probes P1-P4: qa/evidence/image-privacy-mask/checker-a.md
