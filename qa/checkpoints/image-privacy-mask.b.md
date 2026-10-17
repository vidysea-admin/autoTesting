# Checkpoint B - image-privacy-mask (cycle 0)
Code hash: head e975ff60, src/autotester/core/image_privacy.py from d6ab9e30; tests 7ef9f9c8; lock unchanged vs base; env: Windows 11, venv in worktree, Tesseract at C:/Program Files/Tesseract-OCR; original checker: coordinator B (this file).
- `pytest tests/test_image_privacy.py tests/test_image_privacy_engine.py tests/test_run_failure_artifacts.py -p no:xdist -o addopts=` (3 files, 53 collected) -> 53 passed
- same runner on test_grade_evidence, test_provider_vision_integration, test_run_case_pipeline, test_video_frames, test_vision_probe, test_mutation_check (127 collected) -> 127 passed
- `ruff check src tests` -> pass
- falsification copy (git archive HEAD): GREEN 49 passed (two privacy files); C1 x2, C2 x2, C3 x1 mutants red on named tests
- probes (scratchpad probe.py, probe2.py), data: synthetic images only, no real screenshots

## Cycle 1
Code hash: head cfa7732b (image_privacy.py:87 QUOTE_NONE); repair base 5bad0129; lock unchanged; env Windows 11, worktree venv, Tesseract at C:/Program Files/Tesseract-OCR; original checker: coordinator B (this file).
- `pytest tests/test_image_privacy.py tests/test_image_privacy_engine.py tests/test_run_failure_artifacts.py -p no:xdist -o addopts=` (3 files) -> 54 passed
- `ruff check src tests` -> pass
- falsification copy (git archive HEAD): `-k quote` green 1 passed; QUOTE_NONE removed -> red at tests/test_image_privacy.py:295
- probes: scratchpad probe_c1b.py, synthetic images only; quote/CR/short-row variants fail closed or mask
