# Verdict - mongo-store-u12f (checker A)

**Cycle checked:** 1
**Verdict:** PASS (4 findings, none blocking: 2 test gaps, 1 wording, 1 pre-existing double fault)
**Head checked:** dee5bb71 on feat/mongo-store-u12f (cycle 1 on top of 4ade61de). Contract `qa/contracts/mongo-store.md` M38, M39, M40, M34, M8, M37.
**Checker:** A, fresh context. Did not read the other checker's verdict. No `.env` value read or printed. This seat's cycle-0 verdict is kept unchanged at the bottom ("Cycle 0 record").

## Commands run (this worktree, fake Mongo only, <= 2 test files per call)

| Command | Result |
|---|---|
| `env -u ANTHROPIC_BASE_URL uv run pytest tests/test_session_store_u12f.py tests/test_session_store_u12.py -o addopts= -q` | 39 passed |
| same, `test_session_store_u12_redaction.py test_credential_store_u11f.py` | 37 passed |
| same, `test_manual_login.py test_multi_role_session.py` | 13 passed |
| same, `test_role_session_port_login.py test_entry_browser_reuse_lent.py` | 16 passed |
| same, `test_role_session_port.py test_ui_project_edit.py` | 24 passed |
| `uv run ruff check src tests scripts` | All checks passed |
| `uv run autotester doctor > .work/doctor-u12f-chkA1.txt` | exit 0, last line `doctor: clean` |
| `uv run python scripts/mutation_check.py qa/evidence/mongo-store-u12f/mutations.json --repo . > .work/mut-chkA1.txt` | exit 0, `25/25 mutations killed`; `git status --short` empty afterwards |
| own probes, scratch files outside the repo (`PYTHONPATH=tests`) | 38 passed (non-finite matrix, ahead/malformed, injected failures at every store call); 4 more passed (non-numeric `saved_at`) |
| own mutants (12, each restored after its run, `git status` clean after) | 10 killed, 2 survived (F-2, F-3) |

Line counts: `browser/profiles.py` 272, `ui/routes_project_edit.py` 278, `tests/test_session_store_u12f.py` 287, all <= 300; doctor function-length rule clean.

## Judged items

1. **Non-finite times (C1) - verified.** `src/autotester/browser/profiles.py:150-152` rejects any `expires_at`/`saved_at` that is not an int/float, is a bool, or fails `math.isfinite`. Probe matrix on `load_session(now=NOW)` (all returned `None`): `saved NaN`, `expires NaN`, `expires -inf`, `saved -inf + expires inf`, `expires None`, `saved True` are all DELETED; `saved inf` (with finite or inf `expires`) returns `None` and the document is KEPT (see F-4). `repo_redactor().scrub` and `stored_session_values()` did not raise on any of these documents. The only readers of a stored document's times are `_ahead :139-143` and `_readable :146-157`; `load_session` is called only from `restore_session` (grep of `src`). `scope_state` and `session_values` never read document times. Own mutants "isfinite on `saved` only" and "NaN-only (inf allowed)": both killed. A cookie-level `expires = NaN` is saved (`_expired` is False for NaN) but the document cap still ends it: probe `load_session(now = NOW + 10 days)` returned `None`.
2. **undeclare_secret order (C2) - verified, with F-1 and F-4b.** `ui/routes_project_edit.py:266-275` runs the forget loop first, then `snapshot_credentials`, `drop_credentials`, and the unchanged restore `try` around `save_project`. Injected one failure at each call (credential `T1_P` stored and declared, sessions t1, t2; account t3 sharing the key in the first row):

   | Failure injected | Declared | Credential | Sessions left |
   |---|---|---|---|
   | 2nd `forget_session` (3 accounts use the key) | yes | kept | t2, t3 (t1 forgotten) |
   | `snapshot_credentials` | yes | kept | t2 (t1 forgotten) |
   | `drop_credentials` | yes | kept | t2 |
   | `save_project` | yes | restored | t2 |
   | `save_project`, then `restore_credentials` | yes | GONE | t2 |

   No row orphans a credential under an undeclared key. Rows 1-4 keep the declaration together with its credential. Row 5 is a double fault (F-4b).
3. **Skew (C3) - verified.** `profiles.py:139-143` `_ahead`, called at `:171-172` BEFORE `_readable`: `saved_at == at+300` loads, `at+301` returns `None` and the document stays (`test_the_skew_boundary_is_exactly_five_minutes`; my `>=` mutant was killed). A non-dict `state` (str, list, int, None) is deleted (`:154`; my mutant removing the check was killed). `_ahead` cannot pin a document for any reader whose clock catches up: probe `saved_at = NOW+1000, state="oops"` read at `NOW+800` is deleted; a real login `replace_one`s it by `_id` (`_put_session`), probe confirmed. A document with a far-future or `inf` `saved_at` is kept and never trusted (F-4a).
4. **No regression of cycle 0 - verified.** `_put_session :77` still calls `default_backend().rearm()` (one client across saves; the test counts `client_factory` calls and asserts the newly saved value is refused by the gate). `LiveRolePort.login` saves only after proof (`test_a_failed_login_never_replaces_a_good_stored_session`, `test_a_proven_login_is_saved`). The manual-login and normal-run call-site tests are in the green runs above.

## Findings

- **F-1 (Info, wording) the manifest's "other sessions untouched" is not exact.** When several accounts use the removed key and a later `forget_session` fails, the earlier accounts' sessions are already forgotten (probe row 1: t1 gone, t3 left). The credential and declaration are intact and a forgotten session only logs an account out, so this is benign. The in-code comment ("nothing else changed", `routes_project_edit.py:266-267`) has the same slack.
- **F-2 (Warning, test gap) own mutant E survived.** Removing the numeric guard in `_ahead` (`profiles.py:143`, leaving `saved > at + SKEW_S`) keeps all 39 tests green. In that state a stored `saved_at` of `None` or a string would raise `TypeError` out of `load_session`. The real code is correct (probe: `"x"`, `None`, `[1]`, `{}` all return `None` and are deleted); only the test is missing. Suggest adding those values to the non-finite parametrised test.
- **F-3 (Warning, test gap) own mutant K survived.** A `break` after the first forgotten account (`routes_project_edit.py:270`) is not caught: no test has two accounts sharing the removed key, so "every account built on that key" is pinned for one account only. The code is correct (probe row 1 forgot t1 and t3 and failed on the second call).
- **F-4 (Info, residuals) (a)** `_ahead` keeps a document whose `saved_at` is ahead even when it is malformed, expired by `expires_at`, or `inf`: never trusted, never restored, still masked by the redactor, replaced by the next real login and removed by the M37 lifecycle deletes, but not self-healing while the clock lags it. **(b)** Double fault `save_project` then `restore_credentials` (row 5): the declaration remains, the credential is gone, and the raised error is the restore error. That is the U11 no-transaction limit of `undeclare_secret`, not introduced and not claimed fixed by U12f.

No Block. W5 and W6 of the manifest remain open as stated; live Chromium with the store on is untested (manifest says so). F-2 and F-3 are recommended for the next touch of `tests/test_session_store_u12f.py`; the maker should record them. The commit of this verdict is the only change made by this checker.

---

# Cycle 0 record (this seat, unchanged)

## Verdict text of cycle 0

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
