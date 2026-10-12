# Checkpoint - t200-schedule-wiring (cycle 0, single checker)

Evidence identity: code 8b67fb04 / head 9647f0f7 (manifest-only commit after the code); git archive copy under C:\Users\Lenovo\AppData\Local\Temp (random suffix); uv.lock unchanged; env: Windows 11, root .venv python, PYTHONPATH=copy/src, pytest -o addopts= -p no:cacheprovider; attribution: checker, verdict qa/verdicts/t200-schedule-wiring.md; evidence qa/evidence/t200-schedule-wiring-checker/checker-evidence.md.

| check | command / scope | result |
|---|---|---|
| affected | 4 pytest batches (schedule, queue, cli, ui importers) | 64 + 93 + 145 + 178 passed, 1 skipped |
| lint/doctor | ruff check src tests scripts; autotester doctor | clean |
| e2e | real CLI tick: dry-run, blocked, allowed with recorder, 2 concurrent ticks, server-file overlap | as expected |
| F TS6/HO23/TS4/TS3/TS7/TS5 | one mutation each in its own copy | all green -> red -> green |

Mandatory evidence: complete. Full suite: not run (full-suite trigger: tests/golden/cli_commands.json and the cli_subapps registry list changed, ui/run_queue.submit gained an optional kwarg; the 6c check runs the one full suite).
