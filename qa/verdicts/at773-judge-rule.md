# Verdict - at773-judge-rule (AT-773), cycle 0, Retry 1

Bound to D:/autoTesting; worktree .worktrees/at773-judge-rule; branch wave/at773-judge-rule head 1e0aed21 (clean worktree, master merged at 3322a04f). Policy-Version: proportional-verification/2026-10-06.6. Cycle checked: 0. Retry: 1. Date: 2026-10-11. The earlier same-cycle verdict (BLOCKED-PROCESS) is archived at qa/verdicts/at773-judge-rule.r0-2.md; the cycle-0 verdict is qa/verdicts/at773-judge-rule.r0-1.md. Evidence index: qa/evidence/at773-judge-rule/cycle0-retry1-2026-10-11.md.

## Check plan
Gate (`tick.mjs --lint-manifest` exit 0, head, clean tree); read G6 (qa/contracts/grade.md:56) and E1 (qa/contracts/execute.md:16) verbatim, D-084 item 1 (owner approval) and D-074; step 4c diff scope; class attack on the rule (65 probes) comparing executor and grader unmet detection; affected tests re-run (not reused: grade.py changed on master after the builder pre-check sha, and the head moved); one falsification per criterion in a copy; ruff; doctor. No UI, no browser, no persona walk.

## Gate and tier
- `--lint-manifest` exit 0. Status ready-for-check, Fix cycle 0. Both Pre-check lines present (untagged; the criteria are G6 and E1).
- `Dual check: no` is right. The diff is `stages/grade.py` verdict logic plus 2 test files: no credential handling, no auth or tenant boundary, no production write, and the guard only ever downgrades a PASS. No path:line to cite.
- TIER L, as at cycle 0 (protected test change: the `tests/test_grade.py` pin flips PASS -> INCONCLUSIVE, authorized by D-074/G6 and approved in D-084 item 1, Approved-by Umesh 2026-10-11). Tier unchanged.

## Criteria
- [G6] met. Code: `grade.py::_assertion_guard`, called from `grade()` after the self-consistency check. PASS plus (outcome ASSERTION_FAILED or any `assert <field>: unmet` item) -> INCONCLUSIVE with a note naming the assertions, D-074(b), G6 and the judge scoreboard. FAIL and INCONCLUSIVE pass through; clean runs are untouched. Re-run: the two grade test files, test_grade_evidence and test_execute_assertions are green inside the 331 passed of the affected set. Falsification F-G6: guard disabled (`if False and ...`) -> `test_judge_pass_on_an_unmet_login_assertion_is_never_pass` red on `assert verdict.result is not Result.PASS`; the copy is green before and after restore.
- [E1] met. `git diff master wave/at773-judge-rule -- src/autotester/stages/execute.py` is empty (executor untouched, 14/14 test_execute_assertions green). The amended clause (an ASSERTION_FAILED run still reaches the judge and never ends PASS) is evidenced by tests/test_grade.py:68-82 and the probes. Falsification F-E1: `_outcome_verdict` short-circuits ASSERTION_FAILED -> `test_assertion_failed_run_still_reaches_the_judge_but_can_never_pass` red on `assert judge.prompts, "an ASSERTION_FAILED run never reached the judge"`; green before and after restore.

