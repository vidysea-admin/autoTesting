# Verdict - t136-grade-fix

Cycle checked: 0
Executor: claude-sonnet-subagent (checker: claude-sonnet-subagent)
Base: d9a70882 (git merge-base HEAD int/1017) · Checked: 4093b103 (HEAD 9da902d7 adds only the manifest)

## Check plan
Tier M, single checker. Logic changed in grading + browser evidence -> diff read in full (src 4 files),
affected tests, one falsification per criterion G1-G4 in a copy outside the worktree
(`D:/autoTesting/.work/tmp/chk136/copy`, git archive of 9da902d7), own counterexample probes
(`.work/tmp/chk136/test_probe.py`, `g3.py`). No UI surface -> no browser walk. Lane: normal (lane off).

## Result
VERDICT: PASS
SCOREBOARD: 4/4 criteria met, 2/2 invariants hold (C12 fail-closed, B11 disclosure kept)
TIER: M (multi-file grading behaviour; no auth/tenancy/prod-write trigger in the changed files)
FAILURES: none
CAPABILITY-COVERAGE: not-applicable (no capability row touched)
LIVE-BROWSER: not-applicable (changed paths: stages/grade*.py, browser/evidence.py; G4 covered by fake-page unit tests)
ISSUES-WRITTEN: none (two low PROPOSED-ISSUE lines below; ids are minted by the maker because int/1017 ledger is far ahead of this worktree's AT-1032, a local mint would collide)
EXECUTOR: claude-sonnet-subagent

## Evidence (all run by me)
- Own run: `pytest tests/test_grade_visual.py test_grade_negative_path.py test_screenshot_blank_retry.py test_grade_evidence.py test_grade_defect_field.py test_grade_note_guard.py` -> 253 passed.
- Affected family (19 files: grade*, image_privacy, ai_judge, ai_capture, ai_report, screenshot, evidence) -> 454 passed. `shard_suite --affected --list` returned integration-required (dynamic globs), so the family was chosen by import grep; a 107-file importer run was stopped at the wall budget (my PID, stopped). Full suite not run (not required at M unit check).
- `ruff check src tests scripts` clean; `autotester doctor` clean (2 advisory D-087 warnings).
- Falsification (copy, green before, red after, restored; copy re-run green 40/40):
  - G1 `for image in unseen:` -> `for image in []:` : red test_g1_fail_citing_a_withheld_/absent_screenshot_is_inconclusive (2 failed).
  - G2 `_met_assertions` -> 0 : red test_g2_pass_stands_when_all_images_delivered_and_an_assertion_was_met.
  - G3 adverb cue disabled : red test_g3_negative_path_rejection_note_passes (2 params); extra: drop `_QUALIFIED_INPUT.sub` -> red (1 param).
  - G4 `_is_blank` -> False : red test_g4_blank_frame_is_recaptured / retries_are_bounded; extra: unreadable -> blank=True : red test_g4_an_unreadable_frame_is_not_treated_as_blank.
- Counterexample probes (grade() with fake OCR/judge): FAIL citing delivered image while another image withheld -> FAIL; FAIL citing a DOM assert row with all images withheld -> FAIL; FAIL citing withheld image -> INCONCLUSIVE; PASS+met row, all delivered -> PASS; PASS with one withheld / one absent / met+unmet / no assertion / only a "screenshot blank..." row -> INCONCLUSIVE. G3 (`failure_terms`): correctly/properly/appropriately + rejected/blocked pass only with expects_error; `incorrectly rejected`, `not correctly rejected`, "...rejected, but the form saved", "rejected; returned 500", "wrong amount correctly rejected", "access denied properly but data leaked", "invalid total shown correctly formatted", "crashed after ... correctly blocked" all held; positive path holds all of them.
- B11 disclosure kept: `visual_decision` always returns `VISUAL_PRIVACY_NOTE` first (grade_images.py visual_decision tail); DOM blank row is not an `assert ` row so cannot back a PASS (probe P5f).
- G4 bound: BLANK_RETRIES=3 x (<=1.5 s idle + 0.3 s grace) ~ 5.4 s plus captures; `_timeout()` budget check inside loop; `RunBudgetExceeded` re-raised (evidence.py:120).

## Non-blocking notes (PROPOSED-ISSUE, low)
P1: {"severity":"low","title":"visual_decision: any FAIL citing a withheld screenshot downgrades the whole verdict, including a second failure backed only by a DOM/assert row or a FAIL whose refs mix a withheld image and a DOM row (grade_images.py:_unseen_basis any() over all failures); fail-closed and literal to G1, but erases a DOM-verified functional failure (B11 'must not erase the functional result'). Consider downgrading only when no failure has a non-withheld basis.","source":"t136-grade-fix check cycle 0 probes P1/P2","feature":"t136-grade-fix"}
P2: {"severity":"low","title":"browser/evidence.py _recapture_blank: the recapture page.screenshot() in the loop is not covered by the AT-036 captureScreenshot retry, so a transient CDP compositor race on recapture raises and errors the run instead of keeping the already-captured blank frame.","source":"t136-grade-fix check cycle 0 diff read","feature":"t136-grade-fix"}

EXPLANATION: All four criteria are evidenced by my own runs and a named falsification per criterion went green->red->restored. The grader still FAILs on delivered-image and DOM-row evidence, downgrades only unseen-basis FAILs, and keeps PASS held without full delivery plus a met assertion. The two lows are judgement-edge (mixed refs) and robustness, neither contradicts a criterion.
Metrics: start=unavailable end=2026-10-18T20:37:18Z wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=6 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=unavailable mutants=2 defects_unit=0 defects_6c=0
slow: affected-importer-run 10 (107-file importer family exceeded the budget and was stopped; narrowed to 19 files, 22 s)
