# Verdict - mongo-store-u12f (checker A)

**Cycle checked:** 0
**Verdict:** PASS (4 warnings, none blocking)
**Head checked:** 609e2349 on feat/mongo-store-u12f (cut from master 54db88c6). Contract: `qa/contracts/mongo-store.md` M38, M39, M40, M34, M8; unit U12 follow-up.
**Checker:** A, fresh context. Did not read any other checker's verdict for this unit. No `.env` value read or printed.

## Commands run (this worktree; fake Mongo only; <= 2 test files per call)

| Command | Result |
|---|---|
| `env -u ANTHROPIC_BASE_URL uv run pytest tests/test_session_store_u12f.py tests/test_session_store_u12.py -o addopts= -q` | 28 passed |
| same, `test_session_store_u12_redaction.py test_manual_login.py` | 11 passed |
| same, `test_multi_role_session.py test_role_session_port_login.py` | 13 passed |
| same, `test_entry_browser_reuse_lent.py test_credential_store_u11f.py` | 42 passed |
| same, `test_role_session_port.py test_credential_store_u11f.py` | 44 passed |
| `uv run ruff check src tests scripts` | All checks passed |
| `uv run autotester doctor > .work/doctor-u12f-chkA.txt` | exit 0, `doctor: clean` |
| `uv run python scripts/mutation_check.py qa/evidence/mongo-store-u12f/mutations.json --repo .` | `18/18 mutations killed` |
| own mutant run (18 mutants, file restored via `git checkout` after each; `git status` clean after) | 16 killed, 2 survived (see W-3) |
| own probes (scratch file outside the repo, `PYTHONPATH=tests`) | NaN cap bypass and partial-outage orphan reproduced (W-1, W-2) |

Files: profiles.py 263, multi_role_session.py 211, routes_project_edit.py 276, role_session_port.py 233, test_session_store_u12f.py 229, all <= 300; the doctor function-length rule is clean.

## Judged items

1. **A-W1 one client, gate rebuilt - verified.** `src/autotester/browser/profiles.py:77` calls `default_backend().rearm()`; `store/mongo_backend.py:246` sets `_redactor = None`, rebuilt lazily at `:63`. The test counts `client_factory` calls (1 across 3 saves) and then asserts a `put` of a value saved after the gate was built is refused with `StoreSecretRefused`. Own mutants "rearm removed" and "reset_default_backend() again" are both killed by it.
2. **B-W1 call-site tests - verified.** Own mutants: `manual_login.py:48` capture deleted, capture under account `t1`; `run_execution.py:178` restore deleted, restore under `t1`. All 4 killed by `test_a_manual_login_is_saved_under_the_project_account` and `test_a_normal_run_restores_the_project_account_login` (the latter seeds `t1` with a different value, so wrong-account is distinguishable).
3. **W2 save only after proof - verified.** `multi_role_session.py:206-211` `save_login`; `role_session_port.py:113-114` saves only `if proven`, inside the `try`, so an outage fails closed as `RoleLoginFailed`. The only src caller of `RoleSessions.sign_in` is `role_session_port.py:108` (grep of src and scripts), so no proven login loses its save. The edit to `test_session_store_u12_redaction.py` only ADDS two assertions (`docs == []` after sign_in, then `save_login` truthy); the original assertions are untouched, so it is stronger, not weaker. Own mutants: save regardless of proof, save deleted, wrong account in save_login, save_login no-op: all 4 killed. A failed or unproven login leaves the previous stored session byte-identical (test compares `repr(docs)`).
4. **W3 - verified, with W-1 and W-3 below.** `_readable :138-150` deletes (via `load_session :164-166`) a doc with non-numeric (bool excluded) times, a non-dict state, non-list parts, or a save time more than 300 s ahead; cap `min(expires, saved + MAX_AGE_S)` re-applied. `repo_redactor` reaches `stored_session_values :207-215` -> `session_values`, which reads through `_dicts`; a doc with `cookies=[7,{"value":None}]`, `localStorage=[5,...]` does not raise (test + own `_dicts` mutant killed). Judgement on the 300 s rule: acceptable. Writer and reader normally share one clock (single instance, DEPLOY.md M28), NTP error is milliseconds, and a false delete only forces a re-login (fails closed). Residual: a developer machine with a clock more than 5 minutes fast that shares the database with the host will lose each save. Deleting rather than ignoring is harsher than needed (W-3).
5. **W4 - verified, with W-2.** `ui/routes_project_edit.py:268-270` calls `forget_session` for each role account whose `username_key` or `password_key` is the undeclared key, beside `drop_credentials`. Own mutants wrong account and loop removed: killed. Not forgetting `_project` is right: that login is a human manual login (ML1, reads no secret) and is not tied to any SecretRef key; M37 deletes sessions with the SecretRef/account it is built on. The "restore the credential but not the session" path (a failed project save) is benign: the account is merely logged out and signs in again, as the manifest says.
6. **W5, W6 left open** as stated; not judged here. Live Chromium with the store on is untested (manifest says so).

## Findings

- **W-1 (Warning) NaN defeats the age cap.** `profiles.py:143-147`. `isinstance(n, (int, float))` accepts `float("nan")`. A stored `expires_at = NaN` makes `min(expires, saved + MAX_AGE_S)` return NaN (comparison false), and `NaN <= at` is False, so the doc is readable forever; a NaN `saved_at` with a far-future `expires_at` likewise. Reproduced: `load_session(now = NOW + 5 * MAX_AGE_S)` returned the state for both. Every finite tamper is correctly refused. Needs a write to the store (which already holds the plain cookies), so low severity. Fix: also require `math.isfinite`.
- **W-2 (Warning) the "outage raises before anything changed" claim holds only for the first store call.** `routes_project_edit.py:266-270`: `drop_credentials` runs, then `forget_session` runs OUTSIDE the `try` that restores the credential (`:271-275`). If the store fails between the two calls (`forget_session` raises), the credential value is gone while the project still declares the key. Reproduced (probe: `forget_session` patched to raise, credential docs 1 -> 0, declaration kept). Fix: do the `forget_session` loop BEFORE `drop_credentials` (a failure then changes nothing of value), or inside the `try`. The existing outage test only covers the whole store being down.
- **W-3 (Warning, test gaps) two own mutants survived.** `SKEW_S = 0` (the 300 s boundary and "within skew is accepted" are not pinned) and removal of `not isinstance(state, dict)` at `profiles.py:145` (no test stores a non-dict `state`, though the manifest lists it). Behaviour in code is correct; only the tests are thin. Also, a future-dated document is deleted rather than ignored; ignoring would not destroy a login on a clock fault.
- **W-4 (Info)** `qa/evidence/mongo-store-u12f/tests.txt` records the maker's runs; all five pairs were re-run by me with the same counts.

No Block. W-1 and W-2 are recommended for the next touch of these files, not conditions of this PASS; the maker should record them. The commit of this verdict is the only change made by this checker.
