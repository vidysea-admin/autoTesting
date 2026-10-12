# Verdict - at773-judge-rule (AT-773, judge rule A, D-074(b))

Bound to D:/autoTesting, worktree .worktrees/at773-judge-rule, HEAD 4acce31b, base aa0dca48 (= origin/master at check time).
Policy-Version: proportional-verification/2026-10-06.6. Cycle checked: 0. One checker (not dual; reason below).
Date: 2026-10-07.

## Check plan (step 0)
Diff vs base (4 files): src/autotester/stages/grade.py, tests/test_grade.py, tests/test_grade_assertion_rule.py (new), the manifest.
No UI, no auth, no production write. Signals: logic changed (affected tests + falsification), protected test change (L).
Checks: contract G6 + E1 read; D-074 authority; bypass-path hunt; affected tests; 8 isolated mutants; ruff; doctor; one full suite (queued).

TIER: L - protected test change: tests/test_grade.py::test_assertion_failed_run_still_reaches_the_judge_but_can_never_pass flips its pinned result from PASS to INCONCLUSIVE (the old name was ..._and_the_judge_owns_the_verdict). No security/auth/tenancy and no production write, so one checker, and no per-unit full-suite trigger under policy .7. A full suite is still run because the dispatch asked for exactly one.

## Protected-test justification (the point of this single-checker L)
- Authority exists on origin/master: `git log origin/master -- docs/DECISIONS.md` shows 74da197e "D-074 Umesh answers"; D-074 is at docs/DECISIONS.md:2218, status ACTIVE, Approved-by Umesh (chat 2026-10-07). The maker's manifest says D-074 is not on master; that is wrong in the safe direction (it is there, so no CONTRACT_MISMATCH).
- D-074(b): "A deterministic assertion that failed can never become PASS. For a run with a failed assertion the judge may only return FAIL or INCONCLUSIVE ... amends D-032 (partial): the part of D-032 that let the judge weigh and overrule a recorded failed assertion is removed." Changes-authorized names `src/autotester/stages/grade.py` and `run_case_pipeline.py` for the judge rule. The diff touches grade.py only.
- Contract on origin/master (0f8c19d0 amended it): grade.md G6 and execute.md E1 state the same rule; G6: judge PASS on such a run "is rejected and downgraded to Result.INCONCLUSIVE with a note naming the failed assertion"; a run with no failed assertion is "unaffected".
- The old assertion pinned exactly the behaviour D-074(b) removes (`assert verdict.result is Result.PASS` under a comment "the judge disagrees with the wrongly-authored expectation ... proof the grader, not the outcome enum, owns the verdict"). Changing it to INCONCLUSIVE is the specified new behaviour, not a weakening: the test still asserts the judge is called and `grader_provider == "mock"`, and the new file adds the (a)/(b)/(c) matrix. RULING: the protected change is AUTHORIZED by D-074(b) + G6. The rename is the same change (the old name described the removed behaviour); nothing but the historical manifest qa/manifests/at540-assertion-layer.md refers to the old name.

## Criteria
- [G6] PASS. Code: grade.py:70-96 `_assertion_guard` (read in this check): judge PASS and (outcome ASSERTION_FAILED or any evidence path starting "assert " containing ": unmet") -> INCONCLUSIVE with a note naming the unmet assertion(s), D-074(b), G6 and the judge scoreboard; FAIL and INCONCLUSIVE pass through; the guard never returns PASS from a non-PASS. Call site grade.py:215-221 uses `final`. Ran: tests/test_grade_assertion_rule.py + tests/test_grade.py = 19 passed. Met assertion + PASS stays PASS (test_met_assertions_do_not_trigger_the_guard).
- [E1] PASS. execute.py is untouched; `run_case` still never assigns a verdict, still records `assert <field>: met|unmet` evidence and ASSERTION_FAILED; the amended E1 is satisfied because the final verdict for such a run can only be FAIL or INCONCLUSIVE.
- Dispatcher rule (judge FAIL stays FAIL, guard never upgrades): test_judge_fail_on_an_assertion_failed_run_stays_fail_with_its_failures and the INCONCLUSIVE pass-through test pass; mutant M4 (downgrade FAIL too) goes red.
Scoreboard: 2/2 criteria met on the evidence so far; no invariant of grade.md/execute.md is touched by the diff.

