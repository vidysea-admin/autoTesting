# Verdict - mongo-store-u6a (Checker B, adversarial security)

**Checked by:** /checker B (fresh context, read-only toward src/ and tests/; no maker reasoning used, manifest claims re-run)
**Date:** 2026-10-30
**Branch / head:** `feat/mongo-store-u6a`, code unchanged since `ef740beb` (the only later commit, `91ad928e`, adds a verdict file; I did not read it)
**Contract:** `qa/contracts/mongo-store.md` M29, M30 (U6a; CRITICAL, dual check, D-100)
**Manifest:** `qa/manifests/mongo-store-u6a.md` - `Status: ready-for-check`

**Cycle checked: 0**

## Verdict: PASS (4 non-blocking warnings, no criterion broken)

The seam is a behaviour-neutral extraction. I found no transaction boundary weakened, no query built from
caller-controlled text, no change to hash or token handling, and no new user-existence leak. 18 of the 21
mutants I wrote were killed by the existing suite plus the new seam tests. The 3 survivors (W1: R3, R4; W2: A4) are
holes in the oracle for behaviour the extraction preserved, not defects in the extraction. W3 and W4
are design notes for U6b.

## Commands I ran (worktree `D:/autoTesting/.claude/worktrees/mongo-u6a`, `ANTHROPIC_BASE_URL` unset, max 2 files per call)

| Command | Result |
|---|---|
| `uv run pytest tests/test_auth_store_seam.py tests/test_ui_auth_claim_admin.py -o addopts=` | 21 passed |
| `uv run pytest tests/test_ui_auth_envkeys.py tests/test_ui_auth_policy_table.py -o addopts=` | 25 passed |
| `uv run pytest tests/test_auth_store_seam.py -o addopts= -k m29` (twice) | 3 passed, 3 passed (race tests not flaky) |
| `uv run ruff check src tests scripts` | All checks passed! |
| `uv run autotester doctor > .work/doctor-u6a-b.txt` | exit 0, last line `doctor: clean` |
| scratch copy (`git archive HEAD` into `.work/mut-u6a-b`), unmutated baseline, 9 test files in 5 calls | 21, 34, 54, 23, 14 passed |
| `git diff 0f89becc HEAD --stat -- src` | only `auth/access.py`, `accounts.py`, `groups.py`, `sessions.py`, `store.py`, `store_sqlite.py`; nothing in `ui/`, `stages/`, `cli*`, `auth/audit.py`, `auth/db.py` |

## Findings

### Held (what I attacked and could not break)

1. **Transaction boundaries unchanged.** Every write path runs inside `SqliteAuthStore.transaction()` (`store_sqlite.py:242-245`), which is `db.transaction()` = `BEGIN IMMEDIATE` (`db.py:163`). `claim_admin` (`accounts.py:81-94`) and `signup` (`accounts.py:97-110`) re-check and insert in one transaction. Mutant B1 (claim check moved to `reading()`, insert in a later transaction), B2 (`_becomes_first_admin` evaluated in `reading()` before the signup transaction) and W1 (`transaction()` opening `db.reading()`) were all KILLED by `test_m29_concurrent_claims_yield_exactly_one_admin` / `test_m29_concurrent_first_signups_yield_exactly_one_admin`.
2. **Last-admin guard intact on every path.** `ensure_an_admin_remains` is still called by `_update` (`accounts.py:168`), `set_user_groups`, `update_group`, `delete_group`. Mutants L1 (set_user_groups), L2 (update_group), L3 (delete_group), L4 (`after_delete` dropped), L5 (call removed from `_update`): all KILLED (by the seam last-admin tests or `test_au9_last_admin_cannot_be_locked_out`).
3. **No string-built SQL from caller data.** Every value in `store_sqlite.py` is a `?` parameter. The only formatting is constant: `_USER_HELD.format(...)` with two literals (`:66-67`, moved verbatim from the old `user_managers`) and `add_membership`'s `verb` chosen from a bool (`:166-168`, new but constant-only).
4. **Hash and token handling unchanged.** `login_record` (`store_sqlite.py:54`) is the only read of a hash; `User` and `Group` have no hash field; tokens reach the store only as sha256 (`sessions.py` `_digest`). Mutants R6 (logout no-op), H1 (skip verify for unknown email, AU2), H2 (reset stores the raw password) KILLED. R5 (session expiry check dropped) KILLED.
5. **Authorization checks intact.** A1 (`acts_as_admin` always true), A2 (regroup grant check removed), A3 (`_held` check removed), A5 (delete-Admin/CEO admin check removed): all KILLED by `test_ui_auth_escalation.py`.
6. **Audit and write fence.** No file outside the six auth modules changed, so every audit call site (`ui/`, `auth/audit.py`) is untouched. The write fence (`mongo_guard`) is U1/U4 scope and is not referenced by `auth/` (`grep mongo src/autotester/auth` finds only docstrings); there is no fence to skip in U6a.
7. **No new user-existence leak.** The error strings in `claim_admin`, `signup`, `authenticate` are the pre-extraction strings. `authenticate` still verifies once on every path (`accounts.py:120-124`; mutant H1 proves the test pins it). The duplicate-signup message ("an account with this email already exists") is pre-existing behaviour.

