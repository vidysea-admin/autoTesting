# Manifest - mongo-store-u6a

**Status:** ready-for-check
**Fix cycle:** 0
**Contract:** `qa/contracts/mongo-store.md` (ACTIVE 2026-10-29), unit U6a. **Criticality:** CRITICAL (security backbone), dual check (D-100).
**Branch:** `feat/mongo-store-u6a` from `feat/mongo-store-u1` (`4cc05569`). Not merged, not pushed.
**Criteria owned by U6a (unit table):** M29 (invariants preserved, SQLite side: the existing auth tests are the oracle, run unchanged) and M30 (hashes stay inside, SQLite side). U6b re-runs both over `store_mongo.py`; M29's Mongo two-thread tests are U6b's.

## What changed (D-122 list only: `auth/store.py`, `auth/store_sqlite.py`; no other new module)

| File | Kind | One job |
|---|---|---|
| `src/autotester/auth/store.py` | N (94 lines) | `AuthTx` Protocol (one read/write transaction: users, groups and memberships, sessions, project grants, `ensure_an_admin_remains`), `AuthStore` Protocol (`exists`, `reading`, `transaction`), `auth_store()` factory (SQLite only; U6b adds the Mongo branch) |
| `src/autotester/auth/store_sqlite.py` | N (246 lines) | `SqliteAuthTx` / `SqliteAuthStore`: the SQL statements that were inline in accounts/groups/sessions/access, moved with their text and order unchanged, over `db.transaction()` / `db.reading()` |
| `src/autotester/auth/accounts.py` | E in place | no `sqlite3`, no SQL; calls `auth_store()`; the rules (first-admin D-074, claim D-109, AU2 one hash verify on every path, AU8/AU9 order of checks) are the same code paths |
| `src/autotester/auth/groups.py` | E in place | same; `update_group` check order unchanged (Admin edit, grant diff, member grant, name clash, rename, permissions, members, last-admin) |
| `src/autotester/auth/sessions.py` | E in place | same; only the sha256 of a token reaches the store |
| `src/autotester/auth/access.py` | E in place | `require_*` / `acts_as_admin` take an `AuthTx` instead of a `sqlite3.Connection`; no external caller existed (grep over `src tests scripts`) |
| `tests/test_auth_store_seam.py` | N | 13 tests: Protocol conformance, no-SQL AST scan, M29 threaded invariants, M30 hash containment, session/disabled semantics |
| `qa/evidence/mongo-store-u6a/` | N | `mutation-run.txt`, `mutate.py` (the 11 mutants), `oracle-run.txt` (30 existing test files), `run_pairs.sh` |
| `docs/MAP.md`, `docs/SNAPSHOT.md` | generated | `autotester map` / `autotester snapshot` (doctor `stale-generated`) |

**Not touched:** `auth/db.py` (connection, schema, seeding, `LastAdmin`, `NotAllowed`, `admin_group_id`, `ensure_an_admin_remains`, `_READY`, the `generation` trigger all stay; many existing tests and `tests/auth_login_fixture.py` import them, and editing a test to pass is an M29 falsifier). `auth/config.py`, `ui/helpers.py`, every existing test file: zero diff (`git diff --stat 4cc05569 -- tests` lists only the new file).

## Scope boundary (named so nothing is silently dropped)

Video shares/links/requests/comments (`stages/video_access.py`, `video_requests.py`, `video_comments.py`), `stages/schedule_owner.py`, `ui/intake_gate_auth.py`, `store/notification_prefs.py` still use `db.transaction()` / `db.reading()` directly: that is **U6c**, not U6a. They keep working unchanged because `db.py` is untouched. `auth/audit.py` is a file append, not auth-store state.

## Criteria map

