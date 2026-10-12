# Checkpoint (dual-check coordinator A, repair cycle 3) - t204-team-login
Cycle checked: 3 · Result: PASS (verdict qa/verdicts/t204-team-login.r3.a.md) · Policy-Version: proportional-verification/2026-10-10.9

## Evidence identity
- Bound code: branch `wave/t204-team-login` head `37a1d211` (product `48a08926`; master merge `cc5c4a3b`, parents `40f9de52` and `1c52bf71`; cycle-3 fix `dd7b49e5`; repair base `27a3a0a9`). Head tree hash `fffe608fcb33c9a6d9f916a4e220ef93ba19a76b`; `uv.lock` blob `93f572ebd6d09389ce818ffd7be5e8719603ccbd`.
- Environment: Windows 11, Python 3.11, uv; one `git archive 37a1d211` copy on C: with its own `.venv` (`%TEMP%/chk/t204r3a-*`); each mutation in a further throwaway copy; `autotester.__file__` printed and inside the copy in every probe. No `.env` value read; test accounts only.
- Original checker attribution: coordinator A, evidence under `qa/evidence/t204-team-login-r3-A/` (no other checker's evidence used).

## Checks run (command and scope -> result)
- AU20 repair: `docker compose config` x4 cases + `check_startup` x 3 allow-list shapes + live request guard (au20/q2-table.txt) -> as AU20 says; loopback tables (q3) -> refused; hosts-only concrete bind (q4) -> RAISED at 27a3a0a9 and dd7b49e5.
- `pytest tests/test_hosting_deploy.py tests/test_ui_auth_own_origin.py` -> 90 passed; mutant A (compose default reverted) 4 red; mutant B (loopback refusal removed) 6 red.
- Route walk (routes/walk_routes.py): 74 served = 74 rows, 494 disambiguation probes, 0 mismatch; status matrix (9 principals); path/method/header tricks x 7 targets on real uvicorn -> 0 wrong 2xx.
- `pytest tests/test_ui_auth_*.py` (12 files) -> 254 passed; 8 route-relevant ids x 9 mutants (row removal x3, EXPECTED removal x3, wrong key x3) -> all red as expected.
- Affected tests (unit diff + merge diff + files the merge changed) -> 1079 passed, 1 skipped; intake tests 51 passed, 14 red with the `asgi_helpers.py` edit reverted.
- `ruff check src tests scripts` clean; `autotester doctor` clean; `uv lock --check` ok; no file > 300 lines, no function > 50.
- Trial merge 37a1d211 into master d42e9445 (clone on C:) -> clean; with t205 ecaaf7e4 -> 6 conflicts.
- Full sharded suite (`shard_suite.py --shards 4`, 4255 collected = 4255 ran, venv python of the copy) -> 4228 passed, 21 skipped, 6 failed (AT-858 x2, AT-750, AT-725, AT-921 known; `test_core` env-creation passed alone). Duration 1942 s.

## Reuse
Reusable by a later check only while the head tree hash and the lock blob above are unchanged. The suite result is bound to `37a1d211`.
