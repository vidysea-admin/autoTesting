# Manifest - e2e-fixes-e9

**Status:** checked-PASS (cycle 0, verdict bbe9b824)
**Fix cycle:** 0
**Contract:** `qa/contracts/e2e-fixes.md`, unit E9 (E9.1-E9.3). **Criticality:** MEDIUM, one hold (E9.3b).
**Branch:** `feat/e2e-e9` (worktree `D:/autoTesting/.claude/worktrees/e2e-e9`), cut from master `6eb21a54`. Not merged, not pushed.
**Code SHA:** the commit that adds this file, `git log -1 feat/e2e-e9`.

## What changed

| File | Change |
|---|---|
| `tests/test_credential_store_u11.py:70-74` | allow-list is now the exact 3-file EQUALITY `{core/env.py, ui/env_editor.py, store/migrate_creds.py}` with an M46 comment. Other assertions untouched. |
| `src/autotester/store/mongo_backend.py:73` (`_guard`) | in place: the f-string interpolated the SCREAMING_CASE `MAX_DOC_BYTES` (bound by a tuple assignment at `:35`, so `advice_scan` cannot fold it). Now `{int(MAX_DOC_BYTES)}` (a call, not a bare name). Message still carries key, size, limit (wording `; limit N`). File stays 300 lines. |
| `tests/test_schedule_tick.py` `ALLOWED_OUTSIDE` | gains exactly `auth.store_mongo`, `auth.store_mongo_tx`, `auth.store_mongo_video`, `auth.store_mongo_fence` with a U6a-precedent comment. No `autotester.browser.*` added. |
| `tests/test_schedule_tick.py` TS6 guard | E9.3(b) HELD (see below): the guard test is `xfail(strict=True)`; plus ONE added test pinning `scheduler_side_violations() == ["autotester.store.mongo_routes -> autotester.browser.profiles"]` so a NEW violation still fails (a bare xfail would hide it). |

No `tests/advice_scan.py`, `tests/test_cli_advice_resolves.py`, `ui/`, `browser/profiles.py` or `store/mongo_routes.py` change.

## E9.3(b): HUMAN_GATE (option ii), not option (i)

Edge: `store/mongo_routes.py:195` (`repo_redactor`, lazy `from autotester.browser.profiles import stored_session_values`). Moving it is not cheap or honest here:
- `stored_session_values` (`browser/profiles.py:216`) needs `_collection` (`:62`, uses `SESSION_COLLECTION`), `session_values` (`:199`), `_leaves`, `_dicts`, `MIN_VALUE_LEN`, `MAX_MASKED`; tests call `profiles.session_values`, `profiles.MAX_MASKED`, `profiles.stored_session_values` (`tests/test_session_store_u12f.py:188`, `test_session_store_u12_redaction.py:90,116`), and `profiles.py` itself still uses `_dicts`/`session_values`/`MAX_MASKED` for `capture_session`.
- the only scheduler-reachable homes are existing `store/*` modules: `mongo_routes.py` is 292 lines (cap 300), `mongo_backend.py` is 300. A new module needs a D-entry (not allowed to me).
Decision for Umesh/orchestrator: (a) approve a new store module (e.g. `store/session_values.py`) holding the redaction half, with `browser/profiles.py` importing it; or (b) accept the xfail. Issue id: to be assigned at filing (E9 table); the xfail reason says "E9.3(b) HUMAN_GATE". `browser.profiles` is NOT allow-listed.

## Evidence (all in the worktree, `env -u ANTHROPIC_BASE_URL uv run pytest ... -o addopts= -q`)

- `tests/test_credential_store_u11.py tests/test_cli_advice_resolves.py` -> `63 passed, 21 warnings in 88.05s`
- `tests/test_schedule_tick.py tests/test_mongo_backend_layout.py -rxX` -> `84 passed, 1 xfailed` (XFAIL: the TS6 guard, reason E9.3(b)). `test_mongo_backend_layout.py:62` (`StoreDocTooLarge, match="limit"`) passes unmodified.
- `uv run ruff check src tests scripts` -> `All checks passed!`
- `uv run autotester doctor` (to file) -> only 2 violations, both `docs/SNAPSHOT.md` stale-generated/stale-committed (pre-existing master drift, same as E7 manifest; siblings regenerate the identical line; NOT regenerated here to avoid cross-unit conflicts). No size/duplicate findings.
- `git diff --stat` shows no change in `tests/advice_scan.py` / `tests/test_cli_advice_resolves.py`.

## Mutations (each run, then reverted; `git status` clean of them)

| Mutant | Result |
|---|---|
| E9.2: restore `{MAX_DOC_BYTES}` in the f-string (`mongo_backend.py:73`) | `test_the_collector_reports_what_it_could_not_resolve` FAILS: `[(...mongo_backend.py), 73)] == []` |
| E9.1: rename `credential_collection(` away in `store/migrate_creds.py` | `test_only_the_door_writes_secrets_and_no_crypto_exists` FAILS (equality) |
| E9.3: append `from autotester.browser.session import BrowserSession` to `auth/store_mongo_tx.py` | `test_the_only_scheduler_side_violation_is_the_known_redactor_edge` FAILS (`autotester.auth.store_mongo_tx -> autotester.browser.session` extra); the strict xfail stays xfail, which is why the companion test exists |
| E9.1: fourth user of `credential_collection(` | not run separately; the assertion is `==`, so any extra file fails it by construction |

## Not done

E9.3(b) edge removal and the `repo_redactor` equivalence test (not applicable under option ii). Issue ids unassigned.
