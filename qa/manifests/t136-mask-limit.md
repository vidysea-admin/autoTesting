# Manifest - t136-mask-limit
**Contract:** qa/contracts/browser-and-secrets.md (B11), qa/contracts/grade.md, qa/contracts/core-invariants.md C12
**Goal task:** T-136
**Date:** 2026-10-21
**Fix cycle:** 0 of max 2
**Dual check:** required
dual-trigger: security src/autotester/core/image_privacy.py:38
**Issues addressed:** none
**Authority:** Umesh gate answer, qa/gates/t136-withheld-screenshot-pass.md: "A (keep INCONCLUSIVE; raise the dashboard masking limit so the screenshot is kept)"

## What changed
- src/autotester/core/image_privacy.py:35-38 - `MAX_MASK_FRACTION` 0.6 -> 0.75, with a comment giving the reason. The guard is kept, not removed. Measured with the real Tesseract on the two withheld run-5 screenshots (case_efaed2c0eb91 and case_cfa40e6b95c2 `04-step04-click.png`, 1366x850, 77 boxes, 138 words): mask fraction 0.621, just over 0.6. Every recognized text line is masked across the FULL width (`_text_boxes`), so the fraction measures text density, not leak risk; 0.75 keeps such a dense dashboard while a screen that is mostly text (leaving under a quarter unmasked) is still withheld. After the change both real screenshots are kept through `sanitized_images` (probe run, nothing committed). A per-project setting was not added: five callers use `sanitized_images` and the limit has no project-specific meaning.
- tests/test_image_privacy_engine.py (2 tests added) - synthetic dashboard-shaped OCR (1366x850, 19 text lines, fraction 0.648, a confident secret line and a low-confidence word) is kept with every text band masked, pixel-checked at left, middle and right of each band; a 26-line screen (fraction 0.887) is still withheld as `mask_exceeds_limit`.
- tests/test_grade_visual.py (1 test added) - a screenshot still withheld for `mask_exceeds_limit` with a met `assert` row holds a PASS as INCONCLUSIVE (images_seen 0). `stages/grade_images.py` is unchanged.
- No real screenshot committed; the existing `test_mask_over_sane_fraction_is_withheld` (tests/test_image_privacy.py:260) still passes.

