# Verdict — at329-discard-guard (stale-ledger claim)

**Date:** 2026-09-26 · **Cycle checked:** 1 · **Checker:** claude-sonnet-subagent

```
VERDICT: PASS
SCOREBOARD: 3/3 parts of AT-329's expected clause met on origin/master (test, second mutation entry, optional docstring narrowing)
FAILURES: none
CAPABILITY-COVERAGE: 2/2 rows reproduced (copy c329-1, git-archive of origin/master, own venv; baseline 2 passed; drop under-temp clause → test_cleanup_refuses_a_sandbox_shaped_name_outside_the_temp_dir red only; drop prefix clause → test_cleanup_refuses_to_delete_anything_it_did_not_create red only)
LIVE-BROWSER: not-applicable (unit changes only its manifest)
ISSUES-WRITTEN: AT-329 open→fixed (fix already on master: 14ebf9b + c9b42ee, both ancestors)
EXECUTOR: maker (checker: claude-sonnet-subagent)
EXPLANATION: The guard at scripts/mutation_check.py:260 is two-clause (under temp dir AND mutation-check- prefix) and still armed today: the only autouse fixture (tests/conftest.py:29) is unrelated, and private_temp is non-autouse and unused by both guard tests. The only production caller (mutation_check.py:298) passes an OS-generated mkdtemp root, so no user-controlled path reaches _discard. The ledger row was simply stale.
```

Evidence: `git merge-base --is-ancestor 14ebf9b origin/master` and the same for c9b42ee → both exit 0 · `grep -rn "autouse=True" tests/` → conftest.py:29 only · `grep -rn "_discard(" scripts tests src` → 4 hits (1 production, 3 tests) · worktree: targeted tests 2 passed, ruff clean, doctor clean · diff: `origin/master...HEAD` = the manifest only.
