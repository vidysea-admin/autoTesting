# Manifest - mongo-store-u12f

**Status:** ready-for-check
**Fix cycle:** 1
**Contract:** `qa/contracts/mongo-store.md` (ACTIVE), unit U12 follow-up; criteria M38, M39, M40, M34, M8. **Criticality:** CRITICAL, dual check (D-100).
**Authority:** D-120..D-123 (plain storage, no crypto). Fixes the warnings of the U12 dual check (`qa/verdicts/` A 764ff1e2, B 52d15363). No new `src/` module.
**Branch:** `feat/mongo-store-u12f`, cut from master `54db88c6`. Not merged, not pushed. Cycle 0 PASSED both checkers (5a370f7b, 4ade61de); cycle 1 fixes their three small defects.
**Base SHA:** `54db88c6`; cycle 1 is on top of `4ade61de`.

## What changed

| File | Warning | Change |
|---|---|---|
| `src/autotester/browser/profiles.py` (263 lines) | A-W1 | `_put_session :72` calls `default_backend().rearm()` instead of `reset_default_backend()`: one MongoClient across saves (U11f), gate still rebuilt (M34). |
| same | W3 | `_dicts :84` (list members that are dicts, else nothing); `scope_state :89` keeps only well-formed `localStorage` items per origin; `_readable :138` rejects a document with non-numeric `expires_at`/`saved_at`, a non-dict `state`, non-list `cookies`/`origins`, a `saved_at` more than `SKEW_S` (300 s) ahead, and re-applies the cap `min(expires_at, saved_at + MAX_AGE_S)` on load. `load_session` deletes such a document and returns `None`. `session_values` reads cookies/localStorage through `_dicts`, so `repo_redactor()` (via `stored_session_values`) cannot raise on a bad item. |
| `src/autotester/stages/multi_role_session.py` (211) | W2 | `RoleSessions.sign_in` no longer captures. New `save_login :206` captures on the account's own thread. |
| `src/autotester/stages/role_session_port.py` | W2 | `LiveRolePort.login :113-114` calls `self.roles.save_login(role_id)` only when `proven`, inside the same `try`, so an outage fails the login closed (`RoleLoginFailed`) as before. A failed login or missing proof never overwrites a good stored session. |
| `src/autotester/ui/routes_project_edit.py` (276) | W4 | `undeclare_secret :268-270`: after `drop_credentials`, `forget_session` for every role account whose `username_key` or `password_key` is the undeclared key. See cycle 1 (C2) for the final order. |
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

- W4 scope: wired where a SecretRef is undeclared (the only removal path; there is no role-account delete route, `merge_by_id` only adds/updates). The session is forgotten BEFORE the credential is dropped (cycle 1, C2), so it is not restored if the later drop or project save fails: that only leaves an account logged out, benign. The `_project` login is not forgotten by an undeclare (it is not tied to one key).
- `SKEW_S = 300` and "a tampered `saved_at` ahead of now means delete" are my choices; the contract names the 24h cap only.
- **W5 left open:** a restore may overwrite fresher cookies already in the context (flagged by the checker, not fixed).
- **W6 left open:** the `orchestrate_execute` path does not restore a login (flagged, not fixed).
- Live Chromium with the store on is still untested.

## Fix cycle 1 (both cycle-0 checkers PASSED; three small defects)

| # | Defect | Fix | Test (tests/test_session_store_u12f.py) |
|---|---|---|---|
| C1 | NaN/inf defeated the age cap | `_readable` (profiles.py:148) requires `expires_at` and `saved_at` to be finite (`math.isfinite`) | `test_a_non_finite_time_cannot_defeat_the_age_cap` x5: NaN `expires_at`; NaN `saved_at`; NaN `saved_at` + inf `expires_at`; inf `expires_at`; -inf `saved_at`. Each returns `None` and deletes the document. |
| C2 | Orphaned credential: `forget_session` ran after `drop_credentials`, outside the restore `try` | `undeclare_secret` (routes_project_edit.py:266-270) forgets the sessions FIRST, then snapshots and drops the credential inside the unchanged restore `try`. | `test_a_failing_forget_leaves_the_credential_and_the_declaration_alone`: forget raises -> OSError, credential still stored, declaration still has the key, session untouched. |
| C3 | Skew boundary and non-dict state untested; a lagging reader deleted the document | `_ahead` (profiles.py:139) is checked in `load_session` before `_readable`: a `saved_at` more than `SKEW_S` (300 s) ahead returns `None` and leaves the document (a reader with a slow clock must not erase another reader's login). `_readable` keeps the non-dict `state` rejection. | `test_the_skew_boundary_is_exactly_five_minutes` (literal 300: loads at +300, `None` at +301, document kept), `test_a_save_time_in_the_future_is_not_a_login` (now asserts the document is kept), `test_a_stored_state_that_is_not_a_dict_is_deleted` (str, list, int, None). |

**Correction to the cycle-0 text:** "raises before anything changed" is now true of the forget step only because it runs first: a forget failure raises with the credential, the declaration and the other sessions untouched; a drop or save failure after it restores the credential (sessions already forgotten stay forgotten). In cycle 0 the forget ran after the credential drop and outside the `try`, so that claim was false for a forget failure.

Verification (cycle 1): `qa/evidence/mongo-store-u12f/tests-cycle1.txt` (u12f+u12 39 passed; u12_redaction+u11f 37 passed; u12f alone 22 passed); ruff clean; `autotester doctor` clean (`.work/doctor-u12f.txt`); `mutation-run.txt` now **25/25 killed** (cycle-0 mutant "future save time trusted" re-pointed to the `_ahead` check and extended; 8 new mutants: finiteness off, finiteness on expires only, skew 0, skew boundary inclusive, skew deletes, non-dict check off, forget after drop). Two parametrised cases are equivalent for some mutants (e.g. -inf `saved_at` is rejected by the age arithmetic alone) and are not claimed as kills.
