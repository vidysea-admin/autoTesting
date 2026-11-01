# Verdict - e2e-fixes-e6 (checker C2, fresh recheck)

**Verdict:** PASS
**Cycle checked:** 2
**Unit:** e2e-fixes-e6 (E6, AT-1419), branch `feat/e2e-e6`, code under test `e39c56dd` (cycle-2 fix `896b5ba9`)
**Scope:** cycle-1 finding F1 (flaky `tests/test_live_proxy_ws.py`) and regressions from the `_pump` change. Judged only from the code and fresh runs; no other checker's verdict on this unit was read.
**Environment:** `env -u ANTHROPIC_BASE_URL`, `TMP`/`TEMP` and `--basetemp` under `.work/tmp-c2`, `-o addopts=`, one pytest at a time (C: full, low memory).

## F1 - fixed

`tests/test_live_proxy_ws.py` run 12 consecutive times, each a separate `uv run pytest` (log `.work/c2-ws-repeat.txt`):

```
run 1..12: 13 passed, 2 warnings   (12.0 s - 21.1 s each)      -> 12 of 12 clean, 0 failures, 0 errors
```

(The maker's own log, 12 of 12, is not relied on.)

## `_pump` change review (`src/autotester/ui/routes_live.py:184-207`, file is exactly 300 lines)

- Cleanup (gather the two tasks, `up.close()`, close the client with 1000/1009/1011 by `up.close_code`) is an inner coroutine run under `asyncio.shield(asyncio.ensure_future(cleanup()))` inside the `finally`; a cancelled handler still finishes closing both sides. A second cancel during cleanup takes `except asyncio.CancelledError`, calls `up.transport.abort()` (suppressed) and re-raises, so the upstream is never left open and the cancellation is never swallowed.
- `up.transport` exists on websockets 16.1.1 (the project venv): `websockets/asyncio/connection.py` assigns `self.transport`.
- Independent probe (script `.work/c2-probe.py`, fakes for upstream and client, not committed because it is scratch and the brief forbids editing tests):
  1. single cancel mid-wait with a slow `close()`: cleanup ran to completion, `up.closed=True`, `abort` NOT called, client closed 1000, `CancelledError` propagated;
  2. second cancel while cleanup in flight: `abort` called, `CancelledError` propagated, the detached cleanup still finished (`closed=True`);
  3. normal client disconnect: upstream closed, no abort, client closed 1000.
- No behaviour change for the non-cancel path (mutants b4-b8 still kill, below). The wording/docstring trims elsewhere in the file are comments only (`git diff 9fb34ac5 HEAD -- src/` touches nothing but comments and `_pump`).

## Other E6 verification, re-run

```
test_live_proxy_http + test_live_default_url            -> 39 passed
test_live_proxy_ws + test_ui_auth_policy_table          -> 15 passed
test_hosting_gaps + test_ui_healthz                     -> 41 passed + 1 ERROR (see W1); re-run alone: 42 passed
test_routers_list + test_ui_auth_surface                -> 27 passed
acceptance test_ta02 + test_ta03                        -> 11 passed
test_ui_auth_escalation + test_ui_auth_host_and_consent -> 34 passed
test_hosting_config + test_ui_sidebar                   -> 14 passed
test_ui + test_ui_dashboard                             -> 29 passed
ruff check src tests scripts                            -> All checks passed!
autotester doctor > .work/c2-doctor.txt                 -> exit 0, "doctor: clean" (first attempt hit MemoryError importing rich under load; re-run clean)
scripts/mutation_check.py qa/evidence/e2e-fixes-e6/mutations-ws.json -> 8/8 mutations killed (b1..b8 all KILLED, each by its claimed test)
```

## Warnings (non-blocking)

- **W1** The first `test_hosting_gaps.py::test_every_entry_records_who_and_how_and_the_panel_shows_it` run reported one fixture ERROR in a loaded run sharing a basetemp; re-run with a fresh basetemp passed 42/42. Not in an E6 file; recorded, not reproduced.
- **W2** The new cancel branch (`up.transport.abort()`) has no repo test; the cycle-2 tests deliberately close inside the `with` so the abrupt-client-vanish path is no longer exercised by them. My probe above covers it once, not permanently. Optional follow-up test, not required by E6.1-E6.9.
- **W3** (carried, documented by the maker) client-to-server frame cap behind uvicorn is its default 16 MiB, not 32 MiB.

## Result

F1 is fixed (12/12), `_pump` is cancellation-safe and does not regress the non-cancel path, all other E6 pairs, ruff, doctor and the 8 ws mutants are green. E6 PASS at cycle 2.
