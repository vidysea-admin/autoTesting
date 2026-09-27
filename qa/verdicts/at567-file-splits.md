# Verdict — at567-file-splits

**Date:** 2026-09-25 · **Head checked:** 689b93a (refactor 446b9e5, base master 5bef92f) · **Cycle checked: 1** (manifest Fix cycle: 1 of 3) · **Issues addressed (claimed):** AT-567 (helpers.py / session.py / routes_runs.py; explore_node.py deferred with AT-335)

```
VERDICT: PASS
SCOREBOARD: pure move proven (0 changed bodies, 0 missing definitions); old public names importable; 4 doc anchors restored; all three files well under the C2 cap; core invariants hold
FAILURES: none
CAPABILITY-COVERAGE: not-applicable (behaviour-preserving refactor; the claim "nothing changed" is proven by the checker's own AST identity check plus the full suite and two live runs)
LIVE-BROWSER: qa/evidence/browser-at567-file-splits-2026-09-25-checker/report.json
ISSUES-WRITTEN: none
EXECUTOR: claude-sonnet-subagent (checker: claude-opus-session, checker seat)
EXPLANATION: The three split files now sit at 184 / 270 / 149 lines, and the moved code is byte-identical apart from the four restored docstrings. Serial and parallel runs in a real visible browser behave exactly as before the split. AT-567 should stay open for explore_node.py, which is deferred with AT-335.
```

## Answers to the maker's questions

1. **Retargeted monkeypatches:** correct, and necessary. A monkeypatch works on the module where a name is looked up. `run_and_grade_case_resilient` (9 patches) and `default_session_factory` (1) are now looked up in `ui/run_execution.py`, so patching them on `routes_runs` would silently intercept nothing; retargeting is the only correct move. The names still looked up in `routes_runs` (`LangChainFallbackProvider` x14, `plan_parallel_run` x2) are still patched there. The class-level `BrowserSession.start/close` patches work wherever the class is imported. No test was deleted and no assertion changed.
2. **session.py at 270:** 30 lines of headroom. Enough for now, but the next evidence-shaped addition belongs in `browser/evidence.py` (61 lines), not `session.py`.

## Note (not blocking)

`routes_runs` no longer exposes two private helpers, `_run_entry_case` and `_run_and_grade_resilient`, so the "every old name re-exported" claim covers public names plus 8 of 10 private ones. Nothing in src, tests or scripts imports either name from `routes_runs` (grepped), so nothing breaks.

## What I re-ran

- **Pure-move proof** (`scratchpad/at567_identity.py`, the AST of every top-level def/class/method in the three base files at 5bef92f versus the six new files): 51 definitions, **46 identical, 4 docstring-only** (`settle`, `assert_expected`, `screenshot`, `_run_cases_serially`, the restored anchors), 0 changed, 0 missing.
- **Old names** importable from the old modules: helpers 15/15, session 8/8, routes_runs 8/10 (see the note).
- **Anchors** present: "E5 holds either way" (settle), "C7: facts recorded, the grader still owns the verdict" (assert_expected), "full history: execute.md's amendment log" (evidence.py screenshot), "Playwright raises "Sync API inside the…" (run_execution.py).
- `ruff` clean · `doctor` clean (copy).
- **Every non-browser test file** (copy): `1 failed, 1565 passed, 5 skipped`; the one failure is the `.git`-dependent `test_uploaded_recordings_are_gitignored`. Net: all green.
- Diff scope 5bef92f..446b9e5: 12 files, all listed; test removals are only monkeypatch-target lines.
- **Mode D**, real visible Chromium driven by the checker's own Python Playwright script (the Playwright MCP didn't reconnect after a restart):
  - serial (n=1 by budget) and parallel (pinned to n=2), each with an entry case + 2 ordinary cases + one grader outage;
  - both: 303, 6 distinct screenshot paths for 6 steps, entry case in its own folder with the homepage bytes, outage case completed + INCONCLUSIVE;
  - run view 12/12 images, 0 console and 0 HTTP errors, export 6 PNGs, no secret anywhere.

## Status: PASS
