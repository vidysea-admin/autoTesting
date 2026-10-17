# Checkpoint B - image-privacy-mask (cycle 0)
Code hash: head e975ff60, src/autotester/core/image_privacy.py from d6ab9e30; tests 7ef9f9c8; lock unchanged vs base; env: Windows 11, venv in worktree, Tesseract at C:/Program Files/Tesseract-OCR; original checker: coordinator B (this file).
- `pytest tests/test_image_privacy.py tests/test_image_privacy_engine.py tests/test_run_failure_artifacts.py -p no:xdist -o addopts=` (3 files, 53 collected) -> 53 passed
- same runner on test_grade_evidence, test_provider_vision_integration, test_run_case_pipeline, test_video_frames, test_vision_probe, test_mutation_check (127 collected) -> 127 passed
- `ruff check src tests` -> pass
- falsification copy (git archive HEAD): GREEN 49 passed (two privacy files); C1 x2, C2 x2, C3 x1 mutants red on named tests
- probes (scratchpad probe.py, probe2.py), data: synthetic images only, no real screenshots