## Bypass-path hunt (every caller)
- `git grep "Verdict("` in src and scripts: only grade.py:105 (`_verdict`, the single producer of PASS) and run_case_pipeline.py:136 and :202, which build Result.INCONCLUSIVE rule verdicts (`_unjudged_replay`, grader-exception path). No `Result.PASS` literal is assigned anywhere outside the schema.
- Callers of `grade()`: run_case_pipeline.py:168 (`run_and_grade_case`), :199 (`_resilient`), :229 (`grade_errored_result`, ERRORED only), and scripts/bench_trial.py:104, scripts/regression_proof.py:147, scripts/run_pathlynks_first_cases.py:139. All go through `grade()`, so all go through the guard. The UI (ui/run_execution.py) only `save_verdict`s what these return.
- Script replay (`stages/script_replay.py`) never grades; `judge_replays=False` yields INCONCLUSIVE by rule. Report export (`report_export.py:85`, `routes_report.py:230`) only reads verdicts. `ux_advisory.py` returns UXJudgment, not a Verdict. No `model_copy(update={"result"...})` anywhere.
- Conclusion: no bypass path found.

## Falsifications (L: per claim). 8 isolated copies of `git archive 4acce31b` under scratchpad/at773chk/Mn_*; scripts/ copied in because conftest imports regression_proof. Green before: base copy 19 passed.
| id | single-hunk edit in grade.py | claim | result |
|---|---|---|---|
| M1 | `if False:` in the guard | ASSERTION_FAILED + judge PASS is never PASS | 3 failed: test_judge_pass_on_an_unmet_login_assertion_is_never_pass, test_judge_pass_on_a_completed_run_carrying_unmet_assert_evidence_is_never_pass, test_grade.py::test_assertion_failed_run_still_reaches_the_judge_but_can_never_pass |
| M2 | trigger = outcome only | unmet evidence alone triggers | 1 failed (the completed-run-with-unmet-evidence test) |
| M3 | trigger = unmet evidence only (outcome limb dropped) | ASSERTION_FAILED outcome alone triggers (first limb of G6) | SURVIVED: 19 passed |
| M4 | guard also downgrades FAIL | FAIL stays FAIL | 1 failed (test_judge_fail_on_an_assertion_failed_run_stays_fail_with_its_failures) |
| M5 | guard downgrades every PASS | a run with no failed assertion is unaffected | 4 failed |
| M6 | guard emits FAIL not INCONCLUSIVE | G6 says INCONCLUSIVE | 3 failed |
| M7 | call site bypasses the guard (`verdict_result=judgment.result`) | wiring | 3 failed |
| M8 | note no longer names the assertion | note names the failed assertion | 2 failed |
Traceback paths print `..\base\tests`: stale .pyc co_filename carried by Copy-Item, harmless; the sources run are the copies (results above differ per mutant).
M3 is the only survivor. Every test builds ASSERTION_FAILED with an unmet evidence item, so the outcome-only limb of G6 ("outcome is ASSERTION_FAILED, OR carries unmet evidence") is not isolated. It is defence in depth, but reachable: execute.py's `_assertions_unmet` matches `"unmet"` anywhere in the path, so it can set ASSERTION_FAILED on a met item whose detail text contains "unmet", where the guard's `": unmet"` test would not match. The criterion itself is falsified (M1, M2), and L mutant guidance is not a floor. Non-blocking: low row P1. Not a FAIL, since the code is right and only the test is thin.

## 4c diff scope
Only the 4 files above. Nothing deleted except the replaced test body/name and two docstring paragraphs that described the removed behaviour. All are listed in the manifest's "What changed".

