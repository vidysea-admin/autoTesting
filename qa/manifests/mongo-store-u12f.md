# Manifest - mongo-store-u12f

**Status:** ready-for-check
**Fix cycle:** 0
**Contract:** `qa/contracts/mongo-store.md` (ACTIVE), unit U12 follow-up; criteria M38, M39, M40, M34, M8. **Criticality:** CRITICAL, dual check (D-100).
**Authority:** D-120..D-123 (plain storage, no crypto). Fixes the warnings of the U12 dual check (`qa/verdicts/` A 764ff1e2, B 52d15363). No new `src/` module.
**Branch:** `feat/mongo-store-u12f`, cut from master `54db88c6`. Not merged, not pushed.
**Base SHA:** `54db88c6`

## What changed

| File | Warning | Change |
|---|---|---|
| `src/autotester/browser/profiles.py` (263 lines) | A-W1 | `_put_session :72` calls `default_backend().rearm()` instead of `reset_default_backend()`: one MongoClient across saves (U11f), gate still rebuilt (M34). |
| same | W3 | `_dicts :84` (list members that are dicts, else nothing); `scope_state :89` keeps only well-formed `localStorage` items per origin; `_readable :138` rejects a document with non-numeric `expires_at`/`saved_at`, a non-dict `state`, non-list `cookies`/`origins`, a `saved_at` more than `SKEW_S` (300 s) ahead, and re-applies the cap `min(expires_at, saved_at + MAX_AGE_S)` on load. `load_session` deletes such a document and returns `None`. `session_values` reads cookies/localStorage through `_dicts`, so `repo_redactor()` (via `stored_session_values`) cannot raise on a bad item. |
| `src/autotester/stages/multi_role_session.py` (211) | W2 | `RoleSessions.sign_in` no longer captures. New `save_login :206` captures on the account's own thread. |
| `src/autotester/stages/role_session_port.py` | W2 | `LiveRolePort.login :113-114` calls `self.roles.save_login(role_id)` only when `proven`, inside the same `try`, so an outage fails the login closed (`RoleLoginFailed`) as before. A failed login or missing proof never overwrites a good stored session. |
| `src/autotester/ui/routes_project_edit.py` (276) | W4 | `undeclare_secret :268-270`: after `drop_credentials`, `forget_session` for every role account whose `username_key` or `password_key` is the undeclared key. Done before the project save with the credential delete, so a store outage still raises before anything changed (U11f order). |
| `tests/test_session_store_u12f.py` (229) | all | 11 tests, each names its warning. |
| `tests/test_session_store_u12_redaction.py` | W2 | the role-sessions test now asserts `sign_in` alone stores nothing, then `save_login` stores (same test name, so the U12 evidence spec stays valid). |
| `qa/evidence/mongo-store-u12f/` | | `mutations.json`, `mutation-run.txt`, `tests.txt`. |

## Verification (all run in this worktree)

- Tests, two files per call, `env -u ANTHROPIC_BASE_URL uv run pytest ... -o addopts=` (`qa/evidence/mongo-store-u12f/tests.txt`): u12f+u12 28 passed; u12_redaction+manual_login 11 passed; entry_browser_reuse_lent+u11f 42 passed; multi_role_session+role_session_port_login 13 passed; role_session_port+u11f 44 passed.
- `uv run ruff check src tests scripts`: All checks passed.
- `uv run autotester doctor > .work/doctor-u12f.txt`: `doctor: clean` (exit 0). `uv run autotester map` produced no change.
- Mutation: `uv run python scripts/mutation_check.py qa/evidence/mongo-store-u12f/mutations.json --repo .` -> `18/18 mutations killed` (`mutation-run.txt`; sources restored, `git status` clean of mutants).

## Criteria map

| Warning | Test (tests/test_session_store_u12f.py) | Mutants killed |
|---|---|---|
| A-W1 one client, gate rebuilt | `test_session_saves_reuse_one_client_and_the_gate_still_rebuilds` | save resets backend; no rearm |
| B-W1 `manual_login.py:48` | `test_a_manual_login_is_saved_under_the_project_account` | save deleted; wrong account |
| B-W1 `run_execution.py:178` | `test_a_normal_run_restores_the_project_account_login` (also proves it restores `_project`, not t1) | restore deleted; wrong account |
| W2 | `test_a_failed_login_never_replaces_a_good_stored_session`, `test_a_proven_login_is_saved` (real `LiveRolePort.login` over `RoleFake`, probe stubbed) | save before proof; save when proof fails; proven not saved |
| W3 | `test_a_malformed_stored_state_is_deleted_not_raised` (`cookies=5`), `test_a_bad_stored_item_never_breaks_the_run_wide_redactor`, `test_a_stored_localstorage_shape_error_does_not_stop_a_restore`, `test_a_tampered_far_future_expiry_is_not_trusted_on_load`, `test_a_save_time_in_the_future_is_not_a_login` | shape check removed; cap not re-applied; future save trusted; three `_dicts` reverts |
| W4 | `test_undeclaring_a_role_credential_key_forgets_that_accounts_login` (password key of t1: t1 gone, t2 and `_project` kept) | forget removed; username-only; forget all |

## Judgement calls and left-open items

- W4 scope: wired where a SecretRef is undeclared (the only removal path; there is no role-account delete route, `merge_by_id` only adds/updates). If the later project save fails, the credential value is restored but the session is not: it is only a logged-out account, benign. The `_project` login is not forgotten by an undeclare (it is not tied to one key).
- `SKEW_S = 300` and "a tampered `saved_at` ahead of now means delete" are my choices; the contract names the 24h cap only.
- **W5 left open:** a restore may overwrite fresher cookies already in the context (flagged by the checker, not fixed).
- **W6 left open:** the `orchestrate_execute` path does not restore a login (flagged, not fixed).
- Live Chromium with the store on is still untested.
