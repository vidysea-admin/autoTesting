# Checkpoint B — t153-behavioural-checks (cycle 0)

Attribution: coordinator B, verdict qa/verdicts/t153-behavioural-checks.b.md. Env: Windows, root .venv python via PYTHONPATH to a `git archive 2653bbcb` copy, `-p no:xdist -p no:cacheprovider`.
Code identity: src/autotester/{schema/ai_check.py,stages/ai_capture.py,stages/ai_judge.py,stages/grade.py} and tests at commit 2653bbcb (product ff901f72); pre-check blobs test_ai_capture.py:4fd639e test_grade_evidence.py:2af58c0 test_approval_signing.py:709601f.

| Check | Command / scope | Result |
|---|---|---|
| AI6/AI7 verify | pytest tests/test_ai_capture.py tests/test_grade_evidence.py tests/test_approval_signing.py (130 collected) | 130 passed |
| AI6 grep | grep -n "Result\.\|Verdict(" stages/ai_capture.py | exit 1, empty |
| Closure | pytest tests/test_ai_catalog.py tests/test_grade.py tests/test_schema.py | 59 passed |
| ruff | ruff check src tests scripts | clean |
| doctor | autotester doctor | only stale-generated docs/SNAPSHOT.md (pre-existing) |
| Falsify AI6 | verdict overwritten after grade() (copy) | green 11 passed -> red 7 failed |
| Falsify AI7 judge | drop redactor= from JUDGED grade() (copy) | green 112 -> red 2 failed (test_grade_evidence.py:240) |
| Mutant | drop require_approval (copy) | green 77 -> red 1 failed |
| Mutant | drop input assert_clean (copy) | green 77 -> red 40 failed |
| Bypass probes | scratchpad/probe-b/probe_b.py, probe_b2.py (no model, no network, throwaway signing key) | all refused/scrubbed except the 3 low/medium findings in the verdict |

Full suite: not run by B. Result: PASS.
