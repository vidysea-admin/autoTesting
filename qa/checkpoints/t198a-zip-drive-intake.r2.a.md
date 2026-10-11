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
| full suite | shard_suite --ref dba80100 --shards 4 -- -o addopts= (Retry 1, runner fixed) | 3742 passed, 7 failed, 19 skipped, collect proof ok 3768; 1462 s overall. All 7 known or load flakes: AT-920, AT-792 (master has fix 238a1b7c, passes with master's test file in a copy of this head), AT-858, AT-921, AT-725, plus 2 that pass alone (AT-750a, AT-858 file). Classified by single-test runs on git archives of dba80100 and master b0385cd6. Evidence qa/evidence/t198a-zip-drive-intake-r2-A/. PASS |

Attribution: checker A coordinator (claude-sonnet-subagent) plus one scope-scan sub-checker.

Retry 1 (2026-10-11): verdict PASS written to qa/verdicts/t198a-zip-drive-intake.r2.a.md; the earlier BLOCKED-PROCESS verdict is qa/verdicts/t198a-zip-drive-intake.r2-1.a.md. All other rows above reused by evidence identity (head, src, tests and lock unchanged).
