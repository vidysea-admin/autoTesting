# Manifest - t181-oracle-fix

**Status:** checked-PASS
**Fix cycle:** 1
**Unit:** T-181 follow-up: oracle defect AT-997 and gain-verdict fixes.
**Contract:** qa/contracts/core-invariants.md C12 (fail closed); qa/contracts/grade.md; qa/contracts/agent-layer.md AL12/AL13.
**Issues addressed:** AT-997

## What was built
1. `stages/grade_note_guard.py` (new, one job): a judge PASS whose own note carries an un-negated defect word is downgraded to INCONCLUSIVE. Wired into `stages/grade.py::grade` after the assertion guard. Conservative toward INCONCLUSIVE (a correct PASS that mentions an expected error is also held).
2. Root cause 1: the default rubric (`run_case_pipeline._rubric_for_claim`) asked "evidence is consistent with: <rationale>", and the rationale names the seeded bug, so observing the bug met c1. Wording now says the product behaved correctly and that defect evidence means NOT met. `skills/grade/SKILL.md` gains a result-must-agree-with-note rule.
3. `agents/comparison.py`: a `step_cap` halt is no gain (as `agents/gain.py` documents); a 0-vs-0 tie on bugs and false positives is `no_evidence` (new `Comparison.verdict` value), not GAIN; a nonzero tie that gains says it is a tie.
4. Tests: `tests/test_grade_note_guard.py` (recorded judge output, `tests/fixtures/t181_recorded_judge_output.json`), 4 new in `tests/test_agent_gain.py`.

## Not done
Part 3, the live AL12 re-run (qa/verdicts/t181-live.r2.md): held for the Ollama provider unit (wave/ollama-primary). Previous agent's uncommitted Ollama tier edits are in `git stash` on this branch, deliberately not committed (provider selection is that unit's).
