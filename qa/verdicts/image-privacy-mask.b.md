# Verdict B - image-privacy-mask (coordinator B, dual check)
Cycle checked: 1
Date: 2026-10-18 (checker clock 2026-10-17T23:1xZ UTC)
Head: cfa7732b on wave/image-privacy-mask; base e1d59c35 (git merge-base with int/1017 verified); repair base 5bad0129 (ancestor of HEAD verified)
Policy-Version: proportional-verification/2026-10-17.13

## Plan
Repair-scoped check (cycle 1). Failed criteria on side B: none. Repair diff 5bad0129..cfa7732b read in full: 1 product line (src/autotester/core/image_privacy.py:87, `csv.DictReader(..., delimiter="\t", quoting=csv.QUOTE_NONE)`) and 1 new test (tests/test_image_privacy.py:285-295) plus manifest text. Criterion C1 is the repaired one (re-run + falsified); C2/C3 input files are untouched by the repair, but C2 is exercised by the same file run and by the fail-closed probes below. Step 4c whole-unit scope scan vs e1d59c35: src image_privacy.py, tests x3, docs/MAP.md, qa/* only; nothing outside the manifest's declared scope. No full suite (tier L security: pre-push 6c owns it).

## Evidence
- `pytest tests/test_image_privacy.py tests/test_image_privacy_engine.py tests/test_run_failure_artifacts.py -p no:xdist -o addopts=` (TMP in session scratchpad) -> 54 passed in 18.03s (53 at cycle 0 + the new test).
- `ruff check src tests` -> All checks passed!
- Falsification C1 (copy of `git archive HEAD src tests scripts pyproject.toml`, `autotester.__file__` printed from the copy): `-k quote` GREEN 1 passed; with `, quoting=csv.QUOTE_NONE` removed -> RED, AssertionError at tests/test_image_privacy.py:295 (secret row after the `"hi` token released unmasked); copy only, bound tree untouched.
- Synthetic probe (scratchpad probe_c1b.py, module path printed = worktree src; synthetic images only):
  - real Tesseract, black "password: hunter2SECRET" + black "api_key sk-live-ABC123" + faint grey text: released 1, withheld 0; both secret bands blacked; re-OCR of the released PNG yields no words.
  - blank image (OCR returns nothing) -> withheld, reason `no_recognized_text`.
  - TSV tokens `"hi`, lone `"`, `a"b`, `""`, `'x` followed by a high-confidence secret row: all 2 boxes, the secret row 2 band covered.
  - token containing `\r` -> csv.Error, row with missing fields -> TypeError; both land in `sanitized_images`'s generic handler -> `sanitation_failed`, image withheld (fail closed).
- Hint (3) MAX_MASK_FRACTION 0.6: `_check_mask_area` raises `mask_exceeds_limit` and the image is withheld before any pixel is drawn (image_privacy.py:115-123, 139-140). It withholds more, never less: fail-safe.
- Hint (4) `.env` read: `_env_tesseract` (image_privacy.py:46-55) reads the process env, else `dotenv_values(repo .env).get("AUTOTESTER_TESSERACT")`; one key retrieved, no log or exception text carries a value; a non-file or non-existent path is skipped (line 64) and OSError is swallowed; a UnicodeDecodeError would surface as `sanitation_failed` (withhold). The executable is run as an argv list with no shell (line 74), so abuse is bounded to whoever can already write the repo-root `.env` or process env (the owner, who already holds every secret in it).

## Result
C1 met (repair works, falsified red), C2 met (fail-closed paths hold, incl. csv.Error / short row), C3 met (unchanged by repair; its 5 lookup tests are inside the 54 passed). Invariants: I5 (secrets never reach a model call or artifact) holds for the probed inputs; I2 design rules: file stays under 300 lines, doctor not re-run (repair is 1 line).

PROPOSED-ISSUE: {"severity":"low","title":"Faint text that Tesseract does not emit at all (no level-5 row) is not masked","evidence":"probe_c1b.py: grey (215,215,215) 'faintword xyz' on white returned lum extrema (215,255) after sanitation, i.e. left visible while neighbouring text lines were blacked; same behaviour at base, documented as heuristic OCR in the module docstring","fix":"optionally mask the whole image band or add a luminance-contrast pass; candidate, not a unit"}

VERDICT: PASS
SCOREBOARD: 3/3 criteria met, 2/2 invariants hold (I5, I2)
TIER: L (security gate keeping secrets out of model calls, src/autotester/core/image_privacy.py:61; dual check, coordinator B)
FAILURES: none (P1 is a non-blocking low proposal)
CAPABILITY-COVERAGE: not-applicable (backend privacy gate, no UI)
LIVE-BROWSER: not-applicable (src/autotester/core/image_privacy.py)
ISSUES-WRITTEN: none (dual check: PROPOSED-ISSUE P1 above)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The cycle-1 repair (QUOTE_NONE at image_privacy.py:87) closes the quote-start token swallow; the new test fails without it and every quote and malformed-row variant I probed either masks the secret row or withholds the image. No full suite run (pre-push 6c).
Metrics: start=2026-10-17T23:02:00Z end=2026-10-17T23:12:00Z wall_min=10 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=1 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-17.13 lane=normal check_s=600 mutants=0 defects_unit=0 defects_6c=0
slow: reading checker protocol 3 min