## Close-the-class attack (qa/evidence/at773-judge-rule/class-attack-output.txt; labels produced by the real `assert_expected`)
| Attack | Result |
|---|---|
| each assertion kind unmet (url, visible_text, absent_text, dom_asserts, network), outcome COMPLETED and ASSERTION_FAILED, judge PASS | INCONCLUSIVE in all 10; the same kinds met + PASS -> PASS (5) |
| unreadable page / url (`unmet (page unreadable)`, `unmet (url unreadable)`) + PASS | INCONCLUSIVE (3) |
| 5 assertions with one or two unmet (4 variants, each also with outcome ASSERTION_FAILED); all-met control | INCONCLUSIVE x8; all met -> PASS |
| judge result matrix x {outcome only, unmet only, both}: PASS / FAIL / INCONCLUSIVE / BLOCKED | PASS -> INCONCLUSIVE; FAIL, INCONCLUSIVE, BLOCKED unchanged (see P1); a clean COMPLETED run is unchanged for all 4 |
| ASSERTION_FAILED with no unmet item (M3), and with empty evidence | INCONCLUSIVE, note says `outcome assertion_failed` |
| ERRORED / NOT_RUN (+unmet) + judge PASS; BLOCKED_HITL | INCONCLUSIVE / INCONCLUSIVE / BLOCKED, judge never called |
| missing screenshot file + unmet + PASS | INCONCLUSIVE; the note carries both the shortfall and the D-074 text |
| self-inconsistent judge PASS (failures non-empty) on an unmet run | INCONCLUSIVE (G3 path) |
| `Redactor` (master's new param): clean prompt + unmet + PASS; secret value in the prompt | INCONCLUSIVE; BLOCKED with judge not called and no value in the note |
| 3 unmet items; judge's own note | note names all 3; judge note preserved and joined |
| met item whose detail contains "unmet" (`expected to contain 'unmet'`, `.unmet` selector, `status: unmet`) | the executor flags every one (substring "unmet"); the grader's `": unmet"` scan flags only the `status: unmet` form. The run outcome is ASSERTION_FAILED in every case, so the outcome limb downgrades: no false PASS. The only disagreement effect is a false INCONCLUSIVE, and it originates in execute.py (P3) |
| unmet label carried by a non-dom/network evidence kind | grader flags it, executor does not: grader is a superset, worse-only |
| retired case | `grade()` takes only rubric + RawResult and never sees case status, so the rule is identical for any case: n/a by construction |

No path found where an unmet assertion yields PASS. Bypass hunt: the only `RawResult(...)` producer for a judged run is execute.py:233; `ai_judge._rule_verdict` goes through `grade()`; no other `Verdict(... PASS)` constructor exists outside grade.py.

## Findings (none blocking)
PROPOSED-ISSUE P1: {"severity":"low","feature":"grade","title":"G6 says grade() returns only FAIL or INCONCLUSIVE for a failed-assertion run, but a judge answer of BLOCKED passes through unchanged (Judgment.result allows BLOCKED)","evidence":"src/autotester/stages/grade.py _assertion_guard acts only on PASS; probe matrix judge=BLOCKED in class-attack-output.txt","note":"never PASS, so the operative D-074(b) rule holds; either clamp BLOCKED in the guard or word G6 as 'never PASS'"}
PROPOSED-ISSUE P2: {"severity":"low","feature":"grade","title":"M3: the outcome-only limb of the guard (ASSERTION_FAILED with no unmet item) is required by the G6 text and works (probe: INCONCLUSIVE), but no test pins it","evidence":"tests/test_grade_assertion_rule.py _result always adds an unmet item for ASSERTION_FAILED; dropping `result.outcome is Outcome.ASSERTION_FAILED or` leaves all tests green (cycle-0 M3)","decision":"not a FAIL: the behaviour is correct and G6's own falsifiable clause is met by F-G6; add a test with ASSERTION_FAILED and no unmet item"}
PROPOSED-ISSUE P3: {"severity":"low","feature":"execute","title":"execute.py::_assertions_unmet matches the substring 'unmet' anywhere, so a MET assertion whose expected text contains 'unmet' marks the run ASSERTION_FAILED; with G6 such a case can now never PASS","evidence":"src/autotester/stages/execute.py:85-86 versus grade.py _unmet_assertions (': unmet'); probe rows 'met-item word unmet'","note":"false INCONCLUSIVE only, never a false PASS; pre-existing detector, tighten it to the `: unmet` label shape"}
WARN: the old test name `..._judge_owns_the_verdict` survives only in immutable history (qa/manifests/at540-assertion-layer.md); not a finding.

VERDICT: PASS
SCOREBOARD: 2/2 criteria met (G6, E1), 0/0 invariants touched
TIER: L (protected test change tests/test_grade.py, authorized D-074/D-084; no security/auth/tenancy/prod-write; one checker)
FAILURES: none
CAPABILITY-COVERAGE: 2/2 rows reproduced by the checker in isolated copies (green before, red after, restored); mutants beyond the floor: 0 (cycle-0's 8 stand as guidance; M3 decided above)
LIVE-BROWSER: not-applicable (changed paths: src/autotester/stages/grade.py, tests/)
ISSUES-WRITTEN: none (P1-P3 are PROPOSED-ISSUE lines; the maker mints the rows)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The rule holds for every assertion kind, multiple assertions, unreadable pages, an outcome with no evidence item, the non-judged outcomes and the Redactor path: an unmet assertion never ends PASS, and the judge can only make a result worse. slow: affected-tests run 35 min (machine load, 331 tests) plus ruff/doctor about 8 min, so wall exceeded the L target; every mandatory check finished. Full-suite trigger: none from this unit; the 6c integration check covers it.
Retry: 1
Metrics: start=2026-10-11T05:10:50Z end=2026-10-11T07:10:00Z wall_min=119 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.6
