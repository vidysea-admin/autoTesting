# Verdict - t181-oracle-fix

**Manifest:** qa/manifests/t181-oracle-fix.md
**Contract:** core-invariants C12; grade.md; agent-layer AL12/AL13
**Cycle checked:** 1
**Verdict: PASS** (one residual logged as AT-998)

## Findings
- Recorded case caught: both recorded PASS-with-bug-note rows (pipeline and agent) become INCONCLUSIVE.
- Negations correct: "no error", "without errors", "did not fail", "no issues found and no error", "does not show an error message" are not held.
- Caught paraphrases: "error shown", "unable to log in", "Login failed", "rejected", "fails to load", "displayed incorrectly".
- NOT caught (keyword-only, no defect word): "login did not succeed", "login unsuccessful", "access was blocked", "timed out", "stayed on login page", "not working as expected", "nothing happened". Logged AT-998 (open, medium). The rubric fix (defect evidence = not met) is the primary fix; the guard is a backstop.
- False-INCONCLUSIVE measurement: scanned every PASS row with a note in tests/**/*.json and qa/evidence verdict JSON: 6 PASS rows, 5 with notes, 2 flipped; both are the recorded bug-note rows (true positives). 0 legitimate PASSes flipped. Known cost: a correct PASS whose note mentions an expected error (negative case) is held (documented, accepted).
- Fail-closed: C12 requires it; INCONCLUSIVE (human look) is the right state, not FAIL (the judge's result and note disagree, so the truth is unknown; FAIL would assert a defect unproven).
- Bypass grep: all product-case Verdict construction is in grade.py::_verdict and two INCONCLUSIVE-only sites in run_case_pipeline.py; the only PASS source is grade(). ai_judge.py is rule-based (failures list), not a free-text judge.
- Issue id: AT-996 collided with wave/comment-refusal-ux (team-intake). Our row renumbered to AT-997 (code, tests, manifest, issues.jsonl updated); max id across branches was 996.
- Tests: test_grade_note_guard, test_agent_gain, test_agent_comparison, test_grade*, 87 passed. ruff clean. doctor: 1 violation, the known undeclared langchain_ollama (Ollama unit).
