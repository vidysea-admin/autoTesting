# Verdict - mongo-store-u6a (Checker A, functional / contract)

**Cycle checked:** 0
**Verdict:** PASS
**Unit:** U6a (`qa/contracts/mongo-store.md`, criteria M29 and M30, SQLite side). Branch `feat/mongo-store-u6a`, head `ef740beb` (merge `4a56cdab` of master `0f89becc`).
**Role:** Checker A (functional / contract). Checker B (adversarial security) is separate; U6a is dual-checked (D-100), so this is half of the PASS.
**Method:** fresh context; manifest claims re-run, not trusted; read-only toward `src/` and `tests/`; two test files per pytest call, one call at a time, `env -u ANTHROPIC_BASE_URL`; no `.env` value read or printed.

## Findings (numbered, none blocking)

1. **Every auth SQL path is behind the seam.** A grep for `sqlite3|execute|db.transaction|db.reading|db.connect` over `accounts.py groups.py sessions.py access.py policy.py config.py context.py loopback.py defaults.py passwords.py` returns nothing. The only auth modules with SQL are `auth/db.py` (connection, schema, seeding, `LastAdmin`, `ensure_an_admin_remains`, `admin_group_id`: unchanged, by design) and `auth/store_sqlite.py`. A repo-wide grep for `FROM|INTO|UPDATE` on `users|groups|memberships|sessions|group_permissions|project_grants` outside those two files hits only `stages/schedule_owner.py:35,40`, `ui/intake_gate_auth.py:37,42`, `stages/video_requests.py:128,139`: all U6c scope (unit table: schedule_owner, intake_gate_auth, video shares/links/requests/comments) and named in the manifest's scope boundary. Not a U6a defect.
2. **Public signatures unchanged.** AST comparison of public defs and classes, `4cc05569` vs head, for `accounts`, `groups`, `sessions`, `access`: nothing added or removed. Only change: five `access` helpers (`acts_as_admin`, `require_may_grant`, `require_admin`, `require_may_touch`, `require_may_regroup`) take `tx: AuthTx` instead of `conn: sqlite3.Connection`. A grep over `src tests scripts` finds no caller outside `access.py`, `accounts.py`, `groups.py`, so no external contract moves. Informational.
3. **claim_admin keeps D-109 single-transaction semantics.** `auth/accounts.py:81-94`: inside one `auth_store().transaction()` it runs `_claim_refusal(tx, tx.get_user(user_id))` (`:59-70`: disabled or missing user, Admin/CEO group missing, `admin_has_member`, configured first-admin address), then `tx.add_membership`, `tx.ensure_an_admin_remains()`, `_loaded`. `SqliteAuthStore.transaction` (`auth/store_sqlite.py:243`) wraps `db.transaction()`, which executes `BEGIN IMMEDIATE` (`auth/db.py:163`) and rolls back on any exception. Re-check and insert are one write-locked transaction, the same shape as the old inline SQL. `may_claim_admin` (`:73`) stays a read and `claim_admin` re-checks. Refusal strings are byte-identical to base (diff reviewed).
4. **Behaviour-neutral extraction, reviewed line by line.** Full diff of `accounts.py`, `groups.py`, `sessions.py`, `access.py` against `4cc05569`: statement text and order preserved in `store_sqlite.py`; check order of `update_group`, `delete_group`, `set_user_groups`, `approve_waiting`, `decline_waiting`, `bootstrap_admin` (`INSERT OR IGNORE` via `ignore_existing`) and `_update`'s rowcount to "no such account" are unchanged. With no store env set the factory returns the SQLite store only (`auth/store.py:91-94`, `test_factory_returns_the_sqlite_store`); the seam reads no env, so default behaviour is the pre-change behaviour.
5. **Minor deltas, all benign (informational).** (a) `authenticate` (`accounts.py:113`) now builds the `User` (one extra group-name query) via `login_record` before the password check; AU2 verify-once-on-every-path is unchanged and the hash is returned only by `login_record`. (b) `_loaded` (`accounts.py:39`) raises `AccountError("no such account")` where the base would have crashed on a `None` row; unreachable inside the transaction that just inserted. (c) `update_group` and `delete_group` read the group via `get_group` (a few more reads inside the same write transaction), same decisions. (d) `resource_for` uses `people.get(..., set())` instead of pre-seeding every relation: same result.
6. **M30 (SQLite side).** `User` and `Group` carry no hash field; the `AuthTx` methods mentioning a hash are exactly `login_record`, `insert_user`, `set_password_hash`, `enable_with_password_hash` (`test_only_login_paths_of_the_protocol_mention_a_hash`); `test_password_hash_never_leaves_the_store` is green.
7. **Design rules.** `auth/store.py` 94 lines, `store_sqlite.py` 246, `accounts.py` 259, `groups.py` 108, `sessions.py` 70, `access.py` 145 (all <= 300). Longest function across the six: `groups.py::update_group`, 27 lines (<= 50). Module docstrings state one job. `doctor` agrees.
8. **Net diff vs master is scoped.** `git diff 0f89becc HEAD --stat`: 13 files, only `auth/{access,accounts,groups,sessions,store,store_sqlite}.py`, `tests/test_auth_store_seam.py` (new), `docs/MAP.md`, `qa/evidence/mongo-store-u6a/*` and the manifest. `git diff 0f89becc HEAD --name-only -- tests` lists only the new test file, so no existing test is edited; the test-file changes visible against `4cc05569` (`test_ui_auth_own_origin.py` etc.) come from master's D-110, not this branch.
9. **Open for U6b, not U6a.** M29's Mongo two-thread admin-guard and unique-index tests; the Protocol's roughly 49 row-level methods leave U6b to implement CAS per method (manifest question 1). This checker does not require coarser operations; Checker B or U6b may revisit.

