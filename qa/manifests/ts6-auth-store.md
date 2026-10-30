# ts6-auth-store — TS6 scheduler import boundary admits the U6a AuthStore seam

**Status:** ready-for-check
**Fix cycle:** 0
**Contract:** qa/contracts/team-schedules.md TS6 (scheduler side reaches no browser/pipeline module); qa/contracts/mongo-store.md M29
**Authority:** D-120..D-123 (mongo-store U6a, merged 3400132f)
**Round cap:** (a) SECURITY CLASS -- import-boundary regression net, uncapped
**Base SHA:** 0a2cbe45
**Code SHA:** (this commit)

## Problem
`tests/test_schedule_tick.py::test_the_scheduler_side_reaches_no_browser_or_pipeline_module_even_transitively` fails on master 0a2cbe45:
`AssertionError: assert ['autotester....store_sqlite'] == []`. U6a made `auth/access.py` import `autotester.auth.store` (-> `auth.store_sqlite`),
and the test's `ALLOWED_OUTSIDE` lists `auth.db` (the account store) but not the seam that now fronts it. Found by the U3c maker.

## What changed
- `tests/test_schedule_tick.py:157-159`: add `autotester.auth.store`, `autotester.auth.store_sqlite` to `ALLOWED_OUTSIDE`, beside `auth.db`.
  The walk still descends into them (`todo.append(dep)` at :221), so any browser/pipeline import they gain still fails TS6.
- No src change.

## Verification
- `uv run pytest tests/test_schedule_tick.py -o addopts=` -> `21 passed, 10 warnings in 19.24s`
- `uv run ruff check tests/test_schedule_tick.py` -> `All checks passed!`
