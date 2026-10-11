# Checkpoint - t198a-zip-drive-intake, seat A, cycle 2 (r2.a)

Head dba80100, product sha 39533108 (src unchanged since a765c4dd). Repair base 3918a8aa (ancestor, verified).
Environment: Windows 11, worktree venv (uv --project .worktrees/t198a-zip-drive-intake), Python 3.11, zipfile stdlib of that interpreter.
Code hashes: src/autotester/sources/zip_intake.py at dba80100 (git blob of that path); tests as in the tree at dba80100.
Lock hash: uv.lock identical to master (merge brought no src/tests/lock change: `git diff --stat 3918a8aa 388bd5a0 -- src tests` = the 4 fix files only).

| check | command / scope | result |
|---|---|---|
| affected tests, bound tree | pytest -p no:xdist -o addopts= tests/test_zip_intake_{names,limits,register,atomic}.py test_ui_intake.py test_cli_intake.py test_drive_intake.py test_ui_intake_drive.py | 174 passed |
| attack matrix (62 archives x expand_zip + upload route) + 300 expand fuzz + 60 route fuzz | scratch tests under qa/evidence/t198a-zip-drive-intake-r2a/ | 128 passed, 0 raised, 0 status>=500, 0 staged leftovers, 0 row without file |
| breadth (BaseException / our-bug / containment propagate) | test_breadth.py | 10 passed |
| falsification ctor | copy, `except Exception` -> `except ZeroDivisionError` | 3 passed -> 2 failed |
| falsification guard | copy, `_guarded` `except Exception` -> `except ZeroDivisionError` | 4 passed -> 4 failed |
| scope scan | sub-checker, `master..dba80100` non-merge commits | all files in declared scope |
| full suite | shard_suite --ref dba80100 --shards 4 | NOT RUN: tool deadlocked in git archive (pid 78212 idle), lock held by pid 57556; BLOCKED-PROCESS |

Attribution: checker A coordinator (claude-sonnet-subagent) plus one scope-scan sub-checker.
