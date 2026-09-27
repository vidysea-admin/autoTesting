# Verdict — at233-score-near-miss

**Date:** 2026-09-26 · **Cycle checked:** 1 · **Checker:** claude-sonnet-subagent

```
VERDICT: PASS
SCOREBOARD: AT-233 met: a threshold-rejected best candidate keeps its similarity and seconds_apart, stays found=False, and stays distinguishable from a no-candidate row
FAILURES: none
CAPABILITY-COVERAGE: 2/2 rows reproduced: test_score_near_miss.py run against a git-archive copy of base bb4be39 → the 2 near-miss tests red (assert 0.0 > 0.0), the no-candidate test green; all green on the branch copy
LIVE-BROWSER: not-applicable (stages/score.py, tests/test_score_near_miss.py)
ISSUES-WRITTEN: none
EXECUTOR: maker (checker: claude-sonnet-subagent)
EXPLANATION: A probe (near-miss + real match + no-candidate + false positive) run unchanged in base and branch copies gives identical found, recall, missed, false_positives and other rows. Only the near-miss row's own similarity (0.0→0.75) and seconds_apart (null→2.0) change, so no aggregate counts a near-miss as matched. Consumers checked: scripts/score_video_issues.py (dumps as_dict only); bench.py is a separate scorer; no ui module imports stages.score. _best_candidate is a verbatim extraction.
```

Evidence: branch copy: 4 score test files 55 passed, 2 skipped (real-corpus, pre-existing) · ruff clean · doctor clean · score.py 272 lines, score() 42, _best_candidate() 20 · `git diff --name-status bb4be39 HEAD` = manifest, stages/score.py, tests/test_score_near_miss.py; test_score.py and test_score_cli.py unchanged.
