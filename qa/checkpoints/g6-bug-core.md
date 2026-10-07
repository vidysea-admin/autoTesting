# Checkpoint — g6-bug-core (cycle 0)

Environment fingerprint: Windows 11, cpython 3.11 (worktree .venv), no browser/deploy/data snapshot. Subject: HEAD 7e23fa9a (base c09debd1). uv.lock sha256 0f25d574ae096863...
Code hashes (sha256 prefix, git-archive copy): stages/bug_loop.py d17006544daf6864, schema/tracked_bug.py c5043b2566f1f66f, stages/issues.py 7e475cba3184a612, tests/test_bug_loop.py 0d3dbcca3d5a5c03, tests/test_bug_loop_close.py 4925e8a16e58d41d. No conftest/config/dependency change in the diff (tests/bug_loop_fixture.py is new and imported only by the two new test files).
Attribution: single checker (claude-sonnet-subagent), this transcript.

| check | command + scope | result |
|---|---|---|
| affected tests | pytest -p no:cacheprovider (13 files named in the verdict), `-m "not harness"`, in git-archive copy g6chk-7e23fa9a, PYTHONPATH=<copy>/src | 218 passed, 1 skipped, 1 copy-artifact failure (test_uploaded_recordings_are_gitignored needs .git; passes in the bound tree) |
| ruff | `ruff check src tests scripts` in copy | pass |
| doctor | `autotester doctor` in copy | clean |
| TB5 numstat | `git diff --numstat c09debd1 HEAD -- src/autotester/stages/issues.py` | 16 0; 258 lines |
| falsification TB1-TB6 | 14 single-hunk mutants, one fresh copy each, named nodes only | all green-before, red-after on the named test |
| probes | late-verdict, first/last_seen, other-criterion FAIL, deleted-case | findings P1-P4 (verdict) |
| diff scope 4c | `git diff c09debd1 HEAD --stat --diff-filter=DR` | no deletions/renames |

Remaining: full suite (combined G-core head) — the maker's one run on the G2+G3+G5+G6 integration head. No other mandatory evidence outstanding.
