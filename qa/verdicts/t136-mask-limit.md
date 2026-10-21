# Verdict - t136-mask-limit (coordinator A of a dual check)
Date: 2026-10-21 · Bound to: D:/autoTesting/.worktrees/t136-mask-limit · Head checked: d530dbe1 (code 7ac56034) · Base: 8956c9bc (= merge-base with int/1019) · Cycle checked: 0
Policy-Version: proportional-verification/2026-10-19.17 · Dual check: coordinator A (no side effects; findings are PROPOSED-ISSUE lines)

## Check plan (step 0)
Diff = 1 product constant (`image_privacy.py:35-38`, 5 lines incl. comment), 3 new tests, manifest. No UI, no data, no prompt change -> no Mode D, no persona walk, no outcome-grader. Routed checks: (1) criterion tests + falsification per changed criterion (C1, C2); (2) security read of the masking path (dual-trigger `image_privacy.py:38`); (3) independent real-Tesseract probe of a kept image (the manifest's open point); (4) fail-closed (C12) regression: all other users of `sanitized_images`. Nothing below reuses the maker's run outputs.

## Evidence (all commands run by me on d530dbe1)
- `uv run pytest tests/test_image_privacy_engine.py tests/test_image_privacy.py tests/test_grade_visual.py` -> 66 passed.
- Wider closure: `uv run pytest <every tests/ file naming image_privacy|sanitized_images>` -> 210 passed (152 s). src callers: grade_images, run_artifacts, video_frames, vision_probe, leak_evidence. No test depends on the old 0.6 value (git grep: only engine test line 173 mentions it, as "over the old limit").
- `uv run ruff check src tests scripts` -> All checks passed. `uv run autotester doctor` -> doctor: clean.
- Candidates (`shard_suite.py --list --candidates`): reference hits for MAX_MASK_FRACTION / mask_exceeds_limit are the three selected test files; the only product-code sibling of the constant is `image_privacy.py:8,125` (docstring and the single comparison); no second limit exists. The 541-file import closure is not required: a constant changed, no signature or return shape.
- Falsification C1 (copy via git archive, never the bound tree): `MAX_MASK_FRACTION = 0.6` -> test_dashboard_shaped_screenshot_is_kept_with_every_text_band_masked FAILED, 12 passed; green before (13 passed in the bound tree).
- Falsification C2 (copy): `stages/grade_images.py:88` `if unseen` -> `if False` -> 3 failed (..._screenshot_was_withheld, ..._is_absent, ..._dashboard_screenshot_is_withheld_for_mask_size), 11 passed.
- Independent real-OCR probe (my script, real Tesseract, synthetic 1366x850 page with a password line, an e-mail line, an API-key line and a red non-text block; nothing real, nothing committed): 22 lines -> fraction 0.734, KEPT; re-OCR of the kept output found 0 words; 0 of the original's ink pixels (sampled x=60..700, every row) were left un-blacked. 26 lines -> 0.842 and 30 lines -> 0.929, both WITHHELD `mask_exceeds_limit`.

## Criteria
- C1 MET: a dashboard-shaped screen (0.648 synthetic-OCR, 0.734 real OCR) is kept with every text band black across the full width (engine test checks left, middle and right pixels of each band, including the confident-secret line and the low-confidence word); a mostly-text screen (0.842, 0.887) is still withheld.
- C2 MET: a screenshot withheld for `mask_exceeds_limit` with a met assertion stays INCONCLUSIVE (images_seen 0); `stages/grade_images.py` is unchanged (diff of src/autotester/stages is empty), and the C2 falsification goes red when the hold is removed.
- C12 (fail closed) holds: every withhold path (`local_ocr_unavailable`, `uncertain_ocr`, `invalid_ocr_geometry`, `no_recognized_text`, oversize, animated, `mask_exceeds_limit` at a low limit) still has its passing test; only the one numeric threshold changed.

## Security judgement: is 0.75 safe?
Yes. The limit decides only whether an image is released at all; it never changes which pixels are masked. `_text_boxes` (unchanged, `image_privacy.py:90-114`) blacks out every recognized text line across x=0..width plus every low-confidence word, `_sanitize_one` draws all boxes before saving, and `_check_mask_area` (`:117-126`) runs before any release and is a pure withhold gate. Raising the cap lets through only images whose masked share is between 0.6 and 0.75, so the unmasked remainder in a kept image falls from at least 40% to at least 25%: less original content crosses the boundary, not more. The residual risk of a kept image is text OCR did not see (artwork, faces, odd glyphs), which the fraction does not measure and which the module docstring already states as the standing limit. No OCR-recognized secret or PII text can escape in a kept image (probe: 0 residual words, 0 un-blacked ink pixels).
Is 0.75 evidence-justified? Partly. The only measurement is 0.621 on one page (two screenshots of the same Pathlynks dashboard, per the manifest; I did not open the real screenshots); 0.75 is a judgement with a 0.13 margin. A denser dashboard (about 0.76 and up) would be withheld again, and a kept page at 0.73 is about 70% black, so its value to the grader is layout only. It is safe and gate-approved (qa/gates/t136-withheld-screenshot-pass.md, answer A), so not a FAIL; recorded as P1.

## Findings (non-blocking)
PROPOSED-ISSUE: {"id":"P1","severity":"low","type":"evidence","summary":"MAX_MASK_FRACTION 0.75 rests on one measured page (0.621); no distribution of real dashboards backs the margin","fix":"when more post-login screenshots exist (other Pathlynks roles, T-212/T-218 legs), record their mask fractions and re-justify or adjust the limit; consider logging the fraction on withhold"}

VERDICT: PASS
SCOREBOARD: 2/2 criteria met, 1/1 invariants hold (C12 fail closed; B11 no recognized text unmasked in a kept image)
TIER: L (security masking guard, dual-trigger image_privacy.py:38; product change is one constant, 5 lines)
FAILURES: none
CAPABILITY-COVERAGE: 2/2 rows reproduced (C1 limit falsification red, C2 hold falsification red)
LIVE-BROWSER: not-applicable (changed paths: src/autotester/core/image_privacy.py, tests only)
ISSUES-WRITTEN: none (dual coordinator: PROPOSED-ISSUE P1 above)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The change is one constant; the masking itself (full-width bands for every recognized line and every low-confidence word) is untouched, and my own real-Tesseract probe shows a 0.734-fraction page kept with zero residual OCR text and 0.84+ pages still withheld. Both falsifications went red in isolated copies and the 210-test closure of all image_privacy users is green. The 0.75 value is a judgement from one measurement, flagged as P1.
Metrics: start=2026-10-21T07:05:00Z end=2026-10-21T07:26:00Z wall_min=21 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=1260 mutants=0 defects_unit=0 defects_6c=0
