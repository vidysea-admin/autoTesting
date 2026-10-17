# Verdict: image-privacy-mask (coordinator A)
Date: 2026-10-17 · Cycle checked: 1 · Policy: proportional-verification/2026-10-17.13 · Head: cfa7732b · Base: e1d59c35 (git merge-base HEAD int/1017) · Repair base: 5bad0129 (ancestor of HEAD, verified)

## Check plan
Tier L security (dual-trigger src/autotester/core/image_privacy.py:61), dual check, I am coordinator A. Lane check not applicable (repair cycle). Plan: repair diff 5bad0129..cfa7732b read in full (step 4c, 1 src line + 1 test); whole-unit scan vs e1d59c35; re-run the failed criterion C1 and the 3 affected test files (the repair touches the parser that C2 and C3 sit beside); 1 falsification for C1; security probes (synthetic secret + low-confidence word, OCR empty, real Tesseract, quote tokens, mask limit, lookup source). No full suite (6c covers it).

VERDICT: PASS
SCOREBOARD: 3/3 criteria met, 3/3 invariants hold (core-invariants 5 secrets never reach a model call, design rules, architecture security model)
TIER: L (security gate that decides which screenshot pixels reach an external model: image_privacy.py:61 `_text_boxes`; repair is image_privacy.py:87)
FAILURES: none
CAPABILITY-COVERAGE: 1/1 repaired row reproduced (C1); C2/C3 inputs unchanged in behaviour, covered by the 54-test run and probes
LIVE-BROWSER: not-applicable (changed paths: src/autotester/core/image_privacy.py, tests)
ISSUES-WRITTEN: none (dual coordinator; findings are PROPOSED-ISSUE lines)
EXECUTOR: claude-sonnet-subagent (maker build) (checker: claude-sonnet-subagent)

## Evidence (details: qa/evidence/image-privacy-mask/checker-a-c1.md)
- C1 repair: `csv.DictReader(..., delimiter="\t", quoting=csv.QUOTE_NONE)` at image_privacy.py:87 (read). Probe: tokens `"`, `"a ""b`, `c'd"` before a secret row -> all rows parsed, released, secret bands black.
- Acceptance: pytest on tests/test_image_privacy.py, test_image_privacy_engine.py, test_run_failure_artifacts.py -> 54 passed, exit 0. ruff on changed files clean.
- FALSIFY C1: tests/test_image_privacy.py::test_token_starting_with_quote_does_not_swallow_following_secret_row green in copy -> red at tests/test_image_privacy.py:295 `assert (255, 255, 255) == (0, 0, 0)` after removing `quoting=csv.QUOTE_NONE`; the named assertion, not an import error. Bound tree untouched.
- C1 security probe: synthetic image, confident secret line plus low-confidence word: released, both black, far corner white. Real Tesseract (Windows path) on a screenshot with password/SSN/tiny text: released, re-OCR of the output finds none of the planted strings.
- C2 probes: header-only/empty/blank-only TSV, text-free real image -> `no_recognized_text`; nan/inf -> `uncertain_ocr`; non-blank out-of-image box -> `invalid_ocr_geometry`; short row, conf `abc`, CR in token -> `sanitation_failed`. All withheld with fixed codes, no OCR text in any reason.
- C3: real engine found via the Windows path with tesseract off PATH; env/dotenv/Windows precedence tests pass (5 lookup tests inside the 54).
- Hint 3, MAX_MASK_FRACTION 0.6: fail-safe. It only adds a withhold path and runs before any pixel is drawn (image_privacy.py:139-141); a 20-band dense page was withheld `mask_exceeds_limit`. Live headroom is thin (0.50 vs 0.6 in the manifest), an availability note, not a privacy one.
- Hint 4, `.env` read: `dotenv_values(...).get("AUTOTESTER_TESSERACT")` returns one value, never logged or placed in a message or os.environ; a directory or missing file is rejected. The path is owner-controlled (env/.env), so not abusable beyond the repo owner; see P3 for the one gap.
- Step 4c: repair diff is 1 src line + 1 new test, no removal. Whole-unit scan vs e1d59c35: product/test files all in What-changed; the only removed test row is the `conf=84` withheld case, which C1 inverts by contract; `uncertain` fixture 30 -> 101 keeps fail-closed intent; no def/class/export removed.

PROPOSED-ISSUE: {"sev":"low","type":"security-gap","title":"Blank low-confidence OCR row with out-of-image geometry is skipped unmasked while a non-blank one withholds","where":"src/autotester/core/image_privacy.py:95-98","fix":"clamp the box to the image and mask it instead of `continue`","proof":"probe p7_blank_badgeo: row x=280..340 on a 300 px image released with that region unmasked; real Tesseract clamps boxes so reach is low"}
PROPOSED-ISSUE: {"sev":"medium","type":"security-gap","title":"Text Tesseract reports no row for at all is released unmasked (pre-existing at e1d59c35, now the only residual path since uncertain words are masked)","where":"src/autotester/core/image_privacy.py:106-109","fix":"consider a pixel-level residual check (for example mask regions of non-background ink outside every band) or a documented acceptance of the limit; not a regression","proof":"real Tesseract probe: a 235-grey `token: ZXCVBNM98765` line stays readable in the released image; a larger word beside tiny text pokes below its band (qa/evidence/image-privacy-mask/checker-a-c1.md)"}
PROPOSED-ISSUE: {"sev":"low","type":"security-hardening","title":"AUTOTESTER_TESSERACT accepts a relative path and expands ${OTHER} from the repo .env","where":"src/autotester/core/image_privacy.py:46-55,63-65","fix":"require an absolute path and use dotenv_values(..., interpolate=False)","proof":"probe_env: relative `tesseract.exe` accepted from cwd and executed by name; `${OTHER}` expanded into the candidate; never logged"}

EXPLANATION: The cycle-0 failure (a token starting with a double quote made csv.DictReader swallow the rows after it, releasing a secret line unmasked) is fixed in place at image_privacy.py:87 and pinned by a test that goes red on the named assertion when the fix is removed. C2 and C3 behaviour is unchanged and re-evidenced by the 54-test run and my own probes; nothing found is a regression, so the three notes above are non-blocking proposed ledger rows. Wall time includes reading the policy; the 6c pre-push run covers the full-suite trigger.
Metrics: start=2026-10-17T23:01:17Z end=2026-10-17T23:11:00Z wall_min=10 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=1 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-17.13 lane=normal check_s=583 mutants=0 defects_unit=0 defects_6c=0
