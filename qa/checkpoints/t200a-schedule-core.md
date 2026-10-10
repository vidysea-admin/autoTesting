# Checkpoint - t200a-schedule-core (cycle 0, checker A, single check)

Evidence identity: code 4662f250 / head 782bb254 (git archive copy, scratchpad check-t200a/base); lock: uv.lock unchanged; env: Windows 11, root .venv python, PYTHONPATH=copy/src, pytest -p no:xdist -p no:cacheprovider; attribution: checker coordinator, verdict qa/verdicts/t200a-schedule-core.md.

| check | command / scope | result |
|---|---|---|
| affected | pytest tests/test_schedule_{model,due,marker,catchup,overlap,failures}.py (112 collected) | 112 passed |
| lint | ruff check src tests scripts (copy) | passed |
| F TS1 | weekday `> 6` -> `> 7`, test_schedule_model.py | 45 green -> red [weekday 7] |
| F TS2 | fixed-rule tz -> UTC, test_schedule_due.py | 14 green -> 4 red |
| F TS3 | `inside[-1]` -> `inside[0]`, test_schedule_catchup.py | 22 green -> 1 red |
| F TS4 | drop `e.active`, test_schedule_overlap.py | 6 green -> 2 red |
| F TS7 | stale `>` -> `>=`, test_schedule_failures.py | 19 green -> 2 red |
| G torn | `_rebuilt` returns None, test_schedule_marker.py | 6 green -> 1 red |
| G race | exists()-then-open claim, two-process test x12 | 6 red of 12; real code 6 of 6 green |

Mandatory evidence: complete. Full suite: not run (full-suite trigger: none).