## Verification scope
Policy-Version: proportional-verification/2026-10-19.17
Tier: L - privacy masking is a security control (image sanitation before external model delivery, B11)
Round: 3 files, 2 criteria, est 15 min - one constant, three tests
Base / checked state: base 8956c9bc; code commit 7ac56034; the manifest commit follows and touches only qa/manifests
Gate answers: qa/gates/t136-withheld-screenshot-pass.md: "A (keep INCONCLUSIVE; raise the dashboard masking limit so the screenshot is kept)"
Affected tests / full-suite trigger: tests/test_image_privacy_engine.py, tests/test_image_privacy.py (limit test), tests/test_grade_visual.py; no conftest, fixture, lockfile or runner-config change, so no full-suite trigger. The builder runs no full suite.
Tests[C1]: tests/test_image_privacy_engine.py::test_dashboard_shaped_screenshot_is_kept_with_every_text_band_masked, ::test_mostly_sensitive_screenshot_is_still_withheld, plus tests/test_image_privacy.py (incl. ::test_mask_over_sane_fraction_is_withheld and the fail-closed set)
Tests[C2]: tests/test_grade_visual.py::test_g2_pass_is_held_when_a_dashboard_screenshot_is_withheld_for_mask_size, plus the existing ::test_g2_pass_is_held_when_a_screenshot_was_withheld and ::test_g2_pass_is_held_when_a_screenshot_is_absent
Tests[C12]: tests/test_image_privacy.py::test_unusable_ocr_still_withholds_with_fixed_reason, ::test_mask_over_sane_fraction_is_withheld and tests/test_image_privacy_engine.py::test_mostly_sensitive_screenshot_is_still_withheld - core-invariants C12 (fail closed) is the invariant the limit change must not weaken: every withhold case stays withheld
Pre-check[C1]: 7ac56034 uv run pytest tests/test_image_privacy_engine.py tests/test_image_privacy.py tests/test_grade_visual.py -> 66 passed t=3 blobs=tests/test_image_privacy_engine.py:5ac7acc,tests/test_image_privacy.py:b99f6d6,tests/test_grade_visual.py:4cbe009
Pre-check[C2]: 7ac56034 uv run pytest tests/test_image_privacy_engine.py tests/test_image_privacy.py tests/test_grade_visual.py -> 66 passed t=3 blobs=tests/test_image_privacy_engine.py:5ac7acc,tests/test_image_privacy.py:b99f6d6,tests/test_grade_visual.py:4cbe009
Pre-check[C12]: 7ac56034 uv run pytest tests/test_image_privacy_engine.py tests/test_image_privacy.py tests/test_grade_visual.py -> 66 passed t=3 blobs=tests/test_image_privacy_engine.py:5ac7acc,tests/test_image_privacy.py:b99f6d6,tests/test_grade_visual.py:4cbe009
Falsification[C1]: same tree, `MAX_MASK_FRACTION = 0.6` restored (the base value) -> 1 failed (test_dashboard_shaped_screenshot_is_kept_with_every_text_band_masked: 0.648 > 0.6 limit), 12 passed; edit reverted.
Falsification[C2]: same tree, stages/grade_images.py:88 `if unseen` replaced by `if False` (a withheld screenshot no longer holds a PASS) -> 3 failed (test_g2_pass_is_held_when_a_screenshot_was_withheld, ..._is_absent, test_g2_pass_is_held_when_a_dashboard_screenshot_is_withheld_for_mask_size), 11 passed; file restored from backup.
Metrics: start=2026-10-21T00:00:00Z end=2026-10-21T00:00:00Z wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=0 mutants=0 defects_unit=0 defects_6c=0 builder_min=unavailable

## How to verify (commands + expected)
- `uv run pytest tests/test_image_privacy_engine.py tests/test_image_privacy.py tests/test_grade_visual.py` -> expected: 66 passed
- `uv run ruff check src tests scripts` -> expected: All checks passed!
- `uv run autotester doctor` -> expected: doctor: clean

## Actual outputs (from maker's own run)
```
pytest (3 files): 66 passed, 1 warning
uv run ruff check src tests scripts: All checks passed!
uv run autotester doctor: doctor: clean   (decision-citation lines are pre-existing advisory output)
real-screenshot probe (sanitized_images on run-01M5A1FTWZR0XV0WS0QHGDMBXY efae/cfa4 04-step04-click.png): both "kept", reasons []
```
Open point for the checker: the 0.75 value is a judgement (measured 0.621 on the real dashboard; the margin covers a slightly denser dashboard). The security read should confirm full-width masking (`_text_boxes`) is unchanged, so every secret/PII band is still blacked out in a kept image.

## Capability coverage (each new claim -> its isolating falsification)
| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| C1 | a dashboard-shaped screenshot (fraction 0.648) is kept with every band masked | tests/test_image_privacy_engine.py::test_dashboard_shaped_screenshot_is_kept_with_every_text_band_masked | limit back to 0.6 | green in the tree, then "1 failed, 12 passed" |
| C1 | a mostly-sensitive screen is still withheld | ::test_mostly_sensitive_screenshot_is_still_withheld | (guard kept; existing test_mask_over_sane_fraction_is_withheld also covers it) | green |
| C2 | a screenshot still withheld never yields PASS | tests/test_grade_visual.py::test_g2_pass_is_held_when_a_dashboard_screenshot_is_withheld_for_mask_size | `if unseen` -> `if False` in grade_images.py:88 | "3 failed, 11 passed" |

## Live browser evidence
SKIP - maker smoke only; checker runs Mode D when UI changed. No UI surface changed (src/autotester/core/image_privacy.py, tests only); no live run was made.

## Status: ready-for-check