### Warnings (non-blocking; none violates M29/M30 as scoped to U6a)

**W1 - oracle gap: `decline_waiting` and `bootstrap_admin` session revocation are untested.** Mutant R3 (`accounts.py:239`, `tx.delete_user_sessions` removed from `decline_waiting`) and R4 (`accounts.py:254`, removed from `bootstrap_admin` for an existing account) SURVIVED the seam file plus `test_ui_auth_{accounts,login,escalation,survivors,cli_and_limits}`, `test_account_generation`, `test_ui_signup_requests{,_f1}`, `test_notification_profile`. Behaviour demo on the scratch copy (script run on clean HEAD, then on the mutants):
```
clean HEAD:  R4 old session still live after bootstrap reset: False
             R3 declined account's old session live after re-enable: False
mutants:     R4 ... True
             R3 ... True
```
Consequence: a CLI password reset of an existing admin would leave the stolen session alive, and a declined-then-re-enabled account would resurrect its session. The extraction preserved the correct behaviour; only the tests do not pin it. U6b has to re-implement both, so add tests before it starts (a new test in `tests/test_auth_store_seam.py`, not an edit of an existing test).

**W2 - oracle gap: a non-admin with `groups.manage` editing the Admin/CEO group is not pinned.** Mutant A4 (`groups.py:79-80`, the `require_admin(... "edit the Admin/CEO group")` guard disabled) SURVIVED. `test_p5_only_admin_edits_or_deletes_the_admin_group` only passes because its edit also adds a member and an admin-only permission, which a second guard refuses. Demo (non-admin Ops with `groups.manage` renames Admin/CEO and removes `credentials.view`):
```
clean HEAD:  refused: refused: only an Admin/CEO member can edit the Admin/CEO group
mutant A4:   NON-ADMIN EDITED THE ADMIN/CEO GROUP: Admin/CEO (edited) False
```
The seam implementation is correct; the guard is just carried by one line that no test isolates. Add a rename/strip-permission case as above before U6b copies the rule.

**W3 - `reading()` hands out the same write-capable type as `transaction()`.** `AuthStore.reading()` returns `AuthTx` (`store.py:86`), whose docstring says "Writes are meaningful only on a transaction" (`store.py:22`) but nothing enforces it. On SQLite a write issued through `reading()` autocommits with no `BEGIN IMMEDIATE` and no last-admin check. Proven:
```
with auth_store().reading() as tx: tx.set_disabled(<only admin id>, True)
-> only admin disabled via reading(): True
```
No current caller does this (the writes under `reading()` in `sessions.resolve_session` open their own `transaction()`, as before), and the old `db.reading()` allowed the same, so this is not a regression. For U6b, give `reading()` a read-only Protocol (`AuthReadTx`) so a Mongo implementation cannot be driven into unguarded writes.