| Crit | Code | Test |
|---|---|---|
| M29 behaviour-neutral extraction | `store_sqlite.py` (every statement of the old modules; `git diff 4cc05569 -- src/autotester/auth/accounts.py` shows the SQL removed and the same decisions kept) | the 30 existing files below, unedited, 0 failures |
| M29 one admin from concurrent first signups | `accounts.py::signup` + `_becomes_first_admin` over `SqliteAuthTx` in `db.transaction()` (BEGIN IMMEDIATE) | `test_auth_store_seam.py::test_m29_concurrent_first_signups_yield_exactly_one_admin` (6 threads x 5 fresh stores, Barrier); existing `test_ui_auth_accounts.py::test_au7_two_simultaneous_first_signups_make_one_admin`. Mutants S3 (first-admin always true), S7 (transaction downgraded to a read): KILLED |
| M29 claim: exactly one admin | `accounts.py::claim_admin`, `_claim_refusal` | `::test_m29_concurrent_claims_yield_exactly_one_admin` (4 threads x 5 stores; losers raise `AccountError`); existing `test_ui_auth_claim_admin.py`. Mutant S4 (no "already exists" check): KILLED |
| M29 last-admin | `store_sqlite.py::ensure_an_admin_remains` -> `db.ensure_an_admin_remains`; called by `_update`, `set_user_groups`, `update_group`, `delete_group`, `claim_admin` | `::test_m29_disabling_the_last_two_admins_leaves_one_enabled` (15 repetitions, two threads each disabling a different admin; at least one stays enabled, one `LastAdmin`), `::test_last_admin_guard_survives_delete_and_regroup`. Mutants S2 (guard no-op), S7: KILLED |
| M29 generation immutable, ids not reused, sessions hash-only, disabling effective next request, seeded once | unchanged in `db.py` (trigger, `INTEGER PRIMARY KEY`, `_seed_once`); sessions via `sessions.py::_digest` | existing `test_account_generation.py` (trigger, generation survives reset/bootstrap), `test_ui_auth_groups.py` (seed once across restart); new `::test_seam_round_trip_users_groups_sessions` (raw `sessions.token_hash == sha256(token)`, disable ends the session), `::test_a_disabled_account_or_expired_session_never_resolves`. Mutants S6 (raw token stored), S1 (`u.disabled = 0` dropped): KILLED |
| M29 seam shape | `store.py` Protocol vs `store_sqlite.py` | `::test_sqlite_store_implements_every_protocol_method` (names and parameter lists, both Protocols), `::test_business_modules_hold_no_sql` (AST: no `sqlite3` import, no `execute*`, no `db.transaction/reading/connect` in accounts/groups/sessions/access), `::test_factory_returns_the_sqlite_store`. Mutants S9 (a method renamed), S10 (`import sqlite3` added to groups): KILLED |
| M30 hashes stay inside | `User` / `Group` carry no hash field; `login_record` is the only read of a hash; the `AuthTx` methods that mention a hash are exactly the login/write four | `::test_password_hash_never_leaves_the_store` (`password_hash` not in `User.model_fields` / `Group.model_fields`; `$argon2` appears only in `users` across every other table; repr of `list_users`, `get_user`, `find_user`, `list_groups`, a resolved principal, `user_managers`, `list_waiting`, and the duplicate-signup error text contain neither `argon2` nor `password_hash`), `::test_only_login_paths_of_the_protocol_mention_a_hash`. Mutant S5 (hash appended to the error text): KILLED. List APIs / UI responses / audit rows: the existing `test_ui_auth_*` suites (admin user lists, refusal audit) are green unchanged; `audit.py` is untouched |
| AU16 read creates no store | `SqliteAuthStore.exists` -> `db.store_exists` | `::test_reading_a_missing_store_creates_nothing` |

## Verify

Run in `D:/autoTesting/.claude/worktrees/mongo-u6a`. The disk was at 100%, so `uv sync` could not build a venv here (os error 112). I used the shared venv of the `mongo-u1` worktree with `PYTHONPATH=<this worktree>/src` (checked: `autotester.__file__` resolves to this worktree). Each call: `pytest <2 files> -o addopts= -p no:cacheprovider -q`, one at a time.

Existing oracle, 30 unedited files in 15 two-file calls, **all green** (full output: `qa/evidence/mongo-store-u6a/oracle-run.txt`):

