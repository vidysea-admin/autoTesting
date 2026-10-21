# Verdict B - at1363-reocr (coordinator B, blind)
Date: 2026-10-21 · Bound to D:/autoTesting/.worktrees/at1363-reocr · Head f38624ce (code 6ecd9364) · Base 83e8f71e · Policy proportional-verification/2026-10-19.17
Cycle checked: 0
Verdict: PASS

## Check plan
Logic change in a privacy guard (dual-trigger src/autotester/core/image_privacy.py:186). Plan: scoped tests, lint/doctor, full diff read, 1 falsification per criterion (C1, C2, C3) in copies, skip-path check for C3, real-screenshot re-measure (read-only, 38 local PNGs, base vs head), adversarial synthetic probe.
TIER: L (security masking guard, dual-trigger image_privacy.py:186, as dispatched; not raised)

## Evidence (all run by this checker; detail in qa/checkpoints/at1363-reocr.b.md and qa/evidence/at1363-reocr-b/)
- `uv run pytest tests/test_image_privacy_reocr.py tests/test_image_privacy.py tests/test_image_privacy_engine.py tests/test_grade_visual.py tests/test_video_frames.py` -> 113 passed. ruff clean. `autotester doctor` clean.
- Diff read in full (`git diff 83e8f71e..6ecd9364`, 4 files): _sanitize_one masks pass 1, then up to MAX_REOCR_PASSES=3 re-reads of the saved sanitized file; _leftover_boxes masks every non-blank word whose box has a non-black pixel (any confidence) with its line band; wholly-black boxes are ignored; _mask checks the CUMULATIVE box list against MAX_MASK_FRACTION (0.75, unchanged); after the 3rd re-mask the image is withheld text_remains_after_mask (never trusted unread). The destination only reaches batch.paths on success. _words is one shared validator (NaN, conf>100, geometry fail closed). The delimiter is now a literal tab character, equal to the old "\t".
- C1 met: the re-read reads the sanitized pixels, masks leftovers, bounded, else withholds (test_c1_* green; the stub OCR sees BLACK pixels on the re-read).
- C2 met: MAX_MASK_FRACTION unchanged; old withhold tests (unusable OCR, over-limit, geometry, OCR failure) green; tests/test_grade_visual.py green (withheld -> INCONCLUSIVE, never PASS).
- C3 met: synthetic PIL images + per-pass stub OCR; the real-Tesseract test ran (inside the 113 passed). In a copy with every tesseract lookup removed it SKIPS ("not provisioned"): 11 passed 1 skipped.
- Existing-test edits (3 tests) judged intent-preserving, not weakened: nested test 1->2 and 2->4 calls (a nested pass adds no OCR still holds: 2 stays 2); snapshot test asserts the decoded-snapshot property on the FIRST read, later reads are of the masked copy (cannot equal the source); video test failure moved from call 2 to call 3 = frame 1's first read (frame 0 now takes 2 reads). No assertion deleted, no threshold lowered, no skip added.

## Falsification (1 per criterion, in copies under .work/tmp/b-mut, bound tree untouched; control copy 64 passed over the three image_privacy test files)
- C1: re-read ignores confident words (`_confidence < MIN_CONFIDENCE and` added in _leftover_boxes) -> 5 failed.
- C2: `_check_mask_area(applied, ...)` removed from _mask -> 3 failed (incl. test_mask_over_sane_fraction_is_withheld, test_mostly_sensitive_screenshot_is_still_withheld).
- C3: mask fill black -> white -> 25 failed (incl. the real-Tesseract engine tests).

## Judgement: can secret/PII text survive in a KEPT image?
Re-measure on 38 real local Pathlynks screenshots (read-only; method of P1 in t136-mask-limit: sanitize, then default-psm OCR of the kept output; qa/evidence/at1363-reocr-b/):
- base 83e8f71e: 38/38 kept, 34/38 still have readable words in the output (162 words conf>=60). The AT-1363 defect reproduces.
- head: 18 kept, 20 withheld (19 mask_exceeds_limit, 1 text_remains_after_mask); 0 of 18 kept images has a readable word on the default read. The AT-1363 acceptance measure is met.
- Residual, not a C1 failure (filed as P1): a sparse-mode read (psm 11) still finds words in 16 of the 18 kept images. I opened one kept output (kept25, a pre-login screen): "Sign In", "Sign Up", the "Password" label, "Login" and a text fragment are visibly readable. They are UI labels, not credential/contact/configured values (what B11 enumerates). Cause: the re-read uses the same default page segmentation as pass 1, so it shares that blind spot.
- Black-box rule: sound. Only a box with NO non-black pixel is ignored, so a partly black box is masked and counted; a readable word cannot sit in an all-black box. Cost: a mask-edge word box is re-masked each pass, bounded by 3 passes and the cumulative limit.
- Synthetic dark-theme probe (real Tesseract): large and mid text, an email and a phone number are masked and unreadable on psm 3, 11 and 12; text Tesseract never recognizes (10-12 px dim "tiny private note", an Aadhaar-shaped string) stays in the kept image, as before. This is the inherent heuristic limit in the module docstring, not introduced here.

FAILURES: none
PROPOSED-ISSUE: {"id":"P1","sev":"medium","area":"security/image_privacy","title":"Re-read uses the same default Tesseract page segmentation as pass 1; a sparse-mode read (psm 11) still finds words in 16 of 18 kept real screenshots (Login, Sign In/Up, Password label visible in kept25)","evidence":"qa/evidence/at1363-reocr-b/measure.py and words2.py (psm 11 columns)","fix_direction":"also re-read with --psm 11 (or a contrast-inverted copy) and mask or withhold on any hit; add a light-on-dark test","pre_existing":true}
PROPOSED-ISSUE: {"id":"P2","sev":"medium","area":"product/T-136","title":"The cumulative mask now withholds 19 of 38 real screenshots as mask_exceeds_limit (base kept all 38); the post-login dashboards that motivated the 0.6 -> 0.75 raise withhold again, so their visual coverage stays INCONCLUSIVE","evidence":"qa/evidence/at1363-reocr-b/measure-head.txt vs measure-base.txt","fix_direction":"Umesh decides: accept the fail-closed trade or tune the limit or line-band width; not a checker call","pre_existing":false}
PROPOSED-ISSUE: {"id":"P3","sev":"low","area":"tests","title":"test_c3 real-engine test is green without the re-read loop (maker disclosed it); real-engine coverage of the loop itself exists only in stubs","fix_direction":"add a real-engine image where pass 1 misses a word that a re-read finds","pre_existing":false}

Metrics: start=2026-10-21T10:49:00Z end=2026-10-21T11:06:00Z wall_min=17 agent_min=17 blocked_min=0 suite_runs=0 repeat_runs=0 mutations=3 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=1020 mutants=0 defects_unit=0 defects_6c=0
