# Verdict - at1363-reocr (coordinator A of a dual check)
Verdict: PASS
Cycle checked: 0
Bound to: D:/autoTesting/.worktrees/at1363-reocr, code 6ecd9364, head f38624ce (base 83e8f71e is an ancestor; manifest/qa commit only after the code commit)
Policy-Version: proportional-verification/2026-10-19.17
TIER: L - dual-trigger security src/autotester/core/image_privacy.py:186 (B11 masking guard); not raised or lowered

## Check plan
Logic changed in a privacy guard: affected tests, one falsification per changed criterion (C1, C2, C3) in a copy, step 4c diff read, real-engine readability re-measure on local screenshots. No UI change, so no Mode D / walks. No LLM prompt change.

## Criteria
- C1 PASS. `_sanitize_one` (image_privacy.py:171-191) masks pass-1 boxes, then re-reads the sanitized file up to MAX_REOCR_PASSES=3 times, masks every leftover word with its line band, returns only on a clean read, and withholds `text_remains_after_mask` if the third re-mask is unread. Tests: reocr C1 tests read the masked pixels (pixel sequence [WHITE, BLACK] asserted), bound reads at 1+3. Falsified in a copy (green 64 before, red after): `_leftover_boxes` never counts words -> 5 failed; re-mask not drawn -> 3 failed.
- C2 PASS. Limit/constants unchanged (MAX_MASK_FRACTION 0.75; diff only adds MAX_REOCR_PASSES). Cumulative check in `_mask` (:163-164). Falsified: area check removed -> 3 failed; limit doubled -> 2 failed. Withheld -> INCONCLUSIVE rests on tests/test_grade_visual.py (unchanged, green).
- C3 PASS. Synthetic PIL images with per-pass stub OCR; the real-Tesseract test ran and PASSED here (-rA), and skips cleanly when absent (copy with discovery disabled: 11 passed, 1 skipped with the reason). Falsified: `_mask` no longer saves the mask -> 24 failed.
- C12 (fail closed, manifest-cited) PASS: all old withhold cases unchanged and green; the re-read adds three more fixed-reason withholds (OCR failure, bad geometry, text remaining).

## Judged in particular
- Wholly-black rule (:142 `getextrema()[1] > 0`): a word is ignored only when every pixel of its box is 0 in grey; one non-black pixel makes it a leftover and it is masked. Text cannot be read from an all-black box, so no text survives by this rule; a partial-black box is conservatively masked (fail closed). Mutant that counts nothing is caught.
- Edits to existing tests are intent-preserving: test_nested (OCR calls 1->2 and 2->4: reuse still proved, the nested pass adds zero); test_ocr_uses_decoded_snapshot (snapshot assertion kept for the first read, `path != screenshot` kept for all, final black-pixel assertion kept); test_video_frames (injected failure moved 2->3 so it still hits frame 1). No assertion deleted, no threshold lowered, no skip added. `delimiter="\t"` became a literal tab character in `_words` (same value, ruff clean): cosmetic.
- `_text_boxes` behaviour re-read against base: same boxes, same order, same errors.
- Real screenshots (38 PNG under live-t136-r5 runs, read-only, nothing committed). Independent probe = 3x upscale Tesseract psm 11 + 6, words >=3 alnum, conf>=50. Pass-1-only masking (base behaviour): 38 kept, 37 with readable words, 310 words (8.2/image), 34 images with >=3 words. New code: 18 kept, 20 withheld (19 mask_exceeds_limit, 1 text_remains_after_mask). On the 18 kept, words fell from 144 to 26 (2 images clean, 4 with >=3 words). Residue seen: partner-logo captions (e.g. a school-name logo strip), a "Login" button label, clipped glyph fragments at a band edge. Not credentials, but proves a stronger reader than the pipeline's own 1x OCR still reads some kept pixels (heuristic limit already stated in the module docstring).

## Findings (PROPOSED-ISSUE, none blocking)
PROPOSED-ISSUE low: on 38 real Pathlynks screenshots the new loop withholds 20 (53%), 19 of them `mask_exceeds_limit` from cumulative re-masking, against 0 withheld before. Fail-closed and within C2 (limit unchanged), but visual coverage drops sharply; Umesh may want the 0.75 limit or the leftover-band rule (a full-width band per OCR noise word) reviewed against real data. Evidence: scratchpad measure.py output, counts above.
PROPOSED-ISSUE low: residual readable text (logo captions, "Login", partial glyphs) survives in 16 of 18 kept real screenshots under a 3x-upscale probe; consider a second read at 2x-3x scale in the re-read pass (not a criterion of AT-1363).
PROPOSED-ISSUE low: the real-Tesseract test passes without the loop (manifest says so); it proves the output reads empty, not that the loop was needed.

## Floor
Falsification 1 per changed criterion met (C1 x2, C2 x2, C3 x1, plus skip-path check; 5 mutants, all red, copy at D:/autoTesting/.work/tmp/chkA-mut, tree restored and identical). Step 4c diff read in full (5 files, +315/-30). Re-run: 113 passed (5 files), ruff All checks passed, autotester doctor clean. No full suite run. No .env opened, no push, no merge.

Metrics: start=2026-10-21T10:40:00Z end=2026-10-21T11:05:00Z wall_min=25 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=5 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=1500 mutants=5 defects_unit=0 defects_6c=0