## Commands run and outputs

Run in `D:/autoTesting/.claude/worktrees/mongo-u6a` as `env -u ANTHROPIC_BASE_URL uv run pytest tests/<a>.py tests/<b>.py -o addopts= -p no:cacheprovider -q`:

```
test_auth_store_seam + test_ui_auth_claim_admin           21 passed
test_ui_auth_accounts + test_ui_auth_host_and_consent     26 passed
test_ui_auth_cli_and_limits + test_ui_auth_envkeys        29 passed
test_ui_auth_escalation + test_ui_auth_groups             54 passed
test_ui_auth_hardening + test_ui_auth_login               40 passed
test_ui_auth_own_origin + test_ui_origin_guard           205 passed
test_ui_auth_policy_table + test_ui_auth_refusal_audit     6 passed
test_ui_auth_surface + test_ui_auth_survivors             27 passed
test_account_generation + test_auth_loopback              15 passed
test_portal_requests + test_portal_share                  22 passed
test_schedule_owner_guard + test_intake_gate_auth         21 passed
test_tracker_auth + test_ui_signup_requests               37 passed
test_ui_signup_requests_f1 + test_notification_profile    31 passed
test_grant_bounds_caps + test_hosting_gaps                43 passed
test_inbox_scope + test_acceptance_isolation              17 passed
test_role_accounts_routes + test_authz_gate               31 passed
test_auth_deploy_files + test_crawl_guidance_seam         24 passed
```

17 calls, 0 failures. Flake check on the threaded invariants, `pytest tests/test_auth_store_seam.py -k m29`, three more runs: `3 passed` each time.

- `uv run ruff check --no-cache src tests scripts` gives `All checks passed!`
- `uv run autotester doctor` (output redirected to a file) exits 0 with `doctor: clean`; two advisory `decision-citation-known-disputed` warnings (D-087, non-blocking), unrelated.
- Static checks: AST public-signature diff (finding 2), file and function length script (finding 7), the greps cited in findings 1 and 2.

## Not done by this checker

The full suite was not run (machine memory rule). The 11-mutant mutation run was not repeated; the oracle plus the new seam tests were re-run instead, and `qa/evidence/mongo-store-u6a/mutation-run.txt` is the maker's record, not evidence for this verdict. The dual check needs Checker B's independent verdict before the maker may flip the manifest to `checked-PASS`.
