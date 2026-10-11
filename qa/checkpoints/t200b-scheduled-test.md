# Checkpoint - t200b-scheduled-test (coordinator A, cycle 0)

Identity: code head 0d9a3b56 (product sha e4e1b3a9), base 09828f2d, policy proportional-verification/2026-10-10.9, environment = worktree .venv (uv.lock unchanged by the diff), original attribution = checker coordinator, `qa/verdicts/t200b-scheduled-test.md`.

| Check | Command and scope | Code hashes | Result |
|---|---|---|---|
| TS5 gate | `pytest -p no:xdist -o addopts= tests/test_schedule_gate.py` (8 collected) | schedule_gate.py, scheduler.py, schema/schedule.py at 0d9a3b56 | 8 passed; 5 mutants killed |
| TS7 tick | tests/test_schedule_tick.py tests/test_schedule_failures.py (32) | schedule_tick.py at 0d9a3b56 | 32 passed; 7 mutants killed |
| TS1 purge | tests/test_schedule_tick.py (13) | schedule_store.py at 0d9a3b56 | 13 passed; 3 mutants killed; race defect reproduced |
| TS6 guard | tests/test_schedule_tick.py::test_the_tick_modules_import_no_browser_or_pipeline_code | tests/test_schedule_tick.py:160-180 | passes on an added pipeline import (hole) |
| wide set / env readers / ruff / doctor | see evidence file | 0d9a3b56 | 133 / 64 passed, clean, clean |

Not run: full suite (no security/prod-write full-suite trigger applies to a single coordinator here; a dual check will run its own), browser (no UI surface).