## Affected tests / lint / doctor (run by me in the worktree)
- `uv run pytest` on the 17 test files that import stages.grade or run_case_pipeline (including test_script_replay, test_ui_runs_*, test_video_*), `-m "not harness"`: 119 passed, 1 warning, 222.8 s.
- `uv run ruff check src tests scripts`: All checks passed.
- `uv run autotester doctor`: 1 violation, `stale-generated: docs/SNAPSHOT.md`. The diff touches no doc, so this is the generated snapshot lagging, not this unit; `autotester snapshot` at merge time. The manifest said "doctor: clean", true only on the maker's tree.

## Rulings on what the maker skipped
1. grade SKILL.md prompt hint (pinned by tests/fixtures/golden_prompts/grade.md via test_sk3): LOW ledger row (P2), not a gap. G6 asks for the code guard only, and the guard holds whatever the judge says.
2. ARCHITECTURE.md line 90 ("the grader alone still owns every verdict"): FINE, no row. Still true: the guard lives inside grade(), the grader stage, and the sentence is about the executor not grading. An edit would need a D-entry naming that section, and none is needed.

## Not yet run (mandatory)
Full suite `uv run pytest --deselect tests/test_crawl_inventory_live.py` in the worktree, under D:/autoTesting/.work/suite.lock. The lock was held by the t203 checker (since 19:29 IST) when I tried; the coordinator then set the queue and this unit is 6th (after T-125 checker A, at758-759 dual, T-204 dual, 8f integration head). I did not take the lock. Merge, issue flips and push also remain.

PROPOSED-ISSUE rows (written at PASS, after a duplicate check; ids next after the max on master at merge time, which was AT-801 at check time):
- P1 low test-gap: no test isolates the outcome-only limb of G6 (ASSERTION_FAILED with no unmet evidence item); M3 survives. Fix: one test with that RawResult and judge PASS -> INCONCLUSIVE.
- P2 low prompt: skills/grade/SKILL.md could say that a recorded unmet assertion caps the judge at FAIL/INCONCLUSIVE (needs a golden-fixture edit).
- P3 low process: manifest claims "D-074 is not on origin/master" and "doctor: clean"; D-074 is at docs/DECISIONS.md:2218, and doctor reports stale docs/SNAPSHOT.md on this tree. Wording, never a FAIL.
- P4 low robustness: `_unmet_assertions` matches `": unmet"` while execute.py::_assertions_unmet matches `"unmet"` anywhere; the matchers can disagree on a met item whose detail contains "unmet". One shared helper would remove the drift.

VERDICT: CONTINUE-NEEDED
Remaining: full suite (queued 6th); then, if green apart from the known pre-existing failures (AT-750, AT-772, redact perf, test_reconcile_schema rc2/AT-792), merge onto the latest origin/master, re-run tests/test_grade_assertion_rule.py and tests/test_grade.py, flip the manifest to checked-PASS, mark AT-773 fixed, add P1-P4, push origin master (D-007). Everything else is evidenced and would PASS on the present evidence.
SCOREBOARD: 2/2 criteria met (G6, E1), 0 invariants touched
TIER: L (protected test change: tests/test_grade.py::test_assertion_failed_run_still_reaches_the_judge_but_can_never_pass; one checker by dispatch)
FAILURES: none
CAPABILITY-COVERAGE: 7/8 mutants reproduced red (M1, M2, M4-M8); M3 survived (P1, low)
LIVE-BROWSER: not-applicable (changed paths: src/autotester/stages/grade.py, tests)
ISSUES-WRITTEN: none (rows deferred to PASS)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: D-074(b) is on origin/master and G6/E1 authorize the PASS-to-INCONCLUSIVE flip in the protected test. Every grading caller goes through grade() and its guard, 7 of 8 mutants fail the suite, and the survivor is a low test gap. Only the queued full suite remains.
Resume: 0 of 2 (first dispatch; CONTINUE-NEEDED is for the lock queue, not a budget overrun)
Metrics: start=2026-10-07T14:27:00Z end=2026-10-07T15:20:00Z wall_min=53 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=8 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.6
(Metrics times are approximate, from `date` readings at 19:59 and 20:44 IST; wall includes a network outage.)