```
test_ui_auth_accounts + test_ui_auth_claim_admin        21 passed
test_ui_auth_cli_and_limits + test_ui_auth_envkeys      29 passed
test_ui_auth_escalation + test_ui_auth_groups           54 passed
test_ui_auth_hardening + test_ui_auth_host_and_consent  32 passed
test_ui_auth_login + test_ui_auth_own_origin            96 passed
test_ui_auth_policy_table + test_ui_auth_refusal_audit   6 passed
test_ui_auth_surface + test_ui_auth_survivors           27 passed
test_account_generation + test_auth_loopback            15 passed
test_portal_requests + test_portal_share                22 passed
test_schedule_owner_guard + test_intake_gate_auth       21 passed
test_tracker_auth + test_ui_signup_requests             37 passed
test_ui_signup_requests_f1 + test_notification_profile  31 passed
test_grant_bounds_caps + test_hosting_gaps              43 passed
test_inbox_scope + test_acceptance_isolation            17 passed
test_role_accounts_routes + test_authz_gate             31 passed
```

New: `tests/test_auth_store_seam.py` -> `13 passed` (re-run after the ruff fix).
`ruff check --no-cache src tests scripts` -> `All checks passed!`.
`doctor`: before regeneration only `stale-generated` / `stale-committed` for `docs/MAP.md` and `docs/SNAPSHOT.md`; regenerated with `autotester map` and `autotester snapshot`, committed. No design-rule finding: store.py 94, store_sqlite.py 246, accounts.py 259 lines, every function under 50.
The full suite was not run (memory rule). The 30 files are every test that imports an auth module or builds the login gate via `auth_harness` / `auth_login_fixture`, plus `test_acceptance_isolation`, `test_hosting_gaps`, `test_inbox_scope`.

## Mutation spec (`qa/evidence/mongo-store-u6a/mutation-run.txt`, runner `mutate.py`; 11/11 killed)

| Mutant | Edit | Killed by |
|---|---|---|
| S1 | `live_principal` drops `u.disabled = 0` | `test_a_disabled_account_or_expired_session_never_resolves` (first run SURVIVED the round-trip test, because a disable ends the session so that test could not reach it; the new test was added and S1 then killed) |
| S2 | `ensure_an_admin_remains` becomes a no-op | `test_last_admin_guard_survives_delete_and_regroup`, `test_m29_disabling_the_last_two_admins_leaves_one_enabled` |
| S3 | `_becomes_first_admin` always true on loopback | `test_m29_concurrent_first_signups_yield_exactly_one_admin` |
| S4 | `_claim_refusal` loses the "administrator already exists" check | `test_m29_concurrent_claims_yield_exactly_one_admin` |
| S5 | duplicate-signup error text carries the hash | `test_password_hash_never_leaves_the_store` |
| S6 | `create_session` stores the raw token | `test_seam_round_trip_users_groups_sessions` |
| S7 | `SqliteAuthStore.transaction` opens a read connection (no BEGIN IMMEDIATE) | the `test_m29_*` concurrency tests |
| S8 | `require_may_touch` never requires admin | existing `test_ui_auth_escalation.py` |
| S9 | `has_session` renamed in `SqliteAuthTx` | `test_sqlite_store_implements_every_protocol_method` |
| S10 | `import sqlite3` added to `groups.py` | `test_business_modules_hold_no_sql` |
| S11 | `delete_user` returns False | existing `test_ui_auth_accounts.py` |

## Things the checker should look at

1. **Protocol granularity.** `AuthTx` is a row-level unit-of-work seam (about 49 methods), not one method per route action. The policy checks (`access.require_*`) must run inside the same transaction as the write (SQLite: BEGIN IMMEDIATE), and a Mongo implementation (U6b) can satisfy each method with CAS and unique indexes without transactions. If the checker wants coarser atomic operations, say so in the verdict.
2. **`authenticate`** now builds the `User` (one extra group-name query) even when the password check fails. The verify-once-on-every-path rule (AU2) is unchanged and no hash is returned beyond `login_record`.
3. **`update_group` / `delete_group`** read the group through `get_group` (which also loads permissions and members) instead of selecting only `seed`: same decisions, a few more reads inside the transaction.
4. **`enable_with_password_hash`** is the old `UPDATE users SET password_hash = ?, disabled = 0` of `bootstrap_admin`, kept as one statement.
5. `auth/db.py` still owns `ensure_an_admin_remains` / `admin_group_id` (used by `SqliteAuthTx` and, for `admin_group_id`, by `tests/auth_login_fixture.py`). Moving them out would edit existing tests.
6. The shared-venv workaround above: `uv run` in this worktree fails on a full disk, not on the code.
