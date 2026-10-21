# Verdict B - t136-mask-limit (coordinator B, blind)
Date: 2026-10-21 · Bound to D:/autoTesting/.worktrees/t136-mask-limit · Head 8fc7c215 (product/test files = 7ac56034) · Base 8956c9bc · Policy proportional-verification/2026-10-19.17
Cycle checked: 0

## Check plan
Logic changed (one constant in a privacy guard) -> affected tests + floor falsification. Security trigger image_privacy.py:38 -> security read of the mask path plus a real-image residual-text probe. No UI/prompt/data surface -> no Mode D, no persona walks, no live model call. No full suite (policy .7).
TIER: L (security masking guard, dual-trigger src/autotester/core/image_privacy.py:38, as dispatched; not raised)

## Evidence (every command run by this checker; detail in qa/checkpoints/t136-mask-limit.b.md)
- `uv run pytest tests/test_image_privacy_engine.py tests/test_image_privacy.py tests/test_grade_visual.py` -> 66 passed. ruff clean. doctor: clean.
- Diff read in full (`git diff 8956c9bc 7ac56034`): the only src change is image_privacy.py:35-38 (0.6 -> 0.75 plus comment). `_text_boxes` (image_privacy.py:85-114) is unchanged: every recognized line becomes a full-width band (0, top-4, size[0], bottom+4) and every word under MIN_CONFIDENCE 85 gets its own box. stages/grade_images.py unchanged.
- C1: test_dashboard_shaped_screenshot_is_kept_with_every_text_band_masked (fraction 0.648, pixel-checked left/middle/right of 19 bands) and test_mostly_sensitive_screenshot_is_still_withheld (0.887 -> mask_exceeds_limit). Falsified: M1 limit 0.6 -> 1 red; M4 limit 0.95 -> withhold test red. M3 (band shrunk to word extent) -> 5 red, so full-width masking is pinned.
- C2: test_g2_pass_is_held_when_a_dashboard_screenshot_is_withheld_for_mask_size; M2 (grade_images.py:88 `if unseen` -> `if False`) -> 3 red.
- C12 fail-closed: existing withhold tests (unusable OCR, mask over limit, geometry) green; no withhold branch except the constant changed.
- Real-image probe, 52 real Pathlynks screenshots (all 22 of run-01M5A1... plus 30 random others): all 52 kept, max mask fraction 0.636 (both run-5 dashboards 0.621), 0 originally recognized word boxes left unmasked (every box pixel black). No text the masker RECOGNIZED escapes at any fraction up to the new limit.

## Judgement on the open point (is 0.75 safe, is it justified)
- The raise adds no leak path for recognized text: the guard only decides release vs withhold, and masking of recognized text is identical at 0.6 and 0.75 (M3 + probe). 0.75 is acceptable. Evidence for the value: real data tops out at 0.636 across 52 images (headroom 0.11); a synthetic mostly-text screen at 0.887 is still withheld. It is a judgement, not a derived threshold (P3, low).
- Residual risk the guard never covered and the raise now exposes on the dashboard: text the FIRST Tesseract pass does not recognize is not masked. Re-OCR of the sanitized output of the two newly kept run-5 dashboards finds 5 words with conf >= 92 still readable in unmasked pixels (shapes only: 'Aa','Aaaaa' at y=171; 'Aaaaaaaa','Aaaaaaa' at y=452; 'Aaaaaa' at y=581; letters only, no digit, no @, so not credential-, phone- or email-shaped; content deliberately not read, Pathlynks data rule). The same class exists in images kept at the OLD limit (re-OCR hits in 46 of 52, e.g. 11 words in case_093f5070df7 at fraction 0.34), so it is pre-existing and independent of the constant; the module docstring says OCR is heuristic. Not a FAIL: the changed code (a constant) is not the defect, and B11 enumerates credentials, contact details and configured fields, which these shapes do not match. I cannot rule out a person name in the header (y=171); that is the maker's and Umesh's call.

FAILURES: none
PROPOSED-ISSUE: {"id":"P1","sev":"medium","area":"security/image_privacy","title":"Single-pass OCR leaves readable text in kept images: re-OCR of the sanitized output finds conf>=85 words (46 of 52 real Pathlynks screenshots; 5 words on each newly kept T-136 dashboard)","evidence":"qa/checkpoints/t136-mask-limit.b.md; reproduce: sanitized_images([png]) then _local_ocr(batch.paths[0]), count level-5 words conf>=85","fix_direction":"after masking re-run OCR on the output and mask or withhold when recognized text remains (or OCR a contrast-inverted copy); add a test with light-on-dark text","pre_existing":true}
PROPOSED-ISSUE: {"id":"P2","sev":"low","area":"tests","title":"The 2 new engine tests use synthetic OCR rows, so no test pins the residual-text property on a kept dense image","fix_direction":"cover with P1's second-pass check"}
PROPOSED-ISSUE: {"id":"P3","sev":"low","area":"image_privacy.py:38","title":"0.75 rests on one measured dashboard (0.621) plus a synthetic bound; no density-vs-leak analysis","fix_direction":"record the 52-image distribution (max 0.636) in the comment or a decision entry; revisit if a denser real screen is withheld"}

VERDICT: PASS
SCOREBOARD: 2/2 criteria met (C1, C2), 1/1 invariants hold (core-invariants C12)
TIER: L (security masking guard image_privacy.py:38)
CAPABILITY-COVERAGE: 3/3 rows reproduced (C1 kept, C1 mostly-sensitive withheld, C2)
LIVE-BROWSER: not-applicable (src/autotester/core/image_privacy.py and tests only)
ISSUES-WRITTEN: none (dual check: PROPOSED-ISSUE lines P1-P3 only)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The constant change is as described, the recognized-text masking path is untouched and pinned by tests (M3 red when bands are narrowed), the withhold guard and the INCONCLUSIVE hold still work (M2, M4 red), and real screenshots show no recognized word left unmasked. One security caveat remains, pre-existing OCR-miss text (P1), which the raise newly exposes on the run-5 dashboard; flagged for the maker and Umesh, not a defect of this change.
Metrics: start=2026-10-21T07:07:00Z end=2026-10-21T07:33:00Z wall_min=26 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=4 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=1560 mutants=2 defects_unit=0 defects_6c=0
