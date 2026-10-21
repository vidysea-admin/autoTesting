# Manifest - at1384-mask-band
**Contract:** qa/contracts/browser-and-secrets.md (B11), qa/contracts/grade.md, qa/contracts/core-invariants.md C12
**Goal task:** T-136
**Date:** 2026-10-21
**Fix cycle:** 0 of max 2
**Dual check:** required
dual-trigger: security src/autotester/core/image_privacy.py:152
**Issues addressed:** AT-1384
**Authority:** qa/gates/at1384-mask-limit-band.md Answered line (Umesh-delegated default 2026-10-21: per-project limit, default unchanged, Pathlynks raised from measured fractions) and qa/gates/t136-withheld-screenshot-pass.md answer A; criteria C1-C2 in .work/briefs/build-at1384-mask-band.md
**Base SHA:** c437d3a5 (worktree .worktrees/at1384-mask-band, branch wave/at1384-mask-band)
**Code SHA:** 714720db

## What changed
- src/autotester/schema/image_privacy.py:8-11 - `DEFAULT_MASK_LIMIT = 0.75` (today's value) and `CEILING_MASK_LIMIT = 0.9` (no project may raise the limit past it; above it the guard would withhold nothing).
- src/autotester/schema/project.py (`Project.image_mask_limit`, after `headed`) - the per-project setting, in the existing `Project` model: float, default `DEFAULT_MASK_LIMIT`, `0 < x <= CEILING_MASK_LIMIT` (extra="forbid" is inherited). Every other project, committed or old, keeps 0.75.
- src/autotester/core/image_privacy.py - `MAX_MASK_FRACTION` is now `DEFAULT_MASK_LIMIT` (value unchanged); `sanitized_images(paths, *, mask_limit=None)` threads the limit through `_prepare_image` -> `_sanitize_one` -> `_mask` -> `_check_mask_area(boxes, size, limit)` (:152). None reads `MAX_MASK_FRACTION` at call time. A limit outside (0, ceiling] (incl. NaN) raises `invalid_mask_limit`, which withholds the image (fail closed, C12). `_text_boxes`, `_line_bands`, `_leftover_boxes` and the re-read loop are untouched, so every detected text region is still masked full-width in a kept image.
- Wiring (each passes the project's value; callers with no project in scope keep the default): stages/grade_images.py (`judge_images(..., mask_limit=None)`, new `project_mask_limit(store)`), stages/grade.py (`grade(..., mask_limit=None)`), stages/run_case_pipeline.py (both `grade(` calls use `project_mask_limit(store)`; this is the UI/CLI run path), stages/orchestrate_downstream.py (`project.image_mask_limit`), agents/tools.py (`ctx.project.image_mask_limit`), stages/run_artifacts.py (`_assemble_case(..., mask_limit)` for failure bundles). `visual_decision` in stages/grade_images.py is unchanged: a withheld screenshot still grades INCONCLUSIVE, never PASS. Not wired, default applies: stages/ai_judge.py, stages/leak_evidence.py, providers/video_frames.py, providers/vision_probe.py.
- projects/pathlynks/project.json - `"image_mask_limit": 0.85` (measurement below). pathlynks-prepod and every other project are unchanged (0.75).
- tests/golden/pre_g11_project.json - one line added (`"image_mask_limit": 0.75`): `Project` now writes the field and this fixture is the byte-identical round-trip proof (tests/test_multi_role_schema.py). No key removed or changed.
- Tests added (synthetic images and stub OCR only; no real screenshot copied or committed): tests/test_image_privacy_engine.py (+4 tests, 8 cases), tests/test_grade_visual.py (+3), tests/test_project_schema_team.py (+2).

## Measurement (C1) - recorded masking metadata only
Read-only probe (scratchpad script, nothing copied or saved): `sanitized_images` over the 38 real Pathlynks PNGs under .worktrees/live-t136-r5/projects/pathlynks/runs with `_check_mask_area` replaced by a recorder, so the limit never fired. The cumulative mask only grows, so the last pass fraction is what any limit is compared with. Final cumulative mask fractions of the 38 images:
- 1.0 x6 (re-read noise bands cover the whole image; nothing useful is left)
- 0.7576 x4, 0.76, 0.7788, 0.7835, 0.7941, 0.8106, 0.8129, 0.8141, 0.8224 x2 -> 14 images between 0.75 and 0.83
- 0.6106, 0.5906, 0.46, 0.4529, 0.4153, 0.3976 x2, 0.3965 x9, 0.3776 x2, 0.0576 -> 18 images at or under 0.75
Under today's 0.75 that is 19 `mask_exceeds_limit` + 1 `text_remains_after_mask` = 20 withheld (matches the at1363-reocr checker's 20 of 38). Six images (0.6106, 0.7576 x4, 0.8129) still show readable text after the third re-mask; that is not a limit matter and they stay withheld at any limit.
Chosen value 0.85 = the largest kept fraction 0.8224 plus a 0.0276 margin, and under the six fully-masked (1.0) images, which must stay withheld. Real-engine confirmation at the committed value (`sanitized_images(mask_limit=0.85)` over the same 38 files, counts only): 26 kept, 6 `mask_exceeds_limit` (the 1.0 images), 6 `text_remains_after_mask`; up from 18 kept. Every kept image is masked by the unchanged full-width band rule.

## Verification scope
Policy-Version: proportional-verification/2026-10-19.17
Tier: L - privacy masking is a security control (image sanitation before external model delivery, B11)
Round: 10 src files + 3 test files + 1 golden + 1 project file, 2 criteria, est 60 min - one setting threaded through one call chain, 9 tests
Base / checked state: base c437d3a5; code commit 714720db; the manifest commit follows and touches only qa/manifests
Gate answers: qa/gates/at1384-mask-limit-band.md (Answered 2026-10-21, Umesh-delegated default): per-project limit, default unchanged, Pathlynks raised from measured fractions, every secret/PII region masked, a mostly-sensitive image withheld, INCONCLUSIVE rule unchanged
Affected tests / full-suite trigger: tests/test_image_privacy_engine.py, tests/test_image_privacy.py, tests/test_image_privacy_reocr.py, tests/test_project_schema_team.py, tests/test_grade_visual.py, tests/test_multi_role_schema.py (golden), tests/test_orchestrate_downstream.py, tests/test_run_failure_artifacts.py, tests/test_video_frames.py, tests/test_agent_loop.py, tests/test_agent_fallback.py (callers); no conftest, fixture helper, lockfile or runner-config change, so no full-suite trigger. The builder runs no full suite.
Tests[C1]: tests/test_project_schema_team.py::test_image_mask_limit_defaults_to_todays_value_and_is_bounded, ::test_pathlynks_declares_a_limit_above_the_default_and_other_projects_keep_it; tests/test_image_privacy_engine.py::test_pathlynks_dense_dashboard_is_kept_at_its_project_limit_with_every_band_masked, ::test_the_default_limit_still_withholds_that_dashboard; tests/test_grade_visual.py::test_at1384_dashboard_over_default_limit_is_kept_under_the_project_limit, ::test_at1384_project_limit_is_read_from_the_project_config
Tests[C2]: tests/test_image_privacy_engine.py::test_pathlynks_dense_dashboard_is_kept_at_its_project_limit_with_every_band_masked (every band, incl. the secret line and the low-confidence line, is black at left, middle and right), ::test_a_mostly_sensitive_image_is_still_withheld_at_the_project_limit, ::test_a_nonsense_mask_limit_fails_closed; tests/test_grade_visual.py::test_at1384_a_screenshot_above_the_project_limit_still_grades_inconclusive, plus the unchanged ::test_g2_pass_is_held_when_a_dashboard_screenshot_is_withheld_for_mask_size and tests/test_image_privacy_reocr.py (cumulative limit across re-read passes)
Tests[C12]: tests/test_image_privacy.py::test_mask_over_sane_fraction_is_withheld, ::test_unusable_ocr_still_withholds_with_fixed_reason and tests/test_image_privacy_engine.py::test_mostly_sensitive_screenshot_is_still_withheld - every old withhold case stays withheld; an invalid limit withholds
Pre-check[C1]: 714720db uv run pytest tests/test_image_privacy_engine.py tests/test_grade_visual.py tests/test_project_schema_team.py tests/test_multi_role_schema.py -> 114 passed t=3 blobs=tests/test_image_privacy_engine.py:b1ce053,tests/test_grade_visual.py:ebdd9c8,tests/test_project_schema_team.py:6b90e17
Pre-check[C2]: 714720db uv run pytest tests/test_image_privacy_engine.py tests/test_image_privacy.py tests/test_image_privacy_reocr.py tests/test_grade_visual.py -> 89 passed t=6 blobs=tests/test_image_privacy_engine.py:b1ce053,tests/test_image_privacy.py:ae4e461,tests/test_grade_visual.py:ebdd9c8
Pre-check[C12]: 714720db uv run pytest tests/test_image_privacy_engine.py tests/test_image_privacy.py tests/test_image_privacy_reocr.py tests/test_grade_visual.py -> 89 passed t=6 blobs=tests/test_image_privacy_engine.py:b1ce053,tests/test_image_privacy.py:ae4e461
Falsification[C1]: copy of src/tests/scripts/projects in .work/tmp/mut1384 (PYTHONPATH on the copy, control 38 passed over test_image_privacy_engine + test_grade_visual): `_prepare_image` hands `None` to `_sanitize_one` (project limit ignored) -> 7 failed; `grade` stops passing `mask_limit` to `judge_images` -> 1 failed (test_at1384_dashboard_over_default_limit_is_kept_under_the_project_limit); restored copy 38 passed.
Falsification[C2]: same copy: `_check_mask_area` comparison replaced by `if False` -> 6 failed; `_mask` draws nothing -> 10 failed (secret band no longer black).
Metrics: start=2026-10-21T00:00:00Z end=2026-10-21T00:00:00Z wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=4 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=0 mutants=4 defects_unit=0 defects_6c=0 builder_min=unavailable

## How to verify (commands + expected)
- `uv run pytest tests/test_image_privacy_engine.py tests/test_image_privacy.py tests/test_image_privacy_reocr.py tests/test_project_schema_team.py tests/test_grade_visual.py tests/test_multi_role_schema.py tests/test_orchestrate_downstream.py tests/test_run_failure_artifacts.py tests/test_video_frames.py tests/test_agent_loop.py tests/test_agent_fallback.py` -> expected: 251 passed
- `uv run ruff check src tests scripts` -> expected: All checks passed!
- `uv run autotester doctor` -> expected: 2 violations, both docs/SNAPSHOT.md stale-generated/stale-committed (pre-existing, regenerated by the coordinator); none in this unit's files

## Actual outputs (from maker's own run)
```
pytest (11 files): 251 passed, 1 warning
uv run ruff check src tests scripts: All checks passed!
uv run autotester doctor: 2 violation(s), both docs/SNAPSHOT.md (pre-existing, unrelated)
```

## Live browser evidence
SKIP - maker smoke only; checker runs Mode D when UI changed. No UI surface changed.

## Status: ready-for-check
