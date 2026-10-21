# Manifest - at1363-reocr
**Contract:** qa/contracts/browser-and-secrets.md (B11), qa/contracts/grade.md, qa/contracts/core-invariants.md C12
**Goal task:** T-136
**Date:** 2026-10-21
**Fix cycle:** 0 of max 2
**Dual check:** required
dual-trigger: security src/autotester/core/image_privacy.py:186
**Issues addressed:** AT-1363
**Authority:** Umesh 2026-10-21 "fix kro"; criteria C1-C3 in .work/briefs/build-at1363-reocr.md (checker B PROPOSED-ISSUE P1, qa/verdicts/t136-mask-limit.b.md)
**Base SHA:** 8956c9bc (worktree .worktrees/at1363-reocr, branch wave/at1363-reocr)
**Code SHA:** 6ecd9364

## What changed
- src/autotester/core/image_privacy.py (194 -> 238 lines) - `_sanitize_one` (:171-191) now masks the first-pass boxes, then reads the sanitized file again (`MAX_REOCR_PASSES = 3`). Any non-blank word the re-read finds whose box still shows a non-black pixel (`_leftover_boxes`, :133) is masked with its full-width line band through the new `_mask` (:159); the loop returns as soon as a re-read finds nothing. If the third re-read still found words, the image is withheld with the new fixed reason `text_remains_after_mask` (the last re-mask is never trusted unread). `_mask` checks the CUMULATIVE box list against `MAX_MASK_FRACTION` every pass, so a later pass can withhold with `mask_exceeds_limit`.
- Same file, refactor in place: the row parsing of `_text_boxes` moved to `_words` and the line-band step to `_line_bands` so pass 1 and the re-read share one validator (NaN, conf > 100, bad geometry still fail closed). `_text_boxes(tsv, size)` keeps its signature and behaviour (existing tests monkeypatch it). A word whose box is wholly black is ignored on re-read: it cannot be read, and OCR noise over the mask would otherwise withhold every image.
- tests/test_image_privacy_reocr.py (new, 12 tests, synthetic PIL images, stub OCR per pass, one real-Tesseract test that skips when not provisioned). No screenshot committed.
- Existing tests adjusted only where they count or order OCR calls, which a mandatory re-read changes: tests/test_image_privacy.py `test_nested_sanitizers_reuse_only_verified_copy` (OCR calls 1 -> 2 and 2 -> 4; the point, that a nested pass adds none, is kept) and `test_ocr_uses_decoded_snapshot_not_mutable_source` (the decoded-snapshot assertion applies to the first read; later reads are of the masked copy); tests/test_video_frames.py `test_partial_withholding_retains_original_index_and_time` (the injected OCR failure moved from call 2 to call 3 so it still hits frame 1).
- Real-engine probe (nothing committed): 900x260 synthetic image with a black line, a grey line and 13 px grey small print -> kept; reads found 10 words (pass 1) then 0 (re-read).