**W4 - minor: no test scans `store_sqlite.py` for string-built SQL.** `test_business_modules_hold_no_sql` covers only the four business modules. The two `.format` / f-string sites listed in held-3 are constant-only today; a lint test (no f-string or `+` argument to `execute` in `store_sqlite.py`) would keep them so. Also informational: `login_record` now builds the `User` (one extra group query) for an existing account before the password is verified (`store_sqlite.py:54-58`); the added time is microseconds against an argon2 verify and every path still verifies, so I do not count it as an enumeration channel.

## Mutation table (scratch copy only; the worktree `src/` and `tests/` were never edited)

Runner: `python mutate_b.py`, scratch copy `.work/mut-u6a-b` (deleted afterwards), `PYTHONPATH=<scratch>/src` (checked: `autotester.__file__` resolves into the scratch copy), each mutant restored in a `finally`. A mutant is KILLED when any listed file pair fails.

| Mutant | Edit | Result | Killed by |
|---|---|---|---|
| B1 | claim check in `reading()`, insert in a later transaction | KILLED | `test_m29_concurrent_claims_yield_exactly_one_admin` |
| B2 | `_becomes_first_admin` in `reading()` before the signup transaction | KILLED | `test_m29_concurrent_first_signups_yield_exactly_one_admin` |
| W1 | `SqliteAuthStore.transaction` opens `db.reading()` | KILLED | `test_m29_concurrent_claims_yield_exactly_one_admin` |
| L1 | `set_user_groups` without `ensure_an_admin_remains` | KILLED | `test_last_admin_guard_survives_delete_and_regroup` |
| L2 | `update_group` without it | KILLED | `test_au9_last_admin_cannot_be_locked_out` |
| L3 | `delete_group` without it | KILLED | `test_last_admin_guard_survives_delete_and_regroup` |
| L4 | `after_delete=deleting` dropped | KILLED | `test_last_admin_guard_survives_delete_and_regroup` |
| L5 | `_update` without the guard | KILLED | `test_m29_disabling_the_last_two_admins_leaves_one_enabled` |
| R1 | `_update` never ends sessions | KILLED | `test_au8_password_reset_revokes_sessions` |
| R2 | `reset_password` without session revoke | KILLED | `test_au8_password_reset_revokes_sessions` |
| R3 | `decline_waiting` without session revoke | SURVIVED | gap W1 |
| R4 | `bootstrap_admin` existing account without session revoke | SURVIVED | gap W1 |
| R5 | `live_principal` expiry check dropped | KILLED | `test_seam_round_trip_users_groups_sessions` |
| R6 | `delete_session` no-op | KILLED | `test_au4_logout_ends_the_session` |
| H1 | unknown email skips the verify | KILLED | `test_au2_an_unknown_email_still_pays_one_verification` |
| H2 | `reset_password` stores the raw password | KILLED | `test_au8_password_reset_revokes_sessions` |
| A1 | `acts_as_admin` always true | KILLED | `test_p5_a_held_admin_only_key_is_still_admin_only_to_grant` |
| A2 | `require_may_regroup` grant check removed | KILLED | `test_p5_users_manage_cannot_hand_out_a_group_it_does_not_cover` |
| A3 | `require_may_grant` `_held` check removed | KILLED | `test_p5_a_new_group_cannot_carry_more_than_its_creator_holds` |
| A4 | `update_group` Admin/CEO `require_admin` disabled | SURVIVED | gap W2 |
| A5 | `delete_group` Admin/CEO `require_admin` disabled | KILLED | `test_p5_only_admin_edits_or_deletes_the_admin_group` |

(The maker's own S1-S11 were not repeated; B1/B2/L1-L5/R*/H*/A* are additional.) 18 killed, 3 survived of the 21 rows above.

## What I did not do

Did not run the full suite (memory rule); the 30-file oracle of the manifest was spot-checked through the ~14 files above, all green in the scratch baseline and the worktree. Mongo behaviour is U6b scope and was not judged. No `.env` value was read or printed.
