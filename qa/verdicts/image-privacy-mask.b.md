# Verdict (coordinator B) - image-privacy-mask
Date: 2026-10-17 · Cycle checked: 0 · Policy: proportional-verification/2026-10-17.13 · Tier L (security, dual) · Base e1d59c35 · Head e975ff60 (product d6ab9e30, tests 7ef9f9c8)

## Check plan
Read the full src diff and the three test diffs; criteria C1-C3 vs manifest text; protected-test judgement; security probes with real Tesseract; one falsification per criterion in a copy; affected tests. No full suite (hint 5). No other coordinator artifact read.

## Evidence (all run by me)
- `pytest tests/test_image_privacy.py tests/test_image_privacy_engine.py tests/test_run_failure_artifacts.py -p no:xdist -o addopts=` in the worktree -> 53 passed. `autotester.__file__` resolves to the worktree src. `ruff check src tests` -> All checks passed.
- Importers: test_grade_evidence, test_provider_vision_integration, test_run_case_pipeline, test_video_frames, test_vision_probe, test_mutation_check -> 127 passed (53 + 127 = the manifest's 180).
- Falsification (copy of `git archive HEAD` under the session scratchpad, GREEN 49 passed in the two privacy files first, one isolated copy per mutant):
  - C1: remove the `_check_mask_area` call -> red `test_mask_over_sane_fraction_is_withheld`; drop the low-conf `boxes.append` -> red `test_low_confidence_box_is_blacked_next_to_planted_secret[]`.
  - C2: `confidence > 100` -> `> 1000`, and dropping the NaN test -> red `test_uncertain_or_invalid_ocr_withheld` and `test_unusable_ocr_still_withholds_with_fixed_reason`.
  - C3: swap env/Windows order in `_find_tesseract` -> red `test_lookup_env_beats_windows_and_dotenv`, `test_lookup_reads_only_that_key_from_repo_dotenv`.
- Security probe (real Tesseract, synthetic images, head code, scratch script): black "Password hunterTwo" + grey 200 "faint blurry word" -> released, re-OCR finds no words, secret region 80% black; blank white image -> WITHHELD `no_recognized_text`; near-invisible (235) secret -> recognised, masked; text-dense page -> WITHHELD `mask_exceeds_limit`; no engine -> `local_ocr_unavailable`; `AUTOTESTER_TESSERACT` pointing nowhere -> `local_ocr_unavailable`. No OCR text, path or exception in any reason.

## Criteria
- C1 MET: image_privacy.py:97-100 adds the word box for conf < 85 (incl. 0, -1) and the line band for any non-blank word (:102-108); `_check_mask_area` (:114-123) is called before any pixel is drawn (:140). Every secret band rule is unchanged (the band loop :109-112).
- C2 MET: NaN / >100 -> `uncertain_ocr` (:91-92); non-blank bad geometry -> `invalid_ocr_geometry` (:96-98); no non-blank word -> `no_recognized_text` (:113); OCR exception -> generic `sanitation_failed` (:183-186); missing engine -> `local_ocr_unavailable` (:66). A blank row below 85 with valid geometry is masked but cannot release an image alone (blank-only -> `no_recognized_text`, covered by the test).
- C3 MET: `_find_tesseract` :56-66: `shutil.which`, then env/.env (`_env_tesseract` :46-53), then `WINDOWS_TESSERACT`, first `is_file()` wins, else fail closed.

## Protected test changes (hint 1)
- test_run_failure_artifacts.py: the fixture box is 1 px tall so its band (rows 2..11 of 20 = 0.5) stays under 0.6; the "uncertain" case now uses 101. Assertions untouched; the case still proves a fail-closed withheld image (the test asserts `image_reasons == [..., "uncertain_ocr"]`). Not weakened.
- test_image_privacy.py: `conf=84` left the withheld list because contract C1 changes it to masked; the same value is now asserted as a masked-and-released pixel test (`[84,40,0,-1]`, pixel (12,12) black, (50,50) white), a stricter property. The two `shutil.which` patches became a `no_engine` fixture that also blanks the Windows path, env key and repo `.env`: it asserts the same `local_ocr_unavailable`. No assertion removed, no skip/xfail added.

## Security read (hints 2-4)
- Secret pixels: only text Tesseract emits as a level-5 row is masked, as before. Faint text Tesseract emits no row for (grey 215 on white, probed) is released at the head AND at base e1d59c35 (same probe, tesseract on PATH): not a regression, filed P2 low.
- Hint 3: 0.6 only adds withholding (probe: dense page withheld), fail-safe. Product cost: dense pages now give INCONCLUSIVE; the live set is 0.11-0.50.
- Hint 4: `_env_tesseract` returns one key and never logs it; `dotenv_values` parses the whole file with interpolation (probe: `${SECRET_PROBE}` expanded into the path, which then fails `is_file()`, no leak, `os.environ` untouched). The path is executed only if it is a file and PATH has no tesseract. Operator-set (repo owner), no privilege beyond owning the repo. Hardening notes P1, P3.

PROPOSED-ISSUE: {"type":"security-hardening","severity":"low","title":"WINDOWS_TESSERACT is a relative path on POSIX and AUTOTESTER_TESSERACT may be relative","detail":"image_privacy.py:36,62-66: Path('C:/Program Files/Tesseract-OCR/tesseract.exe') is not absolute on POSIX (PurePosixPath(...).is_absolute() is False, probed), so is_file()/subprocess resolve it against the cwd; a relative AUTOTESTER_TESSERACT such as 'fake.exe' is accepted as-is (probed). Needs write access to the process cwd, which already yields code execution via sys.path, so low. container-smoke runs on ubuntu-latest and no Dockerfile provides tesseract.","fix":"only consider WINDOWS_TESSERACT when os.name == 'nt', and require candidate.is_absolute()"}
PROPOSED-ISSUE: {"type":"coverage-gap","severity":"low","title":"Text Tesseract emits no row for is released unmasked","detail":"Probe: 'token sk-live-9f8e7d6c5b' in grey 215 beside clear black text -> no level-5 row, image RELEASED, region min pixel 215. Identical at base e1d59c35, so pre-existing and out of this unit's scope; the removed withhold-on-low-confidence rule never covered it either.","fix":"candidate: a contrast/low-ink pass or a second OCR on inverted/thresholded input"}
PROPOSED-ISSUE: {"type":"wording","severity":"low","title":"'reads only that one key' is looser than the code; stray literal tab","detail":"image_privacy.py:50 dotenv_values parses the whole repo .env with interpolation; manifest wording says one key. image_privacy.py:87 delimiter is now a literal TAB character instead of the escape sequence (same value, ruff clean).","fix":"dotenv_values(..., interpolate=False); restore the escape sequence in delimiter"}

VERDICT: PASS
SCOREBOARD: 3/3 criteria met, 2/2 invariants hold (core-invariants 5, 2)
TIER: L (security gate, dual-trigger image_privacy.py:61; no tier change)
FAILURES: none (P1-P3 are non-blocking low rows)
CAPABILITY-COVERAGE: not-applicable (backend privacy gate)
LIVE-BROWSER: not-applicable (src/autotester/core/image_privacy.py, tests)
ISSUES-WRITTEN: none (dual coordinator; PROPOSED-ISSUE P1, P2, P3)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The gate now masks low-confidence words and withholds on over-0.6 coverage, NaN/impossible scores, bad geometry, empty/blank-only recognition and a missing or failing engine; every fail-closed exit was re-run and falsified in a copy. Real-Tesseract probes released no secret pixel that base would have withheld; the one unmasked-text gap is identical at base.
Metrics: start=2026-10-17T21:50:00Z end=2026-10-17T22:12:00Z wall_min=22 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=5 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-17.13 lane=normal check_s=1320 mutants=2 defects_unit=0 defects_6c=0
slow: importer tests 6