## Verification scope
Policy-Version: proportional-verification/2026-10-19.17
Tier: L - privacy masking is a security control (image sanitation before external model delivery, B11)
Round: 5 files, 3 criteria, est 40 min - one function loop, two helpers, 12 new tests
Base / checked state: base 8956c9bc; code commit 6ecd9364; the manifest commit follows and touches only qa/manifests
Gate answers: none needed
Affected tests / full-suite trigger: tests/test_image_privacy_reocr.py, tests/test_image_privacy.py, tests/test_image_privacy_engine.py, tests/test_grade_visual.py, tests/test_video_frames.py (caller via providers/video_frames.py); no conftest, fixture, lockfile or runner-config change, so no full-suite trigger. The builder runs no full suite.
Tests[C1]: tests/test_image_privacy_reocr.py::test_c1_* (words missed on pass 1 masked after the re-read; the re-read reads the sanitized pixels; clean image kept after one verifying read; a box inside the black mask is not readable; text on every pass withheld after the last, bounded at 1 + MAX_REOCR_PASSES reads; third re-mask not trusted; text on two successive re-reads masked then clean on the third)
Tests[C2]: tests/test_image_privacy_reocr.py::test_c2_* (cumulative mask over the limit withheld on a later pass; each pass alone under the limit kept; a re-read failure and unusable re-read geometry withhold with fixed reasons) plus the unchanged tests/test_image_privacy.py::test_mask_over_sane_fraction_is_withheld, ::test_unusable_ocr_still_withholds_with_fixed_reason and tests/test_grade_visual.py (withheld -> INCONCLUSIVE, never PASS)
Tests[C3]: tests/test_image_privacy_reocr.py (synthetic PIL images, per-pass stub OCR; ::test_c3_real_tesseract_reread_of_the_sanitized_screenshot_finds_no_word with local Tesseract, skips cleanly otherwise)
Tests[C12]: tests/test_image_privacy.py::test_unusable_ocr_still_withholds_with_fixed_reason, ::test_mask_over_sane_fraction_is_withheld, ::test_ocr_failure_still_withholds_and_does_not_disclose and tests/test_image_privacy_reocr.py::test_c1_text_the_re_ocr_keeps_finding_every_pass_is_withheld_after_the_last, ::test_c2_a_re_ocr_failure_withholds_without_disclosure - core-invariants C12 (fail closed): every old withhold case stays withheld and the re-read adds three more
Pre-check[C1]: 6ecd9364 uv run pytest tests/test_image_privacy_reocr.py tests/test_image_privacy.py tests/test_image_privacy_engine.py tests/test_grade_visual.py tests/test_video_frames.py -> 113 passed t=4 blobs=tests/test_image_privacy_reocr.py:8ab9b6f,tests/test_image_privacy.py:ae4e461,tests/test_image_privacy_engine.py:5ac7acc,tests/test_grade_visual.py:4cbe009,tests/test_video_frames.py:295e96a
Pre-check[C2]: 6ecd9364 uv run pytest tests/test_image_privacy_reocr.py tests/test_image_privacy.py tests/test_image_privacy_engine.py tests/test_grade_visual.py tests/test_video_frames.py -> 113 passed t=4 blobs=tests/test_image_privacy_reocr.py:8ab9b6f,tests/test_image_privacy.py:ae4e461,tests/test_image_privacy_engine.py:5ac7acc,tests/test_grade_visual.py:4cbe009,tests/test_video_frames.py:295e96a
Pre-check[C3]: 6ecd9364 uv run pytest tests/test_image_privacy_reocr.py -> 12 passed t=1 blobs=tests/test_image_privacy_reocr.py:8ab9b6f
Pre-check[C12]: 6ecd9364 uv run pytest tests/test_image_privacy_reocr.py tests/test_image_privacy.py tests/test_image_privacy_engine.py -> 64 passed t=3 blobs=tests/test_image_privacy_reocr.py:8ab9b6f,tests/test_image_privacy.py:ae4e461,tests/test_image_privacy_engine.py:5ac7acc
Falsification[C1]: copy of src/tests/scripts in .work/tmp/reocr-mut (PYTHONPATH on the copy, control 63 passed over the three image_privacy test files): re-read loop disabled -> 10 failed; re-read filter "box wholly black" removed (every reported word counts) -> 21 failed; re-read run on a blank image instead of the sanitized one -> 21 failed; MAX_REOCR_PASSES 3 -> 2 -> 1 failed (the two-successive-re-reads test, added after this mutant first survived).
Falsification[C2]: same copy: `return` instead of raising `text_remains_after_mask` after the last pass -> 2 failed; cumulative `applied` replaced by this pass's `boxes` in the area check -> 1 failed.
Falsification[C3]: same copy: `_mask` draws nothing (`for box in []`) -> 28 failed, including the real-Tesseract test. Honest limit: the real-engine test is green without the re-read loop (pass 1 already masks every word in that image), so it proves the end-to-end output reads empty, not that the loop was needed; the loop is proven by the stubbed tests.
Metrics: start=2026-10-21T10:30:00Z end=2026-10-21T11:30:00Z wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=7 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=0 mutants=7 defects_unit=0 defects_6c=0 builder_min=unavailable

## How to verify (commands + expected)
- `uv run pytest tests/test_image_privacy_reocr.py tests/test_image_privacy.py tests/test_image_privacy_engine.py tests/test_grade_visual.py tests/test_video_frames.py` -> expected: 113 passed
- `uv run ruff check src tests scripts` -> expected: All checks passed!
- `uv run autotester doctor` -> expected: doctor: clean

## Actual outputs (from maker's own run)
```
pytest (5 files): 113 passed, 1 warning
pytest tests/test_image_privacy_reocr.py: 12 passed (real Tesseract test ran, not skipped)
uv run ruff check src tests scripts: All checks passed!
uv run autotester doctor: doctor: clean   (decision-citation lines are pre-existing advisory output)
```
Also run earlier, passing: tests/test_leak_evidence.py tests/test_oracle_responsive.py tests/test_provider_vision_integration.py tests/test_role_session_port.py tests/test_run_case_pipeline.py.
Open points for the checker: (1) a third re-mask is withheld unread rather than read a fourth time, a deliberate fail-closed bound; (2) `_leftover_boxes` ignores words wholly inside black pixels and masks any other recognised word whatever its confidence; (3) real Pathlynks screenshots were not re-run (none committed); the 46-of-52 rate should be re-measured by the checker with local data.

## Capability coverage (each new claim -> its isolating falsification)
| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| C1 | words the first pass missed are masked after a re-read of the sanitized output | tests/test_image_privacy_reocr.py::test_c1_words_missed_on_pass_one_are_masked_after_re_ocr | re-read loop disabled | 10 failed |
| C1 | the re-read reads the masked pixels | ::test_c1_the_re_ocr_reads_the_sanitized_pixels_not_the_original | re-read on a blank image | 21 failed |
| C1 | black-mask OCR noise does not withhold a clean image | ::test_c1_a_box_the_re_ocr_reports_inside_the_black_mask_is_not_readable | black filter removed | 21 failed |
| C1 | bounded passes (3) | ::test_c1_text_that_surfaces_on_each_of_two_re_reads_is_masked_and_the_third_read_is_clean | MAX_REOCR_PASSES 2 | 1 failed |
| C2 | text left after the last pass withholds | ::test_c1_text_the_re_ocr_keeps_finding_every_pass_is_withheld_after_the_last | return instead of raise | 2 failed |
| C2 | cumulative mask limit | ::test_c2_cumulative_mask_over_the_limit_is_withheld_on_a_later_pass | per-pass area check | 1 failed |
| C3 | end-to-end real engine output reads empty | ::test_c3_real_tesseract_reread_of_the_sanitized_screenshot_finds_no_word | `_mask` draws nothing | 28 failed |

## Live browser evidence
SKIP - maker smoke only; checker runs Mode D when UI changed. No UI surface changed (src/autotester/core/image_privacy.py, tests only).

## Status: ready-for-check
